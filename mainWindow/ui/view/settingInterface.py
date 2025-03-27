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
    ExpandGroupSettingCard,
    BodyLabel,
    PushButton,
    setThemeColor,
    ColorDialog,
    SettingCard,
    LineEdit,
    FolderValidator,
    TransparentToolButton,
    ToolTipFilter,
    ToolTipPosition,
    SwitchSettingCard,
    RangeSettingCard,
    ComboBox,
    InfoBar,
    InfoBarPosition,
    PasswordLineEdit
)
from config import cfg
import os


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

        # 创建滚动区域内的主要容器及其布局
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
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )
        self.backgroundCard.optionChanged.connect(self.theme_option_changed)

        self.colorCard = ColorCard(self.scrollWidget, self.mainWindow)
        self.colorCard.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )

        # 个性化相关
        self.customizationGroup = SettingCardGroup(self.tr("个性化"), self.scrollWidget)
        self.directoryCard = PushSettingCard(
            text="选择文件夹",
            icon=FIF.DOWNLOAD,
            title="默认导出目录",
            content=cfg.get(cfg.exportDir),
        )
        self.directoryCard.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )
        self.directoryCard.clicked.connect(self.open_file_dialog)
        
        # 使用新的 AISettingCard 替换原来的 ModelCard 和 ApiCard
        self.aiSettingCard = AISettingCard()
        
        self.completionCard = SwitchSettingCard(
            icon=FIF.PENCIL_INK,
            title="启用自动补全",
            content="开启后，输入时会自动提示相关内容",
            configItem=cfg.enableAutoCompletion,
        )
        self.completionCard.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )
        self.completionTimeCard = RangeSettingCard(
            configItem=cfg.completionTime,
            icon=FluentIcon.STOP_WATCH,
            title="自动补全延迟",
            content="光标停留后多少秒开始自动补全",
        )
        self.completionTimeCard.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )

        # 关于相关
        self.aboutGroup = SettingCardGroup(self.tr("关于"), self.scrollWidget)
        self.helpCard = HyperlinkCard(
            url="https://github.com/tingyuPP/Smart-Memo-Manager/blob/main/README.md",
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
        self.aboutCard.button.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://github.com/tingyuPP/Smart-Memo-Manager")
            )
        )

    def __initLayout(self, text):
        # 设置整体布局，将各个控件添加到布局中
        self.visualGroup.addSettingCard(self.backgroundCard)
        self.visualGroup.addSettingCard(self.colorCard)
        self.customizationGroup.addSettingCard(self.directoryCard)
        self.customizationGroup.addSettingCard(self.aiSettingCard)  # 添加新的卡片
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
        """
        当选项改变时触发，根据用户选择的选项切换主题
        """
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
        """
        当选项改变时触发，根据用户选择的选项切换导入设置
        """
        selected_option = item.value
        cfg.set(cfg.importSetting, selected_option)


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

        # 添加各组到设置卡中
        self.add(self.defaultLabel, self.defaultButton)
        self.add(self.customLabel, self.customButton)

        # 信号连接
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


class AISettingCard(ExpandGroupSettingCard):
    def __init__(self, parent=None):
        super().__init__(
            FluentIcon.ROBOT,
            "AI 设置",
            "配置 AI 模型和 API 密钥",
            parent
        )
        
        # 模型选择
        self.modelLabel = BodyLabel("选择模型")
        self.modelComboBox = ComboBox()
        self.modelComboBox.addItems([
            "DeepSeek Chat (推荐)",
            "DeepSeek Coder",
            "GPT-3.5 Turbo",
            "GPT-4"
        ])
        self.modelComboBox.setCurrentText(self._get_model_display_name(cfg.get(cfg.aiModel)))
        self.modelComboBox.setFixedWidth(200)
        self.modelComboBox.currentTextChanged.connect(self._on_model_changed)
        
        # API 密钥
        self.apiLabel = BodyLabel("API 密钥")
        self.apiKeyEdit = PasswordLineEdit()
        self.apiKeyEdit.setClearButtonEnabled(True)
        self.apiKeyEdit.setFixedWidth(200)
        self.apiKeyEdit.setText(cfg.get(cfg.apiKey))
        self.apiKeyEdit.textChanged.connect(self._on_api_key_changed)

        # 调整内部布局
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        # 添加到设置卡中
        self.add(self.modelLabel, self.modelComboBox)
        self.add(self.apiLabel, self.apiKeyEdit)

    def add(self, label, widget):
        w = QWidget()
        w.setFixedHeight(60)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(48, 12, 48, 12)
        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(widget)
        self.addGroupWidget(w)

    def _get_model_display_name(self, model_id):
        """将模型ID转换为显示名称"""
        model_names = {
            "deepseek-chat": "DeepSeek Chat (推荐)",
            "deepseek-coder": "DeepSeek Coder",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "gpt-4": "GPT-4"
        }
        return model_names.get(model_id, model_id)
    
    def _get_model_id(self, display_name):
        """将显示名称转换为模型ID"""
        model_ids = {
            "DeepSeek Chat (推荐)": "deepseek-chat",
            "DeepSeek Coder": "deepseek-coder",
            "GPT-3.5 Turbo": "gpt-3.5-turbo",
            "GPT-4": "gpt-4"
        }
        return model_ids.get(display_name, display_name)
    
    def _on_model_changed(self, text):
        """当选择改变时更新配置"""
        model_id = self._get_model_id(text)
        cfg.set(cfg.aiModel, model_id)

    def _on_api_key_changed(self, text):
        """当 API 密钥改变时保存配置"""
        cfg.set(cfg.apiKey, text.strip())
        os.environ["DEEPSEEK_API_KEY"] = text.strip()
