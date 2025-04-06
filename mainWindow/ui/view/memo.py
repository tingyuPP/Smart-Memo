# coding:utf-8
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QWidget, QMenu, QApplication, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QEvent

from qfluentwidgets import (
    FluentIcon,
    Action,
    InfoBar,
    InfoBarPosition,
    RoundMenu,
    VBoxLayout,
)

from mainWindow.ui.components.memopage.Ui_memo import Ui_memo
from mainWindow.ui.view.smart_text_edit import SmartTextEdit
from mainWindow.ui.view.todo_extractor import TodoExtractor
from mainWindow.ui.view.ai_handler import AIHandler
from mainWindow.ui.components.memopage.memo_share import MemoShareManager
from mainWindow.ui.components.memopage.memo_export import MemoExportManager

from Database import DatabaseManager



class MemoInterface(Ui_memo, QWidget):

    def __init__(self, parent=None, user_id=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.db = DatabaseManager()
        self.user_id = user_id
        self.memo_id = None

        # 初始化各个管理器
        self.ai_handler = AIHandler.get_instance(self)
        self.share_manager = MemoShareManager(self)
        self.export_manager = MemoExportManager(self)

        # 如果有用户ID，构建AI记忆上下文
        if self.user_id:
            self.ai_handler.ai_service.build_memory_context(self.user_id, self.db)

        # 设置AI记忆更新定时器
        self.memory_update_timer = QTimer(self)
        self.memory_update_timer.timeout.connect(self._update_memory_context)
        self.memory_update_timer.start(1 * 60 * 1000)

        # 设置工具栏动作
        self._setup_toolbar()

        # 设置UI组件
        self._setup_ui_components()

        # 创建待办事项提取器
        self.todo_extractor = TodoExtractor(self)

    def _setup_toolbar(self):
        """设置工具栏按钮和动作"""
        # AI编辑按钮
        self.frame_2.addAction(
            Action(
                FluentIcon.ROBOT,
                "AI编辑",
                triggered=lambda: self.ai_handler.show_ai_menu(self.textEdit),
            )
        )

        self.frame_2.addSeparator()

        # 保存和清空按钮
        save_action = Action(FluentIcon.SAVE, "保存")
        save_action.triggered.connect(self.save_memo)
        self.frame_2.addActions(
            [
                save_action,
                Action(FluentIcon.DELETE, "清空", triggered=self.clear_memo),
            ]
        )

        self.frame_2.addSeparator()

        # 导出和分享按钮
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

        # 提取待办事项按钮
        self.frame_2.addAction(
            Action(
                FluentIcon.CHECKBOX,
                "提取待办事项",
                triggered=self.extract_todos,
            )
        )


    def _setup_ui_components(self):
        """设置UI组件"""
        # 设置输入框提示文本
        self.lineEdit.setPlaceholderText("请输入备忘录标题")
        self.lineEdit_2.setPlaceholderText("请选择标签")

        # 为下拉框添加事件过滤器确保每次点击时刷新内容
        self.lineEdit_2.installEventFilter(self)

        # 创建并设置文本编辑器
        layout = self.frame.layout()
        if layout is None:
            layout = VBoxLayout(self.frame)
            layout.setContentsMargins(30, 40, 30, 20)
            self.frame.setLayout(layout)

        self.textEdit = SmartTextEdit(self)

        # 如果已存在，先移除旧的textEdit
        for i in range(layout.count()):
            if layout.itemAt(i).widget() == self.textEdit:
                layout.removeWidget(self.textEdit)
                self.textEdit.setParent(None)
                break

        # 添加新的textEdit
        layout.addWidget(self.textEdit, 1, 0)

        # 连接信号
        self.textEdit.textChanged.connect(self.update_markdown_preview)
        self.textEdit.textChanged.connect(self.update_word_count)

        # 初始化
        self.update_markdown_preview()
        self.update_word_count()
        self.update_tag_combobox()
        
    def eventFilter(self, obj, event):
        """事件过滤器，用于捕获下拉框点击事件"""
        if obj is self.lineEdit_2:
            if event.type() == QEvent.MouseButtonPress:
                # 在下拉框被点击时刷新标签列表
                self.update_tag_combobox()
            elif event.type() == QEvent.FocusIn:
                # 在下拉框获得焦点时刷新标签列表
                self.update_tag_combobox()
        
        return super().eventFilter(obj, event)

    def _update_memory_context(self):
        """定期更新AI记忆上下文"""
        try:
            if (
                self.user_id
                and hasattr(self, "ai_handler")
                and hasattr(self.ai_handler, "ai_service")
            ):
                self.ai_handler.ai_service.build_memory_context(self.user_id, self.db)
        except Exception:
            pass

    def showEvent(self, event):
        """当窗口显示时调用"""
        if self.user_id:
            self.load_user_tags()  # 先加载最新标签数据

        # print("显示窗口，正在更新标签列表...")  # 调试信息
        self.update_tag_combobox()
        super().showEvent(event)

    def load_user_tags(self):
        """从数据库加载用户的所有历史标签"""
        if not self.user_id:
            return []

        try:
            # 获取用户的所有标签
            tags = self.db.get_user_tags(self.user_id)

            # 提取标签名称
            tag_names = [tag["tag_name"] for tag in tags]
            return tag_names
        except Exception as e:
            print(f"加载用户标签时出错: {str(e)}")
            return []

    def update_tag_combobox(self):
        """更新标签下拉框的选项"""
        current_tag = self.lineEdit_2.text()
        tag_names = self.load_user_tags()

        # print(f"更新标签下拉框，加载了 {len(tag_names)} 个标签: {tag_names}")

        self.lineEdit_2.clear()
        self.lineEdit_2.addItems(tag_names)

        if current_tag and current_tag in tag_names:
            index = self.lineEdit_2.findText(current_tag)
            if index >= 0:
                self.lineEdit_2.setCurrentIndex(index)

    def update_markdown_preview(self):
        """实时更新Markdown预览内容"""
        content = self.textEdit.toPlainText()
        self.textBrowser.setMarkdown(content)

    def save_memo(self, silent=False):
        """保存备忘录到数据库"""
        title = self.lineEdit.text()
        content = self.textEdit.toPlainText()
        category = self.lineEdit_2.text()

        if not title or not content:
            if not silent:
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
            # 如果有分类，保存标签
            if category and self.user_id:
                try:
                    self.db.add_tag(self.user_id, category)
                except Exception as e:
                    print(f"保存标签时出错: {str(e)}")

            # 创建新备忘录或更新现有备忘录
            if self.memo_id is None:
                memo_id = self.db.create_memo(self.user_id, title, content, category)
                if memo_id:
                    self.memo_id = memo_id
                    if not silent:
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
                success = self.db.update_memo(
                    self.memo_id, title=title, content=content, category=category
                )
                if success:
                    if not silent:
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

            # 如果到这里还没返回，说明保存失败
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
        self.memo_id = None
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

        if self.save_memo(silent=True):
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

        if self.save_memo(silent=True):
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
        title = self.lineEdit.text()
        content = self.textEdit.toPlainText()
        category = self.lineEdit_2.text()

        self.export_manager.export_to_pdf(title, content, category)

    def export_to_txt(self):
        """导出备忘录为TXT文件"""
        title = self.lineEdit.text()
        content = self.textEdit.toPlainText()
        category = self.lineEdit_2.text()

        self.export_manager.export_to_txt(title, content, category)

    def share_to(self, platform):
        """分享备忘录到指定平台"""
        title = self.lineEdit.text()
        content = self.textEdit.toPlainText()
        category = self.lineEdit_2.text()

        self.share_manager.share_to(platform, title, content, category)

    def extract_todos(self):
        """从当前备忘录内容中提取待办事项"""
        if not self.user_id:
            InfoBar.error(title="错误", content="请先登录", parent=self)
            return

        memo_content = self.textEdit.toPlainText()
        self.todo_extractor.extract_todos(memo_content, self.user_id, self.ai_handler)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = MemoInterface()
    w.show()
    sys.exit(app.exec_())
