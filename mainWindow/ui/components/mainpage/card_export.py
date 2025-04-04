# coding:utf-8
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter

from qfluentwidgets import InfoBar, InfoBarPosition

import os
from config import cfg


class CardExportManager:
    """备忘录卡片导出管理器，负责处理文件导出功能"""

    @staticmethod
    def get_export_dir():
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

    @staticmethod
    def export_to_pdf(parent, title, content, time_text, timer=None):
        """导出备忘录为PDF文件"""
        try:
            # 获取默认导出目录
            default_dir = CardExportManager.get_export_dir()

            default_filename = f"{title}.pdf"
            default_path = os.path.join(default_dir, default_filename)

            # 停止定时器
            if timer:
                timer.stop()

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                parent, "导出为PDF", default_path, "PDF Files (*.pdf)"
            )

            # 启动定时器
            if timer:
                timer.start(1000)

            if not file_path:  # 用户取消了保存
                return

            # 显示进度提示
            progress_info = InfoBar.info(
                title="正在导出...",
                content=f"正在生成PDF文件，请稍候...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                duration=0,  # 不自动关闭
                parent=parent.window(),
            )

            # 创建工作线程
            class ExportThread(QThread):
                exportFinished = pyqtSignal(bool, str)

                def __init__(self, title, content, time_text, file_path):
                    super().__init__()
                    self.title = title
                    self.content = content
                    self.time_text = time_text
                    self.file_path = file_path

                def run(self):
                    try:
                        # 创建打印机对象
                        printer = QPrinter(QPrinter.HighResolution)
                        printer.setOutputFormat(QPrinter.PdfFormat)
                        printer.setOutputFileName(self.file_path)

                        # 创建文档内容
                        document = QTextDocument()
                        html_content = f"""
                        <h2>{self.title}</h2>
                        <p>{self.content}</p>
                        <p><small>修改时间: {self.time_text}</small></p>
                        """
                        document.setHtml(html_content)

                        # 将文档打印到PDF
                        document.print_(printer)
                        self.exportFinished.emit(True, "")
                    except Exception as e:
                        self.exportFinished.emit(False, str(e))

            # 创建并启动线程
            export_thread = ExportThread(title, content, time_text, file_path)

            # 连接信号
            def on_export_finished(success, error_msg):
                # 关闭进度提示
                progress_info.close()

                if success:
                    # 使用InfoBar显示成功消息
                    InfoBar.success(
                        title="导出成功",
                        content=f"备忘录已成功导出为PDF文件",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=parent.window(),
                    )
                else:
                    # 使用InfoBar显示错误消息
                    InfoBar.warning(
                        title="导出失败",
                        content=f"导出PDF时发生错误：{error_msg}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=parent.window(),
                    )

            export_thread.exportFinished.connect(on_export_finished)
            parent.export_thread = export_thread  # 保存引用防止垃圾回收
            export_thread.start()
            return True

        except Exception as e:
            # 使用InfoBar显示错误消息
            InfoBar.warning(
                title="导出失败",
                content=f"准备导出PDF时发生错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=parent.window(),
            )
            return False

    @staticmethod
    def export_to_txt(parent, title, content, time_text):
        """导出备忘录为TXT文件"""
        try:
            # 获取默认导出目录
            default_dir = CardExportManager.get_export_dir()

            default_filename = f"{title}.txt"
            default_path = os.path.join(default_dir, default_filename)

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                parent, "导出为TXT", default_path, "Text Files (*.txt)"
            )

            if not file_path:  # 用户取消了保存
                return

            # 显示进度提示
            progress_info = InfoBar.info(
                title="正在导出...",
                content=f"正在生成TXT文件，请稍候...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                duration=0,  # 不自动关闭
                parent=parent.window(),
            )

            # 创建工作线程
            class ExportThread(QThread):
                exportFinished = pyqtSignal(bool, str)

                def __init__(self, title, content, time_text, file_path):
                    super().__init__()
                    self.title = title
                    self.content = content
                    self.time_text = time_text
                    self.file_path = file_path

                def run(self):
                    try:
                        # 写入TXT文件
                        with open(self.file_path, "w", encoding="utf-8") as f:
                            f.write(f"标题: {self.title}\n\n")
                            f.write(f"{self.content}\n\n")
                            f.write(f"修改时间: {self.time_text}")
                        self.exportFinished.emit(True, "")
                    except Exception as e:
                        self.exportFinished.emit(False, str(e))

            # 创建并启动线程
            export_thread = ExportThread(title, content, time_text, file_path)

            # 连接信号
            def on_export_finished(success, error_msg):
                # 关闭进度提示
                progress_info.close()

                if success:
                    # 使用InfoBar显示成功消息
                    InfoBar.success(
                        title="导出成功",
                        content=f"备忘录已成功导出为TXT文件",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=parent.window(),
                    )
                else:
                    # 使用InfoBar显示错误消息
                    InfoBar.warning(
                        title="导出失败",
                        content=f"导出TXT时发生错误：{error_msg}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=parent.window(),
                    )

            export_thread.exportFinished.connect(on_export_finished)
            parent.export_thread = export_thread  # 保存引用防止垃圾回收
            export_thread.start()
            return True

        except Exception as e:
            # 使用InfoBar显示错误消息
            InfoBar.warning(
                title="导出失败",
                content=f"准备导出TXT时发生错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=parent.window(),
            )
            return False
