from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget,
    QApplication, QFrame, QWIDGETSIZE_MAX
)
from qfluentwidgets import (
    StateToolTip, InfoBar, PrimaryPushButton, PushButton,
    CheckBox, BodyLabel, CaptionLabel, IconWidget, FluentIcon,
    CardWidget, TextEdit, ComboBox, CalendarPicker, TimePicker,
    VBoxLayout, InfoBarPosition, ScrollArea, Dialog, isDarkTheme, Theme
)
from PyQt5.QtCore import QDate, QTime, QEvent
from datetime import datetime
from Database import DatabaseManager
from mainWindow.ui.view.ai_handler import AIHandler

class TodoExtractThread(QThread):
    """提取待办事项的工作线程"""
    resultReady = pyqtSignal(int, list)

    def __init__(self, ai_handler, memo_content, user_id):
        super().__init__()
        self.ai_handler = ai_handler
        self.memo_content = memo_content
        self.user_id = user_id

    def run(self):
        count, todos = self.ai_handler.extract_todos_from_memo(
            self.memo_content, self.user_id
        )
        self.resultReady.emit(count, todos)


class TodoExtractorDialog(Dialog):
    """待办事项提取对话框"""

    def __init__(self, todos, user_id, parent=None):
        self.todos = todos
        self.user_id = user_id
        self.todo_checkboxes = []  # 存储待办事项的复选框
        self.select_all_checkbox = None  # 全选复选框

        # 调用父类构造函数
        super().__init__("提取的待办事项", "", parent=parent)

        # 设置对话框大小
        self.resize(800, 600)
        self.setMinimumSize(600, 400)
        # 移除重复的最大尺寸设置，只保留一个
        self.setMaximumSize(16777215, 16777215)
        self.setResizeEnabled(True)

        # 设置窗口标志，使用系统标题栏而非自定义标题栏
        self.setWindowFlags(
            Qt.Dialog |
            Qt.CustomizeWindowHint |  # 自定义窗口外观
            Qt.WindowTitleHint |      # 显示标题栏
            Qt.WindowSystemMenuHint | # 显示系统菜单
            Qt.WindowMinMaxButtonsHint | # 显示最小化和最大化按钮
            Qt.WindowCloseButtonHint    # 显示关闭按钮
        )

        # 设置属性以确保全屏时能完全覆盖屏幕
        self.setAttribute(Qt.WA_TranslucentBackground, False)  # 不透明背景
        self.setAttribute(Qt.WA_NoSystemBackground, False)     # 使用系统背景

        # 设置对话框背景样式 - 定义为类变量便于全局使用
        self.bgColor = "#1E1E1E" if isDarkTheme() else "#F5F5F5"
        self.setStyleSheet(f"background-color: {self.bgColor};")

        # 不隐藏标题栏，但在全屏模式下会隐藏
        # 在小屏模式下保持标题栏和控制按钮可见
        if hasattr(self, 'titleBar'):
            self.titleBar.show()
            # 确保标题栏按钮可见
            if hasattr(self.titleBar, 'minBtn'):
                self.titleBar.minBtn.show()
            if hasattr(self.titleBar, 'maxBtn'):
                self.titleBar.maxBtn.show()
            if hasattr(self.titleBar, 'closeBtn'):
                self.titleBar.closeBtn.show()

        # 隐藏窗口标题标签
        if hasattr(self, 'windowTitleLabel'):
            self.windowTitleLabel.setVisible(False)

        # 设置窗口标题
        self.setWindowTitle("提取的待办事项")

        # 设置UI
        self.setup_ui()

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)

    def changeEvent(self, event):
        """处理窗口状态变化事件，如最大化/最小化"""
        if event.type() == QEvent.WindowStateChange:
            # 无论窗口状态如何，都保持标题栏和控制按钮可见
            if hasattr(self, 'titleBar'):
                self.titleBar.show()
                if hasattr(self.titleBar, 'minBtn'):
                    self.titleBar.minBtn.show()
                if hasattr(self.titleBar, 'maxBtn'):
                    self.titleBar.maxBtn.show()
                if hasattr(self.titleBar, 'closeBtn'):
                    self.titleBar.closeBtn.show()

        super().changeEvent(event)

    def setup_ui(self):
        # 移除底部按钮区域和内容标签
        # 安全地处理buttonGroup
        if hasattr(self, 'buttonGroup') and self.buttonGroup:
            try:
                self.buttonGroup.setParent(None)
                self.buttonGroup.deleteLater()
            except RuntimeError:
                # 如果对象已经被删除，忽略错误
                pass

        # 检查contentLabel是否存在且有效
        if hasattr(self, 'contentLabel') and self.contentLabel and not self.contentLabel.isHidden():
            try:
                self.contentLabel.setVisible(False)
            except RuntimeError:
                # 如果对象已经被删除，忽略错误
                pass

        # 添加标题
        title_layout = QHBoxLayout()
        title_icon = IconWidget(FluentIcon.CHECKBOX, self)
        title_icon.setFixedSize(24, 24)
        title_label = BodyLabel("从备忘录中提取的待办事项")
        title_label.setObjectName("ExtractedTodosTitle")

        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)

        # 添加全选/取消全选复选框
        self.select_all_checkbox = CheckBox("全选")
        self.select_all_checkbox.setChecked(True)  # 默认全选
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)

        title_layout.addWidget(self.select_all_checkbox)

        self.textLayout.addLayout(title_layout)

        # 创建滚动区域
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("TodoScrollArea")
        scroll.setMinimumHeight(400)

        # 统一设置滚动区域样式 - 使用类变量保持一致性
        scroll.setStyleSheet(f"background-color: {self.bgColor}; border: none;")

        content_widget = QWidget()
        content_widget.setObjectName("TodoContentWidget")

        # 统一设置内容区域样式 - 使用类变量保持一致性
        content_widget.setStyleSheet(f"background-color: {self.bgColor};")

        # 将内容布局设置到内容区域
        content_layout = VBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        # 清空复选框列表
        self.todo_checkboxes = []

        # 添加待办事项卡片
        for i, todo in enumerate(self.todos):
            card = CardWidget()
            card.setObjectName(f"TodoCard_{i}")
            card_layout = VBoxLayout(card)
            card_layout.setContentsMargins(20, 16, 20, 16)
            card_layout.setSpacing(12)

            # 任务内容
            task_layout = QHBoxLayout()
            task_layout.setSpacing(12)

            # 添加选择复选框
            select_check = CheckBox()
            select_check.setFixedSize(24, 24)
            select_check.setChecked(True)  # 默认选中
            select_check.stateChanged.connect(self._update_select_all_state)
            self.todo_checkboxes.append(select_check)  # 添加到复选框列表

            # 设置选择复选框的样式
            if isDarkTheme():
                select_check.setStyleSheet("""
                    QCheckBox {
                        background: transparent;
                        border: none;
                        spacing: 8px; /* 文本和指示器之间的间距 */
                    }
                    QCheckBox::indicator {
                        width: 22px;
                        height: 22px;
                        border: 2px solid #666;
                        border-radius: 4px;
                        background-color: #2B2B2B;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #0078d4; /* 选中时的背景颜色 */
                        border-color: #0078d4;
                    }
                    QCheckBox::indicator:hover {
                        border-color: #0078d4;
                    }
                """)
            else:
                select_check.setStyleSheet("""
                    QCheckBox {
                        background: transparent;
                        border: none;
                        spacing: 8px; /* 文本和指示器之间的间距 */
                    }
                    QCheckBox::indicator {
                        width: 22px;
                        height: 22px;
                        border: 2px solid #999;
                        border-radius: 4px;
                        background-color: white;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #0078d4; /* 选中时的背景颜色 */
                        border-color: #0078d4;
                    }
                    QCheckBox::indicator:hover {
                        border-color: #0078d4;
                    }
                """)

            # 任务标签
            task_label = BodyLabel(todo.get("task", ""))
            task_label.setWordWrap(True)
            task_label.setMinimumHeight(24)
            task_label.setObjectName("TaskLabel")
            task_label.setStyleSheet("background: transparent;")

            task_layout.addWidget(select_check)  # 选择复选框
            task_layout.addWidget(task_label, 1)

            # 编辑按钮
            edit_button = PushButton("编辑")
            edit_button.setIcon(FluentIcon.EDIT)
            edit_button.clicked.connect(lambda _, idx=i: self._edit_todo_item(idx))
            task_layout.addWidget(edit_button)

            card_layout.addLayout(task_layout)

            # 截止日期和类别
            info_layout = QHBoxLayout()

            # 截止日期
            deadline = todo.get("deadline", "无截止日期")
            deadline_layout = QHBoxLayout()
            deadline_layout.setSpacing(4)

            deadline_icon = IconWidget(FluentIcon.CALENDAR, self)
            deadline_icon.setFixedSize(16, 16)
            deadline_label = CaptionLabel(deadline if deadline else "无截止日期")
            deadline_label.setObjectName("DeadlineLabel")

            # 统一设置透明背景
            deadline_icon.setStyleSheet("background: transparent;")
            deadline_label.setStyleSheet("background: transparent;")

            deadline_layout.addWidget(deadline_icon)
            deadline_layout.addWidget(deadline_label)

            # 类别
            category = todo.get("category", "未分类")
            category_layout = QHBoxLayout()
            category_layout.setSpacing(4)

            category_icon = IconWidget(FluentIcon.TAG, self)
            category_icon.setFixedSize(16, 16)
            category_label = CaptionLabel(category if category else "未分类")
            category_label.setObjectName("CategoryLabel")

            # 统一设置透明背景
            category_icon.setStyleSheet("background: transparent;")
            category_label.setStyleSheet("background: transparent;")

            category_layout.addWidget(category_icon)
            category_layout.addWidget(category_label)

            info_layout.addLayout(deadline_layout)
            info_layout.addStretch(1)
            info_layout.addLayout(category_layout)

            card_layout.addLayout(info_layout)

            # 统一设置卡片样式 - 根据主题设置不同的卡片样式
            card_bg_color = "#2B2B2B" if isDarkTheme() else "#FFFFFF"
            card_border_color = "#3D3D3D" if isDarkTheme() else "#E0E0E0"
            card.setStyleSheet(f"""
                CardWidget {{
                    background-color: {card_bg_color};
                    border: 1px solid {card_border_color};
                    border-radius: 6px;
                }}
            """)

            content_layout.addWidget(card)

        # 将内容区域设置到滚动区域
        scroll.setWidget(content_widget)

        # 将滚动区域添加到主布局
        self.textLayout.addWidget(scroll)

        # 添加按钮
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 16, 0, 0)
        button_layout.setSpacing(12)

        # 添加到待办事项按钮
        add_button = PrimaryPushButton("添加到待办事项")
        add_button.setIcon(FluentIcon.ADD)
        add_button.clicked.connect(self._add_todos_to_database_and_close)

        # 取消按钮
        cancel_button = PushButton("取消")
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch(1)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(add_button)

        self.textLayout.addLayout(button_layout)

    def _edit_todo_item(self, index):
        """编辑待办事项"""
        todo = self.todos[index]
        dialog = TodoEditDialog(todo, self)
        if dialog.exec_() == QDialog.Accepted:
            # 更新待办事项
            self.todos[index] = dialog.get_todo_data()

            # 保存当前的选中状态
            checkbox_states = []
            for checkbox in self.todo_checkboxes:
                checkbox_states.append(checkbox.isChecked())

            # 使用安全的方式重新创建对话框，而不是刷新当前对话框
            try:
                # 创建一个新的对话框并显示
                new_dialog = TodoExtractorDialog(self.todos, self.user_id, self.parent())

                # 恢复选中状态
                if len(checkbox_states) == len(new_dialog.todo_checkboxes):
                    for i, state in enumerate(checkbox_states):
                        new_dialog.todo_checkboxes[i].blockSignals(True)
                        new_dialog.todo_checkboxes[i].setChecked(state)
                        new_dialog.todo_checkboxes[i].blockSignals(False)
                    # 更新全选复选框状态
                    new_dialog._update_select_all_state()

                self.accept()  # 关闭当前对话框
                new_dialog.exec_()  # 显示新对话框
            except Exception as e:
                print(f"创建新对话框时出错: {str(e)}")
                # 如果出错，尝试刷新当前对话框
                QApplication.processEvents()  # 处理所有挂起的事件
                self._refresh_ui()

    def _refresh_ui(self):
        """刷新UI显示"""
        try:
            # 清除现有内容 - 修改为更彻底的清理方式
            if hasattr(self, 'textLayout') and self.textLayout:
                while self.textLayout.count():
                    item = self.textLayout.takeAt(0)
                    if item and item.widget():
                        item.widget().deleteLater()
                    elif item and item.layout():
                        self._clear_layout(item.layout())

            # 重新设置UI
            self.setup_ui()
        except RuntimeError as e:
            print(f"刷新UI时出错: {str(e)}")
            # 如果出错，尝试重新创建对话框
            self.reject()
            dialog = TodoExtractorDialog(self.todos, self.user_id, self.parent())
            dialog.exec_()

    def _clear_layout(self, layout):
        """递归清除布局中的所有元素"""
        try:
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    if item and item.widget():
                        item.widget().deleteLater()
                    elif item and item.layout():
                        self._clear_layout(item.layout())
        except RuntimeError as e:
            print(f"清除布局时出错: {str(e)}")

    def _on_select_all_changed(self, state):
        """全选/取消全选复选框状态改变时的处理"""
        # 将所有待办事项的复选框状态设置为与全选复选框相同
        for checkbox in self.todo_checkboxes:
            # 阻断信号以避免循环触发
            checkbox.blockSignals(True)
            checkbox.setChecked(state == Qt.Checked)
            checkbox.blockSignals(False)

    def _update_select_all_state(self):
        """根据待办事项复选框状态更新全选复选框状态"""
        if not self.todo_checkboxes:
            return

        # 阻断信号以避免循环触发
        self.select_all_checkbox.blockSignals(True)

        # 检查是否所有待办事项都被选中
        all_checked = all(checkbox.isChecked() for checkbox in self.todo_checkboxes)

        # 只有全选和非全选两种状态
        if all_checked:
            # 如果所有待办事项都被选中，则全选复选框也被选中
            self.select_all_checkbox.setChecked(True)
        else:
            # 如果不是所有待办事项都被选中，则全选复选框不被选中
            self.select_all_checkbox.setChecked(False)

        self.select_all_checkbox.blockSignals(False)

    def _add_todos_to_database_and_close(self):
        """添加待办事项到数据库并关闭对话框"""
        # 创建TodoExtractor实例来添加待办事项
        todo_extractor = TodoExtractor(self.parent())

        # 筛选出选中的待办事项
        selected_todos = []
        for i, checkbox in enumerate(self.todo_checkboxes):
            if checkbox.isChecked() and i < len(self.todos):
                selected_todos.append(self.todos[i])

        # 如果没有选中任何待办事项，显示提示并返回
        if not selected_todos:
            InfoBar.warning(
                title="提示",
                content="请至少选择一个待办事项",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        # 添加选中的待办事项到数据库
        added_count = todo_extractor._add_todos_to_database(selected_todos, self.user_id)

        # 显示成功消息
        if added_count > 0:
            InfoBar.success(
                title="添加成功",
                content=f"已成功添加 {added_count} 个待办事项",
                parent=self.parent(),
                position=InfoBarPosition.TOP,
                duration=3000
            )
        else:
            InfoBar.warning(
                title="添加失败",
                content="未能添加任何待办事项",
                parent=self.parent(),
                position=InfoBarPosition.TOP,
                duration=3000
            )

        # 关闭对话框
        self.accept()


class TodoEditDialog(Dialog):
    """待办事项编辑对话框"""

    def __init__(self, todo, parent=None):
        self.todo = todo

        # 调用父类构造函数
        super().__init__("编辑待办事项", "", parent=parent)

        # 设置对话框属性
        self.resize(400, 300)

        # 设置UI
        self.setup_ui()

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)

    def setup_ui(self):
        # 移除底部按钮区域和内容标签
        if hasattr(self, 'buttonGroup'):
            self.buttonGroup.setParent(None)
            self.buttonGroup.deleteLater()

        if hasattr(self, 'contentLabel'):
            self.contentLabel.setVisible(False)

        # 添加标题和图标
        title_layout = QHBoxLayout()
        title_icon = IconWidget(FluentIcon.EDIT, self)
        title_icon.setFixedSize(20, 20)
        title_label = BodyLabel("编辑待办事项")
        title_label.setObjectName("EditTodoTitle")

        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)

        self.textLayout.addLayout(title_layout)
        self.textLayout.addSpacing(10)

        # 任务内容
        task_label = BodyLabel("任务内容:")
        task_label.setObjectName("FieldLabel")
        self.task_edit = TextEdit()
        self.task_edit.setText(self.todo.get("task", ""))
        self.task_edit.setFixedHeight(80)
        self.task_edit.setObjectName("TaskEdit")

        # 截止日期
        deadline_label = BodyLabel("截止日期:")
        deadline_label.setObjectName("FieldLabel")
        date_layout = QHBoxLayout()

        self.date_picker = CalendarPicker()
        self.time_picker = TimePicker()

        # 设置默认日期和时间
        deadline = self.todo.get("deadline", "")
        if deadline and " " in deadline:
            date_str, time_str = deadline.split(" ", 1)
            if date_str and len(date_str.split("-")) == 3:
                year, month, day = map(int, date_str.split("-"))
                self.date_picker.setDate(QDate(year, month, day))

            if time_str and len(time_str.split(":")) >= 2:
                hour, minute = map(int, time_str.split(":")[:2])
                self.time_picker.setTime(QTime(hour, minute))

        date_layout.addWidget(self.date_picker)
        date_layout.addWidget(self.time_picker)

        # 类别
        category_label = BodyLabel("类别:")
        category_label.setObjectName("FieldLabel")
        self.category_combo = ComboBox()
        self.category_combo.addItems(["工作", "学习", "生活", "其他"])
        self.category_combo.setObjectName("CategoryCombo")

        # 设置默认类别
        category = self.todo.get("category", "其他")
        index = self.category_combo.findText(category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)

        # 添加到布局
        self.textLayout.addWidget(task_label)
        self.textLayout.addWidget(self.task_edit)
        self.textLayout.addSpacing(10)
        self.textLayout.addWidget(deadline_label)
        self.textLayout.addLayout(date_layout)
        self.textLayout.addSpacing(10)
        self.textLayout.addWidget(category_label)
        self.textLayout.addWidget(self.category_combo)
        self.textLayout.addSpacing(15)

        # 添加按钮
        button_layout = QHBoxLayout()

        # 保存按钮
        save_button = PrimaryPushButton("保存")
        save_button.setIcon(FluentIcon.SAVE)
        save_button.clicked.connect(self._on_save)

        # 取消按钮
        cancel_button = PushButton("取消")
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch(1)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)

        self.textLayout.addLayout(button_layout)

    def _on_save(self):
        """保存编辑"""
        # 获取编辑后的值
        task = self.task_edit.toPlainText().strip()
        if not task:
            InfoBar.error(
                title="错误",
                content="任务内容不能为空",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return

        # 获取日期时间
        selected_date = self.date_picker.getDate().toString("yyyy-MM-dd")
        selected_time = self.time_picker.getTime().toString("hh:mm")
        deadline = f"{selected_date} {selected_time}"

        # 更新待办事项
        self.todo = {
            'task': task,
            'deadline': deadline,
            'category': self.category_combo.currentText()
        }

        # 接受对话框
        self.accept()

    def get_todo_data(self):
        """获取编辑后的待办事项数据"""
        return self.todo


class TodoExtractor:
    """待办事项提取器"""

    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.state_tooltip = None
        self.todo_thread = None

    def extract_todos(self, memo_content, user_id, ai_handler):
        """从备忘录内容中提取待办事项"""
        if not user_id:
            InfoBar.error(title="错误", content="请先登录", parent=self.parent)
            return

        if not memo_content.strip():
            InfoBar.warning(
                title="提示", content="备忘录内容为空，无法提取待办事项", parent=self.parent
            )
            return

        # 显示加载状态提示
        self.state_tooltip = StateToolTip(
            "正在处理", "AI正在分析备忘录内容，提取待办事项...", parent=self.parent
        )
        self.state_tooltip.move(
            (self.parent.width() - self.state_tooltip.width()) // 2,
            (self.parent.height() - self.state_tooltip.height()) // 2,
        )
        self.state_tooltip.show()
        QApplication.processEvents()

        # 创建并启动线程
        self.todo_thread = TodoExtractThread(
            ai_handler, memo_content, user_id
        )
        self.todo_thread.resultReady.connect(
            lambda count, todos: self._on_todos_extracted(count, todos, user_id)
        )
        self.todo_thread.start()

    def _on_todos_extracted(self, count, todos, user_id):
        """待办事项提取完成的回调"""
        self.safely_close_tooltip()

        if count == 0:
            InfoBar.warning(
                title="提示",
                content="未能从备忘录中提取到待办事项",
                parent=self.parent,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        # 显示提取结果对话框
        dialog = TodoExtractorDialog(todos, user_id, self.parent)
        dialog.exec_()

    def safely_close_tooltip(self):
        """安全关闭提示框"""
        try:
            if hasattr(self, "state_tooltip") and self.state_tooltip:
                self.state_tooltip.close()
                self.state_tooltip = None
        except Exception as e:
            print(f"关闭提示框时出错: {str(e)}")

    def _add_todos_to_database(self, todos, user_id):
        """将待办事项添加到数据库"""
        db = DatabaseManager()
        added_count = 0

        for todo in todos:
            try:
                task = todo.get("task", "")
                deadline = todo.get("deadline", "")
                category = todo.get("category", "其他")

                # 确保任务内容不为空
                if not task:
                    continue

                # 添加到数据库
                todo_id = db.add_todo(
                    user_id=user_id,
                    task=task,
                    deadline=deadline,
                    category=category
                )

                if todo_id:
                    added_count += 1

            except Exception as e:
                print(f"添加待办事项时出错: {str(e)}")

        return added_count
