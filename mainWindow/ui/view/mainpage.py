# coding:utf-8
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QApplication,
    QActionGroup,
)
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    FluentIcon,
    SplitPushButton,
    Action,
    InfoBar,
    InfoBarPosition,
    CheckableMenu,
    MenuIndicatorType,
)

from mainWindow.ui.components.mainpage.Ui_mainpage import Ui_mainwindow
from mainWindow.ui.components.mainpage.AppCard import AppCard  # 导入拆分出去的AppCard类
from Database import DatabaseManager


class MainInterface(Ui_mainwindow, QWidget):

    memo_count_changed = pyqtSignal(int)  # 信号，用于通知备忘录数量变化

    def __init__(self, parent=None, user_id=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.toolButton.setIcon(FluentIcon.ADD)
        self.toolButton_2.setIcon(FluentIcon.SYNC)

        # 连接 toolButton 的点击事件
        self.toolButton.clicked.connect(self.switch_to_memo_interface)
        self.toolButton_2.clicked.connect(self.sync_memos)

        frame2_layout = self.frame_2.layout()

        # 创建 SplitButton 作为排序按钮
        self.sortButton = SplitPushButton("排序方式", self.frame_2)
        self.sortButton.setIcon(FluentIcon.SCROLL)
        frame2_layout.addWidget(self.sortButton)

        # 创建排序字段相关的 Action
        self.nameAction = Action(FluentIcon.FONT, "按名称", checkable=True)
        self.createTimeAction = Action(
            FluentIcon.CALENDAR, "按创建时间", checkable=True
        )
        self.modifiedTimeAction = Action(FluentIcon.EDIT, "按修改时间", checkable=True)

        # 创建排序顺序相关的 Action
        self.ascendAction = Action(FluentIcon.UP, "升序", checkable=True)
        self.descendAction = Action(FluentIcon.DOWN, "降序", checkable=True)

        # 将动作添加到动作组
        self.fieldActionGroup = QActionGroup(self)
        self.fieldActionGroup.addAction(self.nameAction)
        self.fieldActionGroup.addAction(self.createTimeAction)
        self.fieldActionGroup.addAction(self.modifiedTimeAction)

        self.orderActionGroup = QActionGroup(self)
        self.orderActionGroup.addAction(self.ascendAction)
        self.orderActionGroup.addAction(self.descendAction)

        # 设置默认选中状态
        self.modifiedTimeAction.setChecked(True)
        self.descendAction.setChecked(True)

        # 连接信号槽
        self.fieldActionGroup.triggered.connect(self.on_sort_changed)
        self.orderActionGroup.triggered.connect(self.on_sort_changed)

        # 创建菜单
        self.sortMenu = CheckableMenu(
            parent=self, indicatorType=MenuIndicatorType.RADIO
        )
        self.sortMenu.addActions(
            [self.nameAction, self.createTimeAction, self.modifiedTimeAction]
        )
        self.sortMenu.addSeparator()
        self.sortMenu.addActions([self.ascendAction, self.descendAction])

        # 设置菜单
        self.sortButton.setFlyout(self.sortMenu)

        # 创建 QVBoxLayout
        self.cardLayout = QVBoxLayout()
        self.cardLayout.setAlignment(Qt.AlignTop)

        self.scrollAreaWidgetContents.setLayout(
            self.cardLayout
        )  # 将布局设置到已有的 Widget 中

        self.scrollArea.setStyleSheet(
            "QScrollArea{background: transparent; border: none}"
        )

        self.scrollAreaWidgetContents.setStyleSheet("QWidget{background: transparent}")

        # 连接搜索框信号
        self.lineEdit.searchSignal.connect(self.search_memos)
        self.lineEdit.textChanged.connect(self.on_search_text_changed)

        # 初始化数据库连接
        self.db = DatabaseManager()
        self.user_id = user_id

        # 初始加载备忘录列表
        self.update_memo_list()

    def update_memo_list(self):
        """从数据库获取备忘录并更新列表"""
        # 清空现有布局
        for i in reversed(range(self.cardLayout.count())):
            widget = self.cardLayout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # 从数据库获取备忘录
        memos = self.db.get_memos(user_id=self.user_id)

        # 根据选中的排序选项进行排序
        if self.nameAction.isChecked():
            # 按标题字母顺序排序
            memos.sort(
                key=lambda x: self.db.decrypt(x[4]).lower(),
                reverse=not self.ascendAction.isChecked(),
            )
        elif self.createTimeAction.isChecked():
            # 按创建时间排序
            memos.sort(key=lambda x: x[2], reverse=not self.ascendAction.isChecked())
        elif self.modifiedTimeAction.isChecked():
            # 按修改时间排序
            memos.sort(key=lambda x: x[3], reverse=not self.ascendAction.isChecked())

        # 添加 AppCard 到 cardLayout
        for memo in memos:
            # 从数据库中获取的数据
            memo_id = memo[0]
            user_id = memo[1]
            created_time = memo[2]
            modified_time = memo[3]
            title = self.db.decrypt(memo[4])  # 解密标题
            content = self.db.decrypt(memo[5])  # 解密内容
            category = memo[6]

            self.cardLayout.addWidget(
                AppCard(
                    title,
                    content,
                    memo_id=memo_id,
                    modified_time=modified_time,
                    category=category,
                    timer=None,  # 传递 timer
                )
            )  # 修改参数

            self.memo_count_changed.emit(len(memos))

    def sync_memos(self):
        """手动同步备忘录数据"""
        try:
            # 显示同步中提示
            InfoBar.info(
                title="正在同步",
                content="正在从数据库获取最新备忘录数据...",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self,
            )

            # 调用更新方法
            self.update_memo_list()

            # 显示同步成功提示
            InfoBar.success(
                title="同步成功",
                content="备忘录数据已更新",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        except Exception as e:
            # 显示同步失败提示
            InfoBar.error(
                title="同步失败",
                content=f"无法获取最新数据: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def switch_to_memo_interface(self):
        # 调用父窗口 (MainWindow) 的方法来切换到 musicInterface
        main_window = self.window()
        if hasattr(main_window, "switch_to_newmemo_interface"):
            main_window.switch_to_newmemo_interface()

    def on_sort_changed(self, action):
        """处理排序选项变化事件"""
        # 构建当前排序选项文本
        field_text = ""
        if self.nameAction.isChecked():
            field_text = "名称"
        elif self.createTimeAction.isChecked():
            field_text = "创建时间"
        elif self.modifiedTimeAction.isChecked():
            field_text = "修改时间"

        order_text = "升序" if self.ascendAction.isChecked() else "降序"
        sort_option = f"按{field_text}{order_text}"

        # 更新按钮文本显示当前排序方式
        self.sortButton.setText(f"{field_text} {order_text}")

        # 更新备忘录列表
        self.update_memo_list()

        # 显示排序完成提示
        InfoBar.success(
            title="排序完成",
            content=f"已按{sort_option}方式显示备忘录",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )

    def search_memos(self, text):
        """根据输入文本搜索备忘录"""
        if not text.strip():
            # 如果搜索文本为空，显示所有备忘录
            self.update_memo_list()
            return

        # 显示搜索中提示
        InfoBar.info(
            title="正在搜索",
            content=f'正在搜索包含 "{text}" 的备忘录...',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1000,
            parent=self,
        )

        # 清空现有布局
        for i in reversed(range(self.cardLayout.count())):
            widget = self.cardLayout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # 从数据库获取所有备忘录
        all_memos = self.db.get_memos(user_id=self.user_id)
        found_count = 0

        # 筛选出标题包含搜索文本的备忘录
        for memo in all_memos:
            memo_id = memo[0]
            user_id = memo[1]
            created_time = memo[2]
            modified_time = memo[3]
            title = self.db.decrypt(memo[4])  # 解密标题
            content = self.db.decrypt(memo[5])  # 解密内容
            category = memo[6]

            # 检查标题是否包含搜索文本（不区分大小写）
            if text.lower() in title.lower():
                # 创建并添加卡片
                self.cardLayout.addWidget(
                    AppCard(
                        title,
                        content,
                        memo_id=memo_id,
                        modified_time=modified_time,
                        category=category,
                        timer=None,
                    )
                )
                found_count += 1

        # 显示搜索结果信息
        if found_count > 0:
            InfoBar.success(
                title="搜索完成",
                content=f'找到 {found_count} 条包含 "{text}" 的备忘录',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        else:
            InfoBar.warning(
                title="未找到结果",
                content=f'没有找到包含 "{text}" 的备忘录',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )

    def on_search_text_changed(self, text):
        """当搜索框文本变化时，如果文本为空则恢复显示所有备忘录"""
        if not text.strip():
            self.update_memo_list()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = MainInterface()
    w.show()
    sys.exit(app.exec_())
