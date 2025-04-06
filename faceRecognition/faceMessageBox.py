import cv2
import numpy as np
import os
import sys
import time
import json
import urllib.request
from config import cfg
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QMutex, QWaitCondition

from qfluentwidgets import (
    MessageBoxBase,
    SubtitleLabel,
    BodyLabel,
    PrimaryPushButton,
    PushButton,
    ProgressBar,
    InfoBar,
    InfoBarPosition,
    FluentIcon,
    Theme,
)

from Database import DatabaseManager


def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 非打包环境，使用当前路径
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class CameraThread(QThread):
    """摄像头捕获线程 - 负责流畅显示视频流"""

    frameReady = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.running = False
        self.mutex = QMutex()
        self.cap = None

    def start_capture(self):
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
        """停止摄像头捕获"""
        self.running = False
        time.sleep(0.5)

        if hasattr(self, "cap") and self.cap is not None:
            self.cap.release()
            self.cap = None
            cv2.destroyAllWindows()

        print("摄像头资源已释放")

    def run(self):
        """线程主循环"""
        while True:
            self.mutex.lock()
            if not self.running:
                self.mutex.unlock()
                break

            ret, frame = self.cap.read()
            if ret:
                self.frameReady.emit(frame.copy())

            self.mutex.unlock()
            self.msleep(20)

        # 清理资源
        self.mutex.lock()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.mutex.unlock()


class FaceProcessThread(QThread):
    """人脸处理线程 - 负责检测和处理人脸"""

    faceDetected = pyqtSignal(np.ndarray, tuple)
    faceProcessed = pyqtSignal(int, int)
    processingComplete = pyqtSignal()
    faceQualityFeedback = pyqtSignal(tuple, bool)

    def __init__(self, cascade_path, threshold, required_faces, user_id,
                 username):
        super().__init__()
        self.cascade_path = cascade_path

        try:
            cascade_file = resource_path(cascade_path)
            self.face_cascade = cv2.CascadeClassifier(cascade_file)

            if self.face_cascade.empty():
                # 尝试使用OpenCV内置路径
                print(f"使用路径 {cascade_file} 加载级联分类器失败，尝试内置路径...")
                cv2_path = os.path.join(os.path.dirname(cv2.__file__), "data")
                backup_path = os.path.join(
                    cv2_path, "haarcascade_frontalface_default.xml")
                self.face_cascade = cv2.CascadeClassifier(backup_path)

                if self.face_cascade.empty():
                    print(f"内置路径 {backup_path} 加载失败，尝试打包后路径...")
                    # 尝试打包后的标准位置
                    pkg_path = resource_path(
                        "cv2/data/haarcascade_frontalface_default.xml")
                    self.face_cascade = cv2.CascadeClassifier(pkg_path)
                    print(
                        f"打包路径 {pkg_path} 加载状态: {'成功' if not self.face_cascade.empty() else '失败'}"
                    )
        except Exception as e:
            print(f"加载级联分类器出错: {str(e)}")
            self.face_cascade = None

        self.threshold = threshold
        self.required_faces = required_faces
        self.user_id = user_id
        self.username = username
        self.face_images = []
        self.frame = None
        self.new_frame_available = False
        self.running = False
        self.face_count = 0
        self.mutex = QMutex()
        self.condition = QWaitCondition()

    def process_frame(self, frame):
        """接收新帧进行处理"""
        self.mutex.lock()
        self.frame = frame.copy()
        self.new_frame_available = True
        self.condition.wakeOne()
        self.mutex.unlock()

    def start_processing(self):
        """启动处理"""
        self.mutex.lock()
        self.face_count = 0
        self.running = True
        self.mutex.unlock()

        if not self.isRunning():
            self.start()

    def stop_processing(self):
        """停止处理"""
        self.mutex.lock()
        self.running = False
        self.condition.wakeOne()
        self.mutex.unlock()
        self.wait()

    def run(self):
        """线程主循环"""
        while True:
            self.mutex.lock()

            if not self.running:
                self.mutex.unlock()
                break

            if not self.new_frame_available:
                self.condition.wait(self.mutex)
                if not self.running:
                    self.mutex.unlock()
                    break

            # 获取当前帧进行处理
            current_frame = self.frame.copy()
            self.new_frame_available = False
            current_count = self.face_count
            self.mutex.unlock()

            gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray,
                                                       scaleFactor=1.1,
                                                       minNeighbors=5,
                                                       minSize=(30, 30))

            # 处理检测到的人脸
            for x, y, w, h in faces:
                face_area = w * h

                is_good_quality = face_area > self.threshold
                self.faceQualityFeedback.emit((x, y, w, h), is_good_quality)

                if is_good_quality and current_count < self.required_faces:
                    self.mutex.lock()
                    if self.face_count >= self.required_faces:
                        self.mutex.unlock()
                        continue

                    # 提取人脸
                    face_img = current_frame[y:y + h, x:x + w]

                    self.face_images.append(face_img.copy())

                    self.face_count += 1
                    current_count = self.face_count

                    self.faceDetected.emit(face_img, (x, y, w, h))

                    self.faceProcessed.emit(current_count, self.required_faces)

                    self.mutex.unlock()

                    self.msleep(500)
                    break

            # 检查是否完成所需数量
            if current_count >= self.required_faces:
                self.processingComplete.emit()
                break


