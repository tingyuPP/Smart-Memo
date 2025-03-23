from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import (
    QTextCursor,
    QColor, 
    QTextCharFormat  
)
from qfluentwidgets import TextEdit, StateToolTip
from services.ai_service import AIService

class SuggestionThread(QThread):
    """AI建议生成线程"""
    suggestionReady = pyqtSignal(str)
    
    def __init__(self, ai_service, text):
        super().__init__()
        self.ai_service = ai_service
        self.text = text
        
    def run(self):
        try:
            result = self.ai_service.generate_content(
                self.text, 
                "tab续写"  # 确保使用正确的模式名称
            )
            self.suggestionReady.emit(result)
        except Exception as e:
            print(f"生成建议出错: {str(e)}")
            self.suggestionReady.emit("")

class TabContinuationThread(QThread):
    """Tab键续写线程"""
    resultReady = pyqtSignal(str)
    
    def __init__(self, ai_service, context):
        super().__init__()
        self.ai_service = ai_service
        self.context = context
        
    def run(self):
        try:
            result = self.ai_service.generate_content(
                self.context,
                "tab续写"
            )
            self.resultReady.emit(result)
        except Exception as e:
            print(f"续写生成出错: {str(e)}")
            self.resultReady.emit("")

class SmartTextEdit(TextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_service = AIService()
        self._init_ai_modes()
        
        # 建议相关变量
        self.current_suggestion = ""
        self.suggestion_start_pos = None
        self.suggestion_active = False
        self.is_showing_suggestion = False  # 添加标志位防止循环
        
        # 用于延迟触发建议的计时器
        self.suggestion_timer = QTimer(self)
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.timeout.connect(self._request_suggestion)
        
        # 建议生成线程
        self.suggestion_thread = None
        
        # 监听光标位置变化
        self.cursorPositionChanged.connect(self._on_cursor_position_changed)
        
        # 设置建议文本的颜色
        self.suggestion_color = QColor(169, 169, 169)  # 浅灰色
        
        # 添加补全历史缓存
        self.completion_history = []
        self.max_history_size = 5
        
    def _init_ai_modes(self):
        """初始化AI模式"""
        if hasattr(self.ai_service, 'AI_MODES') and '智能提示' not in self.ai_service.AI_MODES:
            self.ai_service.AI_MODES['智能提示'] = {
                "display_name": "智能提示",
                "description": "根据当前输入智能提示后续内容",
                "system_prompt": "你是一位专业的编程助手。请根据用户提供的代码或文本片段，预测并补全后续内容。补全应当自然衔接，符合上下文逻辑。只输出补全的内容，不要重复已有的文本，不要添加任何解释。"
            }
    
    def _on_cursor_position_changed(self):
        """光标位置改变时的处理"""
        if self.is_showing_suggestion:
            return
            
        # 取消当前的建议
        self._clear_suggestion()
        # 重置计时器
        self.suggestion_timer.start(300)  # 0.3秒后触发建议
    
    def _request_suggestion(self):
        """请求AI补全建议"""
        current_text = self.toPlainText()
        cursor = self.textCursor()
        position = cursor.position()
        
        # 获取光标前的文本作为上下文
        context = current_text[:position]
        
        # 检查是否与最近的补全历史重复
        if self.completion_history and any(
            self._is_similar_context(context, hist['context'])
            for hist in self.completion_history
        ):
            # 如果发现相似上下文，使用不同的提示词请求新的补全
            context += "\n[请生成不同于之前的新内容]"
        
        if len(context.strip()) < 5:  # 内容太短不触发
            return
            
        # 清理旧线程
        if self.suggestion_thread and self.suggestion_thread.isRunning():
            self.suggestion_thread.terminate()
            self.suggestion_thread.wait()
        
        # 创建新线程
        self.suggestion_thread = SuggestionThread(self.ai_service, context)
        self.suggestion_thread.suggestionReady.connect(self._handle_suggestion)
        self.suggestion_thread.start()
    
    def _get_context(self, cursor):
        """获取当前上下文"""
        position = cursor.position()
        cursor.setPosition(0)
        cursor.setPosition(position, QTextCursor.KeepAnchor)
        return cursor.selectedText()
    
    def _handle_suggestion(self, suggestion):
        """处理AI建议"""
        # 首先检查建议是否有效
        if not suggestion or len(suggestion.strip()) == 0:
            self._reset_suggestion_state()
            return
        
        # 获取当前光标
        cursor = self.textCursor()
        if cursor.isNull():
            self._reset_suggestion_state()
            return
        
        # 获取并验证位置
        pos = cursor.position()
        
        if not isinstance(pos, int) or pos < 0:
            self._reset_suggestion_state()
            return
        
        # 设置建议状态
        self.suggestion_start_pos = pos
        self.current_suggestion = suggestion
        self.suggestion_active = True
        
        # 显示建议
        self._show_suggestion()

    def _show_suggestion(self):
        """显示建议文本"""
        if not self.suggestion_active or not self.current_suggestion or self.suggestion_start_pos is None:
            return
            
        try:
            self.is_showing_suggestion = True
        
            # 创建新光标并设置位置
            cursor = QTextCursor(self.document())
            cursor.setPosition(self.suggestion_start_pos)
            
            # 设置建议文本格式
            format = QTextCharFormat()
            format.setForeground(self.suggestion_color)
            
            # 插入建议文本
            cursor.insertText(self.current_suggestion, format)
            
            # 恢复光标到原始位置
            cursor.setPosition(self.suggestion_start_pos)
            self.setTextCursor(cursor)
            
        except Exception as e:
            print(f"显示建议时出错: {str(e)}")
        finally:
            self.is_showing_suggestion = False

    def _clear_suggestion(self):
        """清除当前建议"""
        if not self.suggestion_active or self.suggestion_start_pos is None:
            return
        
        try:
            self.is_showing_suggestion = True  # 设置标志位
            
            # 获取当前文档
            document = self.document()
            
            # 创建新的光标用于清除操作
            cursor = QTextCursor(document)
            
            # 设置选区：从建议开始位置到建议结束位置
            start_pos = self.suggestion_start_pos
            end_pos = start_pos + len(self.current_suggestion)
            
            # 确保位置有效
            if start_pos >= document.characterCount():
                return
                
            # 设置选区
            cursor.setPosition(start_pos)
            cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
            
            # 删除选中的建议文本
            cursor.removeSelectedText()
            
            # 恢复光标到原始位置
            cursor.setPosition(start_pos)
            self.setTextCursor(cursor)
            
        except Exception as e:
            print(f"清除建议时出错: {str(e)}")
        finally:
            # 重置所有状态
            self.is_showing_suggestion = False
            self.suggestion_active = False
            self.current_suggestion = ""
            self.suggestion_start_pos = None

    def _reset_suggestion_state(self):
        """重置所有建议相关的状态"""
        if self.is_showing_suggestion:
            return
            
        self.suggestion_active = False
        self.current_suggestion = ""
        self.suggestion_start_pos = None

    def keyPressEvent(self, event):
        """处理按键事件"""
        # 如果有活动的建议，除了特殊键位外，其他任何按键都应该先清除建议
        if self.suggestion_active:
            if event.key() == Qt.Key_Tab:
                # 接受建议
                self._accept_suggestion()
                event.accept()
                return
            elif event.key() == Qt.Key_Escape:
                # 取消建议
                self._clear_suggestion()
                event.accept()
                return
            else:
                # 在处理输入前，确保完全清除建议
                self.blockSignals(True)  # 暂时阻止信号以防止触发其他事件
                self._clear_suggestion()
                self.blockSignals(False)
        
        # 处理实际的按键输入
        super().keyPressEvent(event)
    
    def _accept_suggestion(self):
        """接受当前的补全建议"""
        if self.suggestion_active and self.current_suggestion:
            # 记录这次补全的上下文和结果
            context = self.toPlainText()[:self.suggestion_start_pos]
            self.completion_history.append({
                'context': context,
                'completion': self.current_suggestion
            })
            
            # 限制历史记录大小
            if len(self.completion_history) > self.max_history_size:
                self.completion_history.pop(0)
        
        if not self.suggestion_active or self.suggestion_start_pos is None:  # 修改检查条件
            return
            
        try:
            # 将建议文本的颜色改为正常颜色
            cursor = QTextCursor(self.document())
            cursor.setPosition(self.suggestion_start_pos)
            cursor.movePosition(
                QTextCursor.Right,
                QTextCursor.KeepAnchor,
                len(self.current_suggestion)
            )
            
            format = cursor.charFormat()
            format.setForeground(self.palette().text())
            cursor.setCharFormat(format)
        except:
            pass  # 如果出现任何错误，忽略它
        finally:
            self._reset_suggestion_state()

    def _is_similar_context(self, context1, context2):
        """检查两个上下文是否相似"""
        # 简单的相似度检查：如果最后50个字符相似度超过80%则认为相似
        last_chars1 = context1[-50:] if len(context1) > 50 else context1
        last_chars2 = context2[-50:] if len(context2) > 50 else context2
        
        # 使用编辑距离计算相似度
        def levenshtein_distance(s1, s2):
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            return previous_row[-1]
        
        distance = levenshtein_distance(last_chars1, last_chars2)
        max_length = max(len(last_chars1), len(last_chars2))
        similarity = 1 - (distance / max_length)
        
        return similarity > 0.8

def enhance_text_edit_with_copilot(text_edit, parent_window):
    """为现有的TextEdit添加类似Copilot的智能提示功能"""
    ai_service = AIService()
    
    # 初始化其他功能...
    text_edit.continuation_in_progress = False
    
    # 保存引用，防止垃圾回收
    text_edit._tab_completion_data = {
        'ai_service': ai_service
    }
    
    return text_edit
