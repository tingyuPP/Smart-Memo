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
    PasswordLineEdit,
    PrimaryPushButton,
)
from config import cfg
import os
from services.ai_service import AIService


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

    def add_apply_button_to_api_settings(self):
        """在API设置界面添加应用按钮"""
        # 创建应用按钮
        self.apply_button = PrimaryPushButton("应用")
        self.apply_button.clicked.connect(self.apply_api_settings)

        # 将按钮添加到布局中
        # 假设设置界面有一个按钮布局
        self.button_layout.addWidget(self.apply_button)

    def apply_api_settings(self):
        """应用API设置"""
        try:
            # 保存当前设置到配置文件
            api_key = self.api_key_edit.text().strip()
            if api_key:
                cfg.set(cfg.apiKey, api_key)

            # 重新初始化AI服务
            from services.ai_service import AIService

            # 获取主窗口实例
            main_window = self.window()

            # 重新初始化所有使用AI服务的组件
            if hasattr(main_window, "memo_interface") and hasattr(
                main_window.memo_interface, "ai_handler"
            ):
                # 重新初始化备忘录界面的AI处理器
                main_window.memo_interface.ai_handler.ai_service = AIService()

            if hasattr(main_window, "todo_interface") and hasattr(
                main_window.todo_interface, "ai_handler"
            ):
                # 重新初始化待办界面的AI处理器
                main_window.todo_interface.ai_handler.ai_service = AIService()

            # 显示成功消息
            InfoBar.success(
                title="设置已应用",
                content="API设置已成功应用，无需重启程序",
                parent=self,
            )
        except Exception as e:
            # 显示错误消息
            InfoBar.error(title="应用设置失败", content=f"错误: {str(e)}", parent=self)


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
        super().__init__(FluentIcon.ROBOT, "AI 设置", "配置 AI 模型和 API 密钥", parent)

        # 模型选择
        self.modelLabel = BodyLabel("选择模型")
        self.modelComboBox = ComboBox()

        # 使用 AIService 中的模型配置
        model_display_names = [
            config["display_name"] for config in AIService.MODEL_CONFIGS.values()
        ]
        self.modelComboBox.addItems(model_display_names)

        # 设置当前选中的模型
        current_model = cfg.get(cfg.aiModel)
        current_display_name = AIService.MODEL_CONFIGS.get(current_model, {}).get(
            "display_name", ""
        )
        if current_display_name:
            self.modelComboBox.setCurrentText(current_display_name)

        self.modelComboBox.setFixedWidth(200)
        self.modelComboBox.currentTextChanged.connect(self._on_model_changed)

        # API 密钥
        self.apiLabel = BodyLabel("API 密钥")
        self.apiKeyEdit = PasswordLineEdit()
        self.apiKeyEdit.setClearButtonEnabled(True)
        self.apiKeyEdit.setFixedWidth(200)
        self.apiKeyEdit.setText(cfg.get(cfg.apiKey))
        self.apiKeyEdit.textChanged.connect(self._on_api_key_changed)

        # 自定义模型设置
        self.baseUrlLabel = BodyLabel("Base URL")
        self.baseUrlEdit = LineEdit()
        self.baseUrlEdit.setPlaceholderText("例如: https://api.example.com/v1")
        self.baseUrlEdit.setFixedWidth(200)

        self.modelIdLabel = BodyLabel("Model ID")
        self.modelIdEdit = LineEdit()
        self.modelIdEdit.setPlaceholderText("例如: gpt-3.5-turbo")
        self.modelIdEdit.setFixedWidth(200)

        # 应用按钮
        self.applyLabel = BodyLabel("立即应用设置")
        self.applyButton = PrimaryPushButton("应用")
        self.applyButton.setFixedWidth(120)
        self.applyButton.clicked.connect(self.apply_settings)

        # 调整内部布局
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        # 添加到设置卡中
        self.add(self.modelLabel, self.modelComboBox)
        self.add(self.apiLabel, self.apiKeyEdit)

        # 添加自定义设置（初始隐藏）
        self.customUrlWidget = self._create_setting_widget(
            self.baseUrlLabel, self.baseUrlEdit
        )
        self.customModelWidget = self._create_setting_widget(
            self.modelIdLabel, self.modelIdEdit
        )
        self.addGroupWidget(self.customUrlWidget)
        self.addGroupWidget(self.customModelWidget)

        # 添加应用按钮（与其他设置项保持一致的布局）
        self.add(self.applyLabel, self.applyButton)

        # 初始化自定义设置的可见性
        self._update_custom_settings_visibility()

    def _create_setting_widget(self, label, widget, indent=True):
        """创建一个设置项小部件"""
        w = QWidget()
        w.setFixedHeight(60)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(48, 12, 48, 12)
        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(widget)
        return w

    def add(self, label, widget):
        """添加普通设置项"""
        self.addGroupWidget(self._create_setting_widget(label, widget, indent=False))

    def _update_custom_settings_visibility(self):
        """更新自定义设置的可见性"""
        is_custom = self._get_model_id(self.modelComboBox.currentText()) == "custom"

        # 保存当前展开状态
        was_expanded = self.isExpand

        # 如果是展开状态，先收起
        if was_expanded:
            self.setExpand(False)

        # 设置可见性
        self.customUrlWidget.setVisible(is_custom)
        self.customModelWidget.setVisible(is_custom)

        if is_custom:
            # 加载保存的自定义设置
            self.baseUrlEdit.setText(cfg.get(cfg.customBaseUrl))
            self.modelIdEdit.setText(cfg.get(cfg.customModelId))
            # 连接信号
            self.baseUrlEdit.textChanged.connect(self._on_custom_settings_changed)
            self.modelIdEdit.textChanged.connect(self._on_custom_settings_changed)
        else:
            # 断开信号连接
            try:
                self.baseUrlEdit.textChanged.disconnect()
                self.modelIdEdit.textChanged.disconnect()
            except:
                pass

        # 如果之前是展开状态，重新展开
        if was_expanded:
            self.setExpand(True)

    def _on_custom_settings_changed(self):
        """当自定义设置改变时保存配置"""
        cfg.set(cfg.customBaseUrl, self.baseUrlEdit.text().strip())
        cfg.set(cfg.customModelId, self.modelIdEdit.text().strip())

        # 更新 MODEL_CONFIGS 中的自定义模型配置
        AIService.MODEL_CONFIGS["custom"].update(
            {
                "base_url": self.baseUrlEdit.text().strip(),
                "model_id": self.modelIdEdit.text().strip(),
            }
        )

    def _get_model_id(self, display_name):
        """将显示名称转换为模型ID"""
        for model_id, config in AIService.MODEL_CONFIGS.items():
            if config["display_name"] == display_name:
                return model_id
        return display_name

    def _on_model_changed(self, text):
        """当选择改变时更新配置"""
        model_id = self._get_model_id(text)
        cfg.set(cfg.aiModel, model_id)
        self._update_custom_settings_visibility()

    def _on_api_key_changed(self, text):
        """当 API 密钥改变时保存配置"""
        cfg.set(cfg.apiKey, text.strip())
        os.environ["OPENAI_API_KEY"] = (
            text.strip()
        )  # 使用通用的 OPENAI_API_KEY 环境变量

    def apply_settings(self):
        """应用当前API设置"""
        try:
            # 保存当前设置
            api_key = self.apiKeyEdit.text().strip()
            model_id = self._get_model_id(self.modelComboBox.currentText())

            # 保存到配置
            cfg.set(cfg.apiKey, api_key)
            cfg.set(cfg.aiModel, model_id)

            # 如果是自定义模型，保存自定义设置
            if model_id == "custom":
                base_url = self.baseUrlEdit.text().strip()
                custom_model_id = self.modelIdEdit.text().strip()
                cfg.set(cfg.customBaseUrl, base_url)
                cfg.set(cfg.customModelId, custom_model_id)

                # 更新MODEL_CONFIGS中的自定义模型配置
                AIService.MODEL_CONFIGS["custom"].update(
                    {"base_url": base_url, "model_id": custom_model_id}
                )

            # 更新环境变量
            os.environ["OPENAI_API_KEY"] = api_key

            # 获取主窗口实例
            main_window = self.window()

            # 重新初始化所有使用AI服务的组件
            if hasattr(main_window, "memoInterface") and hasattr(
                main_window.memoInterface, "ai_handler"
            ):
                # 创建新的AIService实例
                new_ai_service = AIService()
                main_window.memoInterface.ai_handler.ai_service = new_ai_service

            if hasattr(main_window, "todoInterface") and hasattr(
                main_window.todoInterface, "ai_handler"
            ):
                # 为待办界面创建新的AIService实例
                new_ai_service = AIService()
                main_window.todoInterface.ai_handler.ai_service = new_ai_service

            # 显示成功消息
            InfoBar.success(
                title="设置已应用",
                content="API设置已成功应用，无需重启程序",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )
        except Exception as e:
            # 显示错误消息
            InfoBar.error(
                title="应用设置失败",
                content=f"错误: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )
