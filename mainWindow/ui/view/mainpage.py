# coding:utf-8
from PyQt5.QtGui import QTextDocument
from PyQt5.QtWidgets import QWidget, QMenu, QAction
from qfluentwidgets import FluentIcon

from mainWindow.ui.view.Ui_mainpage import Ui_mainwindow

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
    InfoBar,
    SubtitleLabel,
    InfoBarPosition,

)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QScrollArea,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QPoint, QSize, QRect, QTimer
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QFont, QColor

import sys
from Database import DatabaseManager  # 导入数据库管理类
from config import cfg
import os

class AppCard(CardWidget):
    def __init__(self, title, content, modified_time=None, category=None, parent=None):
        super().__init__(parent)
        self.modified_time = modified_time
        self.category = category
        self.setup_ui(title, content)
        self.setup_context_menu()
        self.clicked.connect(self.on_double_clicked)  # 连接双击信号
        self.moreButton.clicked.connect(
            self.showContextMenu
        )  # 连接 moreButton 的点击信号

    def setup_ui(self, title, content):
        # 文本区域
        self.titleLabel = SubtitleLabel(title, self)
        truncated_content = content[:50] + "..." if len(content) > 50 else content
        self.contentLabel = BodyLabel(truncated_content, self)
        self.contentLabel.setWordWrap(True)

        # 操作按钮
        # self.openButton = PrimaryPushButton("打开", self)  # 注释掉 openButton
        self.moreButton = TransparentToolButton(FluentIcon.MORE, self)

        # 时间标签
        if self.modified_time:
            self.timeLabel = CaptionLabel(str(self.modified_time), self)
        else:
            self.timeLabel = CaptionLabel("No time", self)

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
        # self.textLayout.addWidget(self.categoryLabel)
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
        export_submenu.setIcon(FluentIcon.PRINT)  # 设置图标
        export_submenu.addActions(
            [
                Action("PDF", triggered=self.export_to_pdf),  # 导出为 PDF
                Action("TXT", triggered=self.export_to_txt),  # 导出为 TXT
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


    def export_to_pdf(self):
        """导出备忘录为PDF文件"""
        try:
            # 获取默认导出目录
            default_dir = cfg.get(cfg.exportDir)
            if not default_dir or not os.path.exists(default_dir):
                # 如果配置的目录不存在，使用export文件夹
                export_dir = os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    ),
                    "export",
                )
                if not os.path.exists(export_dir):
                    os.makedirs(export_dir)
                default_dir = export_dir

            default_filename = f"{self.titleLabel.text()}.pdf"
            default_path = os.path.join(default_dir, default_filename)

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出为PDF", default_path, "PDF Files (*.pdf)"
            )

            if not file_path:  # 用户取消了保存
                return

            # 创建打印机对象
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)

            # 创建文档内容
            document = QTextDocument()
            html_content = f"""
            <h2>{self.titleLabel.text()}</h2>
            <p>{self.contentLabel.text()}</p>
            <p><small>修改时间: {self.timeLabel.text()}</small></p>
            """
            document.setHtml(html_content)

            # 将文档打印到PDF
            document.print_(printer)

            # 使用InfoBar显示成功消息
            InfoBar.success(
                title="导出成功",
                content=f"备忘录已成功导出为PDF文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window(),
            )

        except Exception as e:
            # 使用InfoBar显示错误消息
            InfoBar.warning(
                title="导出失败",
                content=f"导出PDF时发生错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )


    def export_to_txt(self):
        """导出备忘录为TXT文件"""
        try:
            # 获取默认导出目录
            default_dir = cfg.get(cfg.exportDir)
            if not default_dir or not os.path.exists(default_dir):
                # 如果配置的目录不存在，使用export文件夹
                export_dir = os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    ),
                    "export",
                )
                if not os.path.exists(export_dir):
                    os.makedirs(export_dir)
                default_dir = export_dir

            default_filename = f"{self.titleLabel.text()}.txt"
            default_path = os.path.join(default_dir, default_filename)

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出为TXT", default_path, "Text Files (*.txt)"
            )

            if not file_path:  # 用户取消了保存
                return

            # 写入TXT文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"标题: {self.titleLabel.text()}\n\n")
                f.write(f"{self.contentLabel.text()}\n\n")
                f.write(f"修改时间: {self.timeLabel.text()}")

            # 使用InfoBar显示成功消息
            InfoBar.success(
                title="导出成功",
                content=f"备忘录已成功导出为TXT文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window(),
            )

        except Exception as e:
            # 使用InfoBar显示错误消息
            InfoBar.warning(
                title="导出失败",
                content=f"导出TXT时发生错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )


class mainInterface(Ui_mainwindow, QWidget):
    def __init__(self, parent=None, user_id=None):
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

        # 初始化数据库连接
        self.db = DatabaseManager()
        self.user_id = user_id
        # 定时器，定期更新备忘录列表
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_memo_list)
        self.timer.start(6000)  # 每6秒更新一次

        # 初始加载备忘录列表
        self.update_memo_list()

    def update_memo_list(self):
        """从数据库获取备忘录并更新列表"""
        # 清空现有布局
        for i in reversed(range(self.cardLayout.count())):
            widget = self.cardLayout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # 从数据库获取备忘录
        memos = self.db.get_memos(user_id=self.user_id)

        # 添加 AppCard 到 cardLayout
        for memo in memos:
            # 从数据库中获取的数据
            memo_id = memo[0]
            user_id = memo[1]
            created_time = memo[2]
            modified_time = memo[3]
            title = self.db.decrypt(memo[4])  # 解密标题
            content = self.db.decrypt(memo[5])  # 解密内容
            category = memo[6]

            self.cardLayout.addWidget(
                AppCard(title, content, modified_time=modified_time, category=category)
            )  # 修改参数

    def switch_to_music_interface(self):
        # 调用父窗口 (MainWindow) 的方法来切换到 musicInterface
        main_window = self.window()
        if hasattr(main_window, "switch_to_newmemo_interface"):
            main_window.switch_to_newmemo_interface()

    def closeEvent(self, event):
        """关闭窗口时关闭数据库连接"""
        self.db.close()
        event.accept()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = mainInterface()
    w.show()
    sys.exit(app.exec_())
