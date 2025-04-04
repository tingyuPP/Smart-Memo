from qfluentwidgets import (
    ScrollArea,
    SettingCardGroup,
    FluentIcon,
    TitleLabel,
)
from faceRecognition.faceMessageBox import FaceRegistrationMessageBox
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication
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
from mainWindow.ui.components.myInterface.InfoCard import InfoCard
from mainWindow.ui.components.myInterface.AvatarCard import AvatarCard
from mainWindow.ui.components.myInterface.PasswordCard import PasswordCard
from mainWindow.ui.components.myInterface.FaceCard import FaceCard
from mainWindow.ui.components.myInterface.CloudCard import CloudCard


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