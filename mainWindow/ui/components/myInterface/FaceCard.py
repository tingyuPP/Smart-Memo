from qfluentwidgets import (
    FluentIcon,
    PrimaryPushSettingCard,
)
from faceRecognition.faceMessageBox import FaceRegistrationMessageBox
from Database import DatabaseManager


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
