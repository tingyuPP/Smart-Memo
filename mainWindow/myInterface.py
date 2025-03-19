from qfluentwidgets import (ScrollArea, ElevatedCardWidget, AvatarWidget, TitleLabel, BodyLabel,
                            SettingCardGroup, CardWidget, IconWidget, CaptionLabel, PushButton,
                            TransparentToolButton, FluentIcon, InfoBar, InfoBarPosition)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from Database import DatabaseManager

class MyInterface(ScrollArea):
    def __init__(self, text : str, username : str, parent=None):
        super().__init__(parent=parent)
        try:
            self.db = DatabaseManager()
            self.user_data = self.db.get_certain_user(username)
        finally:
            if self.db:
                self.db.close

        self.mainWindow = parent
        self.avatar = self.user_data["avatar"]
        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        font = QFont("黑体", 20)
        font.setBold(True)
        self.infoCard = InfoCard(self.user_data, self)
        self.titleLabel = TitleLabel("个人中心", self)
        self.titleLabel.setFont(font)
        # self.descriptionLabel = BodyLabel("在这里查看和管理您的个人信息")
        self.personalGroup = SettingCardGroup(self.tr('个人资料'), self.scrollWidget)
        self.avatarCard = AvatarCard(FluentIcon.PEOPLE, "修改头像", "更改您的头像", self)


        self.__initWidget()
        self.__initLayout()
        self.setObjectName(text.replace(' ', '-'))

    def __initWidget(self):
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()
        self.setViewportMargins(0, 60, 0, 20)
        self.personalGroup.addSettingCard(self.avatarCard)

    def __initLayout(self):
        # 创建主布局
        self.titleLabel.move(36, 30)
        self.titleLabel.raise_()
        
        self.vBoxLayout.setContentsMargins(36, 10, 36, 0)
        self.vBoxLayout.setSpacing(20)
        
        # 添加标题和描述
        # self.vBoxLayout.addWidget(self.titleLabel)
        # self.vBoxLayout.addWidget(self.descriptionLabel)
        self.vBoxLayout.addSpacing(10)
        
        # 添加信息卡片并水平居中
        self.cardLayout = QHBoxLayout()
        self.cardLayout.addStretch(1)
        self.cardLayout.addWidget(self.infoCard)
        self.cardLayout.addStretch(1)
        self.vBoxLayout.addLayout(self.cardLayout)
        self.vBoxLayout.addWidget(self.personalGroup)
        
        # 添加弹性空间
        self.vBoxLayout.addStretch(1)
        
class InfoCard(ElevatedCardWidget):
    def __init__(self, user_data : dict, parent=None):
        super().__init__(parent=parent)
        self.user_data = user_data
        self.id = user_data["id"]
        self.avatar = AvatarWidget(user_data["avatar"])
        self.avatar.setRadius(48)           
        self.username = user_data["username"]
        
        # 获取或设置备忘录数量（默认为15篇，实际开发中应从数据库获取）
        self.memo_count = user_data.get("memo_count", 15)
        
        self.__initWidget()
        self.__initLayout()

        # 调整卡片宽度适应三部分布局
        self.setFixedWidth(450)  # 增加宽度以适应备忘录统计区域
        self.setFixedHeight(150)  # 保持高度不变

    def __initWidget(self):
        """初始化组件"""
        # 创建用户名标签
        self.usernameLabel = TitleLabel(self.username, self)
        font = QFont("黑体", 16)
        font.setBold(True)
        self.usernameLabel.setFont(font)
        
        # 创建用户ID标签
        self.idLabel = BodyLabel(f"ID: {self.id}", self)
        
        # 设置头像大小
        self.avatar.setFixedSize(100, 100)  # 保持您的原始设置
        
        # 创建分割线
        self.separator = QWidget(self)
        self.separator.setFixedHeight(1)
        self.separator.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")
        
        # 创建垂直分割线
        self.verticalSeparator = QWidget(self)
        self.verticalSeparator.setFixedWidth(1)
        self.verticalSeparator.setMinimumHeight(100)  # 设置最小高度
        self.verticalSeparator.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")
        
        # 创建备忘录标题标签
        self.memoTitleLabel = BodyLabel("备忘录数量", self)
        self.memoTitleLabel.setAlignment(Qt.AlignCenter)
        
        # 创建备忘录数量标签（数字部分）
        self.memoCountLabel = TitleLabel(str(self.memo_count), self)
        count_font = QFont("黑体", 24)
        count_font.setBold(True)
        # self.memoCountLabel.setFont(count_font)
        self.memoCountLabel.setStyleSheet("color: #0078D4;")  # 使用醒目的蓝色

    def __initLayout(self):
        """初始化布局 - 三部分横向布局"""
        # 创建主水平布局
        mainLayout = QHBoxLayout(self)
        mainLayout.setContentsMargins(20, 20, 20, 20)
        mainLayout.setSpacing(20)  # 增加间距以分隔各部分
        
        # 添加头像到左侧，垂直居中
        mainLayout.addWidget(self.avatar, 0, Qt.AlignVCenter)
        
        # 创建中间的垂直布局，放置用户名和ID信息
        infoLayout = QVBoxLayout()
        infoLayout.setSpacing(10)
        infoLayout.addStretch(1)
        
        # 添加用户名，左对齐
        infoLayout.addWidget(self.usernameLabel, 0, Qt.AlignLeft)
        
        # 添加分割线
        infoLayout.addWidget(self.separator)
        
        # 添加ID信息，左对齐
        infoLayout.addWidget(self.idLabel, 0, Qt.AlignLeft)
        
        # 添加弹性空间，使内容垂直居中
        infoLayout.addStretch(1)
        
        # 将中间信息布局添加到主布局
        mainLayout.addLayout(infoLayout)
        
        # 添加垂直分割线
        mainLayout.addWidget(self.verticalSeparator, 0, Qt.AlignVCenter)
        
        # 创建右侧的垂直布局，放置备忘录统计信息
        memoLayout = QVBoxLayout()
        memoLayout.setSpacing(10)
        memoLayout.setContentsMargins(10, 0, 10, 0)
        
        # 添加备忘录标题，左对齐
        memoLayout.addStretch(1)
        memoLayout.addWidget(self.memoTitleLabel, 0, Qt.AlignLeft)  # 改为左对齐
        
        # 创建水平布局放置数量和单位
        countLayout = QHBoxLayout()
        countLayout.setSpacing(2)  # 减少数字和单位之间的间距
        countLayout.addWidget(self.memoCountLabel, 0, Qt.AlignLeft)  # 数字左对齐
        
        # 添加数量布局到备忘录布局
        memoLayout.addLayout(countLayout)
        memoLayout.addStretch(1)
        # 将备忘录布局添加到主布局
        mainLayout.addLayout(memoLayout)
        
        # 设置主布局
        self.setLayout(mainLayout)

