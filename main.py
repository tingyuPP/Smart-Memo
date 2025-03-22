import ctypes
import sys
import os
from PyQt5.QtWidgets import QApplication
from login.loginWindow import LoginWindow
from PyQt5.QtCore import Qt

myappid = "SmartMemo"
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    w = LoginWindow()
    w.show()
    app.exec()
