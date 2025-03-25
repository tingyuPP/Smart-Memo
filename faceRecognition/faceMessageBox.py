import cv2
import numpy as np
import os
import sys
import time
import json
import urllib.request
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QMutex, QWaitCondition

from qfluentwidgets import (MessageBoxBase, SubtitleLabel, BodyLabel, PrimaryPushButton, 
                           PushButton, ProgressBar, InfoBar, InfoBarPosition, FluentIcon)

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
            self.msleep(20)  # 大约50FPS，适当调整可提高或降低帧率
        
        # 清理资源
        self.mutex.lock()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.mutex.unlock()


class FaceProcessThread(QThread):
    """人脸处理线程 - 负责检测和处理人脸"""
    faceDetected = pyqtSignal(np.ndarray, tuple)  # 发送人脸区域和坐标
    faceProcessed = pyqtSignal(int, int)  # 发送当前处理的人脸计数和总数
    processingComplete = pyqtSignal()  # 处理完成信号
    faceQualityFeedback = pyqtSignal(tuple, bool)  # 发送人脸坐标和质量反馈
    
    def __init__(self, cascade_path, threshold, required_faces, user_id, username):
        super().__init__()
        self.cascade_path = cascade_path
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.threshold = threshold
        self.required_faces = required_faces
        self.user_id = user_id
        self.username = username
        
        # self.face_folder = Path("face_data")
        # self.face_folder.mkdir(exist_ok=True)

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
        self.condition.wakeOne()  # 唤醒等待的线程
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
        self.condition.wakeOne()  # 唤醒等待的线程
        self.mutex.unlock()
        self.wait()  # 等待线程结束
    
    def run(self):
        """线程主循环"""
        while True:
            self.mutex.lock()
            
            # 检查是否停止
            if not self.running:
                self.mutex.unlock()
                break
            
            # 等待新帧
            if not self.new_frame_available:
                self.condition.wait(self.mutex)
                if not self.running:  # 再次检查，可能被唤醒是为了停止
                    self.mutex.unlock()
                    break
            
            # 获取当前帧进行处理
            current_frame = self.frame.copy()
            self.new_frame_available = False
            current_count = self.face_count
            self.mutex.unlock()
            
            # 执行人脸检测（耗时操作）
            gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            
            # 处理检测到的人脸
            for (x, y, w, h) in faces:
                face_area = w * h
                
                # 发送人脸质量反馈
                is_good_quality = face_area > self.threshold
                self.faceQualityFeedback.emit((x, y, w, h), is_good_quality)
                
                # 只处理高质量人脸
                if is_good_quality and current_count < self.required_faces:
                    self.mutex.lock()
                    if self.face_count >= self.required_faces:  # 可能其他人脸已经处理完成
                        self.mutex.unlock()
                        continue
                        
                    # 提取人脸
                    face_img = current_frame[y:y+h, x:x+w]
                    
                    self.face_images.append(face_img.copy())
                    
                    # 更新计数
                    self.face_count += 1
                    current_count = self.face_count
                    
                    # 发送人脸区域信号
                    self.faceDetected.emit(face_img, (x, y, w, h))
                    
                    # 发送进度更新
                    self.faceProcessed.emit(current_count, self.required_faces)
                    
                    self.mutex.unlock()
                    
                    # 短暂暂停，避免快速连续捕获同一个人脸
                    self.msleep(500)
                    break  # 每帧只处理一个最佳人脸
            
            # 检查是否完成所需数量
            if current_count >= self.required_faces:
                self.processingComplete.emit()
                break


