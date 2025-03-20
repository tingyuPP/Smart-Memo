# coding:utf-8
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QMenu, QAction
from qfluentwidgets import FluentIcon

from mainWindow.ui.view.Ui_mainpage import Ui_mainwindow

# from Ui_mainpage import Ui_mainwindow

from qfluentwidgets import (
    TitleLabel,
    BodyLabel,
    CardWidget,
    IconWidget,
    CaptionLabel,
    TransparentToolButton,
    FluentIcon,
    PrimaryPushButton,
    RoundMenu,
    Action,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QScrollArea,
)
from PyQt5.QtCore import Qt, QPoint, QSize, QRect
from PyQt5.QtGui import QFont, QColor


import sys


class AppCard(CardWidget):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.setup_ui(title, content)
        self.setup_context_menu()
        self.clicked.connect(self.on_double_clicked)  # 连接双击信号
        self.moreButton.clicked.connect(
            self.showContextMenu
        )  # 连接 moreButton 的点击信号
        
        

    def setup_ui(self, title, content):
        # 文本区域
        self.titleLabel = TitleLabel(title, self)
        self.contentLabel = BodyLabel(content, self)
        self.contentLabel.setWordWrap(True)

        # 操作按钮
        # self.openButton = PrimaryPushButton("打开", self)  # 注释掉 openButton
        self.moreButton = TransparentToolButton(FluentIcon.MORE, self)

        # 时间标签
        self.timeLabel = CaptionLabel("10:30 AM", self)

        # 布局系统
        self.mainLayout = QHBoxLayout(self)
        self.textLayout = QVBoxLayout()
        self.rightActions = QHBoxLayout()

        self.construct_layout()

    def construct_layout(self):
        # 中间文本
        self.mainLayout.addSpacing(15)

        self.textLayout.addWidget(self.titleLabel)
        self.textLayout.addWidget(self.contentLabel)
        self.textLayout.addWidget(self.timeLabel)
        self.mainLayout.addLayout(self.textLayout)

        # 右侧操作区
        # self.rightActions.addWidget(self.openButton)  # 注释掉 openButton
        self.rightActions.addWidget(self.moreButton)
        self.rightActions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.mainLayout.addLayout(self.rightActions)

        # 尺寸策略
        self.setFixedHeight(96)
        # self.openButton.setFixedWidth(80)  # 注释掉 openButton
        self.moreButton.setFixedSize(40, 40)

        # 边距调整
        self.mainLayout.setContentsMargins(16, 8, 16, 8)
        self.textLayout.setContentsMargins(0, 2, 0, 2)
        self.textLayout.setSpacing(4)

    def setup_context_menu(self):
        self.menu = RoundMenu(parent=self)

        # 逐个添加动作，Action 继承自 QAction，接受 FluentIconBase 类型的图标
        self.menu.addAction(
            Action(
                FluentIcon.DELETE,
                "删除",
                triggered=lambda: print("删除成功"),
            )
        )
        self.menu.addAction(
            Action(FluentIcon.ACCEPT, "收藏", triggered=lambda: print("收藏成功"))
        )
        # 添加分割线
        self.menu.addSeparator()

        # 导出为子菜单
        export_submenu = RoundMenu("导出为", self)
        export_submenu.setIcon(FluentIcon.ZOOM_OUT)  # 设置图标
        export_submenu.addActions(
            [
                Action("PDF", triggered=lambda: print("导出为PDF")),  # 导出为 PDF
                Action("Word", triggered=lambda: print("导出为Word")),  # 导出为 Word
            ]
        )
        self.menu.addMenu(export_submenu)

        # 分享到子菜单
        share_submenu = RoundMenu("分享到", self)
        share_submenu.setIcon(FluentIcon.SHARE)  # 设置图标
        share_submenu.addActions(
            [
                Action("微信", triggered=lambda: print("分享到微信")),  # 分享到微信
                Action("QQ", triggered=lambda: print("分享到QQ")),  # 分享到 QQ
            ]
        )
        self.menu.addMenu(share_submenu)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.customContextMenuRequested.connect(self.showContextMenu)  # 注释掉这行

    def showContextMenu(self, pos):
        self.menu.exec_(
            self.moreButton.mapToGlobal(QPoint(0, self.moreButton.height()))
        )

    def on_double_clicked(self):
        # 在这里编写双击 AppCard 后要执行的操作
        print(f"AppCard 双击! Title: {self.titleLabel.text()}")
        # 您可以在这里添加打开应用程序或执行其他操作的代码


class mainInterface(Ui_mainwindow, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.toolButton.setIcon(FluentIcon.ADD)
        self.toolButton_2.setIcon(FluentIcon.SYNC)

        # 连接 toolButton 的点击事件
        self.toolButton.clicked.connect(self.switch_to_music_interface)
        
        self.pushButton.addItem("按名称排序")
        self.pushButton.addItem("按时间排序")
        self.pushButton.addItem("按标签排序")

        # 创建 QVBoxLayout
        self.cardLayout = QVBoxLayout()

        self.scrollAreaWidgetContents.setLayout(
            self.cardLayout
        )  # 将布局设置到已有的 Widget 中

        self.scrollArea.setStyleSheet(
            "QScrollArea{background: transparent; border: none}"
        )

        self.scrollAreaWidgetContents.setStyleSheet("QWidget{background: transparent}")

        # 添加 AppCard 到 cardLayout
        self.cardLayout.addWidget(
            AppCard("Calendar", "Manage your schedule")
        )  # 修改参数
        self.cardLayout.addWidget(AppCard("Camera", "Take a photo"))  # 修改参数
        self.cardLayout.addWidget(AppCard("Mail", "Send an email"))  # 修改参数
        self.cardLayout.addWidget(AppCard("Music", "Listen to music"))
        self.cardLayout.addWidget(AppCard("Video", "Watch a movie"))
        self.cardLayout.addWidget(AppCard("Settings", "Change your preferences"))
        self.cardLayout.addWidget(AppCard("Weather", "Check the weather"))
        self.cardLayout.addWidget(AppCard("Calculator", "Do some math"))
        self.cardLayout.addWidget(AppCard("Notes", "Write a note"))

    def switch_to_music_interface(self):
        # 调用父窗口 (MainWindow) 的方法来切换到 musicInterface
        main_window = self.window()
        if hasattr(main_window, "switch_to_newmemo_interface"):
            main_window.switch_to_newmemo_interface()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = mainInterface()
    w.show()
    sys.exit(app.exec_())
