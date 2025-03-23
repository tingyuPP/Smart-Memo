# coding:utf-8
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QWidget,
    QMenu,
    QAction,
    QMessageBox,
    QLabel,
    QDialog,
    QApplication,
)
from qfluentwidgets import FluentIcon

from mainWindow.ui.view.Ui_memo import Ui_memo

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
    InfoBarPosition,
    TextEdit,
    StateToolTip,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QScrollArea,
    QFileDialog,
)

from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtCore import Qt, QPoint, QSize, QRect, pyqtSlot, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QTextDocument


import sys
import os
import threading
from Database import DatabaseManager  # 导入数据库管理类
from mainWindow.ui.view.ai_handler import AIHandler

from config import cfg

from mainWindow.ui.view.smart_text_edit import SmartTextEdit
from mainWindow.ui.view.smart_text_edit import enhance_text_edit_with_copilot


class memoInterface(Ui_memo, QWidget):
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.db = DatabaseManager()  # 初始化数据库连接
        self.user_id = user_id  # 获取用户ID
        self.ai_handler = AIHandler(self)  # 创建 AI 处理器实例

        self.memo_id = None  # 添加memo_id属性，用于跟踪当前备忘录的ID

        self.frame_2.addAction(
            Action(
                FluentIcon.ROBOT,
                "AI编辑",
                triggered=lambda: self.ai_handler.show_ai_menu(self.textEdit),
            )
        )

        # 添加分隔符
        self.frame_2.addSeparator()

        # 批量添加动作
        save_action = Action(FluentIcon.SAVE, "保存")
        save_action.triggered.connect(self.save_memo)  # 连接保存动作
        self.frame_2.addActions(
            [
                save_action,
                Action(FluentIcon.DELETE, "清空", triggered=self.clear_memo),
            ]
        )
        # 添加分隔符
        self.frame_2.addSeparator()

        # 添加导出和分享按钮
        self.frame_2.addAction(
            Action(
                FluentIcon.PRINT,
                "导出为",
                triggered=self.show_export_menu,
            )
        )

        self.frame_2.addAction(
            Action(
                FluentIcon.SHARE,
                "分享到",
                triggered=self.show_share_menu,
            )
        )

        self.lineEdit.setPlaceholderText("请输入备忘录标题")
        self.lineEdit_2.setPlaceholderText("请选择标签")

        # 为 frame 设置布局管理器
        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(30, 40, 30, 20)  # 设置边距，与原始的 geometry 相匹配
        layout.addWidget(self.textEdit)  # 将原始的 textEdit 添加到布局中

        # 尝试增强现有的textEdit
        try:
            print("正在启用智能文本编辑功能...")
            old_text = self.textEdit.toPlainText()
            new_text_edit = SmartTextEdit(self)
            new_text_edit = enhance_text_edit_with_copilot(new_text_edit, self)  # 增强文本编辑器功能
            new_text_edit.setText(old_text)
            
            # 替换控件
            layout.replaceWidget(self.textEdit, new_text_edit)
            self.textEdit.setParent(None)  # 移除旧的控件
            self.textEdit = new_text_edit  # 更新引用
            
            print("已启用智能文本编辑功能")
        except Exception as e:
            import traceback
            print(f"启用智能文本编辑功能失败: {str(e)}")
            print(traceback.format_exc())

        self.textEdit.textChanged.connect(self.update_word_count)  # 文本改变时更新字数
        self.update_word_count()  # 初始化字数显示

    def save_memo(self, silent=False):
        """保存备忘录到数据库

        Args:
            silent: 是否静默保存（不显示成功消息）

        Returns:
            bool: 保存是否成功
        """
        title = self.lineEdit.text()
        content = self.textEdit.toPlainText()
        category = self.lineEdit_2.text()

        if not title or not content:
            if not silent:  # 只有在非静默模式下才显示警告
                InfoBar.warning(
                    title="警告",
                    content="标题和内容不能为空！",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
            return False

        try:
            # 根据是否有memo_id决定创建新备忘录还是更新现有备忘录
            if self.memo_id is None:
                # 创建新备忘录
                memo_id = self.db.create_memo(self.user_id, title, content, category)
                if memo_id:
                    self.memo_id = memo_id  # 保存新创建的备忘录ID
                    if not silent:  # 只有在非静默模式下才显示成功消息
                        InfoBar.success(
                            title="成功",
                            content="备忘录保存成功！",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self,
                        )
                    return True
            else:
                # 更新现有备忘录
                success = self.db.update_memo(
                    self.memo_id, title=title, content=content, category=category
                )
                if success:
                    if not silent:  # 只有在非静默模式下才显示成功消息
                        InfoBar.success(
                            title="成功",
                            content="备忘录更新成功！",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self,
                        )
                    return True

            # 如果执行到这里，说明保存/更新失败
            InfoBar.error(
                title="错误",
                content="备忘录保存失败！",
                orient=Qt.Vertical,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return False

        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"备忘录保存失败：{str(e)}",
                orient=Qt.Vertical,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return False

    def clear_memo(self):
        """清空备忘录"""
        self.textEdit.clear()
        self.lineEdit.clear()
        self.lineEdit_2.clear()
        self.memo_id = None  # 清空备忘录ID
        self.update_word_count()

    def update_word_count(self):
        """更新字数统计"""
        text = self.textEdit.toPlainText()
        word_count = len(text)
        self.label.setText(f"共{word_count}字")

    def closeEvent(self, event):
        """关闭窗口时关闭数据库连接"""
        self.db.close()
        event.accept()

    def show_export_menu(self):
        """显示导出菜单"""
        # 检查内容是否已填写
        title = self.lineEdit.text()
        content = self.textEdit.toPlainText()

        if not title or not content:
            InfoBar.warning(
                title="警告",
                content="标题和内容不能为空！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 先保存备忘录，确保内容已经存储
        if self.save_memo(silent=True):  # 静默保存，不显示成功消息
            exportMenu = RoundMenu("导出为", self)
            exportMenu.addActions(
                [
                    Action("PDF", triggered=self.export_to_pdf),
                    Action("TXT", triggered=self.export_to_txt),
                ]
            )
            exportMenu.exec_(QCursor.pos())

    def show_share_menu(self):
        """显示分享菜单"""
        # 检查内容是否已填写
        title = self.lineEdit.text()
        content = self.textEdit.toPlainText()

        if not title or not content:
            InfoBar.warning(
                title="警告",
                content="标题和内容不能为空！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 先保存备忘录，确保内容已经存储
        if self.save_memo(silent=True):  # 静默保存，不显示成功消息
            shareMenu = RoundMenu("分享到", self)
            shareMenu.addActions(
                [
                    Action("微信", triggered=lambda: self.share_to("微信")),
                    Action("QQ", triggered=lambda: self.share_to("QQ")),
                ]
            )
            shareMenu.exec_(QCursor.pos())

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

            default_filename = f"{self.lineEdit.text()}.pdf"
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
            category = self.lineEdit_2.text()
            category_text = (
                f"<p><small>分类: {category}</small></p>" if category else ""
            )

            html_content = f"""
            <h2>{self.lineEdit.text()}</h2>
            <p>{self.textEdit.toPlainText()}</p>
            {category_text}
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
                parent=self,
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
                parent=self,
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

            default_filename = f"{self.lineEdit.text()}.txt"
            default_path = os.path.join(default_dir, default_filename)

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出为TXT", default_path, "Text Files (*.txt)"
            )

            if not file_path:  # 用户取消了保存
                return

            # 写入TXT文件
            with open(file_path, "w", encoding="utf-8") as f:
                category = self.lineEdit_2.text()
                f.write(f"标题: {self.lineEdit.text()}\n\n")
                f.write(f"{self.textEdit.toPlainText()}\n\n")
                if category:
                    f.write(f"分类: {category}\n")

            # 使用InfoBar显示成功消息
            InfoBar.success(
                title="导出成功",
                content=f"备忘录已成功导出为TXT文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
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
                parent=self,
            )

    def share_to(self, platform):
        """分享备忘录到指定平台"""
        # 这里可以实现实际的分享功能，目前只显示通知
        InfoBar.success(
            title="分享成功",
            content=f"已分享到{platform}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = memoInterface()
    w.show()
    sys.exit(app.exec_())
