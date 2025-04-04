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

    chunkReceived = pyqtSignal(str)  
    finished = pyqtSignal()  
    error = pyqtSignal(str) 

    def __init__(self, ai_service, mode, text, aux_prompt=""):
        super().__init__()
        self.ai_service = ai_service
        self.mode = mode
        self.text = text
        self.aux_prompt = aux_prompt
        self._stop_requested = False

    def run(self):
        try:
            stream = self.ai_service.generate_content_stream(
                self.text, self.mode, self.aux_prompt
            )

            full_response = ""

            for chunk in stream:
                if self._stop_requested:
                    break

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
        self.mode = mode
        self.input_text = text
        self.result_text = ""
        self.state_tooltip = None
        self.worker_thread = None
        
        self.ai_service = ai_service
        
        title = self.get_mode_display_name()
        content = ""

        super().__init__(title, content, parent=parent)
        
        self.resize(650, 500)
        self.setMaximumSize(16777215, 16777215)
        self.setFixedSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self.setResizeEnabled(True)
        
        self.titleBar.show()
        
        if hasattr(self.titleBar, 'setDoubleClickEnabled'):
            self.titleBar.setDoubleClickEnabled(True)

        if hasattr(self.titleBar, 'minBtn'):
            self.titleBar.minBtn.show()
        if hasattr(self.titleBar, 'maxBtn'):
            self.titleBar.maxBtn.show()
        if hasattr(self.titleBar, 'closeBtn'):
            self.titleBar.closeBtn.show()

        if hasattr(self.titleBar, 'setTitle'):
            self.titleBar.setTitle(title)

        if hasattr(self, 'windowTitleLabel'):
            self.windowTitleLabel.setVisible(False)

        self.setup_ui()

        self.apply_custom_style()

    def setup_ui(self):
        if hasattr(self, 'buttonGroup'):
            self.buttonGroup.setParent(None)
            self.buttonGroup.deleteLater()
        
        if hasattr(self, 'contentLabel'):
            self.contentLabel.setVisible(False)
        
        header_layout = QHBoxLayout()

        mode_icon = self.get_mode_icon()
        self.icon_widget = IconWidget(mode_icon, self)
        self.icon_widget.setFixedSize(32, 32)
        header_layout.addWidget(self.icon_widget)
        
        description = self.get_mode_description()
        desc_label = BodyLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setObjectName("aiDialogDescLabel")
         
        header_layout.addWidget(desc_label, 1)
        
        self.textLayout.addLayout(header_layout)
        
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setObjectName("aiDialogSeparator")
        self.textLayout.addWidget(separator)
        self.textLayout.addSpacing(10)
        
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

        if self.ai_service:
            self.ai_service.resultReady.connect(self.handle_ai_result)
            self.ai_service.errorOccurred.connect(self.handle_ai_error)

        self.use_streaming = True  

    def apply_custom_style(self):
        """应用自定义样式"""
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
            pass  
            self.state_tooltip = None

    def generate_content(self):
        """生成内容"""
        self.disable_all_inputs()
        self.show_loading_state()

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

        self.result_edit.clear()
        self.result_text = ""

        self.stop_any_running_threads()

        if self.use_streaming:
            self.worker_thread = AIStreamWorkerThread(
                self.ai_service,
                self.mode,
                text,
                aux_prompt=aux_prompt,  
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
                aux_prompt=aux_prompt,  
            )
            self.worker_thread.finished.connect(self.handle_ai_result)
            self.worker_thread.error.connect(self.handle_ai_error)

        self.worker_thread.start()

    def stop_generation(self):
        """停止生成过程"""
        if self.worker_thread and isinstance(self.worker_thread, AIStreamWorkerThread):
            self.worker_thread.stop()
            self.stop_button.setEnabled(False)

            self.generate_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            if hasattr(self, "prompt_edit"):
                self.prompt_edit.setReadOnly(False)

            if hasattr(self, "state_tooltip") and self.state_tooltip:
                try:
                    self.state_tooltip.setContent("生成已停止")
                    self.state_tooltip.setState(True)
                    QApplication.processEvents()
                except:
                    pass
                finally:
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
            self.result_text += chunk

            self.result_edit.setText(self.result_text)

            cursor = self.result_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.result_edit.setTextCursor(cursor)

        except Exception:
            pass  

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

        except Exception:
            pass  

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
                    QTimer.singleShot(1000, lambda: self.safely_close_tooltip())

        except Exception as e:
            pass 

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
            pass 

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

    _instance = None  

    @classmethod
    def get_instance(cls, parent=None):
        """获取AIHandler单例实例"""
        if cls._instance is None:
            try:
                cls._instance = AIHandler(parent)
            except Exception:
                import traceback

                traceback.print_exc()
                cls._instance = cls._create_fallback_instance(parent)
        return cls._instance

    @classmethod
    def _create_fallback_instance(cls, parent):
        """创建降级版本的AIHandler实例"""
        handler = object.__new__(cls)
        handler.parent = parent

        handler.ai_service = AIService.__new__(AIService)
        handler.ai_service._memory_context = ""
        handler.ai_service.client = None
        return handler

    def __init__(self, parent: CardWidget):
        if AIHandler._instance is not None:
            return

        self.parent = parent
        self.ai_service = AIService()  

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
            current_cursor = text_edit.textCursor()
            current_position = current_cursor.position()

            current_cursor.movePosition(QTextCursor.End)
            text_edit.setTextCursor(current_cursor)

            current_text = text_edit.toPlainText()

            (
                current_cursor.insertText(result_text)
                if current_text
                else text_edit.setText(result_text)
            )
        else:
            if not text_edit.toPlainText().strip():
                text_edit.setText(result_text)
            else:
                current_cursor = text_edit.textCursor()
                current_cursor.movePosition(QTextCursor.End)
                text_edit.setTextCursor(current_cursor)

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

            try:
                todos = json.loads(result)
                if isinstance(todos, list):
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

            todos = []
            lines = result.strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue

                todo_match = re.search(r'[*\-•]?\s*(.+?)(?:，|,|\s+)(?:截止日期|截止时间|deadline)[:：]?\s*(.+?)(?:，|,|\s+)(?:类别|分类|category)[:：]?\s*(.+?)$', line, re.IGNORECASE)
                
                if todo_match:
                    task = todo_match.group(1).strip()
                    deadline = todo_match.group(2).strip()
                    category = todo_match.group(3).strip()

                    if deadline and any(word in deadline for word in ["今天", "明天", "后天", "下周", "下个月"]):
                        now = datetime.now()
                        
                        if "今天" in deadline:
                            deadline_date = now.strftime("%Y-%m-%d")
                        elif "明天" in deadline:
                            deadline_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
                        elif "后天" in deadline:
                            deadline_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")
                        elif "下周" in deadline:
                            deadline_date = (now + timedelta(days=7)).strftime("%Y-%m-%d")
                        elif "下个月" in deadline:
                            deadline_date = (now + timedelta(days=30)).strftime("%Y-%m-%d")
                        
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
            return 0, []

    def extract_todos_from_memo(self, memo_content, user_id):
        """从备忘录内容中提取待办事项"""
        try:
            system_prompt = self.ai_service.AI_MODES["待办提取"]["system_prompt"]

            from datetime import datetime
            import locale

            try:
                locale.setlocale(locale.LC_TIME, "zh_CN.UTF-8")
            except:
                try:
                    locale.setlocale(locale.LC_TIME, "zh_CN")
                except:
                    pass  

            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")

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

            result = self.ai_service.generate_content(system_prompt + prompt, mode="自定义")

            return self._parse_ai_todo_result(result)
        except Exception:
            pass  
            return 0, []
