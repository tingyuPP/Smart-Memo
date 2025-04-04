# 这是一个demo，展示了如何使用PyQt-Fluent-Widgets库中的FluentWindow类来创建一个主窍口。

from qfluentwidgets import (
    NavigationItemPosition,
    FluentWindow,
    SubtitleLabel,
    setFont,
    AvatarWidget,
    isDarkTheme,
    NavigationWidget,
    SplashScreen,
)
from qfluentwidgets import FluentIcon as FIF
from mainWindow.ui.view.settingInterface import SettingInterface
from mainWindow.ui.view.myInterface import MyInterface
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout
from PyQt5.QtGui import QIcon, QImage, QPainter, QColor, QBrush, QFont
from PyQt5.QtCore import Qt, QRect, QSize, QTimer
import sys
from mainWindow.ui.view.mainpage import MainInterface
from mainWindow.ui.view.memo import MemoInterface
from mainWindow.ui.view.todoInterface import TodoInterface
import os


def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 非打包环境，使用当前路径
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)

        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignCenter)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        self.setObjectName(text.replace(" ", "-"))


class MainWindow(FluentWindow):

    def __init__(self, user_id=None, username=None):
        super().__init__()
        self.splashScreen = SplashScreen(
            QIcon(resource_path("resource/logo.png")), self)
        self.splashScreen.setIconSize(QSize(200, 200))

        try:
            from qframelesswindow import StandardTitleBar

            titleBar = StandardTitleBar(self.splashScreen)
            titleBar.setIcon(QIcon(resource_path("resource/logo.png")))
            titleBar.setTitle("SmartMemo 启动中...")
            self.splashScreen.setTitleBar(titleBar)
        except ImportError:
            print("qframelesswindow 库未安装，跳过标题栏添加")

        self.splashScreen.show()

        QApplication.processEvents()
        self.user_id = user_id
        self.homeInterface = MainInterface(self, user_id)
        self.memoInterface = MemoInterface(self, user_id)
        self.settingInterface = SettingInterface("设置", self)
        self.myInterface = MyInterface("My Interface", username, self)
        self.todoInterface = TodoInterface(self, user_id)

        self.initNavigation()
        self.stackedWidget.currentChanged.connect(
            self.onCurrentInterfaceChanged)
        self.todoInterface.todo_count_changed.connect(self.update_todo_count)
        self.homeInterface.memo_count_changed.connect(self.update_memo_count)

        QTimer.singleShot(1600, self.splashScreen.close)
        self.initWindow()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, "主页")
        self.addSubInterface(self.memoInterface, FIF.ADD, "编辑备忘录")
        self.addSubInterface(self.todoInterface, FIF.PIN, "待办")

        self.navigationInterface.addSeparator()

        self.addSubInterface(self.myInterface, FIF.PEOPLE, "个性化",
                             NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settingInterface, FIF.SETTING, "设置",
                             NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(900, 700)
        self.setMinimumWidth(600)
        self.setWindowIcon(QIcon(resource_path("resource/logo.png")))
        self.setWindowTitle("SmartMemo")

        self.stackedWidget.currentChanged.connect(self.onInterfaceChanged)

    def onInterfaceChanged(self, index):
        current_widget = self.stackedWidget.widget(index)

        # 如果从备忘录编辑界面切换到其他界面，且内容不为空，则自动保存
        if hasattr(self,
                   "memoInterface") and self.memoInterface != current_widget:
            memo = self.memoInterface
            if memo.memo_id or (memo.lineEdit.text().strip()
                                and memo.textEdit.toPlainText().strip()):
                memo.save_memo(silent=True)

        # 如果切换到了备忘录编辑界面，清空内容以便新建
        if hasattr(self,
                   "memoInterface") and current_widget == self.memoInterface:
            self.memoInterface.memo_id = None
            self.memoInterface.lineEdit.clear()
            self.memoInterface.textEdit.clear()
            self.memoInterface.lineEdit_2.clear()
            self.memoInterface.update_word_count()

        # 如果切换到了主页，刷新备忘录列表
        if hasattr(self,
                   "homeInterface") and current_widget == self.homeInterface:
            self.homeInterface.update_memo_list()

    def switch_to_newmemo_interface(self):
        self.navigationInterface.setCurrentItem(
            self.memoInterface.objectName())
        self.switchTo(self.memoInterface)

        if hasattr(self, "memoInterface"):
            self.memoInterface.memo_id = None
            self.memoInterface.lineEdit.clear()
            self.memoInterface.textEdit.clear()
            self.memoInterface.lineEdit_2.clear()
            self.memoInterface.update_word_count()

    def create_round_icon(self, image_path):
        from PyQt5.QtGui import QPainter, QPainterPath, QPixmap, QColor, QPen
        from PyQt5.QtCore import QSize, Qt

        original_pixmap = QPixmap(image_path)
        if original_pixmap.isNull():
            return QIcon()  # 如果无法加载图像，返回空图标

        size = min(original_pixmap.width(), original_pixmap.height())
        target_pixmap = QPixmap(size, size)
        target_pixmap.fill(Qt.transparent)

        path = QPainterPath()
        path.addEllipse(0, 0, size, size)

        # 开始绘制
        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setClipPath(path)

        if original_pixmap.width() != size or original_pixmap.height() != size:
            original_pixmap = original_pixmap.scaled(
                size, size, Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation)
        x = ((size - original_pixmap.width()) //
             2 if original_pixmap.width() < size else 0)
        y = ((size - original_pixmap.height()) //
             2 if original_pixmap.height() < size else 0)

        painter.drawPixmap(x, y, original_pixmap)

        painter.setClipping(False)
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(1, 1, size - 2, size - 2)

        painter.end()

        return QIcon(target_pixmap)

    def onCurrentInterfaceChanged(self, index):
        current_widget = self.stackedWidget.widget(index)

        # 如果切换到了主页，就刷新备忘录列表
        if current_widget == self.homeInterface:
            if hasattr(self.homeInterface, "db") and self.homeInterface.db:
                self.homeInterface.update_memo_list()


        elif current_widget == self.todoInterface:
            if hasattr(self.todoInterface, "db") and self.todoInterface.db:
                self.todoInterface._refresh_list()

    def update_todo_count(self, count):
        self.myInterface.infoCard.update_todo_count(count)

    def update_memo_count(self, count):
        self.myInterface.infoCard.update_memo_count(count)
