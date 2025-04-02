from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, pyqtSlot, QSize
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QApplication,
    QWidget,
    QWIDGETSIZE_MAX,
    QSizePolicy,
    QSpacerItem
)
from PyQt5.QtGui import QCursor, QTextCursor, QColor, QIcon, QFont, QPalette, QLinearGradient
from qfluentwidgets import (
    TextEdit,
    PrimaryPushButton,
    StateToolTip,
    InfoBar,
    InfoBarPosition,
    RoundMenu,
    Action,
    CheckBox,
    FluentIcon,
    CardWidget,
    BodyLabel,
    MessageBoxBase,
    Dialog,
    TransparentToolButton,
    IconWidget,
    Theme,
    isDarkTheme
)
from services.ai_service import AIService
import os, re
from Database import DatabaseManager

class AIWorkerThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, ai_service, mode, text, aux_prompt=""):
        super().__init__()
        self.ai_service = ai_service
        self.mode = mode
        self.text = text
        self.aux_prompt = aux_prompt

    def run(self):
        try:
            result = self.ai_service.generate_content(
                self.text, self.mode, self.aux_prompt
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AIStreamWorkerThread(QThread):
    """处理流式响应的工作线程"""

    chunkReceived = pyqtSignal(str)  # 接收到新的文本块
    finished = pyqtSignal()  # 流式响应完成
    error = pyqtSignal(str)  # 发生错误

    def __init__(self, ai_service, mode, text, aux_prompt=""):
        super().__init__()
        self.ai_service = ai_service
        self.mode = mode
        self.text = text
        self.aux_prompt = aux_prompt
        self._stop_requested = False

    def run(self):
        try:
            # 获取流式响应
            stream = self.ai_service.generate_content_stream(
                self.text, self.mode, self.aux_prompt
            )

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

class AIDialog(Dialog):
    """AI 处理对话框"""

    def __init__(self, mode, text="", parent=None, ai_service=None):
        # 初始化属性
        self.mode = mode
        self.input_text = text
        self.result_text = ""
        self.state_tooltip = None
        self.worker_thread = None
        
        # 使用传入的AI服务实例
        self.ai_service = ai_service
        
        # 获取模式的显示名称作为标题
        title = self.get_mode_display_name()
        content = ""
        
        # 调用父类构造函数
        super().__init__(title, content, parent=parent)
        
        # 设置对话框属性
        self.resize(650, 500)
        self.setMaximumSize(16777215, 16777215)
        self.setFixedSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self.setResizeEnabled(True)
        
        # 显示标题栏
        self.titleBar.show()
        
        # 设置标题栏按钮
        if hasattr(self.titleBar, 'setDoubleClickEnabled'):
            self.titleBar.setDoubleClickEnabled(True)
        
        # 显示标题栏上的按钮
        if hasattr(self.titleBar, 'minBtn'):
            self.titleBar.minBtn.show()
        if hasattr(self.titleBar, 'maxBtn'):
            self.titleBar.maxBtn.show()
        if hasattr(self.titleBar, 'closeBtn'):
            self.titleBar.closeBtn.show()
        
        # 设置标题栏标题
        if hasattr(self.titleBar, 'setTitle'):
            self.titleBar.setTitle(title)
        
        # 隐藏窗口标题标签
        if hasattr(self, 'windowTitleLabel'):
            self.windowTitleLabel.setVisible(False)
        
        # 设置UI
        self.setup_ui()
        
        # 应用自定义样式
        self.apply_custom_style()

    def setup_ui(self):
        # 移除底部按钮区域和内容标签
        if hasattr(self, 'buttonGroup'):
            self.buttonGroup.setParent(None)
            self.buttonGroup.deleteLater()
        
        if hasattr(self, 'contentLabel'):
            self.contentLabel.setVisible(False)
        
        # 创建头部区域 - 只添加图标和描述，删除重复的标题
        header_layout = QHBoxLayout()
        
        # 添加模式图标
        mode_icon = self.get_mode_icon()
        self.icon_widget = IconWidget(mode_icon, self)
        self.icon_widget.setFixedSize(32, 32)
        header_layout.addWidget(self.icon_widget)
        
        # 添加描述（不添加标题）
        description = self.get_mode_description()
        desc_label = BodyLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setObjectName("aiDialogDescLabel")
        
        # 直接将描述添加到布局中，不添加标题标签
        header_layout.addWidget(desc_label, 1)
        
        self.textLayout.addLayout(header_layout)
        
        # 添加分隔线
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setObjectName("aiDialogSeparator")
        self.textLayout.addWidget(separator)
        self.textLayout.addSpacing(10)
        
        # 添加辅助输入区域
        if self.mode not in ["tab续写", "自定义"]:
            aux_layout = QHBoxLayout()
            aux_label = BodyLabel("辅助提示词(可选):")
            aux_label.setMinimumWidth(100)
            self.aux_edit = TextEdit()
            self.aux_edit.setPlaceholderText("在这里输入额外的提示或要求...")
            self.aux_edit.setMaximumHeight(60)
            self.aux_edit.setObjectName("aiDialogAuxEdit")
            aux_layout.addWidget(aux_label)
            aux_layout.addWidget(self.aux_edit)
            self.textLayout.addLayout(aux_layout)
            
        # 如果是自定义模式，添加提示输入框
        if self.mode == "自定义":
            prompt_layout = QHBoxLayout()
            prompt_label = BodyLabel("提示词:")
            prompt_label.setMinimumWidth(100)
            self.prompt_edit = TextEdit()
            self.prompt_edit.setPlaceholderText("请输入 AI 提示词...")
            self.prompt_edit.setMaximumHeight(80)
            self.prompt_edit.setObjectName("aiDialogPromptEdit")
            prompt_layout.addWidget(prompt_label)
            prompt_layout.addWidget(self.prompt_edit)
            self.textLayout.addLayout(prompt_layout)
            
        # 添加结果显示区域
        result_layout = QVBoxLayout()
        result_header = QHBoxLayout()
        
        result_label = BodyLabel("生成结果:")
        result_label.setObjectName("aiDialogResultLabel")
        result_header.addWidget(result_label)
        
        result_header.addStretch(1)
        result_layout.addLayout(result_header)
        
        self.result_edit = TextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("AI 生成的内容将显示在这里...")
        self.result_edit.setMinimumHeight(200)
        self.result_edit.setObjectName("aiDialogResultEdit")
        result_layout.addWidget(self.result_edit)
        
        self.textLayout.addLayout(result_layout)
        
        # 添加按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        
        self.generate_button = PrimaryPushButton("生成")
        self.generate_button.setIcon(FluentIcon.SEND)
        self.generate_button.setEnabled(True)
        self.generate_button.clicked.connect(self.generate_content)
        
        self.use_button = PrimaryPushButton("使用结果")
        self.use_button.setIcon(FluentIcon.ACCEPT)
        self.use_button.setEnabled(False)
        self.use_button.clicked.connect(self.accept)
        
        self.cancel_button = PrimaryPushButton("取消")
        self.cancel_button.setIcon(FluentIcon.CLOSE)
        self.cancel_button.clicked.connect(self.reject)
        
        self.stop_button = PrimaryPushButton("停止生成")
        self.stop_button.setIcon(FluentIcon.CANCEL)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_generation)
        
        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.use_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.stop_button)
        
        self.textLayout.addLayout(button_layout)
        
        # 连接AI服务信号
        if self.ai_service:
            self.ai_service.resultReady.connect(self.handle_ai_result)
            self.ai_service.errorOccurred.connect(self.handle_ai_error)
            
        # 添加流式响应选项
        self.use_streaming = True  # 默认启用流式响应

    def apply_custom_style(self):
        """应用自定义样式"""
        # 设置样式表
        self.setStyleSheet("""
            #aiDialogTitleLabel {
                color: #0078d4;
                margin-bottom: 5px;
            }
            
            #aiDialogDescLabel {
                color: #666666;
                margin-bottom: 10px;
            }
            
            #aiDialogSeparator {
                background-color: #e0e0e0;
                margin: 5px 0;
            }
            
            #aiDialogResultEdit, #aiDialogAuxEdit, #aiDialogPromptEdit {
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 8px;
                background-color: #fafafa;
            }
            
            #aiDialogResultLabel {
                font-weight: bold;
                color: #333333;
            }
        """)
        
        # 如果是深色主题，调整样式
        if isDarkTheme():
            self.setStyleSheet("""
                #aiDialogTitleLabel {
                    color: #60cdff;
                    margin-bottom: 5px;
                }
                
                #aiDialogDescLabel {
                    color: #cccccc;
                    margin-bottom: 10px;
                }
                
                #aiDialogSeparator {
                    background-color: #444444;
                    margin: 5px 0;
                }
                
                #aiDialogResultEdit, #aiDialogAuxEdit, #aiDialogPromptEdit {
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 8px;
                    background-color: #333333;
                }
                
                #aiDialogResultLabel {
                    font-weight: bold;
                    color: #e0e0e0;
                }
            """)

    def get_mode_icon(self):
        """根据模式获取对应的图标"""
        icon_map = {
            "一句诗": FluentIcon.EDIT,
            "摘要": FluentIcon.DOCUMENT,
            "续写": FluentIcon.PENCIL_INK,
            "tab续写": FluentIcon.PENCIL_INK,
            "自定义": FluentIcon.ROBOT,
            "提取待办": FluentIcon.CHECKBOX,
            "润色": FluentIcon.BRUSH,
            "翻译": FluentIcon.LANGUAGE,
            "朋友圈文案": FluentIcon.GLOBE
        }

        return icon_map.get(self.mode, FluentIcon.ROBOT)

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

        # 添加调试代码，检查记忆上下文
        if hasattr(self.ai_service, "_memory_context"):
            context = self.ai_service._memory_context
            if context:
                print(f"AIDialog - 记忆上下文长度: {len(context)} 字符")
            else:
                print("AIDialog - 记忆上下文为空")
        else:
            print("AIDialog - 记忆上下文属性不存在")

        # 获取辅助提示词（如果有）
        aux_prompt = self.aux_edit.toPlainText() if hasattr(self, "aux_edit") else ""

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
            self.worker_thread = AIStreamWorkerThread(
                self.ai_service,
                self.mode,
                text,
                aux_prompt=aux_prompt,  # 添加辅助提示词参数
            )
            self.worker_thread.chunkReceived.connect(self.handle_stream_chunk)
            self.worker_thread.finished.connect(self.handle_stream_finished)
            self.worker_thread.error.connect(self.handle_ai_error)
            self.stop_button.setEnabled(True)
        else:
            self.worker_thread = AIWorkerThread(
                self.ai_service,
                self.mode,
                text,
                aux_prompt=aux_prompt,  # 添加辅助提示词参数
            )
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
            if hasattr(self, "prompt_edit"):
                self.prompt_edit.setReadOnly(False)

            # 显示已停止消息
            if hasattr(self, "state_tooltip") and self.state_tooltip:
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
            if hasattr(self, "prompt_edit"):
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
        if hasattr(self, "prompt_edit"):
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
            if hasattr(self, "prompt_edit"):
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
            if hasattr(self, "prompt_edit"):
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
        if hasattr(self, "prompt_edit"):
            self.prompt_edit.setReadOnly(False)

        event.accept()

    # 添加鼠标事件处理，以便可以拖动无边框窗口
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()


