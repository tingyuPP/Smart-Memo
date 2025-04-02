from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QStackedWidget, QFrame
from PyQt5.QtCore import Qt
from qfluentwidgets import Pivot, SegmentedWidget, setTheme, Theme
from login.view.accountInterface import AccountInterface
from mainWindow.mainWindow import MainWindow
from login.view.faceInterface import FaceLoginInterface
from config import cfg
from qframelesswindow import FramelessWindow, StandardTitleBar
from PyQt5.QtGui import QIcon
import sys, os


def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 非打包环境，使用当前路径
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class LoginWindow(FramelessWindow):

    def __init__(self):
        super().__init__()
        if cfg.get(cfg.themeMode) == Theme.DARK:
            with open(resource_path("resource/dark.qss"), encoding="utf-8") as f:
                self.setStyleSheet(f.read())

        self.segmentedWidget = SegmentedWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.setTitleBar(StandardTitleBar(self))
        self.titleBar.setStyleSheet("background-color: #f0f0f0; ")
        self.setWindowTitle("SmartMemo")
        self.setWindowIcon(QIcon("resource/logo.png"))

        self.accountInterface = AccountInterface(self)
        self.accountInterface.loginSuccess.connect(self.on_login_success)
        self.faceInterface = FaceLoginInterface(self)
        self.faceInterface.loginSuccessful.connect(self.on_login_success)
        self.faceInterface.backClicked.connect(self.back_to_account)

        # 添加标签页
        # self.addSubInterface(self.accountInterface, 'songInterface', 'Song')
        self.accountInterface.setObjectName("accountInterface")
        self.segmentedWidget.addItem(
            routeKey="accountInterface",
            text="账密登录",
            onClick=lambda: self.stackedWidget.setCurrentWidget(self.accountInterface),
        )
        self.stackedWidget.addWidget(self.accountInterface)

        self.faceInterface.setObjectName("faceInterface")
        self.segmentedWidget.addItem(
            routeKey="faceInterface",
            text="人脸识别",
            onClick=lambda: self.stackedWidget.setCurrentWidget(self.faceInterface),
        )
        self.stackedWidget.addWidget(self.faceInterface)

        # 连接信号并初始化当前标签页
        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.stackedWidget.setCurrentWidget(self.accountInterface)
        self.segmentedWidget.setCurrentItem(self.accountInterface.objectName())

        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.addWidget(self.segmentedWidget, 0, Qt.AlignHCenter)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.resize(350, 600)

        # if cfg.get(cfg.themeMode) == "Dark":
        #     with open(f'resource/dark.qss', encoding='utf-8') as f:
        #         self.setStyleSheet(f.read())
        #         self.faceInterface.setStyleSheet(f.read())
        #         self.accountInterface.setStyleSheet(f.read())

    def addSubInterface(self, widget: QLabel, objectName: str, text: str):
        widget.setObjectName(objectName)
        widget.setAlignment(Qt.AlignCenter)
        self.stackedWidget.addWidget(widget)

        # 使用全局唯一的 objectName 作为路由键
        self.segmentedWidget.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget),
        )

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.segmentedWidget.setCurrentItem(widget.objectName())

    def on_login_success(self, user_data):
        user_id = user_data["id"]
        username = user_data["username"]
        print(f"登录成功：{user_id}, {username}")
        self.hide()
        # from mainWindow.mainWindow import MainWindow
        self.mainWindow = MainWindow(user_id, username)
        self.mainWindow.show()
        # print("这里应该打开主窗口")

    def back_to_account(self):
        self.stackedWidget.setCurrentWidget(self.accountInterface)
        self.segmentedWidget.setCurrentItem(self.accountInterface.objectName())
