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
    CheckBox,
    FluentIcon
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
            result = self.ai_service.generate_content(self.text, self.mode, self.aux_prompt)
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
            stream = self.ai_service.generate_content_stream(self.text, self.mode, self.aux_prompt)
            
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

    def __init__(self, mode, text="", parent=None, ai_service=None):
        super().__init__(parent)
        self.mode = mode
        self.input_text = text
        self.result_text = ""
        self.state_tooltip = None
        self.worker_thread = None  # 添加工作线程属性
        
        # 使用传入的AI服务实例，而不是创建新的
        self.ai_service = ai_service
        
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

        # 添加辅助输入区域（除了tab续写和自定义模式外都显示）
        if self.mode not in ["tab续写", "自定义"]:
            aux_layout = QHBoxLayout()
            aux_label = QLabel("辅助提示词(可选):")
            self.aux_edit = TextEdit()
            self.aux_edit.setPlaceholderText("在这里输入额外的提示或要求...")
            self.aux_edit.setMaximumHeight(60)
            aux_layout.addWidget(aux_label)
            aux_layout.addWidget(self.aux_edit)
            layout.addLayout(aux_layout)

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

        # 连接AI服务信号
        if self.ai_service:
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
        
        # 添加调试代码，检查记忆上下文
        if hasattr(self.ai_service, '_memory_context'):
            context = self.ai_service._memory_context
            if context:
                print(f"AIDialog - 记忆上下文长度: {len(context)} 字符")
            else:
                print("AIDialog - 记忆上下文为空")
        else:
            print("AIDialog - 记忆上下文属性不存在")
        
        # 获取辅助提示词（如果有）
        aux_prompt = self.aux_edit.toPlainText() if hasattr(self, 'aux_edit') else ""

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
                aux_prompt=aux_prompt  # 添加辅助提示词参数
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
                aux_prompt=aux_prompt  # 添加辅助提示词参数
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
    
    def __init__(self, parent: QWidget):
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

    def extract_todos_from_memo(self, memo_content, user_id):
        """从备忘录内容中提取待办事项
        
        Args:
            memo_content: 备忘录内容
            user_id: 用户ID
            
        Returns:
            tuple: (添加的待办数量, 有效待办列表)
        """
        try:
            # 构建提示词
            system_prompt = """你是一个专业的待办事项提取助手。请从用户的备忘录内容中识别出所有可能的待办事项。
待办事项通常包含需要完成的任务，可能有截止日期。对于每个识别出的待办事项，请提供以下信息：
1. 任务内容
2. 截止日期（如果有）
3. 类别（如果有）

请以JSON格式返回结果，格式如下：
```json
[
  {
    "task": "任务内容",
    "deadline": "YYYY-MM-DD",
    "category": "类别"
  },
  ...
]
```
如果无法识别截止日期，请使用null。如果无法识别类别，请使用"未分类"。"""

            prompt = f"请从以下备忘录内容中提取所有待办事项：\n\n{memo_content}"
            
            # 使用AI服务生成内容
            # 注意：这里使用generate_content方法而不是process_with_ai
            result = self.ai_service.generate_content(prompt, mode="自定义")
            
            # 尝试解析JSON结果
            todos = self._parse_ai_todo_result(result)
            
            # 处理有效的待办事项
            valid_todos = []
            
            # 处理提取的待办事项
            for todo in todos:
                if not isinstance(todo, dict):
                    continue
                    
                # 确保有任务内容
                task = todo.get('task', '').strip() if isinstance(todo.get('task'), str) else ''
                if not task:
                    continue
                    
                # 处理截止日期
                deadline = todo.get('deadline')
                if not deadline or deadline == "null" or not isinstance(deadline, str):
                    # 如果没有截止日期，设置为一周后
                    from datetime import datetime, timedelta
                    deadline = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                    
                # 处理类别
                category = todo.get('category', '未分类')
                if not category or category == "null" or not isinstance(category, str):
                    category = "未分类"
                    
                valid_todos.append({
                    'task': task,
                    'deadline': deadline,
                    'category': category
                })
            
            # 添加到数据库
            db = DatabaseManager()
            added_count = 0
            
            for todo in valid_todos:
                print(f"添加待办: {todo}")
                todo_id = db.add_todo(user_id, todo['task'], todo['deadline'], todo['category'])
                if todo_id:
                    added_count += 1
            
            return added_count, valid_todos
        except Exception as e:
            import traceback
            print(f"处理待办提取结果时出错: {str(e)}")
            print(traceback.format_exc())
            return 0, []
            
    def _parse_ai_todo_result(self, result):
        """解析AI返回的文本，提取待办事项"""
        import json
        import re
        
        print("AI返回结果:", result)
        
        if not result or not result.strip():
            print("AI返回结果为空")
            return []
        
        # 尝试直接解析JSON
        try:
            # 查找JSON数组模式 [...] 
            json_pattern = r'\[[\s\S]*\]'
            json_match = re.search(json_pattern, result)
            
            if json_match:
                # 提取JSON字符串
                json_str = json_match.group(0)
                print("提取的JSON字符串:", json_str)
                
                # 尝试解析JSON
                todos = json.loads(json_str)
                print(f"成功解析JSON，找到 {len(todos)} 个待办事项")
                return todos
        except Exception as e:
            print(f"JSON解析错误: {str(e)}")
        
        # 如果JSON解析失败，尝试手动解析文本
        print("尝试手动解析文本")
        todos = []
        
        # 分行处理文本
        lines = result.split('\n')
        current_todo = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是新的待办项（数字开头或包含明确的任务标记）
            if re.match(r'^\d+[\.\)、]', line) or line.lower().startswith('task') or '任务' in line:
                # 保存之前的任务（如果有）
                if current_todo and 'task' in current_todo and current_todo['task']:
                    todos.append(current_todo)
                    print(f"添加按行解析的待办: {current_todo}")
                
                # 创建新任务
                current_todo = {"task": "", "deadline": None, "category": "未分类"}
                
                # 提取任务内容
                task_content = re.sub(r'^\d+[\.\)、]\s*', '', line)
                task_content = re.sub(r'^task[:\s]+', '', task_content, flags=re.IGNORECASE)
                task_content = re.sub(r'^任务[:\s]+', '', task_content)
                current_todo['task'] = task_content
            
            # 检查是否包含截止日期
            elif 'deadline' in line.lower() or '截止日期' in line or '截止时间' in line:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                if date_match:
                    current_todo['deadline'] = date_match.group(1)
            
            # 检查是否包含类别
            elif 'category' in line.lower() or '类别' in line or '分类' in line:
                category_match = re.search(r'[类别分类category]+[:\s]+(.+)', line, re.IGNORECASE)
                if category_match:
                    current_todo['category'] = category_match.group(1).strip()
        
        # 添加最后一个任务（如果有）
        if current_todo and 'task' in current_todo and current_todo['task']:
            todos.append(current_todo)
            print(f"添加最后一个按行解析的待办: {current_todo}")
        
        return todos
