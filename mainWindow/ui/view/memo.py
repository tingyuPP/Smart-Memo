# coding:utf-8
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QMessageBox, QLabel, QDialog, QApplication
from qfluentwidgets import FluentIcon

from mainWindow.ui.view.Ui_memo import Ui_memo

from qfluentwidgets import (
    TitleLabel,
    BodyLabel,
    CardWidget,
    IconWidget,
    CaptionLabel,
    TransparentToolButton,
    FluentIcon,
    PrimaryPushButton,
    RoundMenu,
    Action,
    InfoBar,
    InfoBarPosition,
    TextEdit,
    StateToolTip,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QScrollArea,
)
from PyQt5.QtCore import Qt, QPoint, QSize, QRect, pyqtSlot, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QCursor


import sys
import os
import threading
from Database import DatabaseManager  # 导入数据库管理类

# 导入 AI 服务
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from services.ai_service import AIService

# 创建一个工作线程类
class AIWorkerThread(QThread):
    finished = pyqtSignal(str)  # 完成信号
    error = pyqtSignal(str)     # 错误信号
    
    def __init__(self, ai_service, mode, text):
        super().__init__()
        self.ai_service = ai_service
        self.mode = mode
        self.text = text
    
    def run(self):
        try:
            result = self.ai_service.generate_content(self.text, self.mode)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class AIDialog(QDialog):
    """AI 处理对话框"""
    def __init__(self, mode, text="", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.input_text = text
        self.result_text = ""
        self.state_tooltip = None
        self.worker_thread = None  # 添加工作线程属性
        self.setup_ui()
        
        # 设置窗口标志
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
    
    def setup_ui(self):
        # 设置对话框基本属性
        self.setWindowTitle(f"AI {self.get_mode_display_name()}")
        self.resize(600, 400)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 添加说明标签
        description = self.get_mode_description()
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 如果是自定义模式，添加提示输入框
        if self.mode == "自定义":
            prompt_layout = QHBoxLayout()
            prompt_label = QLabel("提示词:")
            self.prompt_edit = TextEdit()
            self.prompt_edit.setPlaceholderText("请输入 AI 提示词...")
            self.prompt_edit.setMaximumHeight(80)
            prompt_layout.addWidget(prompt_label)
            prompt_layout.addWidget(self.prompt_edit)
            layout.addLayout(prompt_layout)
        
        # 添加结果显示区域
        result_label = QLabel("生成结果:")
        layout.addWidget(result_label)
        
        self.result_edit = TextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("AI 生成的内容将显示在这里...")
        layout.addWidget(self.result_edit)
        
        # 添加按钮区域
        button_layout = QHBoxLayout()
        
        self.generate_button = PrimaryPushButton("生成")
        self.generate_button.setEnabled(True)
        self.generate_button.clicked.connect(self.generate_content)
        
        self.use_button = PrimaryPushButton("使用结果")
        self.use_button.setEnabled(False)
        self.use_button.clicked.connect(self.accept)
        
        self.cancel_button = PrimaryPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.use_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 创建 AI 服务实例
        self.ai_service = AIService()
        self.ai_service.resultReady.connect(self.handle_ai_result)
        self.ai_service.errorOccurred.connect(self.handle_ai_error)
    
    def get_mode_display_name(self):
        """获取模式的显示名称"""
        mode_names = {
            "润色": "润色",
            "续写": "续写",
            "朋友圈文案": "朋友圈文案生成",
            "一句诗": "诗句生成",
            "自定义": "自定义生成"
        }
        return mode_names.get(self.mode, self.mode)
    
    def get_mode_description(self):
        """获取模式的描述文本"""
        descriptions = {
            "润色": "AI 将对您的文本进行润色，使其更加优美流畅，同时保持原意不变。",
            "续写": "AI 将基于您的文本继续写作，保持风格一致。",
            "朋友圈文案": "AI 将为您生成一段适合发布在朋友圈的文案，内容积极向上，有文艺气息。",
            "一句诗": "AI 将为您创作一句富有诗意的句子。",
            "自定义": "请输入您的提示词，AI 将根据您的要求生成内容。"
        }
        return descriptions.get(self.mode, "AI 将根据您的需求生成内容。")
    
    def show_loading_state(self):
        """显示加载状态"""
        try:
            # 如果存在旧的 tooltip，先安全关闭
            if hasattr(self, 'state_tooltip') and self.state_tooltip:
                try:
                    self.state_tooltip.close()
                except:
                    pass
                self.state_tooltip = None
            
            # 创建新的 StateToolTip
            self.state_tooltip = StateToolTip(
                title="正在处理",
                content="AI 正在生成内容...",
                parent=self
            )
            
            # 计算对话框中心位置
            dialog_rect = self.geometry()
            tooltip_size = self.state_tooltip.size()
            
            # 计算居中位置
            x = (dialog_rect.width() - tooltip_size.width()) // 2
            y = (dialog_rect.height() - tooltip_size.height()) // 2
            
            # 移动到计算出的位置
            self.state_tooltip.move(x, y)
            
            # 显示 StateToolTip
            self.state_tooltip.show()
            QApplication.processEvents()  # 确保UI更新
            
        except Exception as e:
            print(f"显示加载状态时出错: {str(e)}")
            self.state_tooltip = None

    def generate_content(self):
        """生成内容"""
        # 禁用所有输入控件
        self.disable_all_inputs()
        
        # 显示加载状态（在主线程中）
        self.show_loading_state()
        
        # 创建并启动工作线程
        if self.mode == "自定义":
            text = self.prompt_edit.toPlainText()
            if not text:
                self.handle_ai_error("请输入提示词")
                return
        elif self.mode in ["润色", "续写"]:
            text = self.input_text
            if not text.strip():
                self.handle_ai_error("请输入需要处理的文本")
                return
        else:
            text = ""
            
        # 如果已有工作线程，先清理
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
            
        # 创建新的工作线程
        self.worker_thread = AIWorkerThread(self.ai_service, self.mode, text)
        self.worker_thread.finished.connect(self.handle_ai_result)
        self.worker_thread.error.connect(self.handle_ai_error)
        self.worker_thread.start()
    
    def disable_all_inputs(self):
        """禁用所有输入控件"""
        self.generate_button.setEnabled(False)
        self.use_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        if hasattr(self, 'prompt_edit'):
            self.prompt_edit.setReadOnly(True)
    
    @pyqtSlot(str)
    def handle_ai_result(self, result):
        """处理 AI 生成结果"""
        try:
            self.result_text = result
            self.result_edit.setText(result)
            self.generate_button.setEnabled(True)
            self.use_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            if hasattr(self, 'prompt_edit'):
                self.prompt_edit.setReadOnly(False)
            
            # 更新 StateToolTip 状态
            if hasattr(self, 'state_tooltip') and self.state_tooltip:
                try:
                    self.state_tooltip.setContent("处理完成")
                    self.state_tooltip.setState(True)  # 这会触发自动淡出
                    QApplication.processEvents()
                except:
                    self.state_tooltip = None
                
        except Exception as e:
            print(f"处理AI结果时出错: {str(e)}")

    @pyqtSlot(str)
    def handle_ai_error(self, error_message):
        """处理 AI 生成错误"""
        try:
            self.result_edit.setText(f"错误: {error_message}")
            self.generate_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            if hasattr(self, 'prompt_edit'):
                self.prompt_edit.setReadOnly(False)
            
            # 更新 StateToolTip 状态
            if hasattr(self, 'state_tooltip') and self.state_tooltip:
                try:
                    self.state_tooltip.setContent(f"处理失败: {error_message}")
                    self.state_tooltip.setState(True)  # 这会触发自动淡出
                    QApplication.processEvents()
                except:
                    self.state_tooltip = None
                
        except Exception as e:
            print(f"处理AI错误时出错: {str(e)}")

    def closeEvent(self, event):
        """关闭对话框时清理资源"""
        # 确保工作线程被清理
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
        
        # 清理其他资源
        if self.state_tooltip:
            self.state_tooltip.close()
            self.state_tooltip = None
        
        # 恢复所有输入控件状态
        self.generate_button.setEnabled(True)
        self.use_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        if hasattr(self, 'prompt_edit'):
            self.prompt_edit.setReadOnly(False)
        
        event.accept()


class memoInterface(Ui_memo, QWidget):
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self.db = DatabaseManager()  # 初始化数据库连接
        self.user_id = user_id  # 获取用户ID

        self.frame_2.addAction(
            Action(FluentIcon.ROBOT, "AI编辑", triggered=lambda: self.handleAIAction())
        )

        # 添加分隔符
        self.frame_2.addSeparator()

        # 批量添加动作
        save_action = Action(FluentIcon.SAVE, "保存")
        save_action.triggered.connect(self.save_memo)  # 连接保存动作
        self.frame_2.addActions(
            [
                save_action,
                Action(FluentIcon.DELETE, "清空", triggered=self.clear_memo),
                Action(FluentIcon.SHARE, "分享"),
            ]
        )

        self.lineEdit.setPlaceholderText("请输入备忘录标题")
        self.lineEdit_2.setPlaceholderText("请选择标签")

        self.textEdit.textChanged.connect(self.update_word_count)  # 文本改变时更新字数
        self.update_word_count()  # 初始化字数显示

    def handleAIAction(self):
        # 创建一个子菜单
        aiMenu = RoundMenu("AI编辑", self)
        if not self.textEdit.toPlainText().strip():
            aiMenu.addActions(
                [
                    Action(
                        "为我写一个朋友圈文案",
                        triggered=lambda: self.handleAIFunc("朋友圈文案"),
                    ),
                    Action(
                        "为我写一句诗", triggered=lambda: self.handleAIFunc("一句诗")
                    ),
                    Action("自定义", triggered=lambda: self.handleAIFunc("自定义")),
                ]
            )
        else:
            aiMenu.addActions(
                [
                    Action("润色", triggered=lambda: self.handleAIFunc("润色")),
                    Action("续写", triggered=lambda: self.handleAIFunc("续写")),
                ]
            )
        aiMenu.exec_(QCursor.pos())

    def handleAIFunc(self, mode):
        cursor = self.textEdit.textCursor()
        text = (
            cursor.selectedText()
            if cursor.hasSelection()
            else self.textEdit.toPlainText()
        )
        
        # 创建并显示 AI 对话框
        dialog = AIDialog(mode, text, self)
        result = dialog.exec_()
        
        # 如果用户点击了"使用结果"按钮
        if result == QDialog.Accepted and dialog.result_text:
            if mode == "润色":
                # 如果有选中文本，替换选中文本
                if cursor.hasSelection():
                    cursor.insertText(dialog.result_text)
                else:
                    self.textEdit.setText(dialog.result_text)
            elif mode == "续写":
                # 将生成的内容追加到当前文本后
                current_text = self.textEdit.toPlainText()
                self.textEdit.setText(current_text + "\n\n" + dialog.result_text)
            else:
                # 其他模式直接设置文本
                self.textEdit.setText(dialog.result_text)
            
            # 显示成功消息
            InfoBar.success(
                title='AI 处理完成',
                content=f"{mode}内容已应用",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )


    def save_memo(self):
        """保存备忘录到数据库"""
        title = self.lineEdit.text()
        content = self.textEdit.toPlainText()
        category = self.lineEdit_2.text()

        if not title or not content:
            InfoBar.warning(
                title='警告',
                content="标题和内容不能为空！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,    # 永不消失
                parent=self
            )
            return

        # 调用数据库方法保存备忘录
        memo_id = self.db.create_memo(self.user_id, title, content, category)

        if memo_id:
            InfoBar.success(
                title='成功',
                content="备忘录保存成功！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            self.clear_memo()
        else:
            InfoBar.error(
                title="错误",
                content="备忘录保存失败！",
                orient=Qt.Vertical,  # 内容太长时可使用垂直布局
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )

    def clear_memo(self):
        """清空备忘录"""
        self.textEdit.clear()
        self.lineEdit.clear()
        self.lineEdit_2.clear()
        self.update_word_count()

    def update_word_count(self):
        """更新字数统计"""
        text = self.textEdit.toPlainText()
        word_count = len(text)
        self.label.setText(f"共{word_count}字")

    def closeEvent(self, event):
        """关闭窗口时关闭数据库连接"""
        self.db.close()
        event.accept()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = memoInterface()
    w.show()
    sys.exit(app.exec_())
