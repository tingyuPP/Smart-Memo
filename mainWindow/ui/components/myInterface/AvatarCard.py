from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from qfluentwidgets import (CardWidget, IconWidget, BodyLabel, CaptionLabel,
                            TransparentToolButton, FluentIcon, AvatarWidget)
from Database import DatabaseManager


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
