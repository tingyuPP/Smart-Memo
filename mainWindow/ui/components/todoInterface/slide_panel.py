# coding:utf-8
from PyQt5.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    Qt,
    QDateTime,
    QPoint,
    QDate,
    QTime,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from qfluentwidgets import (
    BodyLabel,
    PrimaryPushButton,
    TextEdit,
    ComboBox,
    CalendarPicker,
    TimePicker,
    Theme,
)

from config import cfg


class SlidePanelManager:
    """滑动面板管理器"""

    @staticmethod
    def setup_slide_panel(parent):
        """设置新建待办的滑动面板"""
        # 半透明遮罩
        mask_widget = QWidget(parent)
        mask_widget.setFixedSize(parent.size())
        mask_widget.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        mask_widget.hide()

        # 滑动面板
        slide_panel = QWidget(parent)
        slide_panel.setObjectName("SlidePanel")
        slide_panel.setAttribute(Qt.WA_StyledBackground)
        slide_panel.setAutoFillBackground(True)
        slide_panel.setFixedWidth(parent.width())
        slide_panel.setMinimumHeight(400)

        # 设置圆角属性
        slide_panel.setProperty("rounded", True)
        slide_panel.setProperty("roundedRadius", 12)

        # 根据主题设置样式
        if cfg.get(cfg.themeMode) == Theme.DARK:
            slide_panel.setStyleSheet(
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
            slide_panel.setStyleSheet(
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
        slide_panel.move(0, parent.height())

        # 面板内容
        panel_layout = QVBoxLayout(slide_panel)
        panel_layout.setContentsMargins(25, 25, 25, 25)
        panel_layout.setSpacing(15)

        # 标题
        header_layout = QHBoxLayout()
        panel_title = BodyLabel("新建待办", slide_panel)
        font = panel_title.font()
        font.setPointSize(12)
        font.setBold(True)
        panel_title.setFont(font)

        header_layout.addWidget(panel_title)
        header_layout.addStretch()
        panel_layout.addLayout(header_layout)

        # 任务输入
        task_input = TextEdit(slide_panel)
        task_input.setPlaceholderText("输入待办事项内容...")
        task_input.setFixedHeight(260)
        task_input.setProperty("borderVisible", True)
        task_input.setProperty("borderRadius", 8)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(20)

        # 分类选择
        category_label = BodyLabel("分类:", slide_panel)
        category_combo = ComboBox(slide_panel)
        category_combo.addItems(["工作", "学习", "生活", "其他"])
        category_combo.setFixedWidth(150)

        # 截止时间
        deadline_label = BodyLabel("截止时间:", slide_panel)

        calendar_picker = CalendarPicker(slide_panel)
        time_picker = TimePicker(slide_panel)

        # 设置默认时间为明天
        month = QDateTime.currentDateTime().date().month()
        year = QDateTime.currentDateTime().date().year()
        day = QDateTime.currentDateTime().date().day()
        calendar_picker.setDate(QDate(year, month, day + 1))

        minute = QDateTime.currentDateTime().time().minute()
        hour = QDateTime.currentDateTime().time().hour()
        time_picker.setTime(QTime(hour, minute))

        # 添加到水平布局
        h_layout.addWidget(category_label)
        h_layout.addWidget(category_combo)
        h_layout.addWidget(deadline_label)
        h_layout.addWidget(calendar_picker)
        h_layout.addWidget(time_picker)
        h_layout.addStretch()

        # 将控件添加到主布局
        panel_layout.addWidget(BodyLabel("待办内容:", slide_panel))
        panel_layout.addWidget(task_input, stretch=1)
        panel_layout.addLayout(h_layout)

        # 提交按钮
        submit_btn = PrimaryPushButton("创建待办", slide_panel)
        submit_btn.setFixedHeight(45)
        panel_layout.addWidget(submit_btn)

        # 动画效果
        animation = QPropertyAnimation(slide_panel, b"pos")
        animation.setDuration(300)
        animation.setEasingCurve(QEasingCurve.OutQuad)

        # 确保遮罩层可接收鼠标事件
        mask_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        slide_panel.setMaximumHeight(int(parent.height() * 0.8))

        return {
            "panel": slide_panel,
            "mask": mask_widget,
            "animation": animation,
            "task_input": task_input,
            "category_combo": category_combo,
            "calendar_picker": calendar_picker,
            "time_picker": time_picker,
            "submit_btn": submit_btn,
        }

    @staticmethod
    def show_panel(components, parent):
        """显示滑动面板"""
        panel = components["panel"]
        mask = components["mask"]
        animation = components["animation"]

        # 更新面板高度
        panel_height = min(int(parent.height() * 0.8), 600)
        panel.setFixedHeight(panel_height)

        # 更新主题样式
        if cfg.get(cfg.themeMode) == Theme.DARK:
            panel.setStyleSheet(
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
            panel.setStyleSheet(
                """
                #SlidePanel {
                    background-color: rgb(255, 255, 255);
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                    border: 1px solid palette(mid);
                }
            """
            )

        # 更新尺寸
        panel.setFixedWidth(parent.width())
        mask.setFixedSize(parent.size())

        # 设置初始位置
        panel.move(0, parent.height())

        # 设置动画
        animation.setDirection(QPropertyAnimation.Forward)
        animation.setStartValue(QPoint(0, parent.height()))
        animation.setEndValue(QPoint(0, parent.height() - panel.height()))

        # 显示面板
        mask.show()
        mask.raise_()
        panel.show()
        panel.raise_()

        # 开始动画
        animation.start()

        # 清空表单内容
        components["task_input"].clear()
        components["category_combo"].setCurrentIndex(0)

        # 更新日期时间为明天
        month = QDateTime.currentDateTime().date().month()
        year = QDateTime.currentDateTime().date().year()
        day = QDateTime.currentDateTime().date().day()
        components["calendar_picker"].setDate(QDate(year, month, day + 1))

        minute = QDateTime.currentDateTime().time().minute()
        hour = QDateTime.currentDateTime().time().hour()
        components["time_picker"].setTime(QTime(hour, minute))

    @staticmethod
    def hide_panel(components):
        """隐藏滑动面板"""
        animation = components["animation"]
        animation.setDirection(QPropertyAnimation.Backward)
        animation.start()