class AvatarCard(CardWidget):
    def __init__(self, icon, title, content, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.iconWidget = IconWidget(icon)
        self.titleLabel = BodyLabel(title, self)
        self.contentLabel = CaptionLabel(content, self)
        self.addButton = TransparentToolButton(FluentIcon.ADD, self)
        self.avatar = AvatarWidget(parent.user_data["avatar"], self)
        self.avatar.setRadius(24)

        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        self.setFixedHeight(73)
        self.iconWidget.setFixedSize(24, 24)
        self.contentLabel.setTextColor("#606060", "#d2d2d2")

        self.hBoxLayout.setContentsMargins(20, 11, 11, 11)
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
                # 获取选中的文件路径
                selected_files = file_dialog.selectedFiles()
                if not selected_files:
                    return
                
                source_path = selected_files[0]
                
                # 获取当前用户ID和文件扩展名
                user_id = self.parent.user_data["id"]
                file_ext = os.path.splitext(source_path)[1]
                
                # 确保resource目录存在
                resource_dir = Path("resource")
                resource_dir.mkdir(exist_ok=True)

                # 删除所有以user_id为前缀的旧头像文件
                old_avatar_pattern = os.path.join(resource_dir, f"{user_id}.*")
                for old_file in glob.glob(old_avatar_pattern):
                    try:
                        os.remove(old_file)
                        print(f"已删除旧头像文件: {old_file}")
                    except Exception as e:
                        print(f"删除旧头像文件失败: {old_file}, 错误: {str(e)}")
                
                # 构建目标文件路径
                target_filename = f"{user_id}{file_ext}"
                target_path = resource_dir / target_filename
                
                # 复制文件到resource目录
                shutil.copy2(source_path, target_path)
                
                # 更新数据库中的头像路径
                db = None
                try:
                    db = DatabaseManager()
                    avatar_path = str(target_path).replace("\\", "/")  # 确保路径格式一致
                    db.update_user_avatar(user_id, avatar_path)
                    
                    # 更新本地用户数据
                    self.parent.user_data["avatar"] = avatar_path
                    
                    # 更新界面显示
                    self.avatar.setImage(QPixmap(avatar_path))
                    self.avatar.setRadius(24)
                    
                    # 更新信息卡中的头像
                    self.parent.infoCard.avatar.setImage(QPixmap(avatar_path))
                    self.parent.infoCard.avatar.setRadius(48)

                    w = InfoBar.success(
                        title="头像更新成功",
                        content="您的头像已经更新成功",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=3000,
                        parent=self.parent
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
                        parent=self.parent
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
                    parent=self.parent
                )
                print(f"头像处理错误: {str(e)}")