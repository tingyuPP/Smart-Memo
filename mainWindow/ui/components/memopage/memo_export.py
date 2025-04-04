# coding:utf-8
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QTextDocument
from PyQt5.QtCore import Qt

from qfluentwidgets import InfoBar, InfoBarPosition

import os
from config import cfg


class MemoExportManager:
    """备忘录导出管理器，负责处理备忘录导出功能"""

    def __init__(self, parent=None):
        self.parent = parent

    def export_to_pdf(self, title, content, category=None):
        """导出备忘录为PDF文件"""
        try:
            default_dir = self._get_export_dir()

            default_filename = f"{title}.pdf"
            default_path = os.path.join(default_dir, default_filename)

            file_path, _ = QFileDialog.getSaveFileName(
                self.parent, "导出为PDF", default_path, "PDF Files (*.pdf)"
            )

            if not file_path:
                return

            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)

            document = QTextDocument()
            category_text = (
                f"<p><small>分类: {category}</small></p>" if category else ""
            )

            html_content = f"""
            <h2>{title}</h2>
            <p>{content}</p>
            {category_text}
            """
            document.setHtml(html_content)

            document.print_(printer)

            InfoBar.success(
                title="导出成功",
                content=f"备忘录已成功导出为PDF文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.parent,
            )
            return True

        except Exception as e:
            InfoBar.warning(
                title="导出失败",
                content=f"导出PDF时发生错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.parent,
            )
            return False

    def export_to_txt(self, title, content, category=None):
        """导出备忘录为TXT文件"""
        try:
            default_dir = self._get_export_dir()

            default_filename = f"{title}.txt"
            default_path = os.path.join(default_dir, default_filename)

            file_path, _ = QFileDialog.getSaveFileName(
                self.parent, "导出为TXT", default_path, "Text Files (*.txt)"
            )

            if not file_path:
                return

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"标题: {title}\n\n")
                f.write(f"{content}\n\n")
                if category:
                    f.write(f"分类: {category}\n")

            InfoBar.success(
                title="导出成功",
                content=f"备忘录已成功导出为TXT文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.parent,
            )
            return True

        except Exception as e:
            InfoBar.warning(
                title="导出失败",
                content=f"导出TXT时发生错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.parent,
            )
            return False

    def _get_export_dir(self):
        """获取导出目录，如不存在则创建"""
        default_dir = cfg.get(cfg.exportDir)
        if not default_dir or not os.path.exists(default_dir):
            export_dir = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                ),
                "export",
            )
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            default_dir = export_dir

        return default_dir
