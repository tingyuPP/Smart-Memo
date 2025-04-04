# coding:utf-8
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialog,
    QApplication,
)
from PyQt5.QtCore import Qt, QByteArray
from PyQt5.QtGui import QPixmap

from qfluentwidgets import (
    CardWidget,
    BodyLabel,
    CaptionLabel,
    PrimaryPushButton,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    TextEdit,
    Dialog,
)

import os
import traceback
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode

from mainWindow.ui.components.mainpage.cloud_storage import CloudStorageManager


class CardShareManager:
    """备忘录卡片分享管理器，负责处理分享到社交媒体的功能"""

    @staticmethod
    def generate_share_image(title, content, time_text, platform, parent_widget=None):
        """创建分享图片并显示"""
        try:
            if parent_widget is None:
                parent_widget = QApplication.activeWindow()

            # 图片尺寸和文本处理参数
            width = 800
            char_width = 16
            chars_per_line = (width - 40) // char_width

            # 文本换行处理
            content_lines = []
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

            # 计算图片高度
            line_height = 22
            total_lines = len(content_lines)
            content_height = total_lines * line_height
            height = 60 + content_height + 50
            height = max(400, min(height, 2000))  # 最小400px，最大2000px

            # 创建图片
            img = Image.new("RGB", (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            # 尝试加载字体
            try:
                title_font = ImageFont.truetype("msyh.ttc", 24)  # 微软雅黑
                content_font = ImageFont.truetype("msyh.ttc", 16)
            except Exception:
                title_font = ImageFont.load_default()
                content_font = title_font

            # 绘制标题背景和标题
            draw.rectangle([(0, 0), (width, 60)], fill=(0, 120, 212))
            draw.text(
                (20, 15), f"【备忘录】{title}", fill=(255, 255, 255), font=title_font
            )

            # 绘制内容
            y_pos = 80
            for line in content_lines:
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

            # 绘制时间
            draw.text(
                (20, height - 30),
                f"修改时间: {time_text}",
                fill=(100, 100, 100),
                font=content_font,
            )

            # 保存图片到临时文件
            file_path, file_name = CloudStorageManager.get_temp_file_path()
            img.save(file_path)

            # 显示上传提示
            InfoBar.info(
                title="正在上传图片",
                content="正在将图片上传到云端，请稍候...",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=parent_widget,
            )

            # 上传到云存储
            image_url = CloudStorageManager.upload_to_obs(file_path, file_name)

            if image_url:
                # 生成二维码
                qr_image = CardShareManager.generate_qrcode(image_url)

                # 显示成功提示
                InfoBar.success(
                    title="分享图片已创建",
                    content=f"请扫描二维码查看图片并分享给{platform}好友",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=parent_widget,
                )

                # 显示分享对话框
                CardShareManager.show_share_dialog(
                    platform, title, qr_image, image_url, parent_widget
                )
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
                CardShareManager.show_local_image_dialog(
                    file_path, platform, parent_widget
                )

            return True
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

            return False

    @staticmethod
    def generate_qrcode(url):
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

            # 生成二维码图像
            img = qr.make_image(fill_color="black", back_color="white")
            img_size = 324
            img = img.resize((img_size, img_size))

            # 转换为QPixmap
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            qimage = QPixmap()
            qimage.loadFromData(QByteArray(buffer.getvalue()))
            return qimage

        except Exception as e:
            print(f"生成二维码时发生错误: {str(e)}")
            return QPixmap()

    @staticmethod
    def show_share_dialog(platform, title, qr_image, image_url, parent_widget):
        """显示带二维码的分享对话框"""
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

        # 设置窗口标志
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)

        # 创建主容器和布局
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 0, 20, 20)
        main_layout.setSpacing(15)

        # 二维码卡片
        qr_card = CardWidget()
        qr_layout = QVBoxLayout(qr_card)
        qr_layout.setContentsMargins(15, 15, 15, 15)
        qr_layout.setAlignment(Qt.AlignCenter)

        # 白色背景容器
        qr_bg = QWidget()
        qr_bg.setObjectName("qrBackground")
        qr_bg.setStyleSheet("#qrBackground{background-color:white; border-radius:8px;}")
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

        # URL信息卡片
        url_card = CardWidget()
        url_layout = QVBoxLayout(url_card)

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
            lambda: CardShareManager.copy_image_to_clipboard(qr_image)
        )

        # 复制链接按钮
        copy_link_button = PrimaryPushButton("复制链接")
        copy_link_button.setIcon(FluentIcon.LINK)
        copy_link_button.clicked.connect(
            lambda: CardShareManager.copy_text_to_clipboard(image_url)
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
        dialog.show()

    @staticmethod
    def show_local_image_dialog(file_path, platform, parent_widget):
        """显示本地图片对话框"""
        dialog = QDialog(parent_widget)
        dialog.setWindowTitle(f"分享到{platform}")

        # 设置窗口标志
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
                center_point.x() - dialog.width() // 2,
                center_point.y() - dialog.height() // 2,
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
        copy_button.clicked.connect(
            lambda: CardShareManager.copy_image_to_clipboard(qimage)
        )
        button_layout.addWidget(copy_button)

        layout.addLayout(button_layout)

        # 显示文件路径
        path_label = QLabel(f"图片保存在: {file_path}")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        dialog.setLayout(layout)
        dialog.show()

    @staticmethod
    def copy_image_to_clipboard(pixmap):
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

    @staticmethod
    def copy_text_to_clipboard(text):
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