class FaceRegistrationMessageBox(MessageBoxBase):
    """人脸注册消息框 - Fluent设计风格"""
    
    # 定义注册成功信号
    registrationComplete = pyqtSignal(str)
    
    def __init__(self, user_id=None, username=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        
        # 配置参数
        self.face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        # self.face_folder = Path("face_data")
        # self.face_folder.mkdir(exist_ok=True)
        
        # 面部捕获相关变量
        self.required_faces = 5  # 需要捕获的人脸数量
        self.face_quality_threshold = 2500  # 人脸质量阈值（面积）
        
        # 创建工作线程
        self.camera_thread = CameraThread()
        self.camera_thread.frameReady.connect(self.update_frame)
        
        self.face_thread = FaceProcessThread(
            self.face_cascade_path, 
            self.face_quality_threshold,
            self.required_faces,
            self.user_id,
            self.username
        )
        self.face_thread.faceDetected.connect(self.on_face_detected)
        self.face_thread.faceProcessed.connect(self.on_face_processed)
        self.face_thread.processingComplete.connect(self.finish_registration)
        self.face_thread.faceQualityFeedback.connect(self.on_face_quality)
        
        # 显示帧和标记临时存储
        self.display_frame = None
        self.faces_feedback = []
        
        # 初始化UI
        self.initMessageBox()
        
        # 定时更新UI的计时器(仅用于刷新显示，不做处理)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.refresh_ui)
        self.extraction_thread = None

        # 添加人脸信息更新计时器
        self.face_update_timer = QTimer()
        self.face_update_timer.timeout.connect(self.update_face_feedback)
        self.face_update_timer.start(500)  # 每500毫秒更新一次
    
    def update_face_feedback(self):
        """定期更新人脸信息，清除过时的框"""
        # 如果摄像头未运行，不需要清除
        if not hasattr(self, 'camera_thread') or not self.camera_thread.isRunning():
            return
            
        # 仅保留最近的几个人脸信息
        if len(self.faces_feedback) > 1:  # 保留最新的1个人脸信息
            self.faces_feedback = self.faces_feedback[-1:]
        
    def initMessageBox(self):
        """初始化消息框UI"""
        # 设置标题
        self.titleLabel = SubtitleLabel("人脸识别录入")
        self.viewLayout.addWidget(self.titleLabel)
        
        # 添加说明文字
        self.descriptionLabel = BodyLabel("请注视摄像头，系统将自动捕获多张人脸图像用于识别")
        self.viewLayout.addWidget(self.descriptionLabel)
        self.viewLayout.addSpacing(10)
        
        # 创建视频显示容器和标签
        self.imageContainer = QWidget()
        self.imageContainer.setStyleSheet("background-color: #F5F5F5; border-radius: 8px;")
        self.imageContainer.setMinimumSize(640, 400)
        imageLayout = QVBoxLayout(self.imageContainer)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(640, 400)
        self.image_label.setText("准备开始捕获人脸")
        self.image_label.setStyleSheet("font-size: 16px; color: #666;")
        imageLayout.addWidget(self.image_label)
        
        self.viewLayout.addWidget(self.imageContainer)
        self.viewLayout.addSpacing(10)
        
        # 添加进度条和标签
        progressLayout = QHBoxLayout()
        self.progress_label = BodyLabel("人脸捕获进度:")
        progressLayout.addWidget(self.progress_label)
        
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, self.required_faces)
        self.progress_bar.setValue(0)
        progressLayout.addWidget(self.progress_bar)
        
        self.viewLayout.addLayout(progressLayout)
        self.viewLayout.addSpacing(10)
        
        # 创建按钮并设置
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
        # 重置计数和进度条
        self.progress_bar.setValue(0)
        self.progress_label.setText("人脸捕获进度: 0/" + str(self.required_faces))

        # 显示进度提示
        InfoBar.info(
            title="处理中",
            content="正在提取人脸特征，请稍候...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        
        # 启动摄像头线程
        if not self.camera_thread.start_capture():
            InfoBar.error(
                title="错误",
                content="无法连接到摄像头!",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
            
        # 更新按钮状态和文本
        self.start_button.setText("停止采集")
        self.start_button.setIcon(FluentIcon.PAUSE)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.stop_capture)
        
        # 启动人脸处理线程
        self.face_thread.start_processing()
        
        # 启动UI刷新定时器
        self.ui_timer.start(33)  # 约30FPS的刷新率

        # 启动人脸信息更新计时器
        self.face_update_timer.start(500)
        
    def stop_capture(self):
        """停止捕获人脸"""
        # 停止UI刷新定时器
        if self.ui_timer.isActive():
            self.ui_timer.stop()
        
        # 停止人脸信息更新计时器
        if self.face_update_timer.isActive():
            self.face_update_timer.stop()
            
        # 停止工作线程
        if self.camera_thread.isRunning():
            self.camera_thread.stop_capture()
            self.camera_thread.wait()  # 确保等待线程完全停止
            
        if self.face_thread.isRunning():
            self.face_thread.stop_processing()
            self.face_thread.wait()  # 确保等待线程完全停止
        
        # 恢复按钮状态
        self.start_button.setText("开始人脸采集")
        self.start_button.setIcon(FluentIcon.CAMERA)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.start_capture)
        
        # 清除图像
        self.image_label.clear()
        self.image_label.setText("准备开始捕获人脸")
        self.image_label.setStyleSheet("font-size: 16px; color: #666;")
        
    def update_frame(self, frame):
        """接收摄像头帧并更新显示缓存"""
        self.display_frame = frame.copy()
        
        # 将帧发送到人脸处理线程
        self.face_thread.process_frame(frame)
        
    def on_face_detected(self, face_img, coords):
        """处理检测到的人脸"""
        # 这里可以添加额外处理，如显示特写等
        pass
        
    def on_face_processed(self, current_count, total_count):
        """更新人脸处理进度"""
        # 在主线程更新UI
        self.progress_bar.setValue(current_count)
        self.progress_label.setText(f"人脸捕获进度: {current_count}/{total_count}")
        
    def on_face_quality(self, coords, is_good_quality):
        """更新人脸质量反馈"""
        x, y, w, h = coords
        # 存储人脸框信息和质量，用于UI刷新
        self.faces_feedback.append((coords, is_good_quality))
        # 控制列表大小，防止无限增长
        if len(self.faces_feedback) > 10:
            self.faces_feedback = self.faces_feedback[-10:]
            
    def refresh_ui(self):
        """刷新UI显示"""
        if self.display_frame is None:
            return
            
        # 复制帧用于显示
        display_copy = self.display_frame.copy()
        
        # 绘制所有人脸框
        for (coords, is_good_quality) in self.faces_feedback:
            x, y, w, h = coords
            color = (0, 255, 0) if is_good_quality else (0, 0, 255)
            cv2.rectangle(display_copy, (x, y), (x+w, y+h), color, 2)
            
            if not is_good_quality:
                cv2.putText(display_copy, "靠近一点", (x, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # 不再清除人脸框信息
        # self.faces_feedback = []  # 删除这一行
        
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
            pixmap = pixmap.scaled(self.image_label.width(), self.image_label.height(), 
                                  Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                  
            self.image_label.setPixmap(pixmap)
            self.image_label.setStyleSheet("")
        except Exception as e:
            print(f"显示图像时出错: {str(e)}")
    
    def finish_registration(self):
        """完成人脸注册流程，使用OpenCV DNN提取特征"""
        # 停止捕获
        self.stop_capture()

        # 创建特征提取线程 - 传递内存中的图像而不是文件路径
        self.extraction_thread = FeatureExtractionThread(
            face_images=self.face_thread.face_images,  # 传递图像列表
            user_id=self.user_id, 
            username=self.username,
            face_count=self.face_thread.face_count
        )
        self.extraction_thread.extractionComplete.connect(self.on_extraction_complete)
        self.extraction_thread.extractionFailed.connect(self.on_extraction_failed)
        
        # 显示进度提示
        InfoBar.info(
            title="处理中",
            content="正在提取人脸特征，请稍候...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        
        # 启动特征提取
        self.extraction_thread.start()
    
    def on_extraction_complete(self, feature_data):
        """特征提取完成回调"""
        # 显示成功消息
        InfoBar.success(
            title="注册成功",
            content=f"已成功注册您的人脸数据，可用于后续登录",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        
        # 发出完成信号
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
            parent=self
        )
    
    def closeEvent(self, event):
        """窗口关闭事件 - 确保所有线程都安全停止"""
        # 停止捕获线程
        self.stop_capture()
        
        # 如果特征提取线程正在运行，停止它
        if hasattr(self, 'extraction_thread') and self.extraction_thread:
            if self.extraction_thread.isRunning():
                self.extraction_thread.terminate()  # 强制终止线程
                self.extraction_thread.wait()       # 等待线程结束
        
        # 调用父类方法
        super().closeEvent(event)


class FeatureExtractionThread(QThread):
    """特征提取线程 - 处理提取的人脸特征"""
    extractionComplete = pyqtSignal(str)  # 发送特征数据
    extractionFailed = pyqtSignal(str)  # 发送错误信息
    
    def __init__(self, face_images, user_id, username, face_count):
        super().__init__()
        self.face_images = face_images  # 直接使用图像列表
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
            # 准备人脸识别模型
            model_file = "faceRecognition/models/openface_nn4.small2.v1.t7"
            
            # 如果模型文件不存在，下载
            if not os.path.exists(model_file):
                model_dir = os.path.dirname(model_file)
                if not os.path.exists(model_dir):
                    os.makedirs(model_dir)
                
                # 下载模型文件
                url = "https://github.com/pyannote/pyannote-data/raw/master/openface.nn4.small2.v1.t7"
                urllib.request.urlretrieve(url, model_file)
            
            # 加载DNN模型
            face_net = cv2.dnn.readNetFromTorch(model_file)
            
            # 从内存中处理图像
            face_features = []
            
            # 处理每张人脸图像
            for image in self.face_images:
                if not self.running:
                    return
                
                # 检查图像有效性
                if image is None or image.size == 0:
                    continue
                    
                # 预处理图像
                blob = cv2.dnn.blobFromImage(
                    image, 1.0/255, (96, 96), (0, 0, 0), swapRB=True, crop=False
                )
                
                # 前向传播获取特征
                face_net.setInput(blob)
                feature_vector = face_net.forward()
                
                # 添加到特征列表
                face_features.append(feature_vector.flatten().tolist())
            
            # 将特征列表转换为JSON字符串
            face_data_json = json.dumps(face_features)

            if not self.running:
                return
            
            # 将特征保存到数据库
            db = DatabaseManager()
            db.update_user(self.user_id, face_data=face_data_json)
            db.close()
            
            # 清空内存中的图像数据
            self.face_images = []
            
            # 发送成功信号
            self.extractionComplete.emit("face_features_stored")
            
        except Exception as e:
            # 发送失败信号
            self.extractionFailed.emit(str(e))


# 如果作为独立程序运行，则创建测试实例
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = FaceRegistrationMessageBox(user_id=1, username="测试用户")
    dialog.exec()