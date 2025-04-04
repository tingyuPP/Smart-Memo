# coding:utf-8
from PyQt5.QtCore import (
    Qt,
    QDateTime,
    QEvent,
    QDate,
    QTime,
    pyqtSignal,
    QPropertyAnimation,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)
from datetime import datetime
from qfluentwidgets import (
    FluentIcon,
    PrimaryPushButton,
    BodyLabel,
    CardWidget,
    ScrollArea,
    InfoBar,
    InfoBarPosition,
    Action,
    RoundMenu,
    Theme,
)

from config import cfg
from Database import DatabaseManager
from mainWindow.ui.components.todoInterface.todo_notifier import TodoNotifier
from mainWindow.ui.components.todoInterface.sound_manager import SoundManager
from mainWindow.ui.components.todoInterface.todo_card import TodoCardManager
from mainWindow.ui.components.todoInterface.slide_panel import SlidePanelManager


class TodoInterface(ScrollArea):

    todo_count_changed = pyqtSignal(int)  # 信号，用于通知待办事项数量变化

    def __init__(self, parent=None, user_id=None):
        super().__init__(parent)
        self.setObjectName("TodoInterface")
        self.user_id = user_id
        self.db = DatabaseManager()

        # 设置透明背景
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("background: transparent; border: none;")
        self.setFrameShape(ScrollArea.NoFrame)

        # 创建主布局
        self.scrollWidget = QWidget()
        self.scrollWidget.setAttribute(Qt.WA_StyledBackground)
        self.scrollWidget.setStyleSheet("background: transparent;")
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        # 顶部工具栏
        self._setup_toolbar()

        # 待办列表区域
        self._setup_todo_list()

        # 新建待办的滑动面板（初始隐藏）
        self._setup_slide_panel()

        # 加载数据
        self._refresh_list()

        # 初始化提醒系统
        self.notifier = TodoNotifier(self.user_id)
        # 连接信号
        self.notifier.status_changed.connect(self._update_todo_status)
        self.notifier.query_todos.connect(self.notifier.handle_db_query)
        self.notifier.todos_result.connect(self._update_notifier_todos)

        # 启动提醒系统
        self.notifier.start()

        # 音频管理器
        self.sound_manager = SoundManager()

    def _setup_toolbar(self):
        """顶部工具栏设置"""
        self.toolbar = QWidget()
        self.toolbar.setAttribute(Qt.WA_StyledBackground)
        self.toolbar.setFixedHeight(60)

        self.toolbarLayout = QHBoxLayout(self.toolbar)
        self.toolbarLayout.setContentsMargins(20, 0, 20, 0)

        # 创建垂直布局来放置标题和日期
        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)

        # 主标题 - "我的一天"
        self.titleLabel = BodyLabel("我的一天", self)
        font = self.titleLabel.font()
        font.setPointSize(14)
        font.setBold(True)
        self.titleLabel.setFont(font)

        # 日期标签
        now = datetime.now()
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        date_str = f"{now.month}月{now.day}日，星期{weekdays[now.weekday()]}"
        self.dateLabel = BodyLabel(date_str, self)
        self.dateLabel.setProperty("secondary", True)  # 使用次要文本颜色

        # 添加到垂直布局
        title_layout.addWidget(self.titleLabel)
        title_layout.addWidget(self.dateLabel)

        # 新建按钮
        self.addBtn = PrimaryPushButton("新建待办", self)
        self.addBtn.setIcon(FluentIcon.ADD)
        self.addBtn.setFixedWidth(120)
        self.addBtn.clicked.connect(self._show_slide_panel)

        self.toolbarLayout.addLayout(title_layout)
        self.toolbarLayout.addStretch()
        self.toolbarLayout.addWidget(self.addBtn)

        self.vBoxLayout.addWidget(self.toolbar)

    def _setup_todo_list(self):
        """待办列表区域设置"""
        self.todoGroup = QWidget()
        self.todoGroup.setAttribute(Qt.WA_StyledBackground)
        self.todoGroup.setStyleSheet("background: transparent;")
        self.todoLayout = QVBoxLayout(self.todoGroup)
        self.todoLayout.setSpacing(15)
        self.todoLayout.setAlignment(Qt.AlignTop)
        self.todoLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.addWidget(self.todoGroup)

    def _setup_slide_panel(self):
        """新建待办的滑动面板"""
        # 创建滑动面板组件
        self.slide_components = SlidePanelManager.setup_slide_panel(self)

        # 连接动画完成信号
        self.slide_components["animation"].finished.connect(self._on_animation_finished)

        # 连接遮罩点击事件
        self.slide_components["mask"].mousePressEvent = (
            lambda e: self._hide_slide_panel()
        )

        # 安装事件过滤器
        self.slide_components["mask"].installEventFilter(self)

        # 连接提交按钮
        self.slide_components["submit_btn"].clicked.connect(self._add_todo)

    def _on_animation_finished(self):
        """动画完成后的处理"""
        if (
            self.slide_components["animation"].direction()
            == QPropertyAnimation.Backward
        ):
            # 隐藏动画完成后
            self.slide_components["panel"].hide()
            self.slide_components["mask"].hide()
            # 确保重置到屏幕底部
            self.slide_components["panel"].move(0, self.height())

    def _show_slide_panel(self):
        """显示滑动面板"""
        # 暂时禁用滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().installEventFilter(self)

        # 显示面板
        SlidePanelManager.show_panel(self.slide_components, self)

    def _hide_slide_panel(self):
        """隐藏滑动面板"""
        # 恢复滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.viewport().removeEventFilter(self)

        # 隐藏面板
        SlidePanelManager.hide_panel(self.slide_components)

    def resizeEvent(self, event):
        """窗口大小改变时调整面板位置"""
        super().resizeEvent(event)

        # 更新遮罩和滑动面板尺寸
        mask = self.slide_components["mask"]
        panel = self.slide_components["panel"]

        mask.setFixedSize(self.size())
        panel.setFixedWidth(self.width())

        if panel.isVisible():
            panel.move(0, self.height() - panel.height())
        else:
            panel.move(0, self.height())

    def _add_todo(self):
        """添加待办事项"""
        task = self.slide_components["task_input"].toPlainText().strip()
        if not task:
            InfoBar.warning("提示", "请输入待办内容", parent=self)
            return

        # 获取日期和时间
        date = self.slide_components["calendar_picker"].date
        time = self.slide_components["time_picker"].time
        deadline = QDateTime(date, time).toString("yyyy-MM-dd HH:mm")
        category = self.slide_components["category_combo"].currentText()

        try:
            # 保存到数据库
            self.db.add_todo(
                user_id=self.user_id,
                task=task,
                category=category,
                deadline=deadline,
            )

            # 关闭面板并刷新
            self._hide_slide_panel()
            self._refresh_list()
            InfoBar.success("成功", "待办已添加", parent=self)

            # 通知数量变化
            todo_count = self.db.get_todo_count(self.user_id)
            self.todo_count_changed.emit(todo_count)

        except Exception as e:
            InfoBar.error("错误", f"添加失败: {str(e)}", parent=self)

    def _refresh_list(self):
        """刷新待办列表"""
        # 清空现有列表
        for i in reversed(range(self.todoLayout.count())):
            widget = self.todoLayout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # 从数据库加载
        try:
            # 查询全部待办
            self.db.cursor.execute(
                """
                SELECT id, task, deadline, category, is_done, is_pinned
                FROM todos 
                WHERE user_id=?
                ORDER BY is_pinned DESC, is_done ASC, deadline ASC
                """,
                (self.user_id,),
            )
            todos = self.db.cursor.fetchall()

            # 分类待办事项
            pinned_todos = []
            regular_todos = []
            completed_todos = []

            for todo in todos:
                todo_id, task, deadline, category, is_done, is_pinned = todo

                if is_done:
                    completed_todos.append(todo)
                elif is_pinned:
                    pinned_todos.append(todo)
                else:
                    regular_todos.append(todo)

            # 添加置顶标签（如果有置顶项）
            if pinned_todos:
                pinned_label = TodoCardManager.create_section_label(
                    "📌 置顶待办", "#D32F2F"
                )
                self.todoLayout.addWidget(pinned_label)

            # 添加置顶待办事项
            for todo in pinned_todos:
                todo_id, task, deadline, category, is_done, is_pinned = todo
                card = TodoCardManager.create_todo_card(
                    todo_id=todo_id,
                    task=task,
                    deadline=deadline,
                    category=category,
                    is_done=is_done,
                    parent=self,
                    on_status_toggled=self._on_status_toggled,
                )

                # 应用置顶样式
                TodoCardManager.apply_pinned_style(card)

                # 添加到布局并设置事件过滤器
                self.todoLayout.addWidget(card)
                card.installEventFilter(self)

            # 如果有置顶项和未完成项，添加分隔符
            if pinned_todos and regular_todos:
                separator = TodoCardManager.create_separator()
                self.todoLayout.addWidget(separator)

                # 添加未完成标签
                regular_label = TodoCardManager.create_section_label(
                    "📋 待办事项", "#2196F3"
                )
                self.todoLayout.addWidget(regular_label)

            # 添加普通未完成待办事项
            for todo in regular_todos:
                todo_id, task, deadline, category, is_done, is_pinned = todo
                card = TodoCardManager.create_todo_card(
                    todo_id=todo_id,
                    task=task,
                    deadline=deadline,
                    category=category,
                    is_done=is_done,
                    parent=self,
                    on_status_toggled=self._on_status_toggled,
                )
                self.todoLayout.addWidget(card)
                card.installEventFilter(self)

            # 如果有未完成项和已完成项，添加分隔符
            if (pinned_todos or regular_todos) and completed_todos:
                separator = TodoCardManager.create_separator()
                self.todoLayout.addWidget(separator)

                # 添加已完成标签
                completed_label = TodoCardManager.create_section_label(
                    "✅ 已完成", "gray"
                )
                self.todoLayout.addWidget(completed_label)

            # 添加已完成待办事项
            for todo in completed_todos:
                todo_id, task, deadline, category, is_done, is_pinned = todo
                card = TodoCardManager.create_todo_card(
                    todo_id=todo_id,
                    task=task,
                    deadline=deadline,
                    category=category,
                    is_done=True,  # 强制设为已完成状态
                    parent=self,
                    on_status_toggled=self._on_status_toggled,
                )
                self.todoLayout.addWidget(card)
                card.installEventFilter(self)

            # 如果没有任何待办事项，显示空状态
            if not todos:
                empty_label = TodoCardManager.create_empty_label()
                self.todoLayout.addWidget(empty_label)

        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"加载待办失败: {str(e)}",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self,
            )

    def _on_status_toggled(self, todo_id, checked):
        """状态开关被切换时的处理函数"""
        # 播放相应的音效
        self.sound_manager.play("complete" if checked else "undo")
        # 更新数据库状态
        self._update_todo_status(todo_id, checked)

    def _update_todo_status(self, todo_id, is_done):
        """更新待办状态"""
        try:
            self.db.update_todo_status(todo_id, is_done)
            self._refresh_list()  # 刷新列表

            todo_count = self.db.get_todo_count(self.user_id)
            self.todo_count_changed.emit(todo_count)
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"状态更新失败: {str(e)}",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self,
            )

    def _delete_todo(self, todo_id, card):
        """删除待办事项"""
        try:
            self.db.cursor.execute("DELETE FROM todos WHERE id=?", (todo_id,))
            self.db.conn.commit()

            # 从界面移除
            card.setParent(None)
            card.deleteLater()

            todo_count = self.db.get_todo_count(self.user_id)
            self.todo_count_changed.emit(todo_count)

            InfoBar.success(
                title="成功",
                content="待办已删除!",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"删除失败: {str(e)}",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self,
            )

    def _update_notifier_todos(self, todos):
        """更新通知器的待办数据缓存"""
        with self.notifier._lock:
            self.notifier.current_todos = todos

    def eventFilter(self, obj, event):
        """事件过滤器，处理右键菜单和滚动事件"""
        # 处理滑动面板的滚动拦截
        if obj == self.viewport() and self.slide_components["panel"].isVisible():
            if event.type() in {
                QEvent.Wheel,  # 滚轮事件
                QEvent.Gesture,  # 触控板手势
                QEvent.TouchUpdate,  # 触摸屏滑动
            }:
                return True  # 直接拦截

        # 处理卡片右键菜单
        if isinstance(obj, CardWidget) and event.type() == QEvent.ContextMenu:
            # 如果是右键点击事件，显示菜单
            self._show_todo_context_menu(obj, event.globalPos())
            return True

        return super().eventFilter(obj, event)

    def _is_todo_pinned(self, todo_id):
        """检查待办是否已置顶"""
        try:
            self.db.cursor.execute("SELECT is_pinned FROM todos WHERE id=?", (todo_id,))
            result = self.db.cursor.fetchone()
            return bool(result[0]) if result else False
        except Exception as e:
            print(f"检查待办置顶状态失败: {e}")
            return False

    def _toggle_todo_pin(self, todo_id, pin_status):
        """切换待办的置顶状态"""
        try:
            self.db.cursor.execute(
                "UPDATE todos SET is_pinned=? WHERE id=?",
                (1 if pin_status else 0, todo_id),
            )
            self.db.conn.commit()

            # 刷新列表
            self._refresh_list()

            # 显示成功消息
            action_text = "置顶" if pin_status else "取消置顶"
            InfoBar.success(
                title="成功",
                content=f"已{action_text}该待办事项",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"更新置顶状态失败: {str(e)}",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self,
            )

    def _show_todo_context_menu(self, card, pos):
        """显示待办事项的右键菜单"""
        # 获取卡片上存储的属性
        todo_id = card.property("todo_id")
        task = card.property("task")
        is_done = card.property("is_done")

        # 创建菜单
        menu = RoundMenu(parent=self)

        # 添加置顶选项
        is_pinned = self._is_todo_pinned(todo_id)
        pin_action = Action(
            FluentIcon.PIN if not is_pinned else FluentIcon.UNPIN,
            "取消置顶" if is_pinned else "置顶待办",
            triggered=lambda: self._toggle_todo_pin(todo_id, not is_pinned),
        )

        # 添加删除选项
        delete_action = Action(
            FluentIcon.DELETE,
            "删除待办",
            triggered=lambda: self._delete_todo(todo_id, card),
        )

        # 根据状态添加选项
        if is_done:
            # 已完成状态下可以重新激活
            restore_action = Action(
                FluentIcon.CANCEL,
                "重新激活",
                triggered=lambda: self._update_todo_status_with_sound(todo_id, False),
            )
            menu.addAction(restore_action)
        else:
            # 未完成状态下可以标记为完成
            complete_action = Action(
                FluentIcon.ACCEPT,
                "标记为完成",
                triggered=lambda: self._update_todo_status_with_sound(todo_id, True),
            )
            menu.addAction(complete_action)
            menu.addAction(pin_action)  # 只有未完成的待办才能置顶

        menu.addSeparator()
        menu.addAction(delete_action)

        # 显示菜单
        menu.exec_(pos)

    def _update_todo_status_with_sound(self, todo_id, is_done):
        """更新待办状态并播放声音"""
        # 播放相应的音效
        self.sound_manager.play("complete" if is_done else "undo")

        # 更新数据库状态
        self._update_todo_status(todo_id, is_done)

    def update_all_todos(self):
        """从数据库获取所有待办事项并更新界面列表"""
        try:
            # 显示同步中提示
            InfoBar.info(
                title="正在同步",
                content="正在从数据库获取最新待办事项...",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self,
            )

            # 刷新列表
            self._refresh_list()

            # 重置通知状态
            self.notifier.reset_notifications()

            # 显示同步成功提示
            InfoBar.success(
                title="同步成功",
                content="待办事项数据已更新",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        except Exception as e:
            # 显示同步失败提示
            InfoBar.error(
                title="同步失败",
                content=f"无法获取最新待办事项: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def closeEvent(self, event):
        """关闭时清理资源"""
        self.db.close()
        event.accept()
