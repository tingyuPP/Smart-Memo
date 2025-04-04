from qfluentwidgets import (
    ElevatedCardWidget,
    AvatarWidget,
    TitleLabel,
    BodyLabel,
    Theme,
)
from PyQt5.QtCore import Qt, QSize, QRect, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from config import cfg


class InfoCard(ElevatedCardWidget):

    def __init__(self, user_data: dict, memo_count: int, todo_count: int, parent=None):
        super().__init__(parent=parent)
        self.user_data = user_data
        self.id = user_data["id"]
        self.avatar = AvatarWidget(user_data["avatar"])
        self.avatar.setRadius(48)
        self.username = user_data["username"]

        # 获取备忘录及待办事项数量
        self.memo_count = memo_count
        self.todo_count = todo_count

        self.__initWidget()
        self.__initLayout()

        self.setFixedWidth(450)
        self.setFixedHeight(150)

        cfg.themeChanged.connect(self.onThemeChanged)

    def __initWidget(self):
        self.usernameLabel = TitleLabel(self.username, self)
        font = QFont("黑体", 16)
        font.setBold(True)
        self.usernameLabel.setFont(font)

        self.idLabel = BodyLabel(f"ID: {self.id}", self)
        id_font = QFont("Microsoft YaHei", 12)
        self.idLabel.setFont(id_font)

        self.avatar.setFixedSize(100, 100)

        self.separator = QWidget(self)
        self.separator.setFixedHeight(1)
        self.separator.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")

        self.verticalSeparator = QWidget(self)
        self.verticalSeparator.setFixedWidth(1)
        self.verticalSeparator.setMinimumHeight(100)
        self.verticalSeparator.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")

        self.verticalSeparator2 = QWidget(self)
        self.verticalSeparator2.setFixedWidth(1)
        self.verticalSeparator2.setMinimumHeight(100)
        self.verticalSeparator2.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")

        self.memoTitleLabel = BodyLabel("备忘录数量", self)
        self.memoTitleLabel.setAlignment(Qt.AlignCenter)

        self.memoCountLabel = TitleLabel(str(self.memo_count), self)
        count_font = QFont("黑体", 24)
        count_font.setBold(True)
        self.memoCountLabel.setStyleSheet("color: #0078D4;")

        self.todoTitleLabel = BodyLabel("待办任务", self)
        self.todoTitleLabel.setAlignment(Qt.AlignCenter)

        self.todoCountLabel = TitleLabel(str(self.todo_count), self)
        self.todoCountLabel.setStyleSheet("color: #107C10;")

    def __initLayout(self):
        mainLayout = QHBoxLayout(self)
        mainLayout.setContentsMargins(20, 20, 20, 20)
        mainLayout.setSpacing(20)  # 增加间距以分隔各部分

        mainLayout.addWidget(self.avatar, 0, Qt.AlignVCenter)

        infoLayout = QVBoxLayout()
        infoLayout.setSpacing(10)
        infoLayout.addStretch(1)

        infoLayout.addWidget(self.usernameLabel, 0, Qt.AlignLeft)
        infoLayout.addWidget(self.separator)
        infoLayout.addWidget(self.idLabel, 0, Qt.AlignLeft)
        infoLayout.addStretch(1)

        mainLayout.addLayout(infoLayout)
        mainLayout.addWidget(self.verticalSeparator, 0, Qt.AlignVCenter)

        memoLayout = QVBoxLayout()
        memoLayout.setSpacing(10)
        memoLayout.setContentsMargins(10, 0, 10, 0)
        memoLayout.addStretch(1)
        memoLayout.addWidget(self.memoTitleLabel, 0, Qt.AlignLeft)

        countLayout = QHBoxLayout()
        countLayout.setSpacing(2)
        countLayout.addWidget(self.memoCountLabel, 0, Qt.AlignLeft)

        memoLayout.addLayout(countLayout)
        memoLayout.addStretch(1)
        mainLayout.addLayout(memoLayout)

        mainLayout.addWidget(self.verticalSeparator2, 0, Qt.AlignVCenter)

        todoLayout = QVBoxLayout()
        todoLayout.setSpacing(10)
        todoLayout.setContentsMargins(10, 0, 10, 0)
        todoLayout.addStretch(1)
        todoLayout.addWidget(self.todoTitleLabel, 0, Qt.AlignLeft)

        todoCountLayout = QHBoxLayout()
        todoCountLayout.setSpacing(2)
        todoCountLayout.addWidget(self.todoCountLabel, 0, Qt.AlignLeft)

        todoLayout.addLayout(todoCountLayout)
        todoLayout.addStretch(1)

        mainLayout.addLayout(todoLayout)

        self.setLayout(mainLayout)

    def onThemeChanged(self, theme: Theme):
        print(1)
        # 使用QTimer延迟执行，确保在组件样式重置后再应用我们的样式
        QTimer.singleShot(10, self._applyCustomStyles)

    def _applyCustomStyles(self):
        self.memoCountLabel.setStyleSheet("color: #0078D4 !important;")
        self.todoCountLabel.setStyleSheet("color: #107C10 !important;")

    def update_todo_count(self, count):
        self.todo_count = count
        self.todoCountLabel.setText(str(count))
        self._applyCustomStyles()

    def update_memo_count(self, count):
        self.memo_count = count
        self.memoCountLabel.setText(str(count))
        self._applyCustomStyles()
