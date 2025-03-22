import cv2
import numpy as np
import json
import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QMutex

from qfluentwidgets import (
    SubtitleLabel,
    BodyLabel,
    PrimaryPushButton,
    TransparentPushButton,
    StateToolTip,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    isDarkTheme,
    setTheme,
    Theme,
)

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from Database import DatabaseManager


class CameraThread(QThread):
    """摄像头捕获线程 - 负责流畅显示视频流"""

    frameReady = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.running = False
        self.mutex = QMutex()
        self.cap = None

    def start_capture(self):
        """启动捕获"""
        self.mutex.lock()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.mutex.unlock()
            return False
        self.running = True
        self.mutex.unlock()

        if not self.isRunning():
            self.start()
        return True

    def stop_capture(self):
        """停止捕获"""
        self.mutex.lock()
        self.running = False
        self.mutex.unlock()
        self.wait()  # 等待线程结束

    def run(self):
        """线程主循环"""
        while True:
            self.mutex.lock()
            if not self.running:
                self.mutex.unlock()
                break

            ret, frame = self.cap.read()
            if ret:
                self.frameReady.emit(frame.copy())  # 发送帧到主线程

            self.mutex.unlock()
            # 控制帧率
            self.msleep(20)  # 大约50FPS

        # 清理资源
        self.mutex.lock()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.mutex.unlock()


