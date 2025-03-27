from PyQt5.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    Qt,
    QDateTime,
    QPoint,
    QTimer,
    QTime,
    QEvent,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGraphicsOpacityEffect,
    QTextEdit,
)
from PyQt5.QtGui import QFont, QColor
from qfluentwidgets import (
    FluentIcon,
    PrimaryPushButton,
    PushButton,
    LineEdit,
    DateTimeEdit,
    ComboBox,
    BodyLabel,
    CardWidget,
    ScrollArea,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    CheckBox,
    isDarkTheme,
    FluentStyleSheet,
    TextEdit,
)
from Database import DatabaseManager
from datetime import datetime


class TodoInterface(ScrollArea):
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
        self.todoLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.addWidget(self.todoGroup)

    def _setup_slide_panel(self):
        """新建待办的滑动面板"""
        # 半透明遮罩 - 使用固定透明度，不会影响其他元素
        # self.maskWidget = QWidget(self.scrollWidget)
        self.maskWidget = QWidget(self)
        self.maskWidget.setFixedSize(self.size())
        self.maskWidget.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.maskWidget.hide()

        # 滑动面板
        # self.slidePanel = CardWidget(self.scrollWidget)
        self.slidePanel = QWidget(self)
        self.slidePanel.setObjectName("SlidePanel")
        self.slidePanel.setAttribute(Qt.WA_StyledBackground)
        # 确保滑动面板使用主题样式
        self.slidePanel.setAutoFillBackground(True)
        self.slidePanel.setFixedWidth(self.width())
        self.slidePanel.setMinimumHeight(400)
        # self.slidePanel.setProperty("hoverEnabled", False)

        # 设置圆角属性
        self.slidePanel.setProperty("rounded", True)
        self.slidePanel.setProperty("roundedRadius", 12)

        self.slidePanel.setStyleSheet("""
        #SlidePanel {
            background-color: palette(window);
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border: 1px solid palette(mid);
        }
    """)

        # 初始位置在屏幕下方
        self.slidePanel.move(0, self.height())

        # 面板内容
        panelLayout = QVBoxLayout(self.slidePanel)
        panelLayout.setContentsMargins(25, 25, 25, 25)
        panelLayout.setSpacing(15)

        # 标题
        headerLayout = QHBoxLayout()
        self.panelTitle = BodyLabel("新建待办", self.slidePanel)
        font = self.panelTitle.font()
        font.setPointSize(12)
        font.setBold(True)
        self.panelTitle.setFont(font)

        headerLayout.addWidget(self.panelTitle)
        headerLayout.addStretch()
        panelLayout.addLayout(headerLayout)

        # 输入表单
        self._setup_input_form(panelLayout)

        # 提交按钮
        self.submitBtn = PrimaryPushButton("创建待办", self.slidePanel)
        self.submitBtn.setFixedHeight(45)
        self.submitBtn.clicked.connect(self._add_todo)
        panelLayout.addWidget(self.submitBtn)

        # 动画效果
        self.animation = QPropertyAnimation(self.slidePanel, b"pos")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.animation.finished.connect(self._on_animation_finished)

        # 遮罩点击事件
        self.maskWidget.mousePressEvent = lambda e: self._hide_slide_panel()

        # 确保遮罩层可接收鼠标事件
        self.maskWidget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.maskWidget.installEventFilter(self)
        self.slidePanel.setMaximumHeight(int(self.height() * 0.8))

    def _on_animation_finished(self):
        """动画完成后的处理"""
        if self.animation.direction() == QPropertyAnimation.Backward:
            # 隐藏动画完成后
            self.slidePanel.hide()
            self.maskWidget.hide()
            # 确保重置到屏幕底部
            self.slidePanel.move(0, self.height())

    def _setup_input_form(self, layout):
        """设置输入表单"""
        # 任务输入
        self.taskInput = TextEdit(self.slidePanel)
        self.taskInput.setPlaceholderText("输入待办事项内容...")
        self.taskInput.setFixedHeight(260)

        # 设置边框属性
        self.taskInput.setProperty("borderVisible", True)
        self.taskInput.setProperty("borderRadius", 8)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(20)

        # 分类选择
        category_label = BodyLabel("分类:", self.slidePanel)
        self.categoryCombo = ComboBox(self.slidePanel)
        self.categoryCombo.addItems(["工作", "学习", "生活", "其他"])
        self.categoryCombo.setFixedWidth(150)

        # 截止时间
        deadline_label = BodyLabel("截止时间:", self.slidePanel)
        self.deadlineEdit = DateTimeEdit(self.slidePanel)
        self.deadlineEdit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.deadlineEdit.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.deadlineEdit.setFixedWidth(220)

        # 添加到水平布局
        h_layout.addWidget(category_label)
        h_layout.addWidget(self.categoryCombo)
        h_layout.addWidget(deadline_label)
        h_layout.addWidget(self.deadlineEdit)
        h_layout.addStretch()

        # 将控件添加到主布局
        layout.addWidget(BodyLabel("待办内容:", self.slidePanel))
        layout.addWidget(self.taskInput, stretch=1)
        layout.addLayout(h_layout)

    def _show_slide_panel(self):
        """显示滑动面板"""
        # 暂时禁用滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().installEventFilter(self)

        panel_height = min(int(self.height() * 0.8), 600)
        self.slidePanel.setFixedHeight(panel_height)

        # 更新面板尺寸
        self.slidePanel.setFixedWidth(self.width())
        self.maskWidget.setFixedSize(self.size())

        # 滑动面板初始位置
        self.slidePanel.move(0, self.height())

        # 确保在显示前设置正确的样式
        self.slidePanel.update()

        # 设置动画
        self.animation.setDirection(QPropertyAnimation.Forward)
        self.animation.setStartValue(QPoint(0, self.height()))
        self.animation.setEndValue(QPoint(0, self.height() - self.slidePanel.height()))

        # 显示遮罩和面板
        self.maskWidget.show()
        self.maskWidget.raise_()
        self.slidePanel.show()
        self.slidePanel.raise_()

        # 开始动画
        self.animation.start()

        # 清空表单
        self.taskInput.clear()
        self.categoryCombo.setCurrentIndex(0)
        self.deadlineEdit.setDateTime(QDateTime.currentDateTime().addDays(1))

    def _hide_slide_panel(self):
        """隐藏滑动面板"""
        # 恢复滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.viewport().removeEventFilter(self)

        # 设置动画反向
        self.animation.setDirection(QPropertyAnimation.Backward)
        self.animation.start()

        # 确保动画完成后断开连接
        try:
            self.animation.finished.disconnect()
        except:
            pass

        # 动画结束后隐藏
        self.animation.finished.connect(
            lambda: (self.slidePanel.hide(), self.maskWidget.hide())
        )

    def eventFilter(self, obj, event):
        """拦截所有可能导致滚动的事件"""
        if obj == self.viewport() and self.slidePanel.isVisible():
            if event.type() in {
                QEvent.Wheel,  # 滚轮事件
                QEvent.Gesture,  # 触控板手势
                QEvent.TouchUpdate,  # 触摸屏滑动
            }:
                return True  # 直接拦截
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        """窗口大小改变时调整面板位置"""
        super().resizeEvent(event)
        self.maskWidget.setFixedSize(self.size())
        self.slidePanel.setFixedWidth(self.width())

        if self.slidePanel.isVisible():
            self.slidePanel.move(0, self.height() - self.slidePanel.height())
        else:
            self.slidePanel.move(0, self.height())

    def _add_todo(self):
        """添加待办事项"""
        task = self.taskInput.toPlainText().strip()
        if not task:
            InfoBar.warning("提示", "请输入待办内容", parent=self)
            return

        try:
            # 保存到数据库
            self.db.add_todo(
                user_id=self.user_id,
                task=task,
                category=self.categoryCombo.currentText(),
                deadline=self.deadlineEdit.dateTime().toString("yyyy-MM-dd HH:mm"),
            )

            # 关闭面板并刷新
            self._hide_slide_panel()
            self._refresh_list()
            InfoBar.success("成功", "待办已添加", parent=self)

        except Exception as e:
            InfoBar.error("错误", f"添加失败: {str(e)}", parent=self)


    def _create_todo_card(self, todo_id, task, deadline, category, is_done):
        """创建单个待办卡片"""
        card = CardWidget()
        card.setAttribute(Qt.WA_StyledBackground)
        card.setFixedHeight(100)
        layout = QVBoxLayout(card)

        # 顶部行（任务+删除按钮）
        top_layout = QHBoxLayout()

        # 任务标签（替代复选框）
        task_label = BodyLabel(task)
        # 使用粗体显示任务内容
        font = task_label.font()
        font.setBold(True)
        task_label.setFont(font)

        # 删除按钮
        delete_btn = PushButton()
        delete_btn.setIcon(FluentIcon.DELETE)
        delete_btn.setFixedSize(28, 28)
        delete_btn.setFlat(True)
        delete_btn.clicked.connect(lambda _, id=todo_id, c=card: self._delete_todo(id, c))

        top_layout.addWidget(task_label, 1)
        top_layout.addWidget(delete_btn)

        # 底部信息行
        bottom_layout = QHBoxLayout()

        # 分类标签
        category_label = BodyLabel(f"🏷️ {category}")
        category_label.setProperty("secondary", True)

        # 截止时间
        deadline_label = BodyLabel(f"⏰ {deadline}")
        deadline_label.setProperty("secondary", True)

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
            todos = self.db.get_todos(self.user_id)
            for todo in todos:
                self._create_todo_card(
                    todo_id=todo[0],
                    task=todo[1],
                    deadline=todo[2],
                    category=todo[3] if len(todo) > 3 else "未分类",
                    is_done=todo[4] if len(todo) > 4 else False,
                )
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"加载待办失败: {str(e)}",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                parent=self,
            )

    def _clear_all(self):
        """清空所有待办"""
        # 这里可以添加确认对话框
        for i in reversed(range(self.todoLayout.count())):
            widget = self.todoLayout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def closeEvent(self, event):
        """关闭时清理资源"""
        self.db.close()
        event.accept()
