# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import (
    FluentIcon,
    ExpandGroupSettingCard,
    PushButton,
    BodyLabel,
    ColorDialog,
    setThemeColor,
    setTheme,
    Theme,
)
from config import cfg


class ColorCard(ExpandGroupSettingCard):

    def __init__(self, parent=None, mainWindow=None):
        super().__init__(FluentIcon.VIEW, "主题颜色", "修改主题颜色", parent)
        self.mainWindow = mainWindow
        self.defaultButton = PushButton("应用")
        self.defaultLabel = BodyLabel("使用默认颜色")
        self.defaultButton.setFixedWidth(135)
        self.customLabel = BodyLabel("使用自定义颜色")
        self.customButton = PushButton("选择颜色")
        self.customButton.setFixedWidth(135)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.add(self.defaultLabel, self.defaultButton)
        self.add(self.customLabel, self.customButton)

        self.defaultButton.clicked.connect(self.set_default_color)
        self.customButton.clicked.connect(self.set_custom_color)

    def add(self, label, widget):
        w = QWidget()
        w.setFixedHeight(60)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(48, 12, 48, 12)
        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(widget)
        self.addGroupWidget(w)

    def set_default_color(self):
        setThemeColor("#ff10abf9", save=True)

    def set_custom_color(self):
        w = ColorDialog(
            cfg.get(cfg.themeColor), "选择主题颜色", self.mainWindow, enableAlpha=False
        )
        w.yesButton.setText("确认")
        w.cancelButton.setText("取消")
        w.editLabel.setText("编辑颜色")
        w.colorChanged.connect(lambda color: setThemeColor(color, save=True))
        w.exec()
