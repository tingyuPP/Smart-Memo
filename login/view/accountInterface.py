from PyQt5.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QStackedWidget,
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from qfluentwidgets import (
    BodyLabel,
    LineEdit,
    PushButton,
    PrimaryPushButton,
    PasswordLineEdit,
    ImageLabel,
    SubtitleLabel,
    InfoBar,
    InfoBarPosition,
)
from Database import DatabaseManager
import os


def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 非打包环境，使用当前路径
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class AccountInterface(QFrame):
    # 定义信号
    loginSuccess = pyqtSignal(dict)
    registerSuccess = pyqtSignal(str)  # 新增注册成功信号

    def __init__(self, parent=None):
        super().__init__()

        # 组件声明
        self.parent = parent
        self.layout = QVBoxLayout(self)
        self.title_label = SubtitleLabel()
        self.logo_label = ImageLabel()

        # 创建一个堆叠部件来切换登录和注册表单
        self.stack_widget = QStackedWidget()

        # 登录表单
        self.login_widget = QFrame()
        self.login_layout = QVBoxLayout(self.login_widget)
        self.username_input = LineEdit()
        self.password_input = PasswordLineEdit()
        self.login_button_layout = QHBoxLayout()
        self.login_button = PrimaryPushButton()
        self.login_to_register_button = PushButton()  # 切换到注册的按钮

        # 注册表单
        self.register_widget = QFrame()
        self.register_layout = QVBoxLayout(self.register_widget)
        self.register_username_input = LineEdit()
        self.register_password_input = PasswordLineEdit()
        self.confirm_password_input = PasswordLineEdit()  # 确认密码
        self.register_button_layout = QHBoxLayout()
        self.register_button = PrimaryPushButton()
        self.register_to_login_button = PushButton()  # 切换回登录的按钮

        # 共用组件
        self.error_label = BodyLabel()
        self.error_timer = QTimer()

        # 初始化组件和布局
        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        """初始化各个控件的属性和行为"""
        # 设置标题和Logo
        self.title_label.setText("Smart Memo")
        self.title_label.setAlignment(Qt.AlignCenter)

        # 尝试加载Logo
        try:
            self.logo_label.setPixmap(QPixmap(resource_path("resource/logo.png")))
            self.logo_label.setFixedSize(120, 120)
            self.logo_label.setScaledContents(True)
        except Exception as e:
            print(f"无法加载logo: {e}")

        # 设置登录表单
        self.username_input.setPlaceholderText("用户名")
        self.username_input.setFixedHeight(40)
        self.password_input.setPlaceholderText("密码")
        self.password_input.setFixedHeight(40)
        self.login_button.setText("登录")
        self.login_button.setFixedHeight(40)
        self.login_to_register_button.setText("注册账号")
        self.login_to_register_button.setFixedHeight(40)

        # 设置注册表单
        self.register_username_input.setPlaceholderText("设置用户名")
        self.register_username_input.setFixedHeight(40)
        self.register_password_input.setPlaceholderText("设置密码")
        self.register_password_input.setFixedHeight(40)
        self.confirm_password_input.setPlaceholderText("确认密码")
        self.confirm_password_input.setFixedHeight(40)
        self.register_button.setText("完成注册")
        self.register_button.setFixedHeight(40)
        self.register_to_login_button.setText("返回登录")
        self.register_to_login_button.setFixedHeight(40)

        # 设置错误提示标签
        self.error_label.setStyleSheet("color: red")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setFixedHeight(30)  # 设置固定高度
        self.error_label.setText("")

        # 设置定时器
        self.error_timer.timeout.connect(self.hide_error)
        self.error_timer.setSingleShot(True)
        self.error_timer.setInterval(5000)

        # 设置按钮信号连接
        self.login_button.clicked.connect(self.login)
        self.login_to_register_button.clicked.connect(self.switch_to_register)
        self.register_button.clicked.connect(self.register)
        self.register_to_login_button.clicked.connect(self.switch_to_login)

        # 回车键处理
        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.login)
        self.register_username_input.returnPressed.connect(
            self.register_password_input.setFocus
        )
        self.register_password_input.returnPressed.connect(
            self.confirm_password_input.setFocus
        )
        self.confirm_password_input.returnPressed.connect(self.register)

    def __initLayout(self):
        """初始化布局"""
        # 设置布局边距和间距
        self.layout.setContentsMargins(20, 30, 20, 30)
        self.layout.setSpacing(15)

        # 添加顶部弹性空间
        self.top_spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.layout.addItem(self.top_spacer)

        # 添加Logo和标题
        self.layout.addWidget(self.logo_label, 0, Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

        # 在标题和输入框之间添加空间
        self.title_space = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(self.title_space)

        # 设置登录表单布局
        self.login_layout.setContentsMargins(0, 0, 0, 0)
        self.login_layout.setSpacing(15)
        self.login_layout.addWidget(self.username_input)
        self.login_layout.addWidget(self.password_input)
        self.login_button_layout.addWidget(self.login_button)
        self.login_button_layout.addWidget(self.login_to_register_button)
        self.login_layout.addLayout(self.login_button_layout)

        # 设置注册表单布局
        self.register_layout.setContentsMargins(0, 0, 0, 0)
        self.register_layout.setSpacing(15)
        self.register_layout.addWidget(self.register_username_input)
        self.register_layout.addWidget(self.register_password_input)
        self.register_layout.addWidget(self.confirm_password_input)
        self.register_button_layout.addWidget(self.register_button)
        self.register_button_layout.addWidget(self.register_to_login_button)
        self.register_layout.addLayout(self.register_button_layout)

        # 添加表单到堆叠部件
        self.stack_widget.addWidget(self.login_widget)
        self.stack_widget.addWidget(self.register_widget)

        # 将堆叠部件添加到主布局
        self.layout.addWidget(self.stack_widget)

        # 添加错误标签区域
        self.error_space = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(self.error_space)
        self.layout.addWidget(self.error_label)

        # 添加底部空间
        self.bottom_spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.layout.addItem(self.bottom_spacer)

        # 默认显示登录表单
        self.stack_widget.setCurrentWidget(self.login_widget)

    def switch_to_register(self):
        """切换到注册界面"""
        self.hide_error()
        self.stack_widget.setCurrentWidget(self.register_widget)
        self.register_username_input.setFocus()

    def switch_to_login(self):
        """切换到登录界面"""
        self.hide_error()
        self.stack_widget.setCurrentWidget(self.login_widget)
        self.username_input.setFocus()

    def login(self):
        """处理登录逻辑"""
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            self.show_error("用户名和密码不能为空")
            return

        db = None
        try:
            db = DatabaseManager()
            user = db.account_login(username, password)
            if user:
                self.show_error("")
                self.error_timer.stop()
                user_data = {"id": user["id"], "username": user["username"]}
                self.loginSuccess.emit(user_data)
                print("登录成功，需要显示主窗口")
            else:
                self.show_error("用户名或密码错误")
                self.error_timer.start()
        finally:
            if db:
                db.close()

    def register(self):
        """处理注册逻辑"""
        username = self.register_username_input.text()
        password = self.register_password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not username or not password:
            self.show_error("用户名和密码不能为空")
            return

        if password != confirm_password:
            self.show_error("两次输入的密码不一致")
            return

        if len(password) < 6:
            self.show_error("密码长度至少为6位")
            return

        # 使用with语句自动管理数据库连接
        db = None
        try:
            db = DatabaseManager()
            success = db.create_user(username, password)
            if not success:
                self.show_error("用户名已存在，请更换用户名")
                return

            w = InfoBar.success(
                title="注册成功！",
                content="",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=2000,
                parent=self.parent,
            )
            w.show()
            self.registerSuccess.emit(username)

            # 延迟后自动切换到登录界面并填充注册的用户名
            QTimer.singleShot(1000, lambda: self._register_success_action(username))
        finally:
            # 确保数据库连接正确关闭
            if db:
                db.close()

    def _register_success_action(self, username):
        """注册成功后的操作"""
        self.switch_to_login()
        self.username_input.setText(username)
        self.password_input.setFocus()

    def show_error(self, message, error=True):
        """显示错误或成功信息"""
        if error:
            self.error_label.setStyleSheet("color: red")
        else:
            self.error_label.setStyleSheet("color: green")

        self.error_label.setText(message)

    def hide_error(self):
        """隐藏错误信息"""
        self.error_label.setText("")
        self.error_timer.stop()
