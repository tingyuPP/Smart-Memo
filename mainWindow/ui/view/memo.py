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
    ComboBox,
    ScrollArea,
    VBoxLayout
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
from Database import DatabaseManager 
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
from mainWindow.ui.view.todo_extractor import TodoExtractor


class MemoInterface(Ui_memo, QWidget):
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.db = DatabaseManager()
        self.user_id = user_id

        self.ai_handler = AIHandler.get_instance(self)
        if self.user_id:  
            self.ai_handler.ai_service.build_memory_context(self.user_id, self.db)

        self.memory_update_timer = QTimer(self)
        self.memory_update_timer.timeout.connect(self._update_memory_context)
        self.memory_update_timer.start(1 * 60 * 1000) 

        self.memo_id = None  

        self.frame_2.addAction(
            Action(
                FluentIcon.ROBOT,
                "AI编辑",
                triggered=lambda: self.ai_handler.show_ai_menu(self.textEdit),
            )
        )

        self.frame_2.addSeparator()

        save_action = Action(FluentIcon.SAVE, "保存")
        save_action.triggered.connect(self.save_memo)
        self.frame_2.addActions(
            [
                save_action,
                Action(FluentIcon.DELETE, "清空", triggered=self.clear_memo),
            ]
        )

        self.frame_2.addSeparator()

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
            layout = VBoxLayout(self.frame)
            layout.setContentsMargins(30, 40, 30, 20)
            self.frame.setLayout(layout)

        self.textEdit = SmartTextEdit(self)

        layout.addWidget(self.textEdit)

        for i in range(layout.count()):
            if layout.itemAt(i).widget() == self.textEdit:
                layout.removeWidget(self.textEdit)
                self.textEdit.setParent(None)  # 解除父子关系
                break

        layout.addWidget(
            self.textEdit, 1, 0
        )  

        self.textEdit.textChanged.connect(self.update_markdown_preview)
        self.textEdit.textChanged.connect(self.update_word_count)

        self.update_markdown_preview()
        self.update_word_count()
        self.update_tag_combobox()

        self.todo_extractor = TodoExtractor(self)

    def _update_memory_context(self):
        """定期更新AI记忆上下文"""
        try:
            if (
                self.user_id
                and hasattr(self, "ai_handler")
                and hasattr(self.ai_handler, "ai_service")
            ):
                self.ai_handler.ai_service.build_memory_context(self.user_id, self.db)
        except Exception:
            pass  

    def showEvent(self, event):
        """当窗口显示时调用"""

        self.update_tag_combobox()

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
        current_tag = self.lineEdit_2.text()

        tag_names = self.load_user_tags()

        self.lineEdit_2.clear()

        self.lineEdit_2.addItems(tag_names)

        if current_tag and current_tag in tag_names:
            index = self.lineEdit_2.findText(current_tag)
            if index >= 0:
                self.lineEdit_2.setCurrentIndex(index)

    def toggle_markdown_preview(self):
        """切换Markdown预览模式"""
        try:

            content = self.textEdit.toPlainText()
            self._current_content = content

            if not self._markdown_preview_enabled:
                self.textEdit.setMarkdown(content)
                self._markdown_preview_enabled = True

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
                self.textEdit.setText(self._current_content)
                self._markdown_preview_enabled = False

                self.frame_2.actions()[-1].setText("Markdown预览")

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
            if not silent:  
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
            if self.memo_id is None:
                memo_id = self.db.create_memo(self.user_id, title, content, category)
                if memo_id:
                    self.memo_id = memo_id  
                    if not silent:  
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
                success = self.db.update_memo(
                    self.memo_id, title=title, content=content, category=category
                )
                if success:
                    if not silent:  
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

        if self.save_memo(silent=True): 
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

        if self.save_memo(silent=True):  
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

            default_filename = f"{self.lineEdit.text()}.pdf"
            default_path = os.path.join(default_dir, default_filename)

            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出为PDF", default_path, "PDF Files (*.pdf)"
            )

            if not file_path:  
                return

            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)

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

            document.print_(printer)

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

            default_filename = f"{self.lineEdit.text()}.txt"
            default_path = os.path.join(default_dir, default_filename)

            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出为TXT", default_path, "Text Files (*.txt)"
            )

            if not file_path: 
                return

            with open(file_path, "w", encoding="utf-8") as f:
                category = self.lineEdit_2.text()
                f.write(f"标题: {self.lineEdit.text()}\n\n")
                f.write(f"{self.textEdit.toPlainText()}\n\n")
                if category:
                    f.write(f"分类: {category}\n")

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
            parent_widget = QApplication.activeWindow()

            title = self.lineEdit.text()
            content = self.textEdit.toPlainText()  
            category = self.lineEdit_2.text()

            width = 800

            content_lines = []
            char_width = 16
            chars_per_line = (width - 40) // char_width

            paragraphs = content.split("\n")

            for paragraph in paragraphs:
                if not paragraph:
                    content_lines.append("")
                    continue

                current_line = ""
                for char in paragraph:
                    current_line += char
                    if len(current_line) >= chars_per_line:
                        content_lines.append(current_line)
                        current_line = ""

                if current_line:
                    content_lines.append(current_line)

            line_height = 22
            total_lines = len(content_lines)
            content_height = total_lines * line_height
            height = 60 + content_height + 50

            height = max(400, min(height, 2000))  

            img = Image.new("RGB", (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            try:
                title_font = ImageFont.truetype("msyh.ttc", 24) 
                content_font = ImageFont.truetype("msyh.ttc", 16)
            except Exception:
                title_font = ImageFont.load_default()
                content_font = title_font

            draw.rectangle([(0, 0), (width, 60)], fill=(0, 120, 212))

            draw.text(
                (20, 15), f"【备忘录】{title}", fill=(255, 255, 255), font=title_font
            )

            y_pos = 80
            for index, line in enumerate(content_lines):
                if y_pos + line_height > height - 40:
                    draw.text(
                        (20, y_pos),
                        "...(内容过长已截断)",
                        fill=(100, 100, 100),
                        font=content_font,
                    )
                    y_pos += line_height
                    break
                if line:
                    draw.text((20, y_pos), line, fill=(0, 0, 0), font=content_font)

                y_pos += line_height

            time_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            category_text = f"分类: {category}" if category else ""
            footer_text = f"{category_text}   修改时间: {time_text}".strip()
            draw.text(
                (20, height - 30),
                footer_text,
                fill=(100, 100, 100),
                font=content_font,
            )

            temp_dir = tempfile.gettempdir()
            unique_id = str(uuid.uuid4())[:8]
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            file_name = f"memo_{unique_id}_{timestamp}.png"
            file_path = os.path.join(temp_dir, file_name)
            img.save(file_path)

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

                InfoBar.success(
                    title="分享图片已创建",
                    content=f"请扫描二维码查看图片并分享给{platform}好友",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=parent_widget,
                )

                dialog = Dialog(
                    f"分享到{platform}",
                    f"请使用{platform}扫描下方二维码查看图片并分享",
                    parent_widget,
                )

                dialog.yesButton.hide()
                dialog.cancelButton.hide()
                dialog.buttonLayout.insertStretch(0, 1)
                dialog.buttonLayout.insertStretch(1)

                dialog.setWindowFlags(
                    Qt.Dialog  
                    | Qt.WindowTitleHint  
                    | Qt.WindowCloseButtonHint  
                )

                dialog.setAttribute(Qt.WA_DeleteOnClose, True)  

                container = QWidget()
                main_layout = VBoxLayout(container)
                main_layout.setContentsMargins(20, 0, 20, 20)  
                main_layout.setSpacing(15)

                # 二维码卡片 - 使用特殊样式确保二维码可见
                qr_card = CardWidget()
                qr_layout = VBoxLayout(qr_card)
                qr_layout.setContentsMargins(15, 15, 15, 15)
                qr_layout.setAlignment(Qt.AlignCenter)

                # 创建一个白色背景容器专门放二维码
                qr_bg = QWidget()
                qr_bg.setObjectName("qrBackground")
                qr_bg.setStyleSheet(
                    "#qrBackground{background-color:white; border-radius:8px;}"
                )
                qr_bg_layout = VBoxLayout(qr_bg)
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
                url_layout = VBoxLayout(url_card)

                url_label = BodyLabel("图片链接:")
                url_layout.addWidget(url_label)

                url_text = TextEdit()
                url_text.setPlainText(image_url)
                url_text.setReadOnly(True)
                url_text.setFixedHeight(60)
                url_layout.addWidget(url_text)

                main_layout.addWidget(url_card)

                # 按钮区域 
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

                dialog.setFixedSize(500, 650)
                dialog.show()  # 非模态显示

            else:
                InfoBar.warning(
                    title="云端上传失败",
                    content="将显示本地图片",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=parent_widget,
                )

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
            # 创建二维码 
            qr = qrcode.QRCode(
                version=4,  
                error_correction=qrcode.constants.ERROR_CORRECT_H,  
                box_size=12,  
                border=5,  
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            img_size = 324  
            img = img.resize((img_size, img_size))

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
            Qt.Dialog  
            | Qt.WindowTitleHint  
            | Qt.WindowCloseButtonHint  
            | Qt.MSWindowsFixedSizeDialogHint  
            | Qt.CustomizeWindowHint  
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose, True) 
        dialog.resize(650, 500)

        if parent_widget:
            center_point = parent_widget.geometry().center()
            dialog.move(
                center_point.x() - dialog.width() / 2,
                center_point.y() - dialog.height() / 2,
            )
        layout = VBoxLayout()

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

        open_button = PrimaryPushButton("打开图片")
        open_button.clicked.connect(lambda: os.startfile(file_path))
        button_layout.addWidget(open_button)

        open_folder_button = PrimaryPushButton("打开文件夹")
        open_folder_button.clicked.connect(
            lambda: os.startfile(os.path.dirname(file_path))
        )
        button_layout.addWidget(open_folder_button)

        copy_button = PrimaryPushButton("复制图片")
        copy_button.clicked.connect(lambda: self._copy_image_to_clipboard(qimage))
        button_layout.addWidget(copy_button)

        layout.addLayout(button_layout)

        path_label = QLabel(f"图片保存在: {file_path}")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        dialog.setLayout(layout)
        dialog.show()  

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

        memo_content = self.textEdit.toPlainText()

        self.todo_extractor.extract_todos(memo_content, self.user_id, self.ai_handler)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = MemoInterface()
    w.show()
    sys.exit(app.exec_())