class FaceVerificationThread(QThread):
    """人脸验证线程 - 负责检测和验证人脸"""

    # 信号定义
    faceDetected = pyqtSignal(np.ndarray, tuple)  # 人脸图像和坐标
    faceQualityFeedback = pyqtSignal(tuple, bool)  # 人脸坐标和质量
    verificationResult = pyqtSignal(bool, int, str)  # 验证结果, 用户ID, 用户名

    def __init__(self):
        super().__init__()
        self.cascade_path = (
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.face_cascade = cv2.CascadeClassifier(self.cascade_path)
        self.threshold = 2500  # 人脸质量阈值
        self.match_threshold = 0.6  # 特征匹配阈值

        # 线程控制
        self.frame = None
        self.new_frame_available = False
        self.running = False

        # 用户数据
        self.users_data = []  # 存储所有用户的人脸特征

        # 线程同步
        self.mutex = QMutex()

        # 初始化模型
        self.model_file = "faceRecognition/models/openface_nn4.small2.v1.t7"
        self.ensure_model_exists()

        # 加载用户数据
        self.load_users_data()

    def ensure_model_exists(self):
        """确保模型文件存在"""
        if not os.path.exists(self.model_file):
            model_dir = os.path.dirname(self.model_file)
            if not os.path.exists(model_dir):
                os.makedirs(model_dir)
            # 通知用户需要下载模型（实际应用中需要实现）
            print("需要下载人脸识别模型，这可能需要一些时间...")

    def load_users_data(self):
        """从数据库加载所有用户的人脸特征"""
        try:
            db = DatabaseManager()
            # 获取所有有人脸数据的用户
            users = db.get_users_with_face_data()
            db.close()

            if not users:
                print("数据库中没有用户人脸数据")
                return

            self.users_data = users
            print(f"已加载 {len(users)} 个用户的人脸数据")
        except Exception as e:
            print(f"加载用户数据出错: {e}")

    def process_frame(self, frame):
        """接收新帧进行处理"""
        self.mutex.lock()
        self.frame = frame.copy()
        self.new_frame_available = True
        self.mutex.unlock()

    def start_verification(self):
        """启动验证"""
        self.mutex.lock()
        self.running = True
        self.mutex.unlock()

        if not self.isRunning():
            self.start()

    def stop_verification(self):
        """停止验证"""
        self.mutex.lock()
        self.running = False
        self.mutex.unlock()
        self.wait()  # 等待线程结束

    def verify_face(self, face_image):
        """验证人脸是否匹配数据库中的用户"""
        # 加载DNN模型
        face_net = cv2.dnn.readNetFromTorch(self.model_file)

        # 预处理图像
        blob = cv2.dnn.blobFromImage(
            face_image, 1.0 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False
        )

        # 获取特征
        face_net.setInput(blob)
        current_feature = face_net.forward().flatten()

        # 与数据库中的所有用户特征比对
        best_match = None
        min_distance = float("inf")

        for user in self.users_data:
            try:
                user_id = user["id"]
                username = user["username"]
                face_data = user["face_data"]

                # 解析JSON特征数据
                stored_features = json.loads(face_data)

                # 计算与每个特征的距离
                for feature in stored_features:
                    distance = np.linalg.norm(current_feature - np.array(feature))
                    if distance < min_distance:
                        min_distance = distance
                        best_match = (user_id, username)
            except Exception as e:
                print(f"处理用户 {user.get('username', 'unknown')} 的特征时出错: {e}")

        # 判断是否匹配（阈值可调）
        if min_distance < self.match_threshold and best_match:
            return True, best_match[0], best_match[1], min_distance
        else:
            return False, None, None, min_distance

    def run(self):
        """线程主循环"""
        while True:
            self.mutex.lock()

            # 检查是否停止
            if not self.running:
                self.mutex.unlock()
                break

            # 检查是否有新帧
            if not self.new_frame_available:
                self.mutex.unlock()
                self.msleep(20)  # 短暂休眠避免CPU占用过高
                continue

            # 获取当前帧进行处理
            current_frame = self.frame.copy()
            self.new_frame_available = False
            self.mutex.unlock()

            # 执行人脸检测
            gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            # 处理检测到的人脸
            for x, y, w, h in faces:
                face_area = w * h

                # 发送人脸质量反馈
                is_good_quality = face_area > self.threshold
                self.faceQualityFeedback.emit((x, y, w, h), is_good_quality)

                # 只处理高质量人脸
                if is_good_quality:
                    # 提取人脸
                    face_img = current_frame[y : y + h, x : x + w]

                    # 发送人脸区域信号
                    self.faceDetected.emit(face_img, (x, y, w, h))

                    # 验证人脸
                    is_match, user_id, username, distance = self.verify_face(face_img)

                    if is_match:
                        self.verificationResult.emit(True, user_id, username)
                        # 成功验证后停止线程
                        self.stop_verification()
                        return

                    # 短暂暂停，避免频繁验证
                    self.msleep(500)
                    break  # 每帧只处理一个最佳人脸


class FaceLoginInterface(QWidget):
    """人脸登录界面"""

    # 定义登录成功信号
    loginSuccessful = pyqtSignal(dict)  # 用户ID和用户名
    backClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 摄像头和验证线程
        self.camera_thread = CameraThread()
        self.camera_thread.frameReady.connect(self.update_frame)

        self.verification_thread = FaceVerificationThread()
        self.verification_thread.faceDetected.connect(self.on_face_detected)
        self.verification_thread.faceQualityFeedback.connect(self.on_face_quality)
        self.verification_thread.verificationResult.connect(self.on_verification_result)

        # 显示帧和标记临时存储
        self.display_frame = None
        self.faces_feedback = []

        # UI定时器
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.refresh_ui)

        # 人脸更新定时器
        self.face_update_timer = QTimer()
        self.face_update_timer.timeout.connect(self.update_face_feedback)

        # 初始化UI
        self.setup_ui()

        # 状态提示
        self.state_tooltip = None

    def setup_ui(self):
        """设置UI界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)

        # 标题
        title_label = SubtitleLabel("人脸登录")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 说明文字
        desc_label = BodyLabel("请将面部对准摄像头，系统将自动进行人脸验证")
        desc_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc_label)
        main_layout.addSpacing(10)

        # 摄像头画面容器
        self.camera_container = QFrame()
        self.camera_container.setObjectName("cameraContainer")
        self.camera_container.setStyleSheet(
            """
            #cameraContainer {
                background-color: #F5F5F5;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """
        )
        self.camera_container.setMinimumSize(480, 360)

        camera_layout = QVBoxLayout(self.camera_container)
        camera_layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("准备启动摄像头")
        self.image_label.setStyleSheet("font-size: 16px; color: #666;")
        camera_layout.addWidget(self.image_label)

        main_layout.addWidget(self.camera_container)
        main_layout.addSpacing(20)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.back_button = TransparentPushButton("返回")
        self.back_button.setIcon(FIF.RETURN)
        self.back_button.clicked.connect(self.on_back_clicked)

        self.start_button = PrimaryPushButton("开始人脸识别")
        self.start_button.setIcon(FIF.CAMERA)
        self.start_button.clicked.connect(self.start_capture)

        button_layout.addWidget(self.back_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.start_button)

        main_layout.addLayout(button_layout)

        # 设置窗口大小策略
        self.setMinimumSize(600, 550)

    def start_capture(self):
        """开始捕获和验证"""
        # 清空状态
        self.faces_feedback = []

        # 显示处理提示
        # InfoBar.info(
        #     title="准备中",
        #     content="正在启动摄像头，请稍候...",
        #     orient=Qt.Horizontal,
        #     isClosable=True,
        #     position=InfoBarPosition.TOP,
        #     duration=3000,
        #     parent=self
        # )

        # 启动摄像头线程
        if not self.camera_thread.start_capture():
            InfoBar.error(
                title="错误",
                content="无法连接到摄像头!",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
            return

        # 更新按钮状态
        self.start_button.setText("停止识别")
        self.start_button.setIcon(FIF.PAUSE)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.stop_capture)

        # 启动验证线程
        self.verification_thread.start_verification()

        # 启动UI刷新定时器
        self.ui_timer.start(33)  # 约30FPS

        # 启动人脸信息更新定时器
        self.face_update_timer.start(500)

        # 显示状态提示
        self.state_tooltip = StateToolTip(
            "识别中", "正在进行人脸识别，请注视摄像头...", self
        )
        # 将提示移到右上角
        self.state_tooltip.move(self.width() - self.state_tooltip.width() - 20, 20)
        self.state_tooltip.show()

    def stop_capture(self):
        """停止捕获和验证"""
        # 停止定时器
        if self.ui_timer.isActive():
            self.ui_timer.stop()

        if self.face_update_timer.isActive():
            self.face_update_timer.stop()

        # 停止工作线程
        if hasattr(self, "camera_thread") and self.camera_thread.isRunning():
            self.camera_thread.stop_capture()

        if (
            hasattr(self, "verification_thread")
            and self.verification_thread.isRunning()
        ):
            self.verification_thread.stop_verification()

        # 恢复按钮状态
        self.start_button.setText("开始人脸识别")
        self.start_button.setIcon(FIF.CAMERA)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.start_capture)

        # 清除图像
        self.image_label.clear()
        self.image_label.setText("准备启动摄像头")
        self.image_label.setStyleSheet("font-size: 16px; color: #666;")

        # 关闭状态提示
        if self.state_tooltip:
            self.state_tooltip.setState(True)
            self.state_tooltip.setContent("识别已停止")
            self.state_tooltip = None

    def update_frame(self, frame):
        """接收摄像头帧并更新显示缓存"""
        self.display_frame = frame.copy()

        # 将帧发送到验证线程
        self.verification_thread.process_frame(frame)

    def on_face_detected(self, face_img, coords):
        """处理检测到的人脸"""
        # 这里可以添加额外处理，如显示特写等
        pass

    def on_face_quality(self, coords, is_good_quality):
        """更新人脸质量反馈"""
        # 存储人脸框信息和质量，用于UI刷新
        self.faces_feedback.append((coords, is_good_quality))

    def update_face_feedback(self):
        """定期更新人脸信息，清除过时的框"""
        # 如果摄像头未运行，不需要清除
        if not hasattr(self, "camera_thread") or not self.camera_thread.isRunning():
            return

        # 仅保留最近的几个人脸信息
        if len(self.faces_feedback) > 1:
            self.faces_feedback = self.faces_feedback[-1:]

    def refresh_ui(self):
        """刷新UI显示"""
        if self.display_frame is None:
            return

        # 复制帧用于显示
        display_copy = self.display_frame.copy()

        # 绘制所有人脸框
        for coords, is_good_quality in self.faces_feedback:
            x, y, w, h = coords
            color = (0, 255, 0) if is_good_quality else (0, 0, 255)
            cv2.rectangle(display_copy, (x, y), (x + w, y + h), color, 2)

            if not is_good_quality:
                cv2.putText(
                    display_copy,
                    "靠近一点",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    2,
                )

        # 显示图像
        self.display_image(display_copy)

    def display_image(self, img):
        """在QLabel中显示OpenCV图像"""
        try:
            rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)

            # 调整图像大小以适应标签
            pixmap = pixmap.scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

            self.image_label.setPixmap(pixmap)
            self.image_label.setStyleSheet("")
        except Exception as e:
            print(f"显示图像时出错: {str(e)}")

    def on_verification_result(self, success, user_id, username):
        """处理验证结果"""
        # 停止捕获
        self.stop_capture()

        if success:
            self.verified_user_id = user_id
            self.verified_username = username
            # 显示成功消息
            InfoBar.success(
                title="验证成功",
                content=f"欢迎回来，{username}!",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

            # 创建一个延时器，2秒后触发登录信号
            QTimer.singleShot(2000, self.emit_login_signal)

        else:
            # 显示失败消息
            InfoBar.error(
                title="验证失败",
                content="未能识别您的身份，请重试或使用其他登录方式",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def emit_login_signal(self):
        """发送登录成功信号"""
        user_data = {"id": self.verified_user_id, "username": self.verified_username}
        self.loginSuccessful.emit(user_data)

    def on_back_clicked(self):
        """返回按钮点击处理"""
        self.stop_capture()
        self.backClicked.emit()

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.stop_capture()
        super().closeEvent(event)


# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置暗色主题
    # setTheme(Theme.DARK)
    window = FaceLoginInterface()
    window.show()
    sys.exit(app.exec_())
