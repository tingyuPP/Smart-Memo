from PyQt5.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    Qt,
    QDateTime,
    QPoint,
    QTimer,
    QTime,
    QEvent,
    QDate,
    pyqtSlot,
    
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGraphicsOpacityEffect,
    QTextEdit,
    QFrame,
    QLabel,
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
    ToggleToolButton,
    CalendarPicker,
    TimePicker,
    Theme,
    RoundMenu,
    Action,
)


import asyncio
from datetime import datetime, timedelta
import threading
from desktop_notifier import DesktopNotifier, Button, ReplyField, Urgency
from PyQt5.QtCore import QObject, pyqtSignal
from Database import DatabaseManager
from config import cfg
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import os
import re


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

        self.slidePanel.setStyleSheet(
            """
        #SlidePanel {
            background-color: palette(window);
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border: 1px solid palette(mid);
        }
    """
        )

        if cfg.get(cfg.themeMode) == Theme.DARK:
            self.slidePanel.setStyleSheet(
                """
            #SlidePanel {
                background-color: rgb(39, 39, 39);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border: 1px solid palette(mid);
            }
        """
            )
        else:
            self.slidePanel.setStyleSheet(
                """
            #SlidePanel {
                background-color: rgb(255, 255, 255);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border: 1px solid palette(mid);
            }
        """
            )

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

        self.calendarPicker = CalendarPicker(self.slidePanel)
        self.timePicker = TimePicker(self.slidePanel)
        month = QDateTime.currentDateTime().date().month()
        year = QDateTime.currentDateTime().date().year()
        day = QDateTime.currentDateTime().date().day()
        self.calendarPicker.setDate(QDate(year, month, day + 1))
        minute = QDateTime.currentDateTime().time().minute()
        hour = QDateTime.currentDateTime().time().hour()
        self.timePicker.setTime(QTime(hour, minute))

        # 添加到水平布局
        h_layout.addWidget(category_label)
        h_layout.addWidget(self.categoryCombo)
        h_layout.addWidget(deadline_label)
        h_layout.addWidget(self.calendarPicker)
        h_layout.addWidget(self.timePicker)
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
        if cfg.get(cfg.themeMode) == Theme.DARK:
            self.slidePanel.setStyleSheet(
                """
            #SlidePanel {
                background-color: rgb(39, 39, 39);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border: 1px solid palette(mid);
            }
        """
            )
        else:
            self.slidePanel.setStyleSheet(
                """
            #SlidePanel {
                background-color: rgb(255, 255, 255);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border: 1px solid palette(mid);
            }
        """
            )

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
        # self.deadlineEdit.setDateTime(QDateTime.currentDateTime().addDays(1))
        month = QDateTime.currentDateTime().date().month()
        year = QDateTime.currentDateTime().date().year()
        day = QDateTime.currentDateTime().date().day()
        self.calendarPicker.setDate(QDate(year, month, day + 1))
        minute = QDateTime.currentDateTime().time().minute()
        hour = QDateTime.currentDateTime().time().hour()
        self.timePicker.setTime(QTime(hour, minute))

    def _hide_slide_panel(self):
        """隐藏滑动面板"""
        # 恢复滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.viewport().removeEventFilter(self)

        # 设置动画反向
        self.animation.setDirection(QPropertyAnimation.Backward)
        self.animation.start()

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

        date = self.calendarPicker.date
        time = self.timePicker.time
        deadline = QDateTime(date, time).toString("yyyy-MM-dd HH:mm")

        try:
            # 保存到数据库
            self.db.add_todo(
                user_id=self.user_id,
                task=task,
                category=self.categoryCombo.currentText(),
                deadline=deadline,
            )

            # 关闭面板并刷新
            self._hide_slide_panel()
            self._refresh_list()
            InfoBar.success("成功", "待办已添加", parent=self)
            
            todo_count = self.db.get_todo_count(self.user_id)
            self.todo_count_changed.emit(todo_count)

        except Exception as e:
            InfoBar.error("错误", f"添加失败: {str(e)}", parent=self)

    def _create_todo_card(self, todo_id, task, deadline, category, is_done):
        """创建单个待办卡片"""
        card = CardWidget()
        card.setAttribute(Qt.WA_StyledBackground)
        card.setFixedHeight(100)
        layout = QVBoxLayout(card)

        # 顶部行（任务+状态切换按钮）
        top_layout = QHBoxLayout()

        # 任务标签
        task_label = BodyLabel(task)
        # 使用粗体显示任务内容
        font = task_label.font()
        font.setBold(True)
        task_label.setFont(font)

        # 设置样式 - 根据完成状态设置
        if is_done:
            task_label.setStyleSheet(
                """
                BodyLabel {
                    font-size: 14px;
                    color: gray;
                    padding: 5px;
                    text-decoration: line-through;
                }
            """
            )
        else:
            if cfg.get(cfg.themeMode) == Theme.DARK:
                task_label.setStyleSheet(
                    """
                    BodyLabel {
                        font-size: 14px;
                        color: white;
                        padding: 5px;
                    }
                """
                )
            else:
                task_label.setStyleSheet(
                    """
                    BodyLabel {
                        font-size: 14px;
                        color: black;
                        padding: 5px;
                    }
                """
                )

        # 状态切换按钮
        status_btn = ToggleToolButton()
        status_btn.setIcon(FluentIcon.CANCEL if is_done else FluentIcon.ACCEPT)
        status_btn.setFixedSize(28, 28)
        status_btn.setChecked(is_done)  # 设置初始状态

        # 添加音效
        def on_status_toggled(checked):
            # 播放相应的音效
            self.sound_manager.play("complete" if checked else "undo")
            # 更新数据库状态
            self._update_todo_status(todo_id, checked)

        status_btn.toggled.connect(on_status_toggled)

        top_layout.addWidget(task_label, 1)
        top_layout.addWidget(status_btn)

        # 底部信息行
        bottom_layout = QHBoxLayout()

        # 分类标签
        category_label = BodyLabel(f"🏷️ {category}")
        category_label.setProperty("secondary", True)
        if is_done:
            category_label.setStyleSheet("color: gray;")

        # 截止时间
        deadline_label = BodyLabel(f"⏰ {deadline}")
        deadline_label.setProperty("secondary", True)
        if is_done:
            deadline_label.setStyleSheet("color: gray;")

        bottom_layout.addWidget(category_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(deadline_label)

        # 添加到卡片
        layout.addLayout(top_layout)
        layout.addLayout(bottom_layout)

        # 添加到列表
        self.todoLayout.addWidget(card)

        # 安装事件过滤器以捕获右键点击事件
        card.installEventFilter(self)

        # 存储卡片属性，用于右键菜单
        card.setProperty("todo_id", todo_id)
        card.setProperty("task", task)
        card.setProperty("is_done", is_done)

        return card

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
            # 修改数据库查询，添加is_pinned字段
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
                pinned_label = BodyLabel("📌 置顶待办")
                pinned_label.setStyleSheet(
                    "color: #D32F2F; font-size: 14px; font-weight: bold; margin-bottom: 5px;"
                )
                self.todoLayout.addWidget(pinned_label)

            # 添加置顶待办事项
            for todo in pinned_todos:
                todo_id, task, deadline, category, is_done, is_pinned = todo
                card = self._create_todo_card(
                    todo_id=todo_id,
                    task=task,
                    deadline=deadline,
                    category=category,
                    is_done=is_done,
                )

                # 为置顶项添加醒目的样式
                if cfg.get(cfg.themeMode) == Theme.DARK:
                    card.setStyleSheet(
                        """
                        CardWidget {
                            background-color: #3F2E00; 
                            border-left: 4px solid #FFC107;
                        }
                    """
                    )
                else:
                    card.setStyleSheet(
                        """
                        CardWidget {
                            background-color: #FFF8E1; 
                            border-left: 4px solid #FFC107;
                        }
                    """
                    )

                # 添加置顶图标
                pin_icon = QLabel(card)
                pin_icon.setPixmap(FluentIcon.PIN.icon().pixmap(16, 16))
                pin_icon.setToolTip("已置顶")
                pin_icon.move(card.width() - 25, 5)
                pin_icon.show()

                # 确保图标跟随卡片大小调整
                card.resizeEvent = lambda e, label=pin_icon, c=card: label.move(
                    c.width() - 25, 5
                )

            # 如果有置顶项和未完成项，添加分隔符
            if pinned_todos and regular_todos:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet(
                    """
                    border: none;
                    background-color: palette(mid);
                    height: 2px;
                    margin: 15px 0;
                """
                )
                self.todoLayout.addWidget(separator)

                # 添加未完成标签
                regular_label = BodyLabel("📋 待办事项")
                regular_label.setStyleSheet(
                    "color: #2196F3; font-size: 14px; font-weight: bold; margin-top: 5px; margin-bottom: 5px;"
                )
                self.todoLayout.addWidget(regular_label)

            # 添加普通未完成待办事项
            for todo in regular_todos:
                todo_id, task, deadline, category, is_done, is_pinned = todo
                self._create_todo_card(
                    todo_id=todo_id,
                    task=task,
                    deadline=deadline,
                    category=category,
                    is_done=is_done,
                )

            # 如果有未完成项和已完成项，添加分隔符
            if (pinned_todos or regular_todos) and completed_todos:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet(
                    """
                    border: none;
                    background-color: palette(mid);
                    height: 2px;
                    margin: 15px 0;
                """
                )
                self.todoLayout.addWidget(separator)

                # 添加已完成标签
                completed_label = BodyLabel("✅ 已完成")
                completed_label.setStyleSheet(
                    "color: gray; font-size: 14px; font-weight: bold; margin-top: 5px; margin-bottom: 5px;"
                )
                self.todoLayout.addWidget(completed_label)

            # 添加已完成待办事项
            for todo in completed_todos:
                todo_id, task, deadline, category, is_done, is_pinned = todo
                self._create_todo_card(
                    todo_id=todo_id,
                    task=task,
                    deadline=deadline,
                    category=category,
                    is_done=True,  # 强制设为已完成状态
                )

            # 如果没有任何待办事项，显示空状态
            if not todos:
                empty_label = BodyLabel("暂无待办事项，点击右上角" + "添加")
                empty_label.setAlignment(Qt.AlignCenter)
                empty_label.setStyleSheet(
                    "color: gray; font-size: 14px; margin: 30px 0;"
                )
                self.todoLayout.addWidget(empty_label)

        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"加载待办失败: {str(e)}",
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

    def eventFilter(self, obj, event):
        """事件过滤器，处理右键菜单和滚动事件"""
        # 处理滑动面板的滚动拦截
        if obj == self.viewport() and self.slidePanel.isVisible():
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


class TodoNotifier(QObject):
    """待办事项提醒系统"""

    # 信号定义
    status_changed = pyqtSignal(int, bool)  # 更新状态信号
    query_todos = pyqtSignal(int)  # 请求待办数据信号
    todos_result = pyqtSignal(list)  # 待办数据结果信号
    # 新增用于触发通知发送的信号
    notification_request = pyqtSignal(
        int, str, str, str
    )  # (todo_id, task, deadline, category)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.notifier = DesktopNotifier()
        self.check_interval = 60  # 检查间隔（秒）
        self._running = False
        self._thread = None
        self.notified_ids = set()  # 已通知的待办ID，避免重复通知
        self.current_todos = []  # 缓存待办数据
        self._lock = threading.Lock()  # 添加线程锁保护共享数据

        # 初始化日志
        import logging

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("TodoNotifier")

        # 连接信号到槽函数
        self.notification_request.connect(self.send_notification_in_main_thread)

    def start(self):
        """启动提醒系统"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        self.logger.info("通知系统已启动")

    def stop(self):
        """停止提醒系统"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        self.logger.info("通知系统已停止")

    def reset_notifications(self):
        """重置已通知状态，允许重新发送通知"""
        with self._lock:
            self.notified_ids.clear()
        self.logger.info("通知状态已重置")

    def handle_db_query(self, user_id):
        """处理数据库查询请求 - 在主线程中执行"""
        try:
            db = DatabaseManager()  # 在主线程创建新的连接
            todos = db.get_todos(user_id, show_completed=False)
            self.todos_result.emit(todos)
            db.close()
            self.logger.debug(f"成功查询到 {len(todos)} 条待办事项")
        except Exception as e:
            self.logger.error(f"查询待办事项失败: {e}")
            self.todos_result.emit([])

    def _run_async_loop(self):
        """运行异步事件循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._check_todos_loop())
        except Exception as e:
            self.logger.error(f"通知循环出错: {e}")
        finally:
            loop.close()
            self.logger.info("通知循环已终止")

    async def _check_todos_loop(self):
        """定期检查待办事项"""
        while self._running:
            # 发送信号请求数据
            self.query_todos.emit(self.user_id)
            # 等待一小段时间以确保数据返回
            await asyncio.sleep(0.5)
            # 检查待办
            await self._process_todos()
            # 等待下一个检查周期
            await asyncio.sleep(self.check_interval)

    async def _process_todos(self):
        """处理待办数据"""
        try:
            now = datetime.now()

            # 使用线程锁保护对共享数据的访问
            todos_to_process = []
            with self._lock:
                todos_to_process = list(self.current_todos)

            for todo in todos_to_process:
                todo_id, task, deadline_str, category, is_done = todo[:5]

                # 跳过已完成的待办
                if is_done:
                    continue

                # 跳过已通知的待办
                with self._lock:
                    if todo_id in self.notified_ids:
                        continue

                # 解析截止时间
                try:
                    # 尝试不同的日期格式
                    formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d"]
                    deadline_dt = None

                    for date_format in formats:
                        try:
                            deadline_dt = datetime.strptime(deadline_str, date_format)
                            # 如果只有日期部分，设置时间为当天结束
                            if date_format == "%Y-%m-%d":
                                deadline_dt = deadline_dt.replace(hour=23, minute=59)
                            break
                        except ValueError:
                            continue

                    if not deadline_dt:
                        # 尝试更灵活的解析
                        try:
                            # 提取日期部分
                            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", deadline_str)
                            # 提取时间部分
                            time_match = re.search(
                                r"(\d{1,2})[:.：](\d{2})", deadline_str
                            )

                            if date_match and time_match:
                                date_str = date_match.group(1)
                                hour, minute = int(time_match.group(1)), int(
                                    time_match.group(2)
                                )
                                deadline_dt = datetime.strptime(
                                    f"{date_str} {hour:02d}:{minute:02d}",
                                    "%Y-%m-%d %H:%M",
                                )
                            elif date_match:
                                deadline_dt = datetime.strptime(
                                    f"{date_match.group(1)} 23:59", "%Y-%m-%d %H:%M"
                                )
                            else:
                                raise ValueError(f"无法解析日期: {deadline_str}")
                        except:
                            self.logger.error(f"无法解析截止时间: {deadline_str}")
                            continue

                    time_left = deadline_dt - now

                    # 通知触发条件
                    if -timedelta(minutes=30) <= time_left <= timedelta(minutes=15):
                        # 使用信号发送通知请求到主线程
                        self.notification_request.emit(
                            todo_id, task, deadline_str, category
                        )

                        # 安全地更新已通知集合
                        with self._lock:
                            self.notified_ids.add(todo_id)

                        self.logger.info(f"添加通知: {task}, 剩余时间: {time_left}")

                except Exception as e:
                    self.logger.error(f"解析截止时间错误: {deadline_str}, {e}")
                    continue

        except Exception as e:
            self.logger.error(f"处理待办事项时出错: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    @pyqtSlot(int, str, str, str)
    def send_notification_in_main_thread(self, todo_id, task, deadline, category):
        """在主线程中发送通知（通过信号调用）"""
        try:
            # 创建通知选项
            def mark_as_done():
                # 只发送信号，让主线程处理数据库操作
                self.status_changed.emit(todo_id, True)
                self.logger.info(f"用户通过通知将待办标记为完成: {task}")

            def dismiss():
                self.logger.info(f"用户已忽略提醒: {task}")

            buttons = [
                Button(title="标记为完成", on_pressed=mark_as_done, identifier="done"),
                Button(title="稍后提醒", on_pressed=dismiss, identifier="dismiss"),
            ]

            time_str = deadline.split(" ")[1] if " " in deadline else deadline

            # 检查是否已过期
            try:
                deadline_dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
                now = datetime.now()
                is_overdue = now > deadline_dt
                title = (
                    f"⚠️ 待办已过期: {category}"
                    if is_overdue
                    else f"📌 待办提醒: {category}"
                )
            except:
                title = f"📌 待办提醒: {category}"

            # 创建一个新的事件循环来运行异步通知方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 在新的事件循环中运行异步方法
                loop.run_until_complete(
                    self.notifier.send(
                        title=title,
                        message=f"{task}\n截止时间: {time_str}",
                        buttons=buttons,
                        urgency=Urgency.Critical,
                        timeout=30,
                    )
                )
            finally:
                loop.close()

            self.logger.info(f"成功发送通知: {task}")

        except Exception as e:
            self.logger.error(f"发送通知时出错: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

import sys
def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 非打包环境，使用当前路径
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class SoundManager:
    """音效管理器"""

    def __init__(self):
        self.player = QMediaPlayer()
        self.sounds = {
            "complete": resource_path("resource/complete.mp3"),
            "undo": resource_path("resource/undo.mp3"),
        }

    def play(self, sound_name):
        """播放指定的音效"""
        if sound_name not in self.sounds:
            return

        sound_path = self.sounds[sound_name]
        if not os.path.exists(sound_path):
            print(f"音效文件不存在: {sound_path}")
            return

        url = QUrl.fromLocalFile(sound_path)
        content = QMediaContent(url)
        self.player.setMedia(content)
        self.player.play()
