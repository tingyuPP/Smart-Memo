# coding:utf-8
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication
from PyQt5.QtCore import Qt, QPoint

from qfluentwidgets import (
    CardWidget,
    BodyLabel,
    CaptionLabel,
    TransparentToolButton,
    FluentIcon,
    RoundMenu,
    Action,
    InfoBar,
    SubtitleLabel,
    InfoBarPosition,
    Dialog,
)

from Database import DatabaseManager
from mainWindow.ui.components.mainpage.card_share import CardShareManager
from mainWindow.ui.components.mainpage.card_export import CardExportManager


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
        self.timer = timer
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
        first_line = content.split("\n")[0] if content else ""  # 获取第一行
        truncated_content = (
            first_line[:20] + "..." if len(first_line) > 20 else first_line
        )
        self.contentLabel = BodyLabel(truncated_content, self)
        self.contentLabel.setWordWrap(True)

        # 操作按钮
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
        self.mainLayout.addLayout(self.textLayout)

        # 右侧操作区
        self.rightActions.addWidget(self.moreButton)
        self.rightActions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.mainLayout.addLayout(self.rightActions)

        # 尺寸策略
        self.setFixedHeight(96)
        self.moreButton.setFixedSize(40, 40)

        # 边距调整
        self.mainLayout.setContentsMargins(16, 8, 16, 8)
        self.textLayout.setContentsMargins(0, 2, 0, 2)
        self.textLayout.setSpacing(4)

    def setup_context_menu(self):
        self.menu = RoundMenu(parent=self)

        # 逐个添加动作
        self.menu.addAction(
            Action(
                FluentIcon.DELETE,
                "删除",
                triggered=self.delete_memo,
            )
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

    def showContextMenu(self, pos):
        self.menu.exec_(
            self.moreButton.mapToGlobal(QPoint(0, self.moreButton.height()))
        )

    def delete_memo(self):
        """删除当前备忘录"""
        if not self.memo_id:
            InfoBar.warning(
                title="无法删除",
                content="找不到备忘录ID",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )
            return

        # 显示确认对话框
        dialog = Dialog(
            "确认删除",
            f"确定要删除备忘录「{self.titleLabel.text()}」吗？此操作不可撤销。",
            self.window(),
        )

        # 设置确认按钮文本
        dialog.yesButton.setText("删除")
        dialog.cancelButton.setText("取消")

        # 如果用户点击确认删除
        if dialog.exec():
            try:
                # 创建数据库连接
                db = DatabaseManager()

                # 执行删除操作
                success = db.delete_memo(self.memo_id)

                # 关闭数据库连接
                db.close()

                if success:
                    # 显示删除成功提示
                    InfoBar.success(
                        title="删除成功",
                        content=f"备忘录「{self.titleLabel.text()}」已删除",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self.window(),
                    )

                    # 刷新主界面的备忘录列表
                    main_window = self.window()
                    if hasattr(main_window, "homeInterface") and hasattr(
                        main_window.homeInterface, "memo_count_changed"
                    ):
                        # 获取新的备忘录数量
                        db = DatabaseManager()
                        count = db.get_memo_count(main_window.homeInterface.user_id)
                        db.close()
                        main_window.homeInterface.memo_count_changed.emit(count)
                    if hasattr(main_window, "update_memo_list"):
                        main_window.update_memo_list()
                    elif hasattr(main_window, "homeInterface") and hasattr(
                        main_window.homeInterface, "update_memo_list"
                    ):
                        main_window.homeInterface.update_memo_list()

                    # 如果卡片仍在布局中，从布局中移除自己
                    parent = self.parent()
                    if parent and hasattr(parent, "layout"):
                        layout = parent.layout()
                        if layout:
                            layout.removeWidget(self)
                            self.deleteLater()
                else:
                    # 显示删除失败提示
                    InfoBar.error(
                        title="删除失败",
                        content="无法删除备忘录，请重试",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self.window(),
                    )
            except Exception as e:
                # 显示错误提示
                InfoBar.error(
                    title="删除失败",
                    content=f"发生错误: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self.window(),
                )

    def on_double_clicked(self):
        """处理双击事件，打开编辑界面"""
        print(f"AppCard 双击! ID: {self.memo_id}")

        # 获取主窗口引用
        main_window = self.window()

        # 判断主窗口是否有switch_to_newmemo_interface方法
        if hasattr(main_window, "switch_to_newmemo_interface"):
            # 首先跳转到memo界面
            main_window.switch_to_newmemo_interface()

            # 将当前备忘录信息传递给memo界面
            if hasattr(main_window, "memoInterface"):
                # 设置memo_id，用于后续保存时更新而非创建新备忘录
                main_window.memoInterface.memo_id = self.memo_id

                # 直接创建数据库连接
                try:
                    db = DatabaseManager()

                    if self.memo_id:
                        # 查询备忘录的所有相关信息
                        db.cursor.execute(
                            "SELECT title, content, category FROM memos WHERE id = ?",
                            (self.memo_id,),
                        )
                        result = db.cursor.fetchone()

                        if result:
                            # 找到记录，解密内容
                            title = db.decrypt(result[0])
                            content = db.decrypt(result[1])
                            category = result[2]

                            # 填充标题
                            main_window.memoInterface.lineEdit.setText(title)

                            # 填充内容
                            main_window.memoInterface.textEdit.setText(content)

                            # 设置分类信息
                            if category:
                                main_window.memoInterface.lineEdit_2.setText(category)
                        else:
                            # 如果在数据库中找不到记录，使用卡片上存储的数据
                            main_window.memoInterface.lineEdit.setText(
                                self.titleLabel.text()
                            )
                            main_window.memoInterface.textEdit.setText(
                                self.full_content
                            )
                            if hasattr(self, "category") and self.category:
                                main_window.memoInterface.lineEdit_2.setText(
                                    self.category
                                )
                    else:
                        # 如果没有memo_id，使用卡片上存储的数据
                        main_window.memoInterface.lineEdit.setText(
                            self.titleLabel.text()
                        )
                        main_window.memoInterface.textEdit.setText(self.full_content)
                        if hasattr(self, "category") and self.category:
                            main_window.memoInterface.lineEdit_2.setText(self.category)

                    # 关闭数据库连接
                    db.close()

                except Exception as e:
                    print(f"获取备忘录数据时出错: {str(e)}")
                    # 出错时使用卡片上存储的内容
                    main_window.memoInterface.lineEdit.setText(self.titleLabel.text())
                    main_window.memoInterface.textEdit.setText(self.full_content)
                    if hasattr(self, "category") and self.category:
                        main_window.memoInterface.lineEdit_2.setText(self.category)

                # 更新字数统计
                main_window.memoInterface.update_word_count()

                # 显示成功提示
                InfoBar.success(
                    title="备忘录已加载",
                    content=f"正在编辑「{main_window.memoInterface.lineEdit.text()}」",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=main_window.memoInterface,
                )

    def share_to_wechat(self):
        """创建微信分享图片"""
        title = self.titleLabel.text()
        content = self.full_content
        time_text = self.timeLabel.text()
        CardShareManager.generate_share_image(title, content, time_text, "微信", self)

    def share_to_qq(self):
        """创建QQ分享图片"""
        title = self.titleLabel.text()
        content = self.full_content
        time_text = self.timeLabel.text()
        CardShareManager.generate_share_image(title, content, time_text, "QQ", self)

    def export_to_pdf(self):
        """导出备忘录为PDF文件"""
        title = self.titleLabel.text()
        content = self.full_content
        time_text = self.timeLabel.text()
        CardExportManager.export_to_pdf(self, title, content, time_text, self.timer)

    def export_to_txt(self):
        """导出备忘录为TXT文件"""
        title = self.titleLabel.text()
        content = self.full_content
        time_text = self.timeLabel.text()
        CardExportManager.export_to_txt(self, title, content, time_text)
