from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QWidget,
    QApplication,
    QFrame,
    QWIDGETSIZE_MAX,
)
from qfluentwidgets import (
    StateToolTip,
    InfoBar,
    PrimaryPushButton,
    PushButton,
    CheckBox,
    BodyLabel,
    CaptionLabel,
    IconWidget,
    FluentIcon,
    CardWidget,
    TextEdit,
    ComboBox,
    CalendarPicker,
    TimePicker,
    VBoxLayout,
    InfoBarPosition,
    ScrollArea,
    Dialog,
    isDarkTheme,
    Theme,
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
        self.todo_checkboxes = []
        self.select_all_checkbox = None

        super().__init__("提取的待办事项", "", parent=parent)

        self.resize(800, 600)
        self.setMinimumSize(600, 400)
        self.setMaximumSize(16777215, 16777215)
        self.setResizeEnabled(True)

        self.setWindowFlags(
            Qt.Dialog
            | Qt.CustomizeWindowHint
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinMaxButtonsHint
            | Qt.WindowCloseButtonHint
        )

        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_NoSystemBackground, False)

        self.bgColor = "#1E1E1E" if isDarkTheme() else "#F5F5F5"
        self.setStyleSheet(f"background-color: {self.bgColor};")

        if hasattr(self, "titleBar"):
            self.titleBar.show()
            if hasattr(self.titleBar, "minBtn"):
                self.titleBar.minBtn.show()
            if hasattr(self.titleBar, "maxBtn"):
                self.titleBar.maxBtn.show()
            if hasattr(self.titleBar, "closeBtn"):
                self.titleBar.closeBtn.show()

        if hasattr(self, "windowTitleLabel"):
            self.windowTitleLabel.setVisible(False)

        self.setWindowTitle("提取的待办事项")

        self.setup_ui()

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)

    def changeEvent(self, event):
        """处理窗口状态变化事件，如最大化/最小化"""
        if event.type() == QEvent.WindowStateChange:
            if hasattr(self, "titleBar"):
                self.titleBar.show()
                if hasattr(self.titleBar, "minBtn"):
                    self.titleBar.minBtn.show()
                if hasattr(self.titleBar, "maxBtn"):
                    self.titleBar.maxBtn.show()
                if hasattr(self.titleBar, "closeBtn"):
                    self.titleBar.closeBtn.show()

        super().changeEvent(event)

    def setup_ui(self):
        if hasattr(self, "buttonGroup") and self.buttonGroup:
            try:
                self.buttonGroup.setParent(None)
                self.buttonGroup.deleteLater()
            except RuntimeError:
                pass

        if (
            hasattr(self, "contentLabel")
            and self.contentLabel
            and not self.contentLabel.isHidden()
        ):
            try:
                self.contentLabel.setVisible(False)
            except RuntimeError:
                pass

        title_layout = QHBoxLayout()
        title_icon = IconWidget(FluentIcon.CHECKBOX, self)
        title_icon.setFixedSize(24, 24)
        title_label = BodyLabel("从备忘录中提取的待办事项")
        title_label.setObjectName("ExtractedTodosTitle")

        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)

        self.select_all_checkbox = CheckBox("全选")
        self.select_all_checkbox.setChecked(True)
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)

        title_layout.addWidget(self.select_all_checkbox)

        self.textLayout.addLayout(title_layout)

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("TodoScrollArea")
        scroll.setMinimumHeight(400)

        scroll.setStyleSheet(f"background-color: {self.bgColor}; border: none;")

        content_widget = QWidget()
        content_widget.setObjectName("TodoContentWidget")

        content_widget.setStyleSheet(f"background-color: {self.bgColor};")

        content_layout = VBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        self.todo_checkboxes = []

        for i, todo in enumerate(self.todos):
            card = CardWidget()
            card.setObjectName(f"TodoCard_{i}")
            card_layout = VBoxLayout(card)
            card_layout.setContentsMargins(20, 16, 20, 16)
            card_layout.setSpacing(12)

            task_layout = QHBoxLayout()
            task_layout.setSpacing(12)

            checkbox_container = QWidget()
            checkbox_container.setFixedSize(24, 24)
            checkbox_container.setStyleSheet("background: transparent; border: none;")

            checkbox_layout = QVBoxLayout(checkbox_container)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setSpacing(0)

            select_check = CheckBox()
            select_check.setFixedSize(24, 24)
            select_check.setChecked(True)
            select_check.stateChanged.connect(self._update_select_all_state)
            self.todo_checkboxes.append(select_check)

            checkbox_layout.addWidget(select_check)
            task_layout.addWidget(checkbox_container)

            task_label = BodyLabel(todo.get("task", ""))
            task_label.setWordWrap(True)
            task_label.setMinimumHeight(24)
            task_label.setObjectName("TaskLabel")
            task_label.setStyleSheet("background: transparent;")

            task_layout.addWidget(task_label, 1)

            edit_button = PushButton("编辑")
            edit_button.setIcon(FluentIcon.EDIT)
            edit_button.clicked.connect(lambda _, idx=i: self._edit_todo_item(idx))
            task_layout.addWidget(edit_button)

            card_layout.addLayout(task_layout)

            info_layout = QHBoxLayout()

            deadline = todo.get("deadline", "无截止日期")
            deadline_layout = QHBoxLayout()
            deadline_layout.setSpacing(4)

            deadline_icon = IconWidget(FluentIcon.CALENDAR, self)
            deadline_icon.setFixedSize(16, 16)
            deadline_label = CaptionLabel(deadline if deadline else "无截止日期")
            deadline_label.setObjectName("DeadlineLabel")

            deadline_icon.setStyleSheet("background: transparent;")
            deadline_label.setStyleSheet("background: transparent;")

            deadline_layout.addWidget(deadline_icon)
            deadline_layout.addWidget(deadline_label)

            category = todo.get("category", "未分类")
            category_layout = QHBoxLayout()
            category_layout.setSpacing(4)

            category_icon = IconWidget(FluentIcon.TAG, self)
            category_icon.setFixedSize(16, 16)
            category_label = CaptionLabel(category if category else "未分类")
            category_label.setObjectName("CategoryLabel")

            category_icon.setStyleSheet("background: transparent;")
            category_label.setStyleSheet("background: transparent;")

            category_layout.addWidget(category_icon)
            category_layout.addWidget(category_label)

            info_layout.addLayout(deadline_layout)
            info_layout.addStretch(1)
            info_layout.addLayout(category_layout)

            card_layout.addLayout(info_layout)

            card_bg_color = "#2B2B2B" if isDarkTheme() else "#FFFFFF"
            card_border_color = "#3D3D3D" if isDarkTheme() else "#E0E0E0"
            card.setStyleSheet(
                f"""
                CardWidget {{
                    background-color: {card_bg_color};
                    border: 1px solid {card_border_color};
                    border-radius: 6px;
                }}
            """
            )

            content_layout.addWidget(card)

        scroll.setWidget(content_widget)

        self.textLayout.addWidget(scroll)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 16, 0, 0)
        button_layout.setSpacing(12)

        add_button = PrimaryPushButton("添加到待办事项")
        add_button.setIcon(FluentIcon.ADD)
        add_button.clicked.connect(self._add_todos_to_database_and_close)

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
            self.todos[index] = dialog.get_todo_data()

            checkbox_states = []
            for checkbox in self.todo_checkboxes:
                checkbox_states.append(checkbox.isChecked())

            try:
                new_dialog = TodoExtractorDialog(
                    self.todos, self.user_id, self.parent()
                )

                if len(checkbox_states) == len(new_dialog.todo_checkboxes):
                    for i, state in enumerate(checkbox_states):
                        new_dialog.todo_checkboxes[i].blockSignals(True)
                        new_dialog.todo_checkboxes[i].setChecked(state)
                        new_dialog.todo_checkboxes[i].blockSignals(False)
                    new_dialog._update_select_all_state()

                self.accept()
                new_dialog.exec_()
            except Exception as e:
                QApplication.processEvents()
                self._refresh_ui()

    def _refresh_ui(self):
        """刷新UI显示"""
        try:
            if hasattr(self, "textLayout") and self.textLayout:
                while self.textLayout.count():
                    item = self.textLayout.takeAt(0)
                    if item and item.widget():
                        item.widget().deleteLater()
                    elif item and item.layout():
                        self._clear_layout(item.layout())

            self.setup_ui()
        except RuntimeError:
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
        except RuntimeError:
            pass

    def _on_select_all_changed(self, state):
        """全选/取消全选复选框状态改变时的处理"""
        for checkbox in self.todo_checkboxes:
            checkbox.blockSignals(True)
            checkbox.setChecked(state == Qt.Checked)
            checkbox.blockSignals(False)

    def _update_select_all_state(self):
        """根据待办事项复选框状态更新全选复选框状态"""
        if not self.todo_checkboxes:
            return

        self.select_all_checkbox.blockSignals(True)

        all_checked = all(checkbox.isChecked() for checkbox in self.todo_checkboxes)

        if all_checked:
            self.select_all_checkbox.setChecked(True)
        else:
            self.select_all_checkbox.setChecked(False)

        self.select_all_checkbox.blockSignals(False)

    def _add_todos_to_database_and_close(self):
        """添加待办事项到数据库并关闭对话框"""
        todo_extractor = TodoExtractor(self.parent())

        selected_todos = []
        for i, checkbox in enumerate(self.todo_checkboxes):
            if checkbox.isChecked() and i < len(self.todos):
                selected_todos.append(self.todos[i])

        if not selected_todos:
            InfoBar.warning(
                title="提示",
                content="请至少选择一个待办事项",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
            return

        added_count = todo_extractor._add_todos_to_database(
            selected_todos, self.user_id
        )

        if added_count > 0:
            InfoBar.success(
                title="添加成功",
                content=f"已成功添加 {added_count} 个待办事项",
                parent=self.parent(),
                position=InfoBarPosition.TOP,
                duration=3000,
            )
        else:
            InfoBar.warning(
                title="添加失败",
                content="未能添加任何待办事项",
                parent=self.parent(),
                position=InfoBarPosition.TOP,
                duration=3000,
            )
        self.accept()


class TodoEditDialog(Dialog):
    """待办事项编辑对话框"""

    def __init__(self, todo, parent=None):
        self.todo = todo

        super().__init__("编辑待办事项", "", parent=parent)

        self.resize(400, 300)

        self.setup_ui()

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)

    def setup_ui(self):
        if hasattr(self, "buttonGroup"):
            self.buttonGroup.setParent(None)
            self.buttonGroup.deleteLater()

        if hasattr(self, "contentLabel"):
            self.contentLabel.setVisible(False)

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

        task_label = BodyLabel("任务内容:")
        task_label.setObjectName("FieldLabel")
        self.task_edit = TextEdit()
        self.task_edit.setText(self.todo.get("task", ""))
        self.task_edit.setFixedHeight(80)
        self.task_edit.setObjectName("TaskEdit")

        deadline_label = BodyLabel("截止日期:")
        deadline_label.setObjectName("FieldLabel")
        date_layout = QHBoxLayout()

        self.date_picker = CalendarPicker()
        self.time_picker = TimePicker()

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

        category_label = BodyLabel("类别:")
        category_label.setObjectName("FieldLabel")
        self.category_combo = ComboBox()
        self.category_combo.addItems(["工作", "学习", "生活", "其他"])
        self.category_combo.setObjectName("CategoryCombo")

        category = self.todo.get("category", "其他")
        index = self.category_combo.findText(category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)

        self.textLayout.addWidget(task_label)
        self.textLayout.addWidget(self.task_edit)
        self.textLayout.addSpacing(10)
        self.textLayout.addWidget(deadline_label)
        self.textLayout.addLayout(date_layout)
        self.textLayout.addSpacing(10)
        self.textLayout.addWidget(category_label)
        self.textLayout.addWidget(self.category_combo)
        self.textLayout.addSpacing(15)

        button_layout = QHBoxLayout()

        save_button = PrimaryPushButton("保存")
        save_button.setIcon(FluentIcon.SAVE)
        save_button.clicked.connect(self._on_save)

        cancel_button = PushButton("取消")
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch(1)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)

        self.textLayout.addLayout(button_layout)

    def _on_save(self):
        """保存编辑"""
        task = self.task_edit.toPlainText().strip()
        if not task:
            InfoBar.error(
                title="错误",
                content="任务内容不能为空",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return

        selected_date = self.date_picker.getDate().toString("yyyy-MM-dd")
        selected_time = self.time_picker.getTime().toString("hh:mm")
        deadline = f"{selected_date} {selected_time}"

        self.todo = {
            "task": task,
            "deadline": deadline,
            "category": self.category_combo.currentText(),
        }

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
                title="提示",
                content="备忘录内容为空，无法提取待办事项",
                parent=self.parent,
            )
            return

        self.state_tooltip = StateToolTip(
            "正在处理", "AI正在分析备忘录内容，提取待办事项...", parent=self.parent
        )
        self.state_tooltip.move(
            (self.parent.width() - self.state_tooltip.width()) // 2,
            (self.parent.height() - self.state_tooltip.height()) // 2,
        )
        self.state_tooltip.show()
        QApplication.processEvents()

        self.todo_thread = TodoExtractThread(ai_handler, memo_content, user_id)
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
                duration=3000,
            )
            return

        dialog = TodoExtractorDialog(todos, user_id, self.parent)
        dialog.exec_()

    def safely_close_tooltip(self):
        """安全关闭提示框"""
        try:
            if hasattr(self, "state_tooltip") and self.state_tooltip:
                self.state_tooltip.close()
                self.state_tooltip = None
        except Exception:
            pass

    def _add_todos_to_database(self, todos, user_id):
        """将待办事项添加到数据库"""
        db = DatabaseManager()
        added_count = 0

        for todo in todos:
            try:
                task = todo.get("task", "")
                deadline = todo.get("deadline", "")
                category = todo.get("category", "其他")

                if not task:
                    continue

                todo_id = db.add_todo(
                    user_id=user_id, task=task, deadline=deadline, category=category
                )

                if todo_id:
                    added_count += 1

            except Exception:
                pass

        return added_count
