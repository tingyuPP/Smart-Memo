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
from mainWindow.ui.view.mainpage import mainInterface
from mainWindow.ui.view.memo import memoInterface
from mainWindow.ui.view.todoInterface import TodoInterface


class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)

        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignCenter)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)

        # 必须给子界面设置全局唯一的对象名
        self.setObjectName(text.replace(" ", "-"))


class MainWindow(FluentWindow):
    """主界面"""

    def __init__(self, user_id=None, username=None):
        super().__init__()
        self.splashScreen = SplashScreen(
            QIcon(":/qfluentwidgets/images/logo.png"), self
        )
        self.splashScreen.setIconSize(QSize(100, 100))
        self.splashScreen.show()

        QApplication.processEvents()
        self.user_id = user_id

        # 创建子界面，实际使用时将 Widget 换成自己的子界面
        self.homeInterface = mainInterface(self, user_id)
        self.memoInterface = memoInterface(self, user_id)
        self.settingInterface = SettingInterface("设置", self)
        self.myInterface = MyInterface("My Interface", username, self)
        self.todoInterface = TodoInterface(self, user_id)
        # print(self.myInterface.objectName())

        self.initNavigation()
        self.stackedWidget.currentChanged.connect(self.onCurrentInterfaceChanged)

        QTimer.singleShot(1600, self.splashScreen.close)
        self.initWindow()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, "主页")
        self.addSubInterface(self.memoInterface, FIF.ADD, "新建备忘录")
        self.addSubInterface(self.todoInterface, FIF.PIN, "待办")

        self.navigationInterface.addSeparator()

        # if self.user_data["avatar"]:
        #     self.addSubInterface(self.myInterface, self.create_round_icon(self.user_data["avatar"]), 'My Page', NavigationItemPosition.BOTTOM)
        # else:
        #     self.addSubInterface(self.myInterface, self.create_round_icon("resource/default_avatar.jpg"), 'My Page', NavigationItemPosition.BOTTOM)
        self.addSubInterface(
            self.myInterface, FIF.PEOPLE, "个性化", NavigationItemPosition.BOTTOM
        )
        self.addSubInterface(
            self.settingInterface, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM
        )

    def initWindow(self):
        self.resize(900, 700)
        self.setMinimumWidth(600)
        self.setWindowIcon(QIcon(":/qfluentwidgets/images/logo.png"))
        self.setWindowTitle("SmartMemo")

        self.stackedWidget.currentChanged.connect(self.onInterfaceChanged)


    def onInterfaceChanged(self, index):
        # 获取上一个界面和当前界面
        current_widget = self.stackedWidget.widget(index)

        # 如果从备忘录编辑界面切换到其他界面，且内容不为空，则自动保存
        if hasattr(self, "memoInterface") and self.memoInterface != current_widget:
            # 检查是否有需要保存的内容
            memo = self.memoInterface
            if memo.memo_id or (
                memo.lineEdit.text().strip() and memo.textEdit.toPlainText().strip()
            ):
                # 尝试静默保存（不显示成功消息）
                memo.save_memo(silent=True)

        # 如果切换到了备忘录编辑界面，清空内容以便新建
        if hasattr(self, "memoInterface") and current_widget == self.memoInterface:
            # 清空编辑界面
            self.memoInterface.memo_id = None  # 重置 memo_id
            self.memoInterface.lineEdit.clear()  # 清空标题
            self.memoInterface.textEdit.clear()  # 清空内容
            self.memoInterface.lineEdit_2.clear()  # 清空分类
            self.memoInterface.update_word_count()  # 更新字数统计

        # 如果切换到了主页，刷新备忘录列表
        if hasattr(self, "homeInterface") and current_widget == self.homeInterface:
            self.homeInterface.update_memo_list()

    def switch_to_newmemo_interface(self):
        # 切换到 memoInterface
        self.navigationInterface.setCurrentItem(self.memoInterface.objectName())
        # 直接设置内容区域的当前页面
        self.switchTo(self.memoInterface)

        # 清空 memoInterface 的内容
        if hasattr(self, "memoInterface"):
            self.memoInterface.memo_id = None  # 重置 memo_id
            self.memoInterface.lineEdit.clear()  # 清空标题
            self.memoInterface.textEdit.clear()  # 清空内容
            self.memoInterface.lineEdit_2.clear()  # 清空分类
            self.memoInterface.update_word_count()  # 更新字数统计

    def create_round_icon(self, image_path):
        """创建圆形图标"""
        from PyQt5.QtGui import QPainter, QPainterPath, QPixmap, QColor, QPen
        from PyQt5.QtCore import QSize, Qt

        # 加载原始图像
        original_pixmap = QPixmap(image_path)
        if original_pixmap.isNull():
            return QIcon()  # 如果无法加载图像，返回空图标

        # 创建透明背景的目标pixmap
        size = min(original_pixmap.width(), original_pixmap.height())
        target_pixmap = QPixmap(size, size)
        target_pixmap.fill(Qt.transparent)

        # 创建圆形裁剪路径
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)

        # 开始绘制
        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        painter.setClipPath(path)

        # 如果原图和目标大小不同，进行缩放
        if original_pixmap.width() != size or original_pixmap.height() != size:
            original_pixmap = original_pixmap.scaled(
                size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )

        # 居中绘制原始图像
        x = (
            (size - original_pixmap.width()) // 2
            if original_pixmap.width() < size
            else 0
        )
        y = (
            (size - original_pixmap.height()) // 2
            if original_pixmap.height() < size
            else 0
        )

        painter.drawPixmap(x, y, original_pixmap)

        # 画一个圆形边框（可选）
        painter.setClipping(False)  # 取消裁剪以便绘制边框
        pen = QPen(QColor(200, 200, 200))  # 浅灰色边框
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(1, 1, size - 2, size - 2)

        painter.end()

        # 创建并返回图标
        return QIcon(target_pixmap)

    def onCurrentInterfaceChanged(self, index):
        """处理界面切换事件"""
        # 获取当前显示的界面
        current_widget = self.stackedWidget.widget(index)

        # 如果切换到了主页，就刷新备忘录列表
        if current_widget == self.homeInterface:
            # 确保主页已初始化数据库连接
            if hasattr(self.homeInterface, "db") and self.homeInterface.db:
                self.homeInterface.update_memo_list()
                print("已切换到主页，更新备忘录列表")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()
