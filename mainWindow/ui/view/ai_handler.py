from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, pyqtSlot
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QApplication,
    QWidget,
)
from PyQt5.QtGui import QCursor, QTextCursor
from qfluentwidgets import (
    TextEdit,
    PrimaryPushButton,
    StateToolTip,
    InfoBar,
    InfoBarPosition,
    RoundMenu,
    Action,
    CheckBox
)
from services.ai_service import AIService


class AIWorkerThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

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

class AIStreamWorkerThread(QThread):
    """处理流式响应的工作线程"""
    chunkReceived = pyqtSignal(str)  # 接收到新的文本块
    finished = pyqtSignal()  # 流式响应完成
    error = pyqtSignal(str)  # 发生错误
    
    def __init__(self, ai_service, mode, text):
        super().__init__()
        self.ai_service = ai_service
        self.mode = mode
        self.text = text
        self._stop_requested = False
    
    def run(self):
        try:
            # 获取流式响应
            stream = self.ai_service.generate_content_stream(self.text, self.mode)
            
            # 累积的完整响应
            full_response = ""
            
            # 处理流式响应
            for chunk in stream:
                if self._stop_requested:
                    break
                
                # 从响应块中提取文本
                if hasattr(chunk.choices[0].delta, "content"):
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        self.chunkReceived.emit(content)
            
            if not self._stop_requested:
                self.finished.emit()
                
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        """请求停止流式响应处理"""
        self._stop_requested = True

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
        
        self.stop_button = PrimaryPushButton("停止生成")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_generation)
        
        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.use_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)

        # 创建 AI 服务实例
        self.ai_service = AIService()
        self.ai_service.resultReady.connect(self.handle_ai_result)
        self.ai_service.errorOccurred.connect(self.handle_ai_error)
        
        # 添加流式响应选项
        self.use_streaming = True  # 默认启用流式响应

    def get_mode_display_name(self):
        """获取模式的显示名称"""
        mode_names = {
            "润色": "润色",
            "续写": "续写",
            "朋友圈文案": "朋友圈文案生成",
            "一句诗": "诗句生成",
            "自定义": "自定义生成",
        }
        return mode_names.get(self.mode, self.mode)

    def get_mode_description(self):
        """获取模式的描述文本"""
        descriptions = {
            "润色": "AI 将对您的文本进行润色，使其更加优美流畅，同时保持原意不变。",
            "续写": "AI 将基于您的文本继续写作，保持风格一致。",
            "朋友圈文案": "AI 将为您生成一段适合发布在朋友圈的文案，内容积极向上，有文艺气息。",
            "一句诗": "AI 将为您创作一句富有诗意的句子。",
            "自定义": "请输入您的提示词，AI 将根据您的要求生成内容。",
        }
        return descriptions.get(self.mode, "AI 将根据您的需求生成内容。")

    def show_loading_state(self):
        """显示加载状态"""
        try:
            if hasattr(self, "state_tooltip") and self.state_tooltip:
                try:
                    self.state_tooltip.close()
                except:
                    pass
                self.state_tooltip = None

            self.state_tooltip = StateToolTip(
                title="正在处理", content="AI 正在生成内容...", parent=self
            )

            dialog_rect = self.geometry()
            tooltip_size = self.state_tooltip.size()

            x = (dialog_rect.width() - tooltip_size.width()) // 2
            y = (dialog_rect.height() - tooltip_size.height()) // 2

            self.state_tooltip.move(x, y)
            self.state_tooltip.show()
            QApplication.processEvents()

        except Exception as e:
            print(f"显示加载状态时出错: {str(e)}")
            self.state_tooltip = None

    def generate_content(self):
        """生成内容"""
        self.disable_all_inputs()
        self.show_loading_state()

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
        
        # 清空结果区域
        self.result_edit.clear()
        self.result_text = ""
        
        # 停止任何正在运行的线程
        self.stop_any_running_threads()
        
        # 根据是否使用流式响应选择不同的处理方式
        if self.use_streaming:
            self.worker_thread = AIStreamWorkerThread(self.ai_service, self.mode, text)
            self.worker_thread.chunkReceived.connect(self.handle_stream_chunk)
            self.worker_thread.finished.connect(self.handle_stream_finished)
            self.worker_thread.error.connect(self.handle_ai_error)
            self.stop_button.setEnabled(True)
        else:
            self.worker_thread = AIWorkerThread(self.ai_service, self.mode, text)
            self.worker_thread.finished.connect(self.handle_ai_result)
            self.worker_thread.error.connect(self.handle_ai_error)
        
        self.worker_thread.start()
    
    def stop_generation(self):
        """停止生成过程"""
        if self.worker_thread and isinstance(self.worker_thread, AIStreamWorkerThread):
            self.worker_thread.stop()
            self.stop_button.setEnabled(False)
            
            # 重新启用生成按钮和其他控件
            self.generate_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            if hasattr(self, 'prompt_edit'):
                self.prompt_edit.setReadOnly(False)
            
            # 显示已停止消息
            if hasattr(self, 'state_tooltip') and self.state_tooltip:
                try:
                    self.state_tooltip.setContent("生成已停止")
                    self.state_tooltip.setState(True)
                    QApplication.processEvents()
                except:
                    pass
                finally:
                    # 设置一个短暂的延迟后关闭提示
                    QTimer.singleShot(1000, lambda: self.safely_close_tooltip())
    
    def stop_any_running_threads(self):
        """停止任何正在运行的线程"""
        if self.worker_thread and self.worker_thread.isRunning():
            if isinstance(self.worker_thread, AIStreamWorkerThread):
                self.worker_thread.stop()
            self.worker_thread.terminate()
            self.worker_thread.wait()
    
    @pyqtSlot(str)
    def handle_stream_chunk(self, chunk):
        """处理流式响应的文本块"""
        try:
            # 追加新的文本块到结果
            self.result_text += chunk
            
            # 更新 UI
            self.result_edit.setText(self.result_text)
            
            # 滚动到底部
            cursor = self.result_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.result_edit.setTextCursor(cursor)
            
        except Exception as e:
            print(f"处理流式响应块时出错: {str(e)}")
    
    @pyqtSlot()
    def handle_stream_finished(self):
        """处理流式响应完成"""
        try:
            self.generate_button.setEnabled(True)
            self.use_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            if hasattr(self, 'prompt_edit'):
                self.prompt_edit.setReadOnly(False)

            if hasattr(self, "state_tooltip") and self.state_tooltip:
                try:
                    self.state_tooltip.setContent("处理完成")
                    self.state_tooltip.setState(True)
                    QApplication.processEvents()
                except:
                    pass
                finally:
                    QTimer.singleShot(1000, lambda: self.safely_close_tooltip())

        except Exception as e:
            print(f"处理流式响应完成时出错: {str(e)}")
    
    def disable_all_inputs(self):
        """禁用所有输入控件"""
        self.generate_button.setEnabled(False)
        self.use_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        if hasattr(self, 'prompt_edit'):
            self.prompt_edit.setReadOnly(True)
    
    def safely_close_tooltip(self):
        """安全关闭提示框"""
        if hasattr(self, "state_tooltip") and self.state_tooltip:
            try:
                self.state_tooltip.close()
            except:
                pass
            self.state_tooltip = None

    @pyqtSlot(str)
    def handle_ai_error(self, error_message):
        """处理 AI 生成错误"""
        try:
            self.result_edit.setText(f"错误: {error_message}")
            self.generate_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            if hasattr(self, 'prompt_edit'):
                self.prompt_edit.setReadOnly(False)

            if hasattr(self, "state_tooltip") and self.state_tooltip:
                try:
                    self.state_tooltip.setContent(f"处理失败: {error_message}")
                    self.state_tooltip.setState(True)
                    QApplication.processEvents()
                except:
                    pass
                finally:
                    # 设置一个短暂的延迟后关闭提示
                    QTimer.singleShot(1000, lambda: self.safely_close_tooltip())

        except Exception as e:
            print(f"处理AI错误时出错: {str(e)}")

    @pyqtSlot(str)
    def handle_ai_result(self, result):
        """处理 AI 生成结果"""
        try:
            self.result_text = result
            self.result_edit.setText(result)
            
            self.generate_button.setEnabled(True)
            self.use_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            if hasattr(self, 'prompt_edit'):
                self.prompt_edit.setReadOnly(False)
            
            if hasattr(self, 'state_tooltip') and self.state_tooltip:
                try:
                    self.state_tooltip.setContent("处理完成")
                    self.state_tooltip.setState(True)
                    QApplication.processEvents()
                except:
                    pass
                finally:
                    QTimer.singleShot(1000, lambda: self.safely_close_tooltip())
            
        except Exception as e:
            print(f"处理AI结果时出错: {str(e)}")

    def closeEvent(self, event):
        """关闭对话框时清理资源"""
        self.stop_any_running_threads()
        
        if self.state_tooltip:
            try:
                self.state_tooltip.close()
            except:
                pass
            self.state_tooltip = None

        self.generate_button.setEnabled(True)
        self.use_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if hasattr(self, 'prompt_edit'):
            self.prompt_edit.setReadOnly(False)

        event.accept()