class AIHandler:
    """AI 功能处理类"""

    _instance = None  # 类变量，用于存储单例实例

    @classmethod
    def get_instance(cls, parent=None):
        """获取AIHandler单例实例"""
        if cls._instance is None:
            try:
                cls._instance = AIHandler(parent)
            except Exception as e:
                print(f"创建AIHandler实例时出错: {str(e)}")
                import traceback

                traceback.print_exc()
                # 创建一个降级版本的AIHandler
                cls._instance = cls._create_fallback_instance(parent)
        return cls._instance

    @classmethod
    def _create_fallback_instance(cls, parent):
        """创建降级版本的AIHandler实例"""
        handler = object.__new__(cls)
        handler.parent = parent
        # 创建一个空的AI服务
        from services.ai_service import AIService

        handler.ai_service = AIService.__new__(AIService)
        handler.ai_service._memory_context = ""
        handler.ai_service.client = None
        return handler

    def __init__(self, parent: CardWidget):
        # 如果已经有实例，直接返回
        if AIHandler._instance is not None:
            return

        self.parent = parent
        self.ai_service = AIService()  # 初始化 AI 服务

        # 设置单例实例
        AIHandler._instance = self

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

        # 传递AI服务实例
        dialog = AIDialog(mode, text, self.parent, ai_service=self.ai_service)
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
            (
                current_cursor.insertText(result_text)
                if current_text
                else text_edit.setText(result_text)
            )
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

    def _parse_ai_todo_result(self, result):
        """解析AI返回的待办事项结果"""
        try:
            import json
            import re
            from datetime import datetime, timedelta
            
            # 尝试直接解析JSON
            try:
                todos = json.loads(result)
                if isinstance(todos, list):
                    # 确保每个待办事项都有必要的字段
                    for todo in todos:
                        if "task" not in todo:
                            todo["task"] = ""
                        if "deadline" not in todo or not todo["deadline"]:
                            todo["deadline"] = "无截止日期"
                        if "category" not in todo or not todo["category"]:
                            todo["category"] = "其他"
                    return len(todos), todos
            except:
                pass
            
            # 如果直接解析失败，尝试从文本中提取
            todos = []
            lines = result.strip().split('\n')
            
            for line in lines:
                # 跳过空行
                if not line.strip():
                    continue
                    
                # 尝试匹配常见的待办事项格式
                todo_match = re.search(r'[*\-•]?\s*(.+?)(?:，|,|\s+)(?:截止日期|截止时间|deadline)[:：]?\s*(.+?)(?:，|,|\s+)(?:类别|分类|category)[:：]?\s*(.+?)$', line, re.IGNORECASE)
                
                if todo_match:
                    task = todo_match.group(1).strip()
                    deadline = todo_match.group(2).strip()
                    category = todo_match.group(3).strip()
                    
                    # 处理相对日期
                    if deadline and any(word in deadline for word in ["今天", "明天", "后天", "下周", "下个月"]):
                        now = datetime.now()
                        
                        if "今天" in deadline:
                            deadline_date = now.strftime("%Y-%m-%d")
                        elif "明天" in deadline:
                            deadline_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
                        elif "后天" in deadline:
                            deadline_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")
                        elif "下周" in deadline:
                            # 简单处理，加7天
                            deadline_date = (now + timedelta(days=7)).strftime("%Y-%m-%d")
                        elif "下个月" in deadline:
                            # 简单处理，加30天
                            deadline_date = (now + timedelta(days=30)).strftime("%Y-%m-%d")
                        
                        # 提取时间部分
                        time_match = re.search(r'(\d{1,2})[:.：](\d{1,2})', deadline)
                        if time_match:
                            hour = int(time_match.group(1))
                            minute = int(time_match.group(2))
                            deadline = f"{deadline_date} {hour:02d}:{minute:02d}"
                        else:
                            deadline = f"{deadline_date} 09:00"
                    
                    todos.append({
                        "task": task,
                        "deadline": deadline,
                        "category": category
                    })
                else:
                    # 如果没有匹配到完整格式，尝试只提取任务内容
                    task_match = re.search(r'[*\-•]?\s*(.+)', line)
                    if task_match:
                        task = task_match.group(1).strip()
                        if task and not task.startswith(("待办事项", "Todo", "任务")):
                            todos.append({
                                "task": task,
                                "deadline": "无截止日期",
                                "category": "其他"
                            })
            
            return len(todos), todos
        except Exception as e:
            print(f"解析AI待办结果出错: {str(e)}")
            return 0, []

    def extract_todos_from_memo(self, memo_content, user_id):
        """从备忘录内容中提取待办事项"""
        try:
            # 构建提示词
            system_prompt = self.ai_service.AI_MODES["待办提取"]["system_prompt"]

            # 添加当前日期信息，帮助AI正确推断日期
            from datetime import datetime
            import locale

            # 设置中文环境
            try:
                locale.setlocale(locale.LC_TIME, "zh_CN.UTF-8")
            except:
                try:
                    locale.setlocale(locale.LC_TIME, "zh_CN")
                except:
                    pass  # 如果设置失败，使用默认环境

            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")

            # 获取星期几（中文）
            weekday_names = [
                "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"
            ]
            weekday = weekday_names[now.weekday()]

            prompt = f"""当前日期：{current_date} ({weekday})

请从以下备忘录内容中提取所有待办事项，并按以下JSON格式返回结果。对于每个待办事项，请提取任务内容、截止日期和类别。
如果无法确定截止日期，请设为当前日期加一天。如果无法确定类别，请根据内容推断为"工作"、"学习"、"生活"或"其他"。

请将相对日期（如"明天"、"下周三"等）转换为具体日期格式（YYYY-MM-DD HH:MM）。

备忘录内容:
{memo_content}

请返回格式如下的JSON数组:
[
  {{"task": "任务内容", "deadline": "YYYY-MM-DD HH:MM", "category": "类别"}},
  ...
]
"""

            # 使用AI服务生成内容
            result = self.ai_service.generate_content(system_prompt + prompt, mode="自定义")

            # 解析JSON结果
            return self._parse_ai_todo_result(result)
        except Exception as e:
            print(f"提取待办事项时出错: {str(e)}")
            return 0, []
