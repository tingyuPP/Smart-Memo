from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFrame, QSpacerItem, QSizePolicy)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from qfluentwidgets import (BodyLabel, LineEdit, PushButton, PrimaryPushButton, 
                            PasswordLineEdit, ImageLabel, SubtitleLabel)

class AccountInterface(QFrame):

    loginSuccess = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        
        # 窗口基本属性设置
        self.setWindowTitle("SmartMemo")
        self.setWindowIcon(QIcon("images/icon.png"))
        # self.setFixedSize(300, 500)
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        
        # 组件声明
        self.layout = QVBoxLayout(self)
        self.title_label = SubtitleLabel()
        self.logo_label = ImageLabel()  # 添加图标显示
        self.username_input = LineEdit()
        self.password_input = PasswordLineEdit()
        self.button_layout = QHBoxLayout()  # 添加水平布局用于并排按钮
        self.login_button = PrimaryPushButton()
        self.register_button = PushButton()  # 添加注册按钮
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
            self.logo_label.setPixmap(QPixmap("images/logo.png"))
            self.logo_label.setFixedSize(120, 120)
            self.logo_label.setScaledContents(True)
        except Exception as e:
            print(f"无法加载logo: {e}")

        # 设置输入框属性
        self.username_input.setPlaceholderText("用户名")
        self.username_input.setFixedHeight(40)
        self.password_input.setPlaceholderText("密码")
        self.password_input.setFixedHeight(40)
        
        # 设置按钮属性
        self.login_button.setText("登录")
        self.login_button.clicked.connect(self.login)
        self.login_button.setFixedHeight(40)
        
        # 设置注册按钮属性
        self.register_button.setText("注册")
        self.register_button.clicked.connect(self.register)
        self.register_button.setFixedHeight(40)
        
        # 设置错误提示标签
        self.error_label.setStyleSheet("color: red")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setFixedHeight(30)
        self.error_label.setText("")
        
        # 设置定时器
        self.error_timer.timeout.connect(self.hide_error)
        self.error_timer.setSingleShot(True)
        self.error_timer.setInterval(5000)
        
        # 设置信号连接
        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.login)
        self.username_input.textChanged.connect(self.hide_error)
        self.password_input.textChanged.connect(self.hide_error)
        
        # 设置初始焦点
        self.username_input.setFocus()

    def __initLayout(self):
        """初始化布局"""
        # 设置布局边距和间距
        self.layout.setContentsMargins(20, 30, 20, 30)
        self.layout.setSpacing(15)
        
        # 添加顶部弹性空间，让组件向下移动
        self.top_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(self.top_spacer)
        
        # 添加组件到布局
        self.layout.addWidget(self.logo_label, 0, Qt.AlignCenter)
        self.layout.addWidget(self.title_label)
        
        # 在标题和输入框之间添加一些空间
        self.title_space = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(self.title_space)
        
        # 添加输入组件
        self.layout.addWidget(self.username_input)
        self.layout.addWidget(self.password_input)
        
        # 设置按钮的水平布局
        self.button_layout.setSpacing(10)
        self.button_layout.addWidget(self.login_button)
        self.button_layout.addWidget(self.register_button)
        
        # 将按钮布局添加到主布局
        self.layout.addLayout(self.button_layout)
        
        # 在错误标签和按钮之间添加一些空间
        self.error_space = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(self.error_space)
        
        # 添加错误标签并保证它有一个固定的位置
        self.layout.addWidget(self.error_label)
        
        # 添加底部弹性空间，保持组件不贴底
        self.bottom_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(self.bottom_spacer)

    def login(self):
        """处理登录逻辑"""
        username = self.username_input.text()
        password = self.password_input.text()
        
        if username == "admin" and password == "admin":
            self.show_error("")
            self.error_timer.stop()
            # self.hide()
            # self.main_window = MainWindow()
            # self.main_window.show()
            self.loginSuccess.emit(username)
            print("登录成功，需要显示主窗口")
        else:
            self.show_error("用户名或密码错误")
            self.error_timer.start()
    
    def register(self):
        """处理注册逻辑"""
        print("打开注册窗口")
        # 这里可以添加注册窗口的打开逻辑
        # self.register_window = RegisterWindow()
        # self.register_window.show()

    def show_error(self, message):
        """显示错误信息"""
        self.error_label.setText(message)
        # 不需要显示/隐藏，只需要设置文本

    def hide_error(self):
        """隐藏错误信息"""
        self.error_label.setText("")
        self.error_timer.stop()