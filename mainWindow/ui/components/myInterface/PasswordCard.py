from PyQt5.QtWidgets import QWidget, QHBoxLayout, QApplication
from qfluentwidgets import (FluentIcon, ExpandGroupSettingCard, BodyLabel,
                            PasswordLineEdit, PrimaryPushButton, InfoBar,
                            InfoBarPosition, ToolButton, ToolTipFilter,
                            ToolTipPosition, LineEdit)
from PyQt5.QtCore import Qt
import string
import random
from Database import DatabaseManager


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
