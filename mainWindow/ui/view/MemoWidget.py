from PyQt5 import QtCore, QtWidgets
from .Ui_memo import Ui_memo


class MemoWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_memo()
        self.ui.setupUi(self)

        # 应用响应式布局
        self.setupResponsiveLayout()

    def setupResponsiveLayout(self):
        # 创建主布局
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 10, 20, 20)
        self.main_layout.setSpacing(10)

        # 顶部布局 - 水平排列两个卡片
        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.setSpacing(10)

        # 添加原始控件到布局中
        self.top_layout.addWidget(self.ui.frame_3, 3)  # 左侧搜索栏占比更大
        self.top_layout.addWidget(self.ui.frame_4, 2)  # 右侧命令栏占比较小

        # 添加顶部布局到主布局
        self.main_layout.addLayout(self.top_layout)

        # 添加主内容区卡片到主布局
        self.main_layout.addWidget(self.ui.frame)

        # 设置内容区占据更多垂直空间
        self.main_layout.setStretch(0, 1)  # 顶部区域
        self.main_layout.setStretch(1, 8)  # 主内容区域

        # 设置各个卡片的内部布局
        self._setupCardLayouts()

    def _setupCardLayouts(self):
        # 标题输入区域内部布局
        self.frame3_layout = QtWidgets.QHBoxLayout(self.ui.frame_3)
        self.frame3_layout.setContentsMargins(20, 10, 20, 10)
        self.frame3_layout.addWidget(self.ui.lineEdit, 7)  # 标题输入框
        self.frame3_layout.addWidget(self.ui.lineEdit_2, 3)  # 标签选择框

        # 命令栏区域内部布局
        self.frame4_layout = QtWidgets.QHBoxLayout(self.ui.frame_4)
        self.frame4_layout.setContentsMargins(10, 10, 10, 10)
        self.frame4_layout.addWidget(self.ui.frame_2)  # 命令栏

        # 主内容区域内部布局
        self.frame_layout = QtWidgets.QVBoxLayout(self.ui.frame)
        self.frame_layout.setContentsMargins(20, 10, 20, 20)

        # 创建标题栏布局（包含字数统计标签）
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.ui.label)

        # 添加到主内容区域布局
        self.frame_layout.addLayout(self.header_layout)
        self.frame_layout.addWidget(self.ui.textEdit)
