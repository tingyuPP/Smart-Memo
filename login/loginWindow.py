from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QStackedWidget
from PyQt5.QtCore import Qt
from qfluentwidgets import Pivot, SegmentedWidget
from login.view.accountInterface import AccountInterface
from mainWindow.mainWindow import MainWindow
from login.view.faceInterface import FaceLoginInterface

class LoginWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.segmentedWidget = SegmentedWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.setWindowTitle("SmartMemo")

        self.accountInterface = AccountInterface(self)
        self.accountInterface.loginSuccess.connect(self.on_login_success)
        self.faceInterface = FaceLoginInterface(self)
        self.faceInterface.loginSuccessful.connect(self.on_login_success)
        self.faceInterface.backClicked.connect(self.back_to_account)

        # 添加标签页
        # self.addSubInterface(self.accountInterface, 'songInterface', 'Song')
        self.accountInterface.setObjectName('accountInterface')
        self.segmentedWidget.addItem(
            routeKey='accountInterface',
            text='账密登录',
            onClick=lambda: self.stackedWidget.setCurrentWidget(self.accountInterface)
        )
        self.stackedWidget.addWidget(self.accountInterface)

        self.faceInterface.setObjectName('faceInterface')
        self.segmentedWidget.addItem(
            routeKey='faceInterface',
            text='人脸识别',
            onClick=lambda: self.stackedWidget.setCurrentWidget(self.faceInterface)
        )
        self.stackedWidget.addWidget(self.faceInterface)

        # 连接信号并初始化当前标签页
        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.stackedWidget.setCurrentWidget(self.accountInterface)
        self.segmentedWidget.setCurrentItem(self.accountInterface.objectName())

        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.addWidget(self.segmentedWidget, 0, Qt.AlignHCenter)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.resize(350, 600)

    def addSubInterface(self, widget: QLabel, objectName: str, text: str):
        widget.setObjectName(objectName)
        widget.setAlignment(Qt.AlignCenter)
        self.stackedWidget.addWidget(widget)

        # 使用全局唯一的 objectName 作为路由键
        self.segmentedWidget.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.segmentedWidget.setCurrentItem(widget.objectName())

    def on_login_success(self, user_data):
        user_id = user_data["id"]
        username = user_data["username"]
        print(f"登录成功：{user_id}, {username}")
        self.hide()
        # from mainWindow.mainWindow import MainWindow
        self.mainWindow = MainWindow(user_id, username)
        self.mainWindow.show()
        # print("这里应该打开主窗口")

    def back_to_account(self):
        self.stackedWidget.setCurrentWidget(self.accountInterface)
        self.segmentedWidget.setCurrentItem(self.accountInterface.objectName())

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    demo = LoginWindow()
    demo.show()
    sys.exit(app.exec_())
