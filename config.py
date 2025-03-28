# coding:utf-8
from enum import Enum
from qfluentwidgets import (
    QConfig,
    OptionsConfigItem,
    OptionsValidator,
    BoolValidator,
    qconfig,
    ConfigItem,
    FolderValidator,
    RangeValidator,
    RangeConfigItem,
    ConfigItem,
)
import os


class MyConfig(QConfig):
    """应用程序的配置类"""

    exportDir = ConfigItem(
        "MainWindow", "ExportDir", "", validator=FolderValidator(), restart=False
    )
    apiKey = ConfigItem(
        "MainWindow",
        "APIKey",
        "",
        restart=False
    )
    enableAutoCompletion = ConfigItem(
        "MainWindow", "EnableAutoCompletion", True, validator=BoolValidator(),restart=False
    )
    completionTime = RangeConfigItem(
        "MainWindow", "CompletionTime", 1, validator=RangeValidator(1, 10), restart=False
    )
    aiModel = OptionsConfigItem(
        "MainWindow",
        "AIModel",
        "deepseek-chat",  # 默认使用 deepseek-chat
        OptionsValidator([
            "deepseek-chat",
            "gpt-4o",
            "glm-4-flash",
            "custom"
        ]),
        restart=False
    )
    # 自定义模型配置
    customBaseUrl = ConfigItem(
        "MainWindow",
        "CustomBaseUrl",
        "",
        restart=False
    )
    
    customModelId = ConfigItem(
        "MainWindow",
        "CustomModelId",
        "",
        restart=False
    )


cfg = MyConfig()
qconfig.load("config/config.json", cfg)

if not cfg.get(cfg.exportDir):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg.set(cfg.exportDir, project_root)
