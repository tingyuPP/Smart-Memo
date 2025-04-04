from qfluentwidgets import (
    ScrollArea, ElevatedCardWidget, AvatarWidget, TitleLabel, BodyLabel,
    SettingCardGroup, CardWidget, IconWidget, CaptionLabel, PushButton,
    TransparentToolButton, FluentIcon, InfoBar, InfoBarPosition,
    ExpandGroupSettingCard, LineEdit, PasswordLineEdit, PrimaryPushButton,
    ToolTipFilter, ToolButton, ToolTipPosition, PrimaryPushSettingCard,
    TransparentDropDownToolButton, RoundMenu, Action, Dialog, Theme)
from faceRecognition.faceMessageBox import FaceRegistrationMessageBox
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from Database import DatabaseManager
from obs import ObsClient
from config import cfg
import string
import random
import uuid
import time
import os
import tempfile
import json
from datetime import datetime


class MyInterface(ScrollArea):

    def __init__(self, text: str, username: str, parent=None):
        super().__init__(parent=parent)
        try:
            self.db = DatabaseManager()
            self.user_data = self.db.get_certain_user(username)
            self.user_id = self.user_data["id"]
            self.memo_count = self.db.get_memo_count(self.user_id)
            self.todo_count = self.db.get_todo_count(self.user_id)

            if "register_time" not in self.user_data:
                self.user_data["register_time"] = "default_time"
                print("警告：用户数据中缺少注册时间字段")
        finally:
            if self.db:
                self.db.close

        self.mainWindow = parent
        self.avatar = self.user_data["avatar"]
        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        font = QFont("黑体", 20)
        font.setBold(True)
        self.infoCard = InfoCard(self.user_data, self.memo_count,
                                 self.todo_count, self)
        self.titleLabel = TitleLabel("个人中心", self)
        self.titleLabel.setFont(font)
        self.personalGroup = SettingCardGroup(self.tr("个人资料"),
                                              self.scrollWidget)
        self.avatarCard = AvatarCard(FluentIcon.PEOPLE, "修改头像", "更改您的头像", self)
        self.securityGroup = SettingCardGroup(self.tr("安全与密码"),
                                              self.scrollWidget)
        self.passwordCard = PasswordCard(self)
        self.faceCard = FaceCard(self)
        self.cloudGroup = SettingCardGroup(self.tr("数据同步"), self.scrollWidget)
        self.cloudCard = CloudCard(FluentIcon.CLOUD, "云端同步", "同步您的备忘录数据到云端",
                                   self)

        self.__initWidget()
        self.__initLayout()
        self.setObjectName(text.replace(" ", "-"))

    def __initWidget(self):
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()
        self.setViewportMargins(0, 60, 0, 20)
        self.personalGroup.addSettingCard(self.avatarCard)
        self.securityGroup.addSettingCard(self.passwordCard)
        self.securityGroup.addSettingCard(self.faceCard)
        self.cloudGroup.addSettingCard(self.cloudCard)

    def __initLayout(self):
        self.titleLabel.move(36, 30)
        self.titleLabel.raise_()

        self.vBoxLayout.setContentsMargins(36, 10, 36, 0)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.addSpacing(10)

        self.cardLayout = QHBoxLayout()
        self.cardLayout.addStretch(1)
        self.cardLayout.addWidget(self.infoCard)
        self.cardLayout.addStretch(1)
        self.vBoxLayout.addLayout(self.cardLayout)
        self.vBoxLayout.addWidget(self.personalGroup)
        self.vBoxLayout.addWidget(self.securityGroup)
        self.vBoxLayout.addWidget(self.cloudGroup)

        self.vBoxLayout.addStretch(1)


