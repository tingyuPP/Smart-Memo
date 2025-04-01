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
    SimpleCardWidget,
    StrongBodyLabel,
    Dialog,
    CheckBox,
    PushButton,
    CalendarPicker,
    TimePicker,
    ComboBox
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

import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import tempfile
from obs import ObsClient
import traceback
import uuid
import datetime
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import (
    QByteArray,
    Qt,
    QPoint,
    QSize,
    QRect,
    pyqtSlot,
    QTimer,
    QThread,
    pyqtSignal,
)
from PyQt5.QtWidgets import QFrame, QDialog

from mainWindow.ui.view.smart_text_edit import SmartTextEdit


class MemoInterface(Ui_memo, QWidget):
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.db = DatabaseManager()
        self.user_id = user_id

        # 使用AIHandler单例
        self.ai_handler = AIHandler.get_instance(self)
        if self.user_id:  # 确保有用户ID时才构建上下文
            self.ai_handler.ai_service.build_memory_context(self.user_id, self.db)

        # 添加定期更新记忆上下文的机制
        self.memory_update_timer = QTimer(self)
        self.memory_update_timer.timeout.connect(self._update_memory_context)
        self.memory_update_timer.start(1 * 60 * 1000)  # 每分钟更新一次

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

        self.frame_2.addAction(
            Action(
                FluentIcon.CHECKBOX,
                "提取待办事项",
                triggered=self.extract_todos,
            )
        )

        self.lineEdit.setPlaceholderText("请输入备忘录标题")
        self.lineEdit_2.setPlaceholderText("请选择标签")

        layout = self.frame.layout()
        if layout is None:
            layout = QVBoxLayout(self.frame)
            layout.setContentsMargins(30, 40, 30, 20)
            self.frame.setLayout(layout)

        # 创建智能文本编辑器并设置配置
        self.textEdit = SmartTextEdit(self)

        layout.addWidget(self.textEdit)

        for i in range(layout.count()):
            if layout.itemAt(i).widget() == self.textEdit:
                layout.removeWidget(self.textEdit)
                self.textEdit.setParent(None)  # 解除父子关系
                break

        layout.addWidget(
            self.textEdit, 1, 0
        )  # 将 textEdit 添加到网格布局的第一行第一列

        # self.textBrowser.setStyleSheet(
        #     "background-color: #F7F7F7; border: 1px solid #E0E0E0; border-radius: 5px;"
        # )

        # 连接信号
        self.textEdit.textChanged.connect(self.update_markdown_preview)
        self.textEdit.textChanged.connect(self.update_word_count)

        # 初始化显示
        self.update_markdown_preview()
        self.update_word_count()
        self.update_tag_combobox()

    def _update_memory_context(self):
        """定期更新AI记忆上下文"""
        try:
            if (
                self.user_id
                and hasattr(self, "ai_handler")
                and hasattr(self.ai_handler, "ai_service")
            ):
                self.ai_handler.ai_service.build_memory_context(self.user_id, self.db)
        except Exception as e:
            print(f"更新记忆上下文时出错: {str(e)}")

    def showEvent(self, event):
        """当窗口显示时调用"""
        # 更新标签下拉框
        self.update_tag_combobox()

        # 调用父类方法
        super().showEvent(event)

    def load_user_tags(self):
        """从数据库加载用户的所有历史标签"""
        if not self.user_id:
            return []

        try:
            # 获取用户的所有标签
            tags = self.db.get_user_tags(self.user_id)

            # 提取标签名称
            tag_names = [tag["tag_name"] for tag in tags]
            return tag_names
        except Exception as e:
            print(f"加载用户标签时出错: {str(e)}")
            return []

    def update_tag_combobox(self):
        """更新标签下拉框的选项"""
        # 保存当前选中的标签
        current_tag = self.lineEdit_2.text()

        # 加载用户的历史标签
        tag_names = self.load_user_tags()

        # 清空现有选项
        self.lineEdit_2.clear()

        # 添加标签选项
        self.lineEdit_2.addItems(tag_names)

        # 如果有原来的标签，则恢复选择
        if current_tag and current_tag in tag_names:
            index = self.lineEdit_2.findText(current_tag)
            if index >= 0:
                self.lineEdit_2.setCurrentIndex(index)

    def toggle_markdown_preview(self):
        """切换Markdown预览模式"""
        try:
            # 获取当前内容
            content = self.textEdit.toPlainText()
            self._current_content = content

            if not self._markdown_preview_enabled:
                # 启用Markdown预览
                self.textEdit.setMarkdown(content)
                self._markdown_preview_enabled = True

                # 更新按钮文本
                self.frame_2.actions()[-1].setText("编辑模式")

                # 添加预览状态提示
                InfoBar.success(
                    title="Markdown预览",
                    content="已切换到预览模式，点击按钮返回编辑模式",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
            else:
                # 返回编辑模式
                self.textEdit.setText(self._current_content)
                self._markdown_preview_enabled = False

                # 更新按钮文本
                self.frame_2.actions()[-1].setText("Markdown预览")

                # 添加编辑状态提示
                InfoBar.info(
                    title="编辑模式",
                    content="已返回编辑模式",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
        except Exception as e:
            InfoBar.error(
                title="切换失败",
                content=f"切换Markdown预览模式失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def update_markdown_preview(self):
        """实时更新Markdown预览内容"""
        content = self.textEdit.toPlainText()
        self.textBrowser.setMarkdown(content)

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
            if category and self.user_id:
                try:
                    self.db.add_tag(self.user_id, category)
                except Exception as e:
                    print(f"保存标签时出错: {str(e)}")
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
        try:
            # 获取当前活动窗口
            parent_widget = QApplication.activeWindow()

            # 准备要分享的内容
            title = self.lineEdit.text()
            content = self.textEdit.toPlainText()  # 直接使用完整内容
            category = self.lineEdit_2.text()

            # 创建图片 - 根据内容长度动态调整高度
            width = 800

            # 改进的文本换行处理逻辑
            content_lines = []
            char_width = 16
            chars_per_line = (width - 40) // char_width

            # 先按照换行符分割文本
            paragraphs = content.split("\n")

            # 处理每个段落，进行宽度限制换行
            for paragraph in paragraphs:
                # 如果是空段落（连续换行），添加一个空行
                if not paragraph:
                    content_lines.append("")
                    continue

                # 处理非空段落，按宽度限制换行
                current_line = ""
                for char in paragraph:
                    current_line += char
                    if len(current_line) >= chars_per_line:
                        content_lines.append(current_line)
                        current_line = ""

                # 添加最后一行（如果有内容）
                if current_line:
                    content_lines.append(current_line)

            # 计算所需高度 = 标题区域(60px) + 行数*行高(22px) + 底部间距(50px)
            line_height = 22
            total_lines = len(content_lines)
            content_height = total_lines * line_height
            height = 60 + content_height + 50

            # 设置最小高度和最大高度
            height = max(400, min(height, 2000))  # 最小400px，最大2000px

            # 创建图片
            img = Image.new("RGB", (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            # 尝试加载默认字体，如果失败则使用默认字体
            try:
                # 使用系统字体
                title_font = ImageFont.truetype("msyh.ttc", 24)  # 微软雅黑
                content_font = ImageFont.truetype("msyh.ttc", 16)
            except Exception:
                # 使用默认字体
                title_font = ImageFont.load_default()
                content_font = title_font

            # 绘制标题背景
            draw.rectangle([(0, 0), (width, 60)], fill=(0, 120, 212))

            # 绘制标题
            draw.text(
                (20, 15), f"【备忘录】{title}", fill=(255, 255, 255), font=title_font
            )

            # 修改: 改进绘制内容行逻辑，正确处理空行
            y_pos = 80
            for index, line in enumerate(content_lines):
                # 安全检查：如果内容将超出图片高度，则停止绘制
                if y_pos + line_height > height - 40:
                    draw.text(
                        (20, y_pos),
                        "...(内容过长已截断)",
                        fill=(100, 100, 100),
                        font=content_font,
                    )
                    y_pos += line_height
                    break

                # 只在非空行时绘制文本，空行只增加间距
                if line:
                    draw.text((20, y_pos), line, fill=(0, 0, 0), font=content_font)

                # 无论行是否为空，都增加垂直位置
                y_pos += line_height

            # 绘制分类和时间
            time_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            category_text = f"分类: {category}" if category else ""
            footer_text = f"{category_text}   修改时间: {time_text}".strip()
            draw.text(
                (20, height - 30),
                footer_text,
                fill=(100, 100, 100),
                font=content_font,
            )

            # 创建临时文件保存图片
            temp_dir = tempfile.gettempdir()
            unique_id = str(uuid.uuid4())[:8]
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            file_name = f"memo_{unique_id}_{timestamp}.png"
            file_path = os.path.join(temp_dir, file_name)
            img.save(file_path)

            # 显示上传中提示
            InfoBar.info(
                title="正在上传图片",
                content="正在将图片上传到云端，请稍候...",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=parent_widget,
            )

            # 上传图片到华为云OBS
            image_url = self._upload_image_to_obs(file_path, file_name)

            if image_url:
                # 生成带图片URL的二维码
                qr_image = self._generate_qrcode_for_url(image_url, platform)

                # 显示成功消息
                InfoBar.success(
                    title="分享图片已创建",
                    content=f"请扫描二维码查看图片并分享给{platform}好友",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=parent_widget,
                )

                # 直接使用标题和指导文本作为Dialog的参数
                dialog = Dialog(
                    f"分享到{platform}",
                    f"请使用{platform}扫描下方二维码查看图片并分享",
                    parent_widget,
                )

                # 隐藏默认按钮
                dialog.yesButton.hide()
                dialog.cancelButton.hide()
                dialog.buttonLayout.insertStretch(0, 1)
                dialog.buttonLayout.insertStretch(1)

                # 设置窗口标志以禁止拖动
                dialog.setWindowFlags(
                    Qt.Dialog  # 基本对话框
                    | Qt.WindowTitleHint  # 有标题栏
                    | Qt.WindowCloseButtonHint  # 有关闭按钮
                )

                dialog.setAttribute(Qt.WA_DeleteOnClose, True)  # 关闭时自动删除

                # 创建主容器和布局
                container = QWidget()
                main_layout = QVBoxLayout(container)
                main_layout.setContentsMargins(20, 0, 20, 20)  # 减小顶部边距
                main_layout.setSpacing(15)

                # 二维码卡片 - 使用特殊样式确保二维码可见
                qr_card = CardWidget()
                qr_layout = QVBoxLayout(qr_card)
                qr_layout.setContentsMargins(15, 15, 15, 15)
                qr_layout.setAlignment(Qt.AlignCenter)

                # 创建一个白色背景容器专门放二维码
                qr_bg = QWidget()
                qr_bg.setObjectName("qrBackground")
                qr_bg.setStyleSheet(
                    "#qrBackground{background-color:white; border-radius:8px;}"
                )
                qr_bg_layout = QVBoxLayout(qr_bg)
                qr_bg_layout.setContentsMargins(10, 10, 10, 10)
                qr_bg_layout.setAlignment(Qt.AlignCenter)

                # 二维码标签
                qr_label = QLabel()
                qr_label.setPixmap(qr_image)
                qr_label.setFixedSize(350, 350)
                qr_label.setAlignment(Qt.AlignCenter)
                qr_bg_layout.addWidget(qr_label)

                # 二维码下方提示文本
                scan_label = CaptionLabel(f"扫描查看「{title}」")
                scan_label.setAlignment(Qt.AlignCenter)
                scan_label.setStyleSheet("color: #505050;")
                qr_bg_layout.addWidget(scan_label)

                qr_layout.addWidget(qr_bg)
                main_layout.addWidget(qr_card)

                # URL信息卡片 - 使用FluentUI样式
                url_card = CardWidget()
                url_layout = QVBoxLayout(url_card)

                # 使用BodyLabel替代QLabel
                url_label = BodyLabel("图片链接:")
                url_layout.addWidget(url_label)

                # 使用TextEdit来显示可选择的文本，自适应主题
                url_text = TextEdit()
                url_text.setPlainText(image_url)
                url_text.setReadOnly(True)
                url_text.setFixedHeight(60)
                url_layout.addWidget(url_text)

                main_layout.addWidget(url_card)

                # 按钮区域 - 使用FluentUI按钮
                button_widget = QWidget()
                button_layout = QHBoxLayout(button_widget)
                button_layout.setContentsMargins(0, 0, 0, 0)
                button_layout.setSpacing(10)

                # 复制图片按钮
                copy_img_button = PrimaryPushButton("复制图片")
                copy_img_button.setIcon(FluentIcon.COPY)
                copy_img_button.clicked.connect(
                    lambda: self._copy_image_to_clipboard(qr_image)
                )

                # 复制链接按钮
                copy_link_button = PrimaryPushButton("复制链接")
                copy_link_button.setIcon(FluentIcon.LINK)
                copy_link_button.clicked.connect(
                    lambda: self._copy_text_to_clipboard(image_url)
                )

                # 关闭按钮
                close_button = PrimaryPushButton("关闭")
                close_button.setIcon(FluentIcon.CLOSE)
                close_button.clicked.connect(dialog.close)

                button_layout.addWidget(copy_img_button)
                button_layout.addWidget(copy_link_button)
                button_layout.addStretch()
                button_layout.addWidget(close_button)

                main_layout.addWidget(button_widget)

                # 将容器添加到对话框
                if dialog.layout():
                    dialog.layout().addWidget(container)

                # 设置对话框大小
                dialog.setFixedSize(500, 650)
                dialog.show()  # 非模态显示

            else:
                # 上传失败，显示本地图片
                InfoBar.warning(
                    title="云端上传失败",
                    content="将显示本地图片",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=parent_widget,
                )

                # 显示本地图片对话框
                self._show_local_image_dialog(file_path, platform, parent_widget)

        except Exception as e:
            print(f"创建分享图片时发生错误: {str(e)}")
            print(traceback.format_exc())

            try:
                parent_widget = QApplication.activeWindow()
                InfoBar.error(
                    title="创建分享图片失败",
                    content=f"错误: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=parent_widget,
                )
            except Exception as inner_error:
                print(f"无法显示错误InfoBar: {str(inner_error)}")

    def _generate_qrcode_for_url(self, url, platform):
        """为URL生成二维码并返回QPixmap"""
        try:
            # 创建二维码 - 修改参数以提高可扫描性
            qr = qrcode.QRCode(
                version=4,  # 提高版本以容纳更多数据
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # 提高错误校正级别
                box_size=12,  # 增加方块大小
                border=5,  # 增加边框宽度
            )
            qr.add_data(url)
            qr.make(fit=True)

            # 生成更大更清晰的二维码图像
            img = qr.make_image(fill_color="black", back_color="white")

            # 确保图像足够大
            img_size = 324  # 设置一个较大的尺寸
            img = img.resize((img_size, img_size))

            # 将PIL图像转换为QPixmap
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            qimage = QPixmap()
            qimage.loadFromData(QByteArray(buffer.getvalue()))

            return qimage

        except Exception as e:
            print(f"生成二维码时发生错误: {str(e)}")
            return QPixmap()

    def _upload_image_to_obs(self, file_path, file_name):
        """上传图片到华为云OBS并返回URL"""
        try:
            # 华为云OBS配置
            ak = "FTCMA0RFFEFYAHZCTUNR"
            sk = "DtOPu5ExOARQuMZHAGewDVzryaH1ht7gSWlflsJ5"
            endpoint = "obs.cn-east-3.myhuaweicloud.com"
            server = f"https://{endpoint}"
            bucket_name = "mypicturebed"

            # 创建OBS客户端
            obs_client = ObsClient(
                access_key_id=ak, secret_access_key=sk, server=server
            )

            try:
                # 读取图片文件
                with open(file_path, "rb") as f:
                    image_content = f.read()

                # 上传到OBS
                object_key = f"memo_share/{file_name}"
                resp = obs_client.putObject(bucket_name, object_key, image_content)

                # 检查上传是否成功
                if resp.status < 300:
                    # 返回可访问的URL - 使用正确的虚拟主机风格URL
                    image_url = f"https://{bucket_name}.{endpoint}/{object_key}"
                    return image_url
                else:
                    print(f"上传失败: {resp.errorCode} - {resp.errorMessage}")
                    return None
            finally:
                # 关闭OBS客户端
                obs_client.close()

        except Exception as e:
            print(f"上传到OBS时发生错误: {str(e)}")
            print(traceback.format_exc())
            return None

    def _show_local_image_dialog(self, file_path, platform, parent_widget):
        """显示本地图片对话框"""
        dialog = QDialog(parent_widget)
        dialog.setWindowTitle(f"分享到{platform}")
        # 设置窗口标志以禁止拖动 - 使用固定位置的对话框
        dialog.setWindowFlags(
            Qt.Dialog  # 基本对话框
            | Qt.WindowTitleHint  # 有标题栏
            | Qt.WindowCloseButtonHint  # 有关闭按钮
            | Qt.MSWindowsFixedSizeDialogHint  # 禁止调整大小 (Windows)
            | Qt.CustomizeWindowHint  # 自定义窗口 - 结合上面的标志限制功能
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)  # 关闭时自动删除
        dialog.resize(650, 500)

        if parent_widget:
            center_point = parent_widget.geometry().center()
            dialog.move(
                center_point.x() - dialog.width() / 2,
                center_point.y() - dialog.height() / 2,
            )
        layout = QVBoxLayout()

        # 说明标签
        instruction_label = QLabel(f"请保存下方图片，并发送给{platform}好友")
        layout.addWidget(instruction_label)

        # 图片标签
        qimage = QPixmap(file_path)
        img_label = QLabel()
        img_label.setPixmap(qimage)
        img_label.setScaledContents(True)
        layout.addWidget(img_label)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 打开图片按钮
        open_button = PrimaryPushButton("打开图片")
        open_button.clicked.connect(lambda: os.startfile(file_path))
        button_layout.addWidget(open_button)

        # 打开文件夹按钮
        open_folder_button = PrimaryPushButton("打开文件夹")
        open_folder_button.clicked.connect(
            lambda: os.startfile(os.path.dirname(file_path))
        )
        button_layout.addWidget(open_folder_button)

        # 复制到剪贴板按钮
        copy_button = PrimaryPushButton("复制图片")
        copy_button.clicked.connect(lambda: self._copy_image_to_clipboard(qimage))
        button_layout.addWidget(copy_button)

        layout.addLayout(button_layout)

        # 显示文件路径
        path_label = QLabel(f"图片保存在: {file_path}")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        dialog.setLayout(layout)
        dialog.show()  # 使用非模态对话框

    def _copy_image_to_clipboard(self, pixmap):
        """复制图片到剪贴板"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)

            parent_widget = QApplication.activeWindow()
            InfoBar.success(
                title="已复制到剪贴板",
                content="图片已复制，可以直接粘贴到聊天窗口",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=parent_widget,
            )
        except Exception as e:
            print(f"复制到剪贴板失败: {str(e)}")

    def _copy_text_to_clipboard(self, text):
        """复制文本到剪贴板"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

            parent_widget = QApplication.activeWindow()
            InfoBar.success(
                title="已复制到剪贴板",
                content="链接已复制，可以直接粘贴分享",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=parent_widget,
            )
        except Exception as e:
            print(f"复制到剪贴板失败: {str(e)}")

    def extract_todos(self):
        """从当前备忘录内容中提取待办事项"""
        if not self.user_id:
            InfoBar.error(title="错误", content="请先登录", parent=self)
            return

        # 获取当前备忘录内容
        memo_content = self.textEdit.toPlainText()
        if not memo_content.strip():
            InfoBar.warning(
                title="提示", content="备忘录内容为空，无法提取待办事项", parent=self
            )
            return

        # 显示加载状态提示
        self.state_tooltip = StateToolTip(
            "正在处理", "AI正在分析备忘录内容，提取待办事项...", parent=self
        )
        self.state_tooltip.move(
            (self.width() - self.state_tooltip.width()) // 2,
            (self.height() - self.state_tooltip.height()) // 2,
        )
        self.state_tooltip.show()
        QApplication.processEvents()

        # 创建一个线程来处理待办提取
        class TodoExtractThread(QThread):
            resultReady = pyqtSignal(int, list)

            def __init__(self, ai_handler, memo_content, user_id):
                super().__init__()
                self.ai_handler = ai_handler
                self.memo_content = memo_content
                self.user_id = user_id

            def run(self):
                count, todos = self.ai_handler.extract_todos_from_memo(
                    self.memo_content, self.user_id
                )
                self.resultReady.emit(count, todos)

        # 创建并启动线程
        self.todo_thread = TodoExtractThread(
            self.ai_handler, memo_content, self.user_id
        )
        self.todo_thread.resultReady.connect(self._on_todos_extracted)
        self.todo_thread.start()

    def _on_todos_extracted(self, count, todos):
        """待办提取完成后的回调"""
        # 关闭加载状态提示
        if hasattr(self, "state_tooltip") and self.state_tooltip:
            self.state_tooltip.setState(True)
            self.state_tooltip.setContent("处理完成")
            QApplication.processEvents()
            # 设置一个短暂的延迟后关闭提示
            QTimer.singleShot(1000, lambda: self.safely_close_tooltip())

        if count > 0:
            InfoBar.success(
                title="提取成功",
                content=f"已成功提取并添加 {count} 个待办事项",
                parent=self,
            )

            # 显示提取结果对话框
            self._show_extracted_todos_dialog(todos)
        else:
            InfoBar.warning(
                title="提示", content="未能从备忘录中识别出待办事项", parent=self
            )

    def _show_extracted_todos_dialog(self, todos):
        """显示提取的待办事项对话框，支持筛选功能"""
        # 创建自定义对话框
        dialog = QDialog(self.window())
        dialog.setWindowTitle("提取的待办事项")
        dialog.resize(500, 600)
        
        # 设置对话框样式
        dialog.setObjectName("ExtractedTodosDialog")
        dialog.setStyleSheet("""
            #ExtractedTodosDialog {
                background-color: white;
                border-radius: 8px;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)  # 增加边距
        main_layout.setSpacing(15)  # 增加间距
        
        # 添加标题和说明文本
        title = TitleLabel("待办事项提取结果")
        title.setAlignment(Qt.AlignCenter)
        description = BodyLabel("以下是从备忘录中提取的待办事项：")
        
        main_layout.addWidget(title)
        main_layout.addWidget(description)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #E0E0E0; height: 1px;")
        main_layout.addWidget(separator)
        
        # 创建选择状态数组
        selected_todos = [True] * len(todos)  # 默认全选
        
        # 添加全选/取消全选复选框
        select_all_layout = QHBoxLayout()
        select_all_checkbox = CheckBox("全选")
        select_all_checkbox.setChecked(True)
        select_all_layout.addWidget(select_all_checkbox)
        select_all_layout.addStretch()
        main_layout.addLayout(select_all_layout)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        # 创建内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        
        # 添加待办列表
        todo_checkboxes = []  # 存储所有复选框的引用
        
        for i, todo in enumerate(todos):
            task = todo.get('task', '')
            deadline = todo.get('deadline', '无截止日期')
            category = todo.get('category', '未分类')
            
            # 创建卡片
            card = CardWidget()
            card.setBorderRadius(8)
            card.setFixedHeight(120)  # 固定高度
            
            # 使用统一的样式
            card.setStyleSheet("""
                CardWidget {
                    background-color: palette(window);
                    border-left: 4px solid palette(highlight);
                }
            """)
            
            # 卡片内部布局
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 10, 15, 10)
            
            # 任务标题行，添加复选框
            title_layout = QHBoxLayout()
            checkbox = CheckBox()
            checkbox.setChecked(True)
            todo_checkboxes.append(checkbox)
            
            task_label = StrongBodyLabel(task)
            task_label.setWordWrap(True)
            
            title_layout.addWidget(checkbox)
            title_layout.addWidget(task_label, 1)
            
            # 编辑按钮
            edit_button = TransparentToolButton(FluentIcon.EDIT)
            edit_button.setFixedSize(24, 24)
            edit_button.setToolTip("编辑待办事项")
            title_layout.addWidget(edit_button)
            
            # 添加编辑功能
            def create_edit_handler(index, current_todo):
                def handle_edit():
                    self._edit_todo_item(dialog, index, current_todo, todos)
                    # 更新UI显示
                    task_label.setText(todos[index].get('task', ''))
                    deadline_label.setText(todos[index].get('deadline', '无截止日期'))
                    category_label.setText(todos[index].get('category', '其他'))
                return handle_edit

            edit_button.clicked.connect(create_edit_handler(i, todo))
            
            # 详细信息行
            details_layout = QHBoxLayout()
            
            # 截止日期
            deadline_icon = IconWidget(FluentIcon.CALENDAR)
            deadline_icon.setFixedSize(16, 16)
            deadline_label = BodyLabel(deadline if deadline else '无截止日期')
            deadline_layout = QHBoxLayout()
            deadline_layout.setSpacing(5)
            deadline_layout.addWidget(deadline_icon)
            deadline_layout.addWidget(deadline_label)
            
            # 类别
            category_icon = IconWidget(FluentIcon.TAG)
            category_icon.setFixedSize(16, 16)
            category_label = BodyLabel(category)
            category_layout = QHBoxLayout()
            category_layout.setSpacing(5)
            category_layout.addWidget(category_icon)
            category_layout.addWidget(category_label)
            
            details_layout.addLayout(deadline_layout)
            details_layout.addStretch(1)
            details_layout.addLayout(category_layout)
            
            # 复选框状态变更处理
            def create_checkbox_handler(index):
                def handle_checkbox_change(state):
                    selected_todos[index] = (state == Qt.Checked)
                    # 更新全选复选框状态，但不触发其信号
                    select_all_checkbox.blockSignals(True)
                    if all(selected_todos):
                        select_all_checkbox.setChecked(True)
                    elif not any(selected_todos):
                        select_all_checkbox.setChecked(False)
                    else:
                        select_all_checkbox.setChecked(False)
                    select_all_checkbox.blockSignals(False)
                return handle_checkbox_change
            
            checkbox.stateChanged.connect(create_checkbox_handler(i))
            
            # 添加到卡片布局
            card_layout.addLayout(title_layout)
            card_layout.addStretch(1)
            card_layout.addLayout(details_layout)
            
            content_layout.addWidget(card)
        
        # 全选/取消全选功能
        def on_select_all_changed(state):
            is_checked = (state == Qt.Checked)
            # 阻止复选框的信号触发，避免循环调用
            for checkbox in todo_checkboxes:
                checkbox.blockSignals(True)
                checkbox.setChecked(is_checked)
                checkbox.blockSignals(False)
            
            # 更新选择状态数组
            for i in range(len(selected_todos)):
                selected_todos[i] = is_checked

        select_all_checkbox.stateChanged.connect(on_select_all_changed)
        
        # 设置滚动区域的内容
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)  # 1表示可伸展比例
        
        # 添加提示
        tip_layout = QHBoxLayout()
        tip_icon = IconWidget(FluentIcon.INFO)
        tip_icon.setFixedSize(16, 16)
        tip = CaptionLabel("勾选您想要添加的待办事项")
        tip_layout.addWidget(tip_icon)
        tip_layout.addWidget(tip)
        tip_layout.addStretch()
        main_layout.addLayout(tip_layout)
        
        # 添加按钮
        button_layout = QHBoxLayout()
        confirm_button = PrimaryPushButton("确定")
        confirm_button.setFixedWidth(120)
        cancel_button = PushButton("取消")
        cancel_button.setFixedWidth(120)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # 确定按钮处理
        def on_confirm():
            # 筛选选中的待办事项
            filtered_todos = [todo for i, todo in enumerate(todos) if selected_todos[i]]
            # 添加到数据库
            added_count = self._add_todos_to_database(filtered_todos)
            InfoBar.success(
                title="添加成功",
                content=f"已添加 {added_count} 个待办事项",
                parent=self
            )
            dialog.accept()
        
        confirm_button.clicked.connect(on_confirm)
        cancel_button.clicked.connect(dialog.reject)
        
        # 显示对话框
        dialog.exec_()

    def safely_close_tooltip(self):
        """安全关闭提示框"""
        try:
            if hasattr(self, "state_tooltip") and self.state_tooltip:
                self.state_tooltip.close()
                self.state_tooltip = None
        except Exception as e:
            print(f"关闭提示框时出错: {str(e)}")

    def _add_todos_to_database(self, todos):
        """将待办事项添加到数据库"""
        from Database import DatabaseManager
        db = DatabaseManager()
        added_count = 0
        
        for todo in todos:
            try:
                task = todo.get("task", "")
                deadline = todo.get("deadline", "")
                category = todo.get("category", "其他")
                
                # 确保任务内容不为空
                if not task:
                    continue
                    
                # 添加到数据库
                todo_id = db.add_todo(
                    user_id=self.user_id,
                    task=task,
                    deadline=deadline,
                    category=category
                )
                
                if todo_id:
                    added_count += 1
                    
            except Exception as e:
                print(f"添加待办事项时出错: {str(e)}")
        
        return added_count

    def _edit_todo_item(self, dialog, index, todo, todos):
        """编辑待办事项"""
        # 创建编辑对话框
        edit_dialog = QDialog(dialog)
        edit_dialog.setWindowTitle("编辑待办事项")
        edit_dialog.resize(400, 300)
        
        # 设置对话框样式
        edit_dialog.setObjectName("EditTodoDialog")
        edit_dialog.setStyleSheet("""
            #EditTodoDialog {
                background-color: white;
                border-radius: 8px;
            }
        """)
        
        # 设置布局
        layout = QVBoxLayout(edit_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 任务内容
        task_label = BodyLabel("任务内容:")
        task_edit = TextEdit()
        task_edit.setPlainText(todo.get('task', ''))
        task_edit.setFixedHeight(80)
        layout.addWidget(task_label)
        layout.addWidget(task_edit)
        
        # 截止日期
        date_label = BodyLabel("截止日期:")
        date_time_layout = QHBoxLayout()
        
        # 解析当前日期和时间
        from datetime import datetime
        from PyQt5.QtCore import QDate, QTime
        
        current_datetime = datetime.now()
        deadline_str = todo.get('deadline', '')
        
        try:
            if deadline_str and deadline_str != '无截止日期':
                deadline_datetime = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
            else:
                deadline_datetime = current_datetime
        except:
            deadline_datetime = current_datetime
        
        # 日期选择器
        date_picker = CalendarPicker()
        date_picker.setDate(QDate(
            deadline_datetime.year,
            deadline_datetime.month,
            deadline_datetime.day
        ))
        
        # 时间选择器
        time_picker = TimePicker()
        time_picker.setTime(QTime(
            deadline_datetime.hour,
            deadline_datetime.minute
        ))
        
        date_time_layout.addWidget(date_picker)
        date_time_layout.addWidget(time_picker)
        
        layout.addWidget(date_label)
        layout.addLayout(date_time_layout)
        
        # 类别
        category_label = BodyLabel("类别:")
        category_combo = ComboBox()
        category_combo.addItems(["工作", "学习", "生活", "其他"])
        category_combo.setCurrentText(todo.get('category', '其他'))
        layout.addWidget(category_label)
        layout.addWidget(category_combo)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_button = PrimaryPushButton("保存")
        cancel_button = PushButton("取消")
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)
        
        layout.addStretch()
        layout.addLayout(button_layout)
        
        # 保存编辑
        def on_save():
            # 获取编辑后的值
            task = task_edit.toPlainText().strip()
            if not task:
                InfoBar.error(
                    title="错误",
                    content="任务内容不能为空",
                    parent=edit_dialog
                )
                return
            
            # 获取日期时间
            selected_date = date_picker.getDate().toString("yyyy-MM-dd")
            selected_time = time_picker.getTime().toString("hh:mm")
            deadline = f"{selected_date} {selected_time}"
            
            # 更新待办事项
            todos[index] = {
                'task': task,
                'deadline': deadline,
                'category': category_combo.currentText()
            }
            
            edit_dialog.accept()
        
        save_button.clicked.connect(on_save)
        cancel_button.clicked.connect(edit_dialog.reject)
        
        # 显示对话框
        edit_dialog.exec_()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = MemoInterface()
    w.show()
    sys.exit(app.exec_())
