# coding:utf-8
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QMenu, QAction
from qfluentwidgets import FluentIcon

from mainWindow.ui.view.Ui_memo import Ui_memo

# from Ui_memo import Ui_memo

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


class memoInterface(Ui_memo, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.frame_2.addAction(
            Action(FluentIcon.ADD, "添加", triggered=lambda: print("添加"))
        )

        # 添加分隔符
        self.frame_2.addSeparator()

        # 批量添加动作
        self.frame_2.addActions(
            [
                Action(
                    FluentIcon.EDIT,
                    "编辑",
                    checkable=True,
                    triggered=lambda: print("编辑"),
                ),
                Action(FluentIcon.COPY, "复制"),
                Action(FluentIcon.SHARE, "分享"),
            ]
        )


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = memoInterface()
    w.show()
    sys.exit(app.exec_())
