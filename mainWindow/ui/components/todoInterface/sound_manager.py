# coding:utf-8
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import os
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
