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

import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import tempfile
from obs import ObsClient
import traceback
import uuid
import datetime
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QByteArray, Qt, QPoint, QSize, QRect, pyqtSlot, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QFrame, QDialog

from mainWindow.ui.view.smart_text_edit import SmartTextEdit

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
        try:
            # 获取当前活动窗口
            parent_widget = QApplication.activeWindow()

            # 准备要分享的内容
            title = self.lineEdit.text()
            content = self.textEdit.toPlainText()
            category = self.lineEdit_2.text()

            # 创建图片
            width, height = 600, 400
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
            draw.text((20, 15), f"【备忘录】{title}", fill=(255, 255, 255), font=title_font)

            # 文本换行处理和绘制内容
            content_lines = []
            current_line = ""
            char_width = 16
            chars_per_line = (width - 40) // char_width

            for char in content:
                if len(current_line) >= chars_per_line or char == "\n":
                    content_lines.append(current_line)
                    current_line = ""
                current_line += char

            if current_line:
                content_lines.append(current_line)

            # 绘制内容行
            y_pos = 80
            for line in content_lines[:15]:
                draw.text((20, y_pos), line, fill=(0, 0, 0), font=content_font)
                y_pos += 22

            # 如果内容被截断，添加提示
            if len(content_lines) > 15:
                draw.text(
                    (20, y_pos),
                    "...(内容已截断)",
                    fill=(100, 100, 100),
                    font=content_font,
                )
                y_pos += 22

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

                # 创建一个非模态对话框
                dialog = QDialog(parent_widget)
                dialog.setWindowTitle(f"分享到{platform}")
                dialog.setWindowFlag(Qt.WindowCloseButtonHint, True)  # 确保有关闭按钮
                dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)  # 移除帮助按钮
                dialog.setAttribute(Qt.WA_DeleteOnClose, True)  # 关闭时自动删除
                dialog.setFixedSize(500, 620)  # 固定大小

                # 创建美化后的布局
                main_layout = QVBoxLayout()
                main_layout.setContentsMargins(20, 20, 20, 20)
                main_layout.setSpacing(15)

                # 顶部标题部分
                title_widget = QWidget()
                title_layout = QHBoxLayout(title_widget)
                title_layout.setContentsMargins(0, 0, 0, 0)

                # 添加图标
                icon_label = QLabel()
                icon_label.setPixmap(FluentIcon.SHARE.icon().pixmap(32, 32))
                title_layout.addWidget(icon_label)

                # 添加标题文本
                title_label = TitleLabel(f"分享到{platform}")
                title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
                title_layout.addWidget(title_label)
                title_layout.addStretch()

                main_layout.addWidget(title_widget)

                # 分隔线
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setStyleSheet("background-color: #E0E0E0;")
                main_layout.addWidget(line)

                # 说明文本框
                instruction_card = CardWidget()
                instruction_layout = QVBoxLayout(instruction_card)
                instruction_icon = QLabel()
                instruction_icon.setPixmap(FluentIcon.INFO.icon().pixmap(24, 24))
                instruction_text = QLabel(f"请使用{platform}扫描下方二维码查看图片并分享")
                instruction_text.setWordWrap(True)
                instruction_text.setStyleSheet("color: #505050; margin: 5px;")

                info_layout = QHBoxLayout()
                info_layout.addWidget(instruction_icon)
                info_layout.addWidget(instruction_text, 1)
                instruction_layout.addLayout(info_layout)

                main_layout.addWidget(instruction_card)

                # 二维码卡片
                qr_card = CardWidget()
                qr_card.setStyleSheet("background-color: white; border-radius: 8px;")
                qr_layout = QVBoxLayout(qr_card)
                qr_layout.setContentsMargins(10, 10, 10, 10)
                qr_layout.setAlignment(Qt.AlignCenter)

                # 二维码标签
                qr_label = QLabel()
                qr_label.setPixmap(qr_image)
                qr_label.setScaledContents(True)
                qr_label.setFixedSize(320, 320)
                qr_label.setAlignment(Qt.AlignCenter)
                qr_label.setStyleSheet("border: 1px solid #E0E0E0;")
                qr_layout.addWidget(qr_label)

                # 二维码下方提示文本
                scan_label = CaptionLabel(f"扫描查看「{title}」")
                scan_label.setAlignment(Qt.AlignCenter)
                qr_layout.addWidget(scan_label)

                main_layout.addWidget(qr_card)

                # URL信息卡片
                url_card = CardWidget()
                url_layout = QVBoxLayout(url_card)
                url_label = QLabel("图片链接:")
                url_text = QLabel(image_url)
                url_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
                url_text.setWordWrap(True)
                url_text.setStyleSheet(
                    "background-color: #F5F5F5; padding: 8px; border-radius: 4px;"
                )

                url_layout.addWidget(url_label)
                url_layout.addWidget(url_text)

                main_layout.addWidget(url_card)

                # 按钮区域
                button_widget = QWidget()
                button_layout = QHBoxLayout(button_widget)
                button_layout.setContentsMargins(0, 0, 0, 0)
                button_layout.setSpacing(10)

                # 复制图片按钮
                copy_img_button = PrimaryPushButton("复制图片")
                copy_img_button.setIcon(FluentIcon.COPY.icon())
                copy_img_button.clicked.connect(
                    lambda: self._copy_image_to_clipboard(qr_image)
                )

                # 复制链接按钮
                copy_link_button = PrimaryPushButton("复制链接")
                copy_link_button.setIcon(FluentIcon.LINK.icon())
                copy_link_button.clicked.connect(
                    lambda: self._copy_text_to_clipboard(image_url)
                )

                # 关闭按钮
                close_button = PrimaryPushButton("关闭")
                close_button.setIcon(FluentIcon.CLOSE.icon())
                close_button.clicked.connect(dialog.close)

                button_layout.addWidget(copy_img_button)
                button_layout.addWidget(copy_link_button)
                button_layout.addStretch()
                button_layout.addWidget(close_button)

                main_layout.addWidget(button_widget)

                dialog.setLayout(main_layout)
                dialog.show()  # 使用show()而不是exec_()，这样对话框是非模态的

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
            obs_client = ObsClient(access_key_id=ak, secret_access_key=sk, server=server)

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


    def _generate_qrcode_for_url(self, url, platform):
        """为URL生成二维码并返回QPixmap"""
        try:
            # 创建二维码
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # 生成二维码图像
            img = qr.make_image(fill_color="black", back_color="white")

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


    def _show_local_image_dialog(self, file_path, platform, parent_widget):
        """显示本地图片对话框"""
        dialog = QDialog(parent_widget)
        dialog.setWindowTitle(f"分享到{platform}")
        dialog.setWindowFlag(Qt.WindowCloseButtonHint, True)
        dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog.resize(650, 500)

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
        open_folder_button.clicked.connect(lambda: os.startfile(os.path.dirname(file_path)))
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


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = memoInterface()
    w.show()
    sys.exit(app.exec_())