class FaceRegistrationMessageBox(MessageBoxBase):
    registrationComplete = pyqtSignal(str)

    def __init__(self, user_id=None, username=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username

        self.face_cascade_path = resource_path(
            "cv2/data/haarcascade_frontalface_default.xml")

        # 面部捕获相关变量
        self.required_faces = 5
        self.face_quality_threshold = 2500

        self.camera_thread = CameraThread()
        self.camera_thread.frameReady.connect(self.update_frame)

        self.face_thread = FaceProcessThread(
            self.face_cascade_path,
            self.face_quality_threshold,
            self.required_faces,
            self.user_id,
            self.username,
        )
        self.face_thread.faceDetected.connect(self.on_face_detected)
        self.face_thread.faceProcessed.connect(self.on_face_processed)
        self.face_thread.processingComplete.connect(self.finish_registration)
        self.face_thread.faceQualityFeedback.connect(self.on_face_quality)

        self.display_frame = None
        self.faces_feedback = []

        self.initMessageBox()

        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.refresh_ui)
        self.extraction_thread = None

        self.face_update_timer = QTimer()
        self.face_update_timer.timeout.connect(self.update_face_feedback)
        self.face_update_timer.start(500)  # 每500毫秒更新一次

    def update_face_feedback(self):
        """定期更新人脸信息，清除过时的框"""
        if not hasattr(self,
                       "camera_thread") or not self.camera_thread.isRunning():
            return

        if len(self.faces_feedback) > 1:
            self.faces_feedback = self.faces_feedback[-1:]

    def initMessageBox(self):
        """初始化消息框UI"""
        self.titleLabel = SubtitleLabel("人脸识别录入")
        self.viewLayout.addWidget(self.titleLabel)

        self.descriptionLabel = BodyLabel("请注视摄像头，系统将自动捕获多张人脸图像用于识别")
        self.viewLayout.addWidget(self.descriptionLabel)
        self.viewLayout.addSpacing(10)

        # 创建视频显示容器和标签
        self.imageContainer = QWidget()
        self.imageContainer.setObjectName("faceImageContainer")
        self.imageContainer.setMinimumSize(640, 400)

        imageLayout = QVBoxLayout(self.imageContainer)
        imageLayout.setContentsMargins(0, 0, 0, 0)
        imageLayout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(640, 400)
        self.image_label.setText("准备开始捕获人脸")
        imageLayout.addWidget(self.image_label)
        if cfg.get(cfg.themeMode) == Theme.DARK:
            self.image_label.setStyleSheet("""
                background-color: #2b2b2b; 
                color: #ffffff;
                font-size: 16px;
                border-radius: 6px;
            """)
        else:
            self.image_label.setStyleSheet("font-size: 16px; color: #666;")

        self.viewLayout.addWidget(self.imageContainer)
        self.viewLayout.addSpacing(10)

        progressLayout = QHBoxLayout()
        self.progress_label = BodyLabel("人脸捕获进度:")
        progressLayout.addWidget(self.progress_label)

        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, self.required_faces)
        self.progress_bar.setValue(0)
        progressLayout.addWidget(self.progress_bar)

        self.viewLayout.addLayout(progressLayout)
        self.viewLayout.addSpacing(10)

        self.start_button = PrimaryPushButton("开始人脸采集")
        self.start_button.setIcon(FluentIcon.CAMERA)
        self.start_button.clicked.connect(self.start_capture)

        self.cancel_button = PushButton("取消")
        self.cancel_button.clicked.connect(self.close)

        self.hideYesButton()
        self.hideCancelButton()
        self.buttonLayout.addWidget(self.start_button)
        self.buttonLayout.addWidget(self.cancel_button)

    def start_capture(self):
        """开始捕获人脸"""
        self.progress_bar.setValue(0)
        self.progress_label.setText("人脸捕获进度: 0/" + str(self.required_faces))

        InfoBar.info(
            title="处理中",
            content="正在提取人脸特征，请稍候...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

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

        self.start_button.setText("停止采集")
        self.start_button.setIcon(FluentIcon.PAUSE)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.stop_capture)

        self.face_thread.start_processing()

        self.ui_timer.start(33)

        self.face_update_timer.start(500)

    def stop_capture(self):
        """停止捕获人脸"""
        if self.ui_timer.isActive():
            self.ui_timer.stop()

        if self.face_update_timer.isActive():
            self.face_update_timer.stop()

        self.faces_feedback = []

        # 停止人脸处理线程
        if hasattr(self, "face_thread") and self.face_thread.isRunning():
            self.face_thread.stop_processing()
            self.face_thread.wait(2000)
            if self.face_thread.isRunning():
                self.face_thread.terminate()
                self.face_thread.wait()

        # 停止摄像头线程
        if hasattr(self, "camera_thread") and self.camera_thread.isRunning():
            self.camera_thread.stop_capture()
            self.camera_thread.wait(2000)
            if self.camera_thread.isRunning():
                self.camera_thread.terminate()
                self.camera_thread.wait()

        self.start_button.setText("开始人脸采集")
        self.start_button.setIcon(FluentIcon.CAMERA)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.start_capture)

        self.image_label.clear()
        self.image_label.setText("准备开始捕获人脸")

        if cfg.get(cfg.themeMode) == Theme.DARK:
            self.image_label.setStyleSheet("""
                background-color: #2b2b2b; 
                color: #ffffff;
                font-size: 16px;
                border-radius: 6px;
            """)
        else:
            self.image_label.setStyleSheet("font-size: 16px; color: #666;")

    def update_frame(self, frame):
        """接收摄像头帧并更新显示缓存"""
        self.display_frame = frame.copy()
        self.face_thread.process_frame(frame)

    def on_face_detected(self, face_img, coords):
        pass

    def on_face_processed(self, current_count, total_count):
        """更新人脸处理进度"""
        self.progress_bar.setValue(current_count)
        self.progress_label.setText(f"人脸捕获进度: {current_count}/{total_count}")

    def on_face_quality(self, coords, is_good_quality):
        """更新人脸质量反馈"""
        x, y, w, h = coords
        self.faces_feedback.append((coords, is_good_quality))
        if len(self.faces_feedback) > 10:
            self.faces_feedback = self.faces_feedback[-10:]

    def refresh_ui(self):
        """刷新UI显示"""
        if self.display_frame is None:
            return

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

        self.display_image(display_copy)

    def display_image(self, img):
        """在QLabel中显示OpenCV图像"""
        try:
            rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_image.data, w, h, bytes_per_line,
                             QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)

            # 调整图像大小以适应标签
            pixmap = pixmap.scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.image_label.setPixmap(pixmap)
        except Exception as e:
            print(f"显示图像时出错: {str(e)}")

            if cfg.get(cfg.themeMode) == Theme.DARK:
                self.image_label.setStyleSheet("""
                    background-color: #2b2b2b; 
                    color: #ffffff;
                    font-size: 16px;
                    border-radius: 6px;
                """)
            else:
                self.image_label.setStyleSheet("font-size: 16px; color: #666;")

    def finish_registration(self):
        """完成人脸注册流程，使用OpenCV DNN提取特征"""
        self.stop_capture()
        self.extraction_thread = FeatureExtractionThread(
            face_images=self.face_thread.face_images,
            user_id=self.user_id,
            username=self.username,
            face_count=self.face_thread.face_count,
        )
        self.extraction_thread.extractionComplete.connect(
            self.on_extraction_complete)
        self.extraction_thread.extractionFailed.connect(
            self.on_extraction_failed)

        InfoBar.info(
            title="处理中",
            content="正在提取人脸特征，请稍候...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

        self.extraction_thread.start()

    def on_extraction_complete(self, feature_data):
        """特征提取完成回调"""
        InfoBar.success(
            title="注册成功",
            content=f"已成功注册您的人脸数据，可用于后续登录",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

        self.registrationComplete.emit(feature_data)

    def on_extraction_failed(self, error_message):
        """特征提取失败回调"""
        InfoBar.error(
            title="错误",
            content=f"处理人脸特征失败: {error_message}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self,
        )

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        if hasattr(self, "camera_thread") and self.camera_thread.isRunning():
            self.stop_capture()

        cv2.destroyAllWindows()

        super().closeEvent(event)


class FeatureExtractionThread(QThread):
    """特征提取线程 - 处理提取的人脸特征"""

    extractionComplete = pyqtSignal(str)
    extractionFailed = pyqtSignal(str)

    def __init__(self, face_images, user_id, username, face_count):
        super().__init__()
        self.face_images = face_images
        self.user_id = user_id
        self.username = username
        self.face_count = face_count
        self.running = True

    def terminate(self):
        """安全终止线程"""
        self.running = False
        super().terminate()

    def run(self):
        """线程主函数"""
        try:
            model_file = resource_path(
                "faceRecognition/models/openface_nn4.small2.v1.t7")

            if not os.path.exists(model_file):
                model_dir = os.path.dirname(model_file)
                if not os.path.exists(model_dir):
                    os.makedirs(model_dir)
                url = "https://github.com/pyannote/pyannote-data/raw/master/openface.nn4.small2.v1.t7"
                urllib.request.urlretrieve(url, model_file)

            face_net = cv2.dnn.readNetFromTorch(model_file)

            face_features = []

            for image in self.face_images:
                if not self.running:
                    return

                # 检查图像有效性
                if image is None or image.size == 0:
                    continue

                blob = cv2.dnn.blobFromImage(image,
                                             1.0 / 255, (96, 96), (0, 0, 0),
                                             swapRB=True,
                                             crop=False)

                face_net.setInput(blob)
                feature_vector = face_net.forward()

                # 添加到特征列表
                face_features.append(feature_vector.flatten().tolist())

            face_data_json = json.dumps(face_features)

            if not self.running:
                return

            db = DatabaseManager()
            db.update_user(self.user_id, face_data=face_data_json)
            db.close()

            self.face_images = []

            self.extractionComplete.emit("face_features_stored")

        except Exception as e:
            self.extractionFailed.emit(str(e))