class AIHandler:
    """AI 功能处理类"""

    def __init__(self, parent: QWidget):
        self.parent = parent

    def show_ai_menu(self, text_edit):
        """显示 AI 菜单"""
        aiMenu = RoundMenu("AI编辑", self.parent)
        if not text_edit.toPlainText().strip():
            aiMenu.addActions(
                [
                    Action(
                        "为我写一个朋友圈文案",
                        triggered=lambda: self.handle_ai_func("朋友圈文案", text_edit),
                    ),
                    Action(
                        "为我写一句诗",
                        triggered=lambda: self.handle_ai_func("一句诗", text_edit),
                    ),
                    Action(
                        "自定义",
                        triggered=lambda: self.handle_ai_func("自定义", text_edit),
                    ),
                ]
            )
        else:
            aiMenu.addActions(
                [
                    Action(
                        "润色", triggered=lambda: self.handle_ai_func("润色", text_edit)
                    ),
                    Action(
                        "续写", triggered=lambda: self.handle_ai_func("续写", text_edit)
                    ),
                ]
            )
        aiMenu.exec_(QCursor.pos())

    def handle_ai_func(self, mode, text_edit):
        """处理 AI 功能"""
        cursor = text_edit.textCursor()
        text = (
            cursor.selectedText() if cursor.hasSelection() else text_edit.toPlainText()
        )

        dialog = AIDialog(mode, text, self.parent)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.result_text:
            self._apply_ai_result(mode, cursor, dialog.result_text, text_edit)

    def _apply_ai_result(self, mode, cursor, result_text, text_edit):
        """应用 AI 处理结果"""
        if mode == "润色":
            if cursor.hasSelection():
                cursor.insertText(result_text)
            else:
                text_edit.setText(result_text)
        elif mode == "续写":
            # 获取当前光标位置
            current_cursor = text_edit.textCursor()
            current_position = current_cursor.position()
            
            # 将光标移动到文本末尾
            current_cursor.movePosition(QTextCursor.End)
            text_edit.setTextCursor(current_cursor)
            
            # 获取当前文本框的所有内容
            current_text = text_edit.toPlainText()

            # 直接插入续写内容，不添加换行和空格
            current_cursor.insertText(result_text) if current_text else text_edit.setText(result_text)
        else:
            # 处理其他模式（朋友圈文案、一句诗、自定义等）
            # 如果文本框为空，直接设置文本
            if not text_edit.toPlainText().strip():
                text_edit.setText(result_text)
            else:
                # 如果文本框不为空，将光标移动到末尾并插入内容
                current_cursor = text_edit.textCursor()
                current_cursor.movePosition(QTextCursor.End)
                text_edit.setTextCursor(current_cursor)
                
                # 在新行插入内容
                current_cursor.insertText("\n\n" + result_text)

        self._show_success_message(mode)

    def _show_success_message(self, mode):
        """显示成功消息"""
        InfoBar.success(
            title="AI 处理完成",
            content=f"{mode}内容已应用",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.parent,
        )
