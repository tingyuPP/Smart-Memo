# coding:utf-8
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QFrame

from qfluentwidgets import CardWidget, BodyLabel, ToggleToolButton, FluentIcon, Theme

from config import cfg


class TodoCardManager:
    """待办卡片管理器"""

    @staticmethod
    def create_todo_card(
        todo_id, task, deadline, category, is_done, parent, on_status_toggled
    ):
        """创建单个待办卡片"""
        card = CardWidget(parent)
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
        status_btn = ToggleToolButton(card)
        status_btn.setIcon(FluentIcon.CANCEL if is_done else FluentIcon.ACCEPT)
        status_btn.setFixedSize(28, 28)
        status_btn.setChecked(is_done)  # 设置初始状态
        status_btn.toggled.connect(lambda checked: on_status_toggled(todo_id, checked))

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

        # 存储卡片属性，用于右键菜单
        card.setProperty("todo_id", todo_id)
        card.setProperty("task", task)
        card.setProperty("is_done", is_done)

        return card

    @staticmethod
    def create_separator():
        """创建分隔线"""
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
        return separator

    @staticmethod
    def create_section_label(text, color):
        """创建分组标签"""
        label = BodyLabel(text)
        label.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: bold; margin-bottom: 5px;"
        )
        return label

    @staticmethod
    def create_empty_label():
        """创建空状态标签"""
        empty_label = BodyLabel("暂无待办事项，点击右上角添加")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("color: gray; font-size: 14px; margin: 30px 0;")
        return empty_label

    @staticmethod
    def apply_pinned_style(card):
        """应用置顶样式"""
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
        return card
