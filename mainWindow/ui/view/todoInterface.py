from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QDateTime
from qfluentwidgets import (
    Action, FluentIcon, InfoBar, InfoBarPosition,
    PrimaryPushButton, DateTimeEdit, LineEdit, 
    CheckBox, BodyLabel, CardWidget, PushButton,
    ScrollArea, SettingCardGroup, ComboBox
)
from Database import DatabaseManager

class TodoInterface(ScrollArea):
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent)
        self.user_id = user_id
        self.db = DatabaseManager()
        self.setObjectName("TodoInterface")
        
        # 主界面布局
        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        
        # 顶部工具栏
        self.toolbar = QWidget()
        self.toolbarLayout = QHBoxLayout(self.toolbar)
        self.toolbarLayout.setContentsMargins(0, 0, 0, 0)
        
        # 添加工具栏按钮
        self.addActions([
            Action(FluentIcon.ADD, '添加', triggered=self._add_todo),
            Action(FluentIcon.DELETE, '清空', triggered=self._clear_all),
            Action(FluentIcon.SYNC, '刷新', triggered=self._refresh_list)
        ])
        
        # 待办输入区域
        self.inputCard = CardWidget()
        self.inputLayout = QVBoxLayout(self.inputCard)
        
        self.taskInput = LineEdit()
        self.taskInput.setPlaceholderText("输入待办事项内容...")
        
        # 分类选择
        self.categoryCombo = ComboBox()
        self.categoryCombo.setPlaceholderText("选择分类")
        self.categoryCombo.addItems(["工作", "学习", "生活", "其他"])
        
        # 截止时间设置
        self.deadlineEdit = DateTimeEdit()
        self.deadlineEdit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.deadlineEdit.setDateTime(QDateTime.currentDateTime().addDays(1))
        
        # 添加按钮
        self.addButton = PrimaryPushButton("添加待办", self)
        self.addButton.clicked.connect(self._add_todo)
        
        # 组装输入区域
        self.inputLayout.addWidget(BodyLabel("新待办事项:"))
        self.inputLayout.addWidget(self.taskInput)
        self.inputLayout.addWidget(BodyLabel("分类:"))
        self.inputLayout.addWidget(self.categoryCombo)
        self.inputLayout.addWidget(BodyLabel("截止时间:"))
        self.inputLayout.addWidget(self.deadlineEdit)
        self.inputLayout.addWidget(self.addButton)
        
        # 待办列表区域
        self.todoGroup = QWidget()
        self.todoLayout = QVBoxLayout(self.todoGroup)
        self.todoLayout.setSpacing(10)
        
        # 添加到主布局
        self.vBoxLayout.addWidget(self.toolbar)
        self.vBoxLayout.addWidget(self.inputCard)
        self.vBoxLayout.addWidget(self.todoGroup)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        
        # 加载已有待办
        self._refresh_list()

    def _add_todo(self):
        """添加新待办事项"""
        task = self.taskInput.text()
        category = self.categoryCombo.currentText()
        deadline = self.deadlineEdit.dateTime().toString("yyyy-MM-dd HH:mm")
        
        if not task:
            InfoBar.warning(
                title="警告",
                content="待办内容不能为空!",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        
        try:
            # 保存到数据库
            todo_id = self.db.add_todo(
                user_id=self.user_id,
                task=task,
                deadline=deadline,
                category=category
            )
            
            # 创建并显示待办卡片
            self._create_todo_card(todo_id, task, deadline, category, False)
            
            # 清空输入
            self.taskInput.clear()
            self.deadlineEdit.setDateTime(QDateTime.currentDateTime().addDays(1))
            
            InfoBar.success(
                title="成功",
                content="待办事项已添加!",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"添加失败: {str(e)}",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def _create_todo_card(self, todo_id, task, deadline, category, is_done):
        """创建单个待办卡片"""
        card = CardWidget()
        card.setFixedHeight(100)
        layout = QVBoxLayout(card)
        
        # 顶部行（复选框+任务+删除按钮）
        top_layout = QHBoxLayout()
        
        # 任务复选框
        self.checkbox = CheckBox(task)
        self.checkbox.setChecked(is_done)
        self.checkbox.stateChanged.connect(
            lambda state: self._update_todo_status(todo_id, state == Qt.Checked)
        )
        
        # 删除按钮
        delete_btn = PushButton("")
        delete_btn.setIcon(FluentIcon.DELETE)
        delete_btn.setToolTip("删除")
        delete_btn.clicked.connect(lambda: self._delete_todo(todo_id, card))
        
        top_layout.addWidget(self.checkbox, 1)
        top_layout.addWidget(delete_btn)
        
        # 底部信息行
        bottom_layout = QHBoxLayout()
        
        # 分类标签
        category_label = BodyLabel(f"🏷️ {category}")
        category_label.setStyleSheet("color: #666;")
        
        # 截止时间
        deadline_label = BodyLabel(f"⏰ {deadline}")
        deadline_label.setStyleSheet("color: #666;")
        
        bottom_layout.addWidget(category_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(deadline_label)
        
        # 添加到卡片
        layout.addLayout(top_layout)
        layout.addLayout(bottom_layout)
        
        # 添加到列表
        self.todoLayout.addWidget(card)

    def _update_todo_status(self, todo_id, is_done):
        """更新待办状态"""
        try:
            self.db.update_todo_status(todo_id, is_done)
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"状态更新失败: {str(e)}",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def _delete_todo(self, todo_id, card):
        """删除待办事项"""
        try:
            self.db.cursor.execute("DELETE FROM todos WHERE id=?", (todo_id,))
            self.db.conn.commit()
            
            # 从界面移除
            card.setParent(None)
            card.deleteLater()
            
            InfoBar.success(
                title="成功",
                content="待办已删除!",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"删除失败: {str(e)}",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def _refresh_list(self):
        """刷新待办列表"""
        # 清空现有列表
        for i in reversed(range(self.todoLayout.count())): 
            self.todoLayout.itemAt(i).widget().setParent(None)
        
        # 从数据库加载
        try:
            todos = self.db.get_todos(self.user_id)
            for todo in todos:
                self._create_todo_card(
                    todo_id=todo[0],
                    task=todo[1],
                    deadline=todo[2],
                    category=todo[3] if len(todo) > 3 else "未分类",
                    is_done=todo[4] if len(todo) > 4 else False
                )
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"加载待办失败: {str(e)}",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def _clear_all(self):
        """清空所有待办"""
        # 这里可以添加确认对话框
        for i in reversed(range(self.todoLayout.count())): 
            widget = self.todoLayout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        
        # 清空数据库（可选）
        # self.db.cursor.execute("DELETE FROM todos WHERE user_id=?", (self.user_id,))
        # self.db.conn.commit()

    def closeEvent(self, event):
        """关闭时清理资源"""
        self.db.close()
        event.accept()