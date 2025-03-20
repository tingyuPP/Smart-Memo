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
from PyQt5.QtGui import QFont, QColor, QCursor


import sys


class memoInterface(Ui_memo, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.frame_2.addAction(
            Action(FluentIcon.ROBOT, "AI编辑", triggered=lambda: self.handleAIAction())
        )

        # 添加分隔符
        self.frame_2.addSeparator()

        # 批量添加动作
        self.frame_2.addActions(
            [
                Action(
                    FluentIcon.SAVE,
                    "保存",
                    
                    triggered=lambda: print("编辑"),
                ),
                Action(FluentIcon.DELETE, "清空"),
                Action(FluentIcon.SHARE, "分享"),
            ]
        )
        
        self.lineEdit.setPlaceholderText("请输入备忘录标题")
        self.lineEdit_2.setPlaceholderText("请选择标签")
        
    def handleAIAction(self):
        # 创建一个子菜单
        aiMenu = RoundMenu("AI编辑", self)
        if not self.textEdit.toPlainText().strip():
            aiMenu.addActions(
                [
                    Action("为我写一个朋友圈文案", triggered=lambda: self.handleAIFunc("朋友圈文案")),
                    Action("为我写一句诗", triggered=lambda: self.handleAIFunc("一句诗")),
                    Action("自定义", triggered=lambda: print("自定义")),
                ]
            )
        else:
            aiMenu.addActions(
                [
                    Action("润色", triggered=lambda: self.handleAIFunc("润色")),
                    Action("续写", triggered=lambda: self.handleAIFunc("续写"))
                ]
            )
        aiMenu.exec_(QCursor.pos())

    def handleAIFunc(self, mode):
        cursor = self.textEdit.textCursor()
        text = cursor.selectedText() if cursor.hasSelection() else self.textEdit.toPlainText()
        print(f"{mode}: {text}")




if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = memoInterface()
    w.show()
    sys.exit(app.exec_())