class InfoCard(ElevatedCardWidget):

    def __init__(self,
                 user_data: dict,
                 memo_count: int,
                 todo_count: int,
                 parent=None):
        super().__init__(parent=parent)
        self.user_data = user_data
        self.id = user_data["id"]
        self.avatar = AvatarWidget(user_data["avatar"])
        self.avatar.setRadius(48)
        self.username = user_data["username"]

        # 获取备忘录及待办事项数量
        self.memo_count = memo_count
        self.todo_count = todo_count

        self.__initWidget()
        self.__initLayout()

        self.setFixedWidth(450)
        self.setFixedHeight(150)

        cfg.themeChanged.connect(self.onThemeChanged)

    def __initWidget(self):
        self.usernameLabel = TitleLabel(self.username, self)
        font = QFont("黑体", 16)
        font.setBold(True)
        self.usernameLabel.setFont(font)

        self.idLabel = BodyLabel(f"ID: {self.id}", self)
        id_font = QFont("Microsoft YaHei", 12)
        self.idLabel.setFont(id_font)

        self.avatar.setFixedSize(100, 100)

        self.separator = QWidget(self)
        self.separator.setFixedHeight(1)
        self.separator.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")

        self.verticalSeparator = QWidget(self)
        self.verticalSeparator.setFixedWidth(1)
        self.verticalSeparator.setMinimumHeight(100)
        self.verticalSeparator.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.1);")

        self.verticalSeparator2 = QWidget(self)
        self.verticalSeparator2.setFixedWidth(1)
        self.verticalSeparator2.setMinimumHeight(100)
        self.verticalSeparator2.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.1);")

        self.memoTitleLabel = BodyLabel("备忘录数量", self)
        self.memoTitleLabel.setAlignment(Qt.AlignCenter)

        self.memoCountLabel = TitleLabel(str(self.memo_count), self)
        count_font = QFont("黑体", 24)
        count_font.setBold(True)
        self.memoCountLabel.setStyleSheet("color: #0078D4;")

        self.todoTitleLabel = BodyLabel("待办任务", self)
        self.todoTitleLabel.setAlignment(Qt.AlignCenter)

        self.todoCountLabel = TitleLabel(str(self.todo_count), self)
        self.todoCountLabel.setStyleSheet("color: #107C10;")

    def __initLayout(self):
        mainLayout = QHBoxLayout(self)
        mainLayout.setContentsMargins(20, 20, 20, 20)
        mainLayout.setSpacing(20)  # 增加间距以分隔各部分

        mainLayout.addWidget(self.avatar, 0, Qt.AlignVCenter)

        infoLayout = QVBoxLayout()
        infoLayout.setSpacing(10)
        infoLayout.addStretch(1)

        infoLayout.addWidget(self.usernameLabel, 0, Qt.AlignLeft)
        infoLayout.addWidget(self.separator)
        infoLayout.addWidget(self.idLabel, 0, Qt.AlignLeft)
        infoLayout.addStretch(1)

        mainLayout.addLayout(infoLayout)
        mainLayout.addWidget(self.verticalSeparator, 0, Qt.AlignVCenter)

        memoLayout = QVBoxLayout()
        memoLayout.setSpacing(10)
        memoLayout.setContentsMargins(10, 0, 10, 0)
        memoLayout.addStretch(1)
        memoLayout.addWidget(self.memoTitleLabel, 0, Qt.AlignLeft)

        countLayout = QHBoxLayout()
        countLayout.setSpacing(2)
        countLayout.addWidget(self.memoCountLabel, 0, Qt.AlignLeft)

        memoLayout.addLayout(countLayout)
        memoLayout.addStretch(1)
        mainLayout.addLayout(memoLayout)

        mainLayout.addWidget(self.verticalSeparator2, 0, Qt.AlignVCenter)

        todoLayout = QVBoxLayout()
        todoLayout.setSpacing(10)
        todoLayout.setContentsMargins(10, 0, 10, 0)
        todoLayout.addStretch(1)
        todoLayout.addWidget(self.todoTitleLabel, 0, Qt.AlignLeft)

        todoCountLayout = QHBoxLayout()
        todoCountLayout.setSpacing(2)
        todoCountLayout.addWidget(self.todoCountLabel, 0, Qt.AlignLeft)

        todoLayout.addLayout(todoCountLayout)
        todoLayout.addStretch(1)

        mainLayout.addLayout(todoLayout)

        self.setLayout(mainLayout)

    def onThemeChanged(self, theme: Theme):
        print(1)
        # 使用QTimer延迟执行，确保在组件样式重置后再应用我们的样式
        QTimer.singleShot(10, self._applyCustomStyles)

    def _applyCustomStyles(self):
        self.memoCountLabel.setStyleSheet("color: #0078D4 !important;")
        self.todoCountLabel.setStyleSheet("color: #107C10 !important;")

    def update_todo_count(self, count):
        self.todo_count = count
        self.todoCountLabel.setText(str(count))
        self._applyCustomStyles()

    def update_memo_count(self, count):
        self.memo_count = count
        self.memoCountLabel.setText(str(count))
        self._applyCustomStyles()


