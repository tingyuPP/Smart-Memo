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
        "deepseek-chat",
        OptionsValidator([
            "deepseek-chat",
            "deepseek-coder",
            "gpt-3.5-turbo",
            "gpt-4"
        ]),
        restart=False
    )


cfg = MyConfig()
qconfig.load("config/config.json", cfg)

if not cfg.get(cfg.exportDir):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg.set(cfg.exportDir, project_root)
