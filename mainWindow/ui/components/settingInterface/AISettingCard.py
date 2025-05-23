from PyQt5.QtWidgets import (
    QHBoxLayout,
    QWidget,
    QVBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
)
from qfluentwidgets import (
    FluentIcon,
    ExpandGroupSettingCard,
    BodyLabel,
    PasswordLineEdit,
    PrimaryPushButton,
    InfoBar,
    InfoBarPosition,
    setThemeColor,
    setTheme,
    Theme,
    ComboBox,
    setFont,
    LineEdit,
)
from PyQt5.QtCore import Qt
from config import cfg
import os
from services.ai_service import AIService


class AISettingCard(ExpandGroupSettingCard):

    def __init__(self, parent=None):
        super().__init__(FluentIcon.ROBOT, "AI 设置", "配置 AI 模型和 API 密钥", parent)

        self.modelLabel = BodyLabel("选择模型")
        self.modelComboBox = ComboBox()

        # 使用 AIService 中的模型配置
        model_display_names = [
            config["display_name"] for config in AIService.MODEL_CONFIGS.values()
        ]
        self.modelComboBox.addItems(model_display_names)

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

        self.applyLabel = BodyLabel("立即应用设置")
        self.applyButton = PrimaryPushButton("应用")
        self.applyButton.setFixedWidth(120)
        self.applyButton.clicked.connect(self.apply_settings)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.add(self.modelLabel, self.modelComboBox)
        self.add(self.apiLabel, self.apiKeyEdit)

        self.customUrlWidget = self._create_setting_widget(
            self.baseUrlLabel, self.baseUrlEdit
        )
        self.customModelWidget = self._create_setting_widget(
            self.modelIdLabel, self.modelIdEdit
        )
        self.addGroupWidget(self.customUrlWidget)
        self.addGroupWidget(self.customModelWidget)

        self.add(self.applyLabel, self.applyButton)

        self._update_custom_settings_visibility()

    def _create_setting_widget(self, label, widget, indent=True):
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
        is_custom = self._get_model_id(self.modelComboBox.currentText()) == "custom"

        was_expanded = self.isExpand

        # 如果是展开状态，先收起
        if was_expanded:
            self.setExpand(False)

        self.customUrlWidget.setVisible(is_custom)
        self.customModelWidget.setVisible(is_custom)

        if is_custom:
            self.baseUrlEdit.setText(cfg.get(cfg.customBaseUrl))
            self.modelIdEdit.setText(cfg.get(cfg.customModelId))
            self.baseUrlEdit.textChanged.connect(self._on_custom_settings_changed)
            self.modelIdEdit.textChanged.connect(self._on_custom_settings_changed)
        else:
            try:
                self.baseUrlEdit.textChanged.disconnect()
                self.modelIdEdit.textChanged.disconnect()
            except:
                pass

        # 如果之前是展开状态，重新展开
        if was_expanded:
            self.setExpand(True)

    def _on_custom_settings_changed(self):
        cfg.set(cfg.customBaseUrl, self.baseUrlEdit.text().strip())
        cfg.set(cfg.customModelId, self.modelIdEdit.text().strip())

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
        model_id = self._get_model_id(text)
        cfg.set(cfg.aiModel, model_id)
        self._update_custom_settings_visibility()

    def _on_api_key_changed(self, text):
        cfg.set(cfg.apiKey, text.strip())
        os.environ["OPENAI_API_KEY"] = text.strip()

    def apply_settings(self):
        try:
            api_key = self.apiKeyEdit.text().strip()
            model_id = self._get_model_id(self.modelComboBox.currentText())

            cfg.set(cfg.apiKey, api_key)
            cfg.set(cfg.aiModel, model_id)

            # 如果是自定义模型，保存自定义设置
            if model_id == "custom":
                base_url = self.baseUrlEdit.text().strip()
                custom_model_id = self.modelIdEdit.text().strip()
                cfg.set(cfg.customBaseUrl, base_url)
                cfg.set(cfg.customModelId, custom_model_id)

                AIService.MODEL_CONFIGS["custom"].update(
                    {"base_url": base_url, "model_id": custom_model_id}
                )

            os.environ["OPENAI_API_KEY"] = api_key

            main_window = self.window()

            # 重新初始化所有使用AI服务的组件
            if hasattr(main_window, "memoInterface") and hasattr(
                main_window.memoInterface, "ai_handler"
            ):
                new_ai_service = AIService()
                main_window.memoInterface.ai_handler.ai_service = new_ai_service

            if hasattr(main_window, "todoInterface") and hasattr(
                main_window.todoInterface, "ai_handler"
            ):
                new_ai_service = AIService()
                main_window.todoInterface.ai_handler.ai_service = new_ai_service

            InfoBar.success(
                title="设置已应用",
                content="API设置成功应用",
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