class AvatarCard(CardWidget):

    def __init__(self, icon, title, content, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.iconWidget = IconWidget(icon)
        self.titleLabel = BodyLabel(title, self)
        self.contentLabel = CaptionLabel(content, self)
        self.addButton = TransparentToolButton(FluentIcon.ADD, self)
        self.avatar = AvatarWidget(parent.user_data["avatar"])
        self.avatar.setRadius(24)

        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        self.setFixedHeight(73)
        self.iconWidget.setFixedSize(16, 16)
        self.contentLabel.setTextColor("#606060", "#d2d2d2")

        self.hBoxLayout.setContentsMargins(15, 11, 11, 11)
        self.hBoxLayout.setSpacing(15)
        self.hBoxLayout.addWidget(self.iconWidget)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.addWidget(self.contentLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)
        self.hBoxLayout.addLayout(self.vBoxLayout)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.avatar, 0, Qt.AlignRight)
        self.hBoxLayout.addWidget(self.addButton, 0, Qt.AlignRight)

        self.addButton.setFixedSize(32, 32)

        self.addButton.clicked.connect(self.browse_avatar)

    def browse_avatar(self):
        """选择并更新用户头像"""
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.QtGui import QPixmap
        import os
        import shutil
        import glob
        from pathlib import Path
        from qfluentwidgets import InfoBar, InfoBarPosition

        # 打开文件选择对话框
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("选择头像图片")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)")

        if file_dialog.exec_():
            try:
                selected_files = file_dialog.selectedFiles()
                if not selected_files:
                    return

                source_path = selected_files[0]

                # 获取当前用户ID和文件扩展名
                user_id = self.parent.user_data["id"]
                file_ext = os.path.splitext(source_path)[1]

                resource_dir = Path("resource")
                resource_dir.mkdir(exist_ok=True)

                old_avatar_pattern = os.path.join(resource_dir, f"{user_id}.*")
                for old_file in glob.glob(old_avatar_pattern):
                    try:
                        os.remove(old_file)
                        print(f"已删除旧头像文件: {old_file}")
                    except Exception as e:
                        print(f"删除旧头像文件失败: {old_file}, 错误: {str(e)}")

                target_filename = f"{user_id}{file_ext}"
                target_path = resource_dir / target_filename

                shutil.copy2(source_path, target_path)

                # 更新数据库中的头像路径
                db = None
                try:
                    db = DatabaseManager()
                    avatar_path = str(target_path).replace("\\", "/")
                    db.update_user(user_id, avatar=avatar_path)

                    self.parent.user_data["avatar"] = avatar_path

                    self.avatar.setImage(QPixmap(avatar_path))
                    self.avatar.setRadius(24)

                    self.parent.infoCard.avatar.setImage(QPixmap(avatar_path))
                    self.parent.infoCard.avatar.setRadius(48)

                    w = InfoBar.success(
                        title="头像更新成功",
                        content="您的头像已经更新成功",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=3000,
                        parent=self.parent,
                    )
                    w.show()

                except Exception as e:
                    InfoBar.error(
                        title="头像更新失败",
                        content=f"更新头像时发生错误: {str(e)}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=3000,
                        parent=self.parent,
                    )
                    print(f"头像更新错误: {str(e)}")
                finally:
                    if db:
                        db.close()

            except Exception as e:
                from qfluentwidgets import InfoBar, InfoBarPosition

                InfoBar.error(
                    title="文件处理错误",
                    content=f"处理头像图片时发生错误: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=3000,
                    parent=self.parent,
                )
                print(f"头像处理错误: {str(e)}")


