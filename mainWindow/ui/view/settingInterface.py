from PyQt5.QtWidgets import (
    QFrame,
    QWidget,
    QApplication,
    QVBoxLayout,
    QSizePolicy,
    QFileDialog,
    QHBoxLayout,
)
from PyQt5.QtGui import QColor, QDesktopServices
from qfluentwidgets import FluentIcon as FIF
from PyQt5.QtCore import Qt, QUrl
from qfluentwidgets import (
    SubtitleLabel,
    setFont,
    OptionsSettingCard,
    setTheme,
    Theme,
    PushSettingCard,
    HyperlinkCard,
    FluentIcon,
    PrimaryPushSettingCard,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
    RangeSettingCard,
    InfoBar,
    PrimaryPushButton,
)
from config import cfg
import os
from mainWindow.ui.components.settingInterface.ColorCard import ColorCard
from mainWindow.ui.components.settingInterface.AISettingCard import AISettingCard


class SettingInterface(ScrollArea):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.mainWindow = parent
        self.__initWidget(text)
        self.__initLayout(text)
        self.setObjectName(text.replace(" ", "-"))

    def __initWidget(self, text):
        self.label = SubtitleLabel(text, self)
        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label.setContentsMargins(0, 0, 0, 0)

        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        self.vBoxLayout.setSpacing(20)

        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        # 视觉相关
        self.visualGroup = SettingCardGroup(self.tr("视觉"), self.scrollWidget)
        self.backgroundCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            self.tr("更改背景样式"),
            self.tr("改变应用程序的背景样式"),
            texts=[self.tr("明亮"), self.tr("暗黑")],
        )
        self.backgroundCard.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.backgroundCard.optionChanged.connect(self.theme_option_changed)

        self.colorCard = ColorCard(self.scrollWidget, self.mainWindow)
        self.colorCard.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))

        # 个性化相关
        self.customizationGroup = SettingCardGroup(self.tr("个性化"),
                                                   self.scrollWidget)
        self.directoryCard = PushSettingCard(
            text="选择文件夹",
            icon=FIF.DOWNLOAD,
            title="默认导出目录",
            content=cfg.get(cfg.exportDir),
        )
        self.directoryCard.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.directoryCard.clicked.connect(self.open_file_dialog)

        self.aiSettingCard = AISettingCard()

        self.completionCard = SwitchSettingCard(
            icon=FIF.PENCIL_INK,
            title="启用自动补全",
            content="开启后，输入时会自动提示相关内容",
            configItem=cfg.enableAutoCompletion,
        )
        self.completionCard.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.completionTimeCard = RangeSettingCard(
            configItem=cfg.completionTime,
            icon=FluentIcon.STOP_WATCH,
            title="自动补全延迟",
            content="光标停留后多少秒开始自动补全",
        )
        self.completionTimeCard.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))

        # 关于相关
        self.aboutGroup = SettingCardGroup(self.tr("关于"), self.scrollWidget)
        self.helpCard = HyperlinkCard(
            url=
            "https://github.com/tingyuPP/Smart-Memo-Manager/blob/main/README.md",
            text="打开帮助页面",
            icon=FluentIcon.HELP,
            title="帮助",
            content="详细了解Smart-Memo-Manager的功能与使用方法",
        )
        self.aboutCard = PrimaryPushSettingCard(
            text="仓库地址",
            icon=FluentIcon.INFO,
            title="关于",
            content="© 版权所有 2025, 当前版本0.1.0",
        )
        self.aboutCard.button.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://github.com/tingyuPP/Smart-Memo-Manager")))

    def __initLayout(self, text):
        # 设置整体布局，将各个控件添加到布局中
        self.visualGroup.addSettingCard(self.backgroundCard)
        self.visualGroup.addSettingCard(self.colorCard)
        self.customizationGroup.addSettingCard(self.directoryCard)
        self.customizationGroup.addSettingCard(self.aiSettingCard)
        self.customizationGroup.addSettingCard(self.completionCard)
        self.customizationGroup.addSettingCard(self.completionTimeCard)
        self.aboutGroup.addSettingCard(self.helpCard)
        self.aboutGroup.addSettingCard(self.aboutCard)
        self.vBoxLayout.addWidget(self.label, 0, Qt.AlignLeft | Qt.AlignTop)
        self.vBoxLayout.addWidget(self.visualGroup)
        self.vBoxLayout.addWidget(self.customizationGroup)
        self.vBoxLayout.addWidget(self.aboutGroup)
        self.vBoxLayout.addStretch(1)
        self.vBoxLayout.setContentsMargins(36, 20, 36, 20)

    def theme_option_changed(self, item):
        selected_option = item.value
        cfg.set(cfg.themeMode, selected_option)
        if selected_option == Theme.LIGHT:
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.DARK)

    def open_file_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            self.directoryCard.setContent(path)
        cfg.set(cfg.exportDir, path)

    def import_option_changed(self, item):
        selected_option = item.value
        cfg.set(cfg.importSetting, selected_option)

    def add_apply_button_to_api_settings(self):
        self.apply_button = PrimaryPushButton("应用")
        self.apply_button.clicked.connect(self.apply_api_settings)
        self.button_layout.addWidget(self.apply_button)

    def apply_api_settings(self):
        """应用API设置"""
        try:
            api_key = self.api_key_edit.text().strip()
            if api_key:
                cfg.set(cfg.apiKey, api_key)
            from services.ai_service import AIService
            main_window = self.window()

            # 重新初始化所有使用AI服务的组件
            if hasattr(main_window, "memo_interface") and hasattr(
                    main_window.memo_interface, "ai_handler"):
                main_window.memo_interface.ai_handler.ai_service = AIService()

            if hasattr(main_window, "todo_interface") and hasattr(
                    main_window.todo_interface, "ai_handler"):
                main_window.todo_interface.ai_handler.ai_service = AIService()

            InfoBar.success(
                title="设置已应用",
                content="API设置已成功应用，无需重启程序",
                parent=self,
            )
        except Exception as e:
            InfoBar.error(title="应用设置失败", content=f"错误: {str(e)}", parent=self)
