# coding:utf-8
from PyQt5.QtGui import QTextDocument
from PyQt5.QtWidgets import (
    QWidget,
    QMenu,
    QAction,
    QDialog,
    QVBoxLayout,
    QLabel,
    QFrame,
)
from qfluentwidgets import FluentIcon

from mainWindow.ui.view.Ui_mainpage import Ui_mainwindow

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
    SubtitleLabel,
    InfoBarPosition,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QScrollArea,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QPoint, QSize, QRect, QTimer, QByteArray, QThread, pyqtSignal
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QFont, QColor, QPixmap

import sys
import os
import qrcode
from io import BytesIO
from Database import DatabaseManager  # 导入数据库管理类
from config import cfg
from PIL import Image, ImageDraw, ImageFont
import tempfile
from obs import ObsClient
import traceback
import uuid
import datetime


class AppCard(CardWidget):
    def __init__(
        self,
        title,
        content,
        memo_id=None,
        modified_time=None,
        category=None,
        parent=None,
        timer=None,
    ):
        super().__init__(parent)
        self.modified_time = modified_time
        self.category = category
        self.memo_id = memo_id
        self.timer=timer    
        self.full_content = content
        self.setup_ui(title, content)
        self.setup_context_menu()
        self.clicked.connect(self.on_double_clicked)  # 连接双击信号
        self.moreButton.clicked.connect(
            self.showContextMenu
        )  # 连接 moreButton 的点击信号

    def setup_ui(self, title, content):
        # 文本区域
        self.titleLabel = SubtitleLabel(title, self)
        # 只在UI中显示截断内容，完整内容已存储在self.full_content中
        truncated_content = content[:20] + "..." if len(content) > 20 else content
        self.contentLabel = BodyLabel(truncated_content, self)
        self.contentLabel.setWordWrap(True)

        # 操作按钮
        # self.openButton = PrimaryPushButton("打开", self)  # 注释掉 openButton
        self.moreButton = TransparentToolButton(FluentIcon.MORE, self)

        # 时间标签
        if self.modified_time:
            self.timeLabel = CaptionLabel(str(self.modified_time), self)
        else:
            self.timeLabel = CaptionLabel("No time", self)

        # 布局系统
        self.mainLayout = QHBoxLayout(self)
        self.textLayout = QVBoxLayout()
        self.rightActions = QHBoxLayout()

        self.construct_layout()

    def construct_layout(self):
        # 中间文本
        self.mainLayout.addSpacing(15)

        self.textLayout.addWidget(self.titleLabel)
        self.textLayout.addWidget(self.contentLabel)
        self.textLayout.addWidget(self.timeLabel)
        # self.textLayout.addWidget(self.categoryLabel)
        self.mainLayout.addLayout(self.textLayout)

        # 右侧操作区
        # self.rightActions.addWidget(self.openButton)  # 注释掉 openButton
        self.rightActions.addWidget(self.moreButton)
        self.rightActions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.mainLayout.addLayout(self.rightActions)

        # 尺寸策略
        self.setFixedHeight(96)
        # self.openButton.setFixedWidth(80)  # 注释掉 openButton
        self.moreButton.setFixedSize(40, 40)

        # 边距调整
        self.mainLayout.setContentsMargins(16, 8, 16, 8)
        self.textLayout.setContentsMargins(0, 2, 0, 2)
        self.textLayout.setSpacing(4)

    def setup_context_menu(self):
        if self.timer:
            self.timer.stop()
        self.menu = RoundMenu(parent=self)

        # 逐个添加动作，Action 继承自 QAction，接受 FluentIconBase 类型的图标
        self.menu.addAction(
            Action(
                FluentIcon.DELETE,
                "删除",
                triggered=lambda: print("删除成功"),
            )
        )
        self.menu.addAction(
            Action(FluentIcon.ACCEPT, "收藏", triggered=lambda: print("收藏成功"))
        )
        # 添加分割线
        self.menu.addSeparator()

        # 导出为子菜单
        export_submenu = RoundMenu("导出为", self)
        export_submenu.setIcon(FluentIcon.PRINT)  # 设置图标
        export_submenu.addActions(
            [
                Action("PDF", triggered=self.export_to_pdf),  # 导出为 PDF
                Action("TXT", triggered=self.export_to_txt),  # 导出为 TXT
            ]
        )
        self.menu.addMenu(export_submenu)

        # 分享到子菜单
        share_submenu = RoundMenu("分享到", self)
        share_submenu.setIcon(FluentIcon.SHARE)  # 设置图标
        share_submenu.addActions(
            [
                Action("微信", triggered=self.share_to_wechat),  # 分享到微信
                Action("QQ", triggered=self.share_to_qq),  # 分享到 QQ
            ]
        )
        self.menu.addMenu(share_submenu)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # if self.timer:
        #     self.timer.start(6000)
        # self.customContextMenuRequested.connect(self.showContextMenu)  # 注释掉这行

    def showContextMenu(self, pos):
        self.menu.exec_(
            self.moreButton.mapToGlobal(QPoint(0, self.moreButton.height()))
        )

    def on_double_clicked(self):
        # 在这里编写双击 AppCard 后要执行的操作
        print(f"AppCard 双击! Title: {self.titleLabel.text()}")
        # 您可以在这里添加打开应用程序或执行其他操作的代码
        main_window = self.window()

        # 判断主窗口是否有switch_to_newmemo_interface方法
        if hasattr(main_window, "switch_to_newmemo_interface"):
            # 首先跳转到memo界面
            main_window.switch_to_newmemo_interface()

            # 将当前备忘录信息传递给memo界面
            if hasattr(main_window, "memoInterface"):
                # 设置memo_id，用于后续保存时更新而非创建新备忘录
                main_window.memoInterface.memo_id = self.memo_id

                # 填充标题
                main_window.memoInterface.lineEdit.setText(self.titleLabel.text())

                # 填充内容 - 使用完整内容而非截断版本
                main_window.memoInterface.textEdit.setText(self.full_content)

                # 设置分类信息（如果有）
                if hasattr(self, "category") and self.category:
                    main_window.memoInterface.lineEdit_2.setText(self.category)

                # 更新字数统计
                main_window.memoInterface.update_word_count()

                InfoBar.success(
                    title="备忘录已加载",
                    content=f"正在编辑「{self.titleLabel.text()}」",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=main_window.memoInterface,
                )

    def share_to_wechat(self):
        """创建微信分享图片"""
        self._generate_share_image("微信")

    def share_to_qq(self):
        """创建QQ分享图片"""
        self._generate_share_image("QQ")

    def _generate_share_image(self, platform):
        """创建分享图片并显示"""
        try:
            # 获取当前活动窗口
            parent_widget = QApplication.activeWindow()

            # 准备要分享的内容
            title = self.titleLabel.text()

            # 优先使用存储的完整内容
            content = self.full_content

            # 如果完整内容为空或需要更新，尝试从数据库获取
            if not content and hasattr(self, "memo_id") and self.memo_id:
                main_window = self.window()
                if hasattr(main_window, "db"):
                    try:
                        # 直接使用memo_id获取备忘录内容
                        main_window.db.cursor.execute(
                            "SELECT title, content FROM memos WHERE id = ?",
                            (self.memo_id,),
                        )
                        result = main_window.db.cursor.fetchone()
                        if result:
                            # 找到记录，解密内容
                            content = main_window.db.decrypt(result[1])
                            # 更新存储的完整内容
                            self.full_content = content
                    except Exception as e:
                        print(f"获取完整内容时出错: {str(e)}")
                        traceback.print_exc()

            # 记录时间
            time_text = self.timeLabel.text()

            # 修改: 改进文本换行处理逻辑，修复重叠问题
            content_lines = []
            width = 800  # 固定宽度
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
            draw.text((20, 15), f"【备忘录】{title}", fill=(255, 255, 255), font=title_font)

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

            # 绘制时间 - 始终在底部
            draw.text(
                (20, height - 30),
                f"修改时间: {time_text}",
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

                # 创建一个非模态对话框，设置合适的标志以防止关闭时退出应用
                dialog = QDialog(parent_widget)
                dialog.setWindowTitle(f"分享到{platform}")
                # 设置窗口标志以禁止拖动 - 使用固定位置的对话框
                dialog.setWindowFlags(
                    Qt.Dialog |  # 基本对话框
                    Qt.WindowTitleHint |  # 有标题栏
                    Qt.WindowCloseButtonHint |  # 有关闭按钮
                    Qt.MSWindowsFixedSizeDialogHint |  # 禁止调整大小 (Windows)
                    Qt.CustomizeWindowHint  # 自定义窗口 - 结合上面的标志限制功能
                )
                
                dialog.setAttribute(Qt.WA_DeleteOnClose, True)  # 关闭时自动删除
                dialog.setFixedSize(500, 650)  # 增加高度以适应更大的二维码



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
                title_label = SubtitleLabel(f"分享到{platform}")
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

                # 二维码标签 - 修改以显示更好的二维码
                qr_label = QLabel()
                qr_label.setPixmap(qr_image)
                qr_label.setScaledContents(False)  # 避免二维码变形
                qr_label.setFixedSize(350, 350)  # 增加尺寸
                qr_label.setAlignment(Qt.AlignCenter)
                qr_label.setStyleSheet(
                    "background-color: white; border: 1px solid #E0E0E0;"
                )
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

                # 显示本地图片对话框 (使用美化后的本地图片对话框)
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
            endpoint = "obs.cn-east-3.myhuaweicloud.com"  # 修改变量名以更清晰
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
                    # 格式: https://<bucket-name>.<endpoint>/<object-key>
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

    def _show_local_image_dialog(self, file_path, platform, parent_widget):
        """显示本地图片对话框"""
        dialog = QDialog(parent_widget)
        dialog.setWindowTitle(f"分享到{platform}")
        # 设置窗口标志以禁止拖动 - 使用固定位置的对话框
        dialog.setWindowFlags(
            Qt.Dialog |  # 基本对话框
            Qt.WindowTitleHint |  # 有标题栏
            Qt.WindowCloseButtonHint |  # 有关闭按钮
            Qt.MSWindowsFixedSizeDialogHint |  # 禁止调整大小 (Windows)
            Qt.CustomizeWindowHint  # 自定义窗口 - 结合上面的标志限制功能
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)  # 关闭时自动删除
        # dialog.setAttribute(Qt.WA_DoubleBuffering, True)  # 启用双缓冲
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

            default_filename = f"{self.titleLabel.text()}.pdf"
            default_path = os.path.join(default_dir, default_filename)

            # 停止定时器
            if self.timer:
                self.timer.stop()

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出为PDF", default_path, "PDF Files (*.pdf)"
            )

            # 启动定时器
            if self.timer:
                self.timer.start(1000)

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
                parent=self.window(),
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
            self.export_thread = ExportThread(
                self.titleLabel.text(),
                self.full_content,
                self.timeLabel.text(),
                file_path,
            )

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
                        parent=self.window(),
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
                        parent=self.window(),
                    )

            self.export_thread.exportFinished.connect(on_export_finished)
            self.export_thread.start()

        except Exception as e:
            # 使用InfoBar显示错误消息
            InfoBar.warning(
                title="导出失败",
                content=f"准备导出PDF时发生错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )

    def export_to_txt(self):
        """导出备忘录为TXT文件"""
        try:
            # 获取默认导出目录
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

            default_filename = f"{self.titleLabel.text()}.txt"
            default_path = os.path.join(default_dir, default_filename)

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出为TXT", default_path, "Text Files (*.txt)"
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
                parent=self.window(),
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
                        # 写入TXT文件 - 使用完整内容而非截断内容
                        with open(self.file_path, "w", encoding="utf-8") as f:
                            f.write(f"标题: {self.title}\n\n")
                            f.write(f"{self.content}\n\n")
                            f.write(f"修改时间: {self.time_text}")
                        self.exportFinished.emit(True, "")
                    except Exception as e:
                        self.exportFinished.emit(False, str(e))

            # 创建并启动线程
            self.export_thread = ExportThread(
                self.titleLabel.text(),
                self.full_content,
                self.timeLabel.text(),
                file_path,
            )

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
                        parent=self.window(),
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
                        parent=self.window(),
                    )

            self.export_thread.exportFinished.connect(on_export_finished)
            self.export_thread.start()

        except Exception as e:
            # 使用InfoBar显示错误消息
            InfoBar.warning(
                title="导出失败",
                content=f"准备导出TXT时发生错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )
        """导出备忘录为TXT文件"""
        try:
            # 获取默认导出目录
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

            default_filename = f"{self.titleLabel.text()}.txt"
            default_path = os.path.join(default_dir, default_filename)

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出为TXT", default_path, "Text Files (*.txt)"
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
                parent=self.window(),
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
                        # 写入TXT文件 - 使用完整内容而非截断内容
                        with open(self.file_path, "w", encoding="utf-8") as f:
                            f.write(f"标题: {self.title}\n\n")
                            f.write(f"{self.content}\n\n")
                            f.write(f"修改时间: {self.time_text}")
                        self.exportFinished.emit(True, "")
                    except Exception as e:
                        self.exportFinished.emit(False, str(e))

            # 创建并启动线程
            self.export_thread = ExportThread(
                self.titleLabel.text(), self.full_content, self.timeLabel.text(), file_path
            )

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
                        parent=self.window(),
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
                        parent=self.window(),
                    )

            self.export_thread.exportFinished.connect(on_export_finished)
            self.export_thread.start()

        except Exception as e:
            # 使用InfoBar显示错误消息
            InfoBar.warning(
                title="导出失败",
                content=f"准备导出TXT时发生错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )


class mainInterface(Ui_mainwindow, QWidget):
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.toolButton.setIcon(FluentIcon.ADD)
        self.toolButton_2.setIcon(FluentIcon.SYNC)

        # 连接 toolButton 的点击事件
        self.toolButton.clicked.connect(self.switch_to_memo_interface)
        self.toolButton_2.clicked.connect(self.sync_memos)

        self.pushButton.addItem("按名称（a-z）排序")
        self.pushButton.addItem("按创建时间从早到晚排序")
        self.pushButton.addItem("按创建时间从晚到早排序")
        self.pushButton.addItem("按修改时间从早到晚排序")
        self.pushButton.addItem("按修改时间从晚到早排序")

        self.pushButton.currentIndexChanged.connect(self.on_sort_option_changed)

        # 创建 QVBoxLayout
        self.cardLayout = QVBoxLayout()

        self.scrollAreaWidgetContents.setLayout(
            self.cardLayout
        )  # 将布局设置到已有的 Widget 中

        self.scrollArea.setStyleSheet(
            "QScrollArea{background: transparent; border: none}"
        )

        self.scrollAreaWidgetContents.setStyleSheet("QWidget{background: transparent}")

        # 初始化数据库连接
        self.db = DatabaseManager()
        self.user_id = user_id
        # 定时器，定期更新备忘录列表
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_memo_list)
        self.timer.start(1000)  

        # 初始加载备忘录列表
        self.update_memo_list()

    def update_memo_list(self):
        """从数据库获取备忘录并更新列表"""
        # 清空现有布局
        for i in reversed(range(self.cardLayout.count())):
            widget = self.cardLayout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # 从数据库获取备忘录
        memos = self.db.get_memos(user_id=self.user_id)
        sort_option = self.pushButton.currentText()

        if sort_option == "按名称（a-z）排序":
            # 按标题字母顺序排序
            memos.sort(key=lambda x: self.db.decrypt(x[4]).lower())
        elif sort_option == "按创建时间从早到晚排序":
            # 按创建时间从早到晚排序（默认，数据库可能已经这样排序）
            memos.sort(key=lambda x: x[2])
        elif sort_option == "按创建时间从晚到早排序":
            # 按创建时间从晚到早排序
            memos.sort(key=lambda x: x[2], reverse=True)
        elif sort_option == "按修改时间从早到晚排序":
            # 按修改时间从早到晚排序
            memos.sort(key=lambda x: x[3])
        elif sort_option == "按修改时间从晚到早排序":
            # 按修改时间从晚到早排序
            memos.sort(key=lambda x: x[3], reverse=True)
        # 添加 AppCard 到 cardLayout
        for memo in memos:
            # 从数据库中获取的数据
            memo_id = memo[0]
            user_id = memo[1]
            created_time = memo[2]
            modified_time = memo[3]
            title = self.db.decrypt(memo[4])  # 解密标题
            content = self.db.decrypt(memo[5])  # 解密内容
            category = memo[6]

            self.cardLayout.addWidget(
                AppCard(
                    title,
                    content,
                    memo_id=memo_id,
                    modified_time=modified_time,
                    category=category,
                    timer=self.timer,  # 传递 timer
                )
            )  # 修改参数

    def sync_memos(self):
        """手动同步备忘录数据"""
        try:
            # 显示同步中提示
            InfoBar.info(
                title="正在同步",
                content="正在从数据库获取最新备忘录数据...",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self,
            )

            # 调用更新方法
            self.update_memo_list()

            # 显示同步成功提示
            InfoBar.success(
                title="同步成功",
                content="备忘录数据已更新",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        except Exception as e:
            # 显示同步失败提示
            InfoBar.error(
                title="同步失败",
                content=f"无法获取最新数据: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
    def switch_to_memo_interface(self):
        # 调用父窗口 (MainWindow) 的方法来切换到 musicInterface
        main_window = self.window()
        if hasattr(main_window, "switch_to_newmemo_interface"):
            main_window.switch_to_newmemo_interface()

            # 清空 memoInterface 的内容
            if hasattr(main_window, "memoInterface"):
                main_window.memoInterface.memo_id = None  # 重置 memo_id
                main_window.memoInterface.lineEdit.clear()  # 清空标题
                main_window.memoInterface.textEdit.clear()  # 清空内容
                main_window.memoInterface.lineEdit_2.clear()  # 清空分类
                main_window.memoInterface.update_word_count()  # 更新字数统计

    def on_sort_option_changed(self, index):
        """处理排序选项变化事件"""
        # 显示排序中提示
        sort_option = self.pushButton.currentText()

        # 更新备忘录列表
        self.update_memo_list()

        # 显示排序完成提示
        InfoBar.success(
            title="排序完成",
            content=f"已按{sort_option}方式显示备忘录",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )

    def closeEvent(self, event):
        """关闭窗口时关闭数据库连接"""
        self.db.close()
        event.accept()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = mainInterface()
    w.show()
    sys.exit(app.exec_())