class PasswordCard(ExpandGroupSettingCard):

    def __init__(self, parent=None):
        super().__init__(FluentIcon.VPN, "修改密码", "更换一个新密码", parent)
        self.parent = parent
        self.oldPassLabel = BodyLabel("旧密码")
        self.oldPassEdit = LineEdit()
        self.oldPassEdit.setClearButtonEnabled(True)
        self.oldPassEdit.setFixedWidth(200)

        self.newPassLabel = BodyLabel("新密码")
        self.generateButton = ToolButton(FluentIcon.SYNC)
        self.generateButton.setToolTip("随机生成密码，请妥善保存")
        self.generateButton.setToolTipDuration(1000)
        self.generateButton.installEventFilter(
            ToolTipFilter(self.generateButton,
                          showDelay=300,
                          position=ToolTipPosition.TOP))
        self.newPassEdit = PasswordLineEdit()
        self.newPassEdit.setClearButtonEnabled(True)
        self.newPassEdit.setFixedWidth(200)

        self.confirmLabel = BodyLabel("确认密码")
        self.confirmEdit = PasswordLineEdit()
        self.confirmEdit.setClearButtonEnabled(True)
        self.confirmEdit.setFixedWidth(200)

        self.reviseLabel = BodyLabel("确认修改")
        self.reviseButton = PrimaryPushButton(FluentIcon.EDIT, "修改密码")

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.add(self.oldPassLabel, self.oldPassEdit)
        self.add(self.newPassLabel, self.newPassEdit, self.generateButton)
        self.add(self.confirmLabel, self.confirmEdit)
        self.add(self.reviseLabel, self.reviseButton)

        self.reviseButton.clicked.connect(self.revise_password)
        self.generateButton.clicked.connect(self.generate_password)

    def add(self, label=None, widget=None, button=None):
        w = QWidget()
        w.setFixedHeight(60)

        layout = QHBoxLayout(w)
        layout.setContentsMargins(48, 12, 48, 12)

        if label:
            layout.addWidget(label)
        layout.addStretch(1)
        if button:
            layout.addWidget(button)
        layout.addWidget(widget)

        self.addGroupWidget(w)

    def generate_password(self):
        """生成一个包含大写字母、小写字母、数字和符号的复杂密码"""

        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()-_=+[]{}|;:,.<>?"
        length = random.randint(12, 16)

        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(symbols),
        ]

        remaining_length = length - len(password)
        all_chars = lowercase + uppercase + digits + symbols
        password.extend(
            random.choice(all_chars) for _ in range(remaining_length))

        random.shuffle(password)
        password = "".join(password)

        self.newPassEdit.setText(password)

        clipboard = QApplication.clipboard()
        clipboard.setText(password)

        InfoBar.success(
            title="密码已生成",
            content="已创建强密码并复制到剪贴板",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=3000,
            parent=self.parent,
        )

        self.confirmEdit.setText(password)

    def revise_password(self):
        """修改密码"""
        old_password = self.oldPassEdit.text()
        new_password = self.newPassEdit.text()
        confirm_password = self.confirmEdit.text()

        if not old_password or not new_password or not confirm_password:
            InfoBar.error(
                title="密码修改失败",
                content="请填写完整的密码信息",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )
            return

        if new_password != confirm_password:
            InfoBar.error(
                title="密码修改失败",
                content="新密码和确认密码不一致",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )
            return

        if len(new_password) < 6:
            InfoBar.error(
                title="密码修改失败",
                content="新密码长度不能少于6位",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )
            return

        if new_password == old_password:
            InfoBar.error(
                title="密码修改失败",
                content="新密码不能和旧密码相同",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )
            return

        db = None
        try:
            db = DatabaseManager()
            username = self.parent.user_data["username"]
            user_id = self.parent.user_data["id"]
            result = db.check_password(username, old_password)
            if result:
                db.update_user(user_id, password=new_password)
                InfoBar.success(
                    title="密码修改成功",
                    content="您的密码已经修改成功",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=3000,
                    parent=self.parent,
                )
                self.oldPassEdit.clear()
                self.newPassEdit.clear()
                self.confirmEdit.clear()
            else:
                InfoBar.error(
                    title="密码修改失败",
                    content="旧密码错误",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=3000,
                    parent=self.parent,
                )
        except Exception as e:
            InfoBar.error(
                title="密码修改失败",
                content=f"修改密码时发生错误: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )
            print(f"密码修改错误: {str(e)}")
        finally:
            if db:
                db.close()


class FaceCard(PrimaryPushSettingCard):

    def __init__(self, parent=None):
        super().__init__(
            text="录入人脸",
            icon=FluentIcon.CAMERA,
            title="人脸信息",
            content="录入或修改您的人脸信息",
            parent=parent,
        )
        self.parent = parent

        self.clicked.connect(self.faceRecognition)

    def faceRecognition(self):
        dialog = FaceRegistrationMessageBox(
            user_id=self.parent.user_data["id"],
            username=self.parent.user_data["username"],
            parent=self.parent.mainWindow,
        )
        dialog.registrationComplete.connect(self.on_face_registration_complete)
        dialog.exec()

    def on_face_registration_complete(self, result):
        pass


class CloudCard(CardWidget):

    def __init__(self, icon, title, content, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.user_id = parent.user_data["id"]
        self.iconWidget = IconWidget(icon)
        self.titleLabel = BodyLabel(title, self)
        self.contentLabel = CaptionLabel(content, self)
        self.menuButton = TransparentDropDownToolButton(FluentIcon.MORE, self)
        self.menu = RoundMenu(parent=self.menuButton)
        self.menu.addAction(
            Action(FluentIcon.SEND, "上传至云端", triggered=self.upload_to_cloud))
        self.menu.addAction(
            Action(
                FluentIcon.CLOUD_DOWNLOAD,
                "下载至本地",
                triggered=self.download_to_local,
            ))
        self.menuButton.setMenu(self.menu)
        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        self.setFixedHeight(73)
        self.iconWidget.setFixedSize(16, 16)
        self.contentLabel.setTextColor("#606060", "#d2d2d2")

        self.hBoxLayout.setContentsMargins(15, 11, 11, 11)
        self.hBoxLayout.setSpacing(15)
        self.hBoxLayout.addWidget(self.iconWidget)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.addWidget(self.contentLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)
        self.hBoxLayout.addLayout(self.vBoxLayout)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.menuButton, 0, Qt.AlignRight)

    def upload_to_cloud(self):
        """将备忘录数据上传到云端备份"""
        try:
            w1 = InfoBar.info(
                title="备份中",
                content="正在准备备份数据...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=1000,  # 持续显示，直到手动关闭
                parent=self.parent,
            )
            w1.show()
            # 从数据库获取备忘录数据
            self.db = DatabaseManager()
            memos = self.db.get_memos(user_id=self.user_id)

            if not memos:
                InfoBar.warning(
                    title="无数据",
                    content="没有找到需要备份的备忘录数据",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=3000,
                    parent=self.parent,
                )
                return

            # 更新状态消息
            w2 = InfoBar.info(
                title="备份中",
                content=f"正在备份{len(memos)}条备忘录到云端...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=1000,
                parent=self.parent,
            )
            w2.show()
            # 解析备忘录数据
            memo_list = []
            for memo in memos:
                memo_id = memo[0]
                user_id = memo[1]
                created_time = memo[2]
                modified_time = memo[3]
                title = self.db.decrypt(memo[4])
                content = self.db.decrypt(memo[5])
                category = memo[6]
                memo_dict = {
                    "memo_id": memo_id,
                    "user_id": user_id,
                    "created_time": created_time,
                    "modified_time": modified_time,
                    "title": title,
                    "content": content,
                    "category": category,
                }
                memo_list.append(memo_dict)

            success, backup_url = self._upload_memos_to_obs(memo_list)
            w1.close()
            w2.close()

        except Exception as e:
            import traceback

            print(f"备份过程出错: {str(e)}")
            print(traceback.format_exc())

            w1.close()
            w2.close()
            InfoBar.error(
                title="备份失败",
                content=f"备份过程中出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )
        finally:
            if hasattr(self, "db") and self.db:
                self.db.close()

    def _upload_memos_to_obs(self, memo_list):
        """上传备忘录数据到华为云OBS备份"""
        try:
            # 华为云OBS配置
            ak = "FTCMA0RFFEFYAHZCTUNR"
            sk = "DtOPu5ExOARQuMZHAGewDVzryaH1ht7gSWlflsJ5"
            endpoint = "obs.cn-east-3.myhuaweicloud.com"
            server = f"https://{endpoint}"
            bucket_name = "mypicturebed"  # 使用同一个bucket

            # 创建OBS客户端
            obs_client = ObsClient(access_key_id=ak,
                                   secret_access_key=sk,
                                   server=server)

            try:
                import json
                import time

                computer_id = self.get_computer_id()

                timestamp = int(time.time())
                user_id = self.user_id
                register_time = str(self.parent.user_data["register_time"])
                register_time = register_time.replace(" ",
                                                      "_").replace(":", "-")
                backup_filename = f"memo_backup_{computer_id}_{user_id}_{register_time}_{timestamp}.json"

                memo_json = json.dumps(memo_list, ensure_ascii=False, indent=2)

                object_key = f"memo_backups/{backup_filename}"
                resp = obs_client.putObject(bucket_name, object_key,
                                            memo_json.encode("utf-8"))

                if resp.status < 300:
                    backup_url = f"https://{bucket_name}.{endpoint}/{object_key}"

                    InfoBar.success(
                        title="备份成功",
                        content=f"成功备份{len(memo_list)}条备忘录到云端",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=3000,
                        parent=self.parent,
                    )

                    return True, backup_url
                else:
                    print(f"上传失败: {resp.errorCode} - {resp.errorMessage}")

                    InfoBar.error(
                        title="备份失败",
                        content=f"备份失败: {resp.errorMessage}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=3000,
                        parent=self.parent,
                    )

                    return False, None
            finally:
                obs_client.close()

        except Exception as e:
            print(f"上传到OBS时发生错误: {str(e)}")
            import traceback

            print(traceback.format_exc())

            InfoBar.error(
                title="备份失败",
                content=f"备份过程中出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

            return False, None

    def get_computer_id(self):
        """获取计算机的唯一标识符"""
        return uuid.UUID(int=uuid.getnode()).hex[-12:]

    def download_to_local(self):
        """下载云端备份文件到本地"""
        try:
            self.download_info_bar = InfoBar.info(
                title="下载中",
                content="正在查询云端备份文件...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,
                parent=self.parent,
            )

            self._query_cloud_backups()

        except Exception as e:
            import traceback

            print(f"下载备份过程出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            InfoBar.error(
                title="下载失败",
                content=f"下载备份过程中出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

    def _query_cloud_backups(self):
        """查询云端备份文件"""
        try:
            ak = "FTCMA0RFFEFYAHZCTUNR"
            sk = "DtOPu5ExOARQuMZHAGewDVzryaH1ht7gSWlflsJ5"
            endpoint = "obs.cn-east-3.myhuaweicloud.com"
            server = f"https://{endpoint}"
            bucket_name = "mypicturebed"

            obs_client = ObsClient(access_key_id=ak,
                                   secret_access_key=sk,
                                   server=server)

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()
                self.download_info_bar = InfoBar.info(
                    title="下载中",
                    content="正在查询备份文件...",
                    orient=Qt.Horizontal,
                    isClosable=False,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=-1,
                    parent=self.parent,
                )

            prefix = f"memo_backups/memo_backup_"
            resp = obs_client.listObjects(bucket_name, prefix=prefix)

            if resp.status < 300:
                user_id = self.user_id
                current_computer_id = self.get_computer_id()

                user_backups = []
                other_device_backups = []

                for content in resp.body.contents:
                    object_key = content.key

                    filename = os.path.basename(object_key)
                    parts = filename.split("_")

                    if len(parts) >= 6 and parts[0] == "memo" and parts[
                            1] == "backup":
                        file_computer_id = parts[2]
                        file_user_id = parts[3]

                        # 获取文件名的末尾部分（时间戳.json）
                        timestamp_part = parts[-1]

                        register_time_parts = parts[4:-1]
                        file_register_time = "_".join(register_time_parts)

                        current_register_time = str(
                            self.parent.user_data.get("register_time",
                                                      "unknown"))
                        current_register_time = (current_register_time.replace(
                            " ", "_").replace(":", "-").replace("/", "-"))

                        if (str(file_user_id) == str(user_id) and
                                file_register_time == current_register_time):
                            timestamp = int(timestamp_part.split(".")[0])
                            backup_info = {
                                "key":
                                object_key,
                                "timestamp":
                                timestamp,
                                "last_modified":
                                content.lastModified,
                                "size":
                                content.size,
                                "computer_id":
                                file_computer_id,
                                "is_current_device":
                                file_computer_id == current_computer_id,
                            }

                            if file_computer_id == current_computer_id:
                                user_backups.append(backup_info)
                            else:
                                other_device_backups.append(backup_info)

                all_backups = user_backups + other_device_backups

                if not all_backups:
                    if hasattr(self,
                               "download_info_bar") and self.download_info_bar:
                        self.download_info_bar.close()

                    InfoBar.warning(
                        title="未找到备份",
                        content="云端没有找到您的备份文件",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=3000,
                        parent=self.parent,
                    )
                    return

                # 按时间戳排序，找出最新的备份
                all_backups.sort(key=lambda x: x["timestamp"], reverse=True)
                latest_backup = all_backups[0]

                if hasattr(self,
                           "download_info_bar") and self.download_info_bar:
                    backup_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(latest_backup["timestamp"]))

                    device_info = ("当前设备" if latest_backup["is_current_device"]
                                   else "其他设备")

                    self.download_info_bar.close()
                    self.download_info_bar = InfoBar.info(
                        title="下载中",
                        content=
                        f"找到最新备份 ({backup_time}, {device_info})，正在下载...",
                        orient=Qt.Horizontal,
                        isClosable=False,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=-1,
                        parent=self.parent,
                    )

                # 下载最新的备份文件
                QTimer.singleShot(
                    500,
                    lambda: self._download_backup_file(obs_client, bucket_name,
                                                       latest_backup),
                )
            else:
                raise Exception(
                    f"查询失败: {resp.errorCode} - {resp.errorMessage}")

        except Exception as e:
            import traceback

            print(f"查询云端备份出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            InfoBar.error(
                title="查询失败",
                content=f"查询云端备份时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

            if "obs_client" in locals():
                obs_client.close()

    def _download_backup_file(self, obs_client, bucket_name, backup_info):
        """下载指定的备份文件"""
        try:
            object_key = backup_info["key"]

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()
                self.download_info_bar = InfoBar.info(
                    title="下载中",
                    content="正在下载备份文件...",
                    orient=Qt.Horizontal,
                    isClosable=False,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=-1,
                    parent=self.parent,
                )

            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, os.path.basename(object_key))

            resp = obs_client.getObject(bucket_name,
                                        object_key,
                                        downloadPath=temp_file)

            if resp.status < 300:
                if hasattr(self,
                           "download_info_bar") and self.download_info_bar:
                    self.download_info_bar.close()
                    self.download_info_bar = InfoBar.info(
                        title="下载中",
                        content="备份下载完成，正在解析数据...",
                        orient=Qt.Horizontal,
                        isClosable=False,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=-1,
                        parent=self.parent,
                    )

                # 解析下载的JSON文件
                QTimer.singleShot(
                    500,
                    lambda: self._parse_backup_file(temp_file, backup_info))
            else:
                raise Exception(
                    f"下载失败: {resp.errorCode} - {resp.errorMessage}")

        except Exception as e:
            import traceback

            print(f"下载备份文件出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            InfoBar.error(
                title="下载失败",
                content=f"下载备份文件时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

        finally:
            obs_client.close()

    def show_confirm_dialog(self, title, content, on_yes, on_no=None):
        dialog = Dialog(title, content, parent=self.parent.mainWindow)

        dialog.yesButton.setText("确定")
        dialog.cancelButton.setText("取消")

        dialog.yesSignal.connect(on_yes)
        if on_no:
            dialog.cancelSignal.connect(on_no)

        dialog.exec()

    def _parse_backup_file(self, file_path, backup_info):
        try:
            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            with open(file_path, "r", encoding="utf-8") as f:
                memo_list = json.load(f)

            backup_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(backup_info["timestamp"]))
            memo_count = len(memo_list)

            backup_summary = {
                "backup_time": backup_time,
                "memo_count": memo_count,
                "user_id": self.user_id,
                "backup_file": os.path.basename(file_path),
                "backup_size": backup_info["size"],
                "memo_categories": {},
            }

            for memo in memo_list:
                category = memo.get("category", "未分类")
                if category not in backup_summary["memo_categories"]:
                    backup_summary["memo_categories"][category] = 0
                backup_summary["memo_categories"][category] += 1

            # 将备份文件保存到本地下载目录
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.exists(downloads_dir):
                downloads_dir = os.path.dirname(file_path)  # 使用临时目录

            # 创建一个带时间戳的备份文件名
            local_filename = f"memo_backup_{self.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            local_filepath = os.path.join(downloads_dir, local_filename)

            import shutil

            shutil.copy2(file_path, local_filepath)

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            InfoBar.success(
                title="下载成功",
                content=f"成功下载{memo_count}条备忘录数据，保存在: {local_filepath}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self.parent,
            )

            dialog_content = (
                f"是否要导入下载的{memo_count}条备忘录数据？\n"
                f"备份时间: {backup_time}\n"
                f'分类统计: {", ".join([f"{k}: {v}条" for k, v in backup_summary["memo_categories"].items()])}'
            )

            # 保存备份列表引用，以便在回调中使用
            self.temp_memo_list = memo_list

            self.show_confirm_dialog(
                "导入数据",
                dialog_content,
                on_yes=lambda: self._import_backup_data(self.temp_memo_list),
            )

        except Exception as e:
            import traceback

            print(f"解析备份文件出错: {str(e)}")
            print(traceback.format_exc())

            InfoBar.error(
                title="解析失败",
                content=f"解析备份文件时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

    def _import_backup_data(self, memo_list):
        """导入备份数据到本地数据库，替换所有现有数据"""
        try:
            self.import_info_bar = InfoBar.info(
                title="导入中",
                content=f"正在准备导入{len(memo_list)}条备忘录数据...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,
                parent=self.parent,
            )

            db = DatabaseManager()

            current_memos = db.get_memos(user_id=self.user_id)
            current_count = len(current_memos) if current_memos else 0

            self.db = db
            self.current_count = current_count
            self.import_memo_list = memo_list

            dialog_content = f"此操作将删除您现有的{current_count}条备忘录，并导入备份中的{len(memo_list)}条备忘录。\n确定要继续吗？"

            self.show_confirm_dialog(
                "替换确认",
                dialog_content,
                on_yes=self._do_import_backup_data,
                on_no=self._cancel_import,
            )

        except Exception as e:
            import traceback

            print(f"导入备份数据出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()

            InfoBar.error(
                title="导入失败",
                content=f"导入备份数据时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

            if hasattr(self, "db") and self.db:
                self.db.close()

    def _cancel_import(self):
        """取消导入操作"""
        if hasattr(self, "import_info_bar") and self.import_info_bar:
            self.import_info_bar.close()

        InfoBar.info(
            title="导入取消",
            content="您已取消导入备份数据",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=3000,
            parent=self.parent,
        )

        if hasattr(self, "db") and self.db:
            self.db.close()

    def _do_import_backup_data(self):
        """执行实际的导入操作"""
        try:
            # 获取之前保存的数据
            db = self.db
            current_count = self.current_count
            memo_list = self.import_memo_list

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()
                self.import_info_bar = InfoBar.info(
                    title="导入中",
                    content="正在删除现有备忘录...",
                    orient=Qt.Horizontal,
                    isClosable=False,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=-1,
                    parent=self.parent,
                )

            # 删除用户的所有备忘录
            db.delete_memos_by_user(self.user_id)

            # 导入统计
            imported_count = 0

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()
                self.import_info_bar = InfoBar.info(
                    title="导入中",
                    content="正在导入备份数据...",
                    orient=Qt.Horizontal,
                    isClosable=False,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=-1,
                    parent=self.parent,
                )

            # 逐条导入备忘录
            for i, memo in enumerate(memo_list):
                if i % (len(memo_list) // 5 or 1) == 0:
                    if hasattr(self,
                               "import_info_bar") and self.import_info_bar:
                        progress = int((i / len(memo_list)) * 100)
                        self.import_info_bar.close()
                        self.import_info_bar = InfoBar.info(
                            title="导入中",
                            content=f"正在导入数据...{progress}%",
                            orient=Qt.Horizontal,
                            isClosable=False,
                            position=InfoBarPosition.BOTTOM_RIGHT,
                            duration=-1,
                            parent=self.parent,
                        )

                title = memo.get("title", "")
                content = memo.get("content", "")
                category = memo.get("category", "")

                db.create_memo(self.user_id, title, content, category)
                imported_count += 1

            db.close()

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()

            InfoBar.success(
                title="导入成功",
                content=f"已删除{current_count}条现有备忘录，导入{imported_count}条备份备忘录",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self.parent,
            )

            if hasattr(self.parent, "mainWindow") and hasattr(
                    self.parent.mainWindow, "refresh_memo_list"):
                self.parent.mainWindow.refresh_memo_list()

            if hasattr(self.parent, "infoCard") and hasattr(
                    self.parent.infoCard, "memoCountLabel"):
                self.parent.infoCard.memoCountLabel.setText(
                    str(imported_count))

        except Exception as e:
            import traceback

            print(f"导入备份数据出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()

            InfoBar.error(
                title="导入失败",
                content=f"导入备份数据时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

        finally:
            if hasattr(self, "db") and self.db:
                self.db.close()
