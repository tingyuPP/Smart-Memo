from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QTextCursor, QColor, QTextCharFormat, QPainter
from qfluentwidgets import TextEdit, StateToolTip
from services.ai_service import AIService
from config import cfg


class SuggestionThread(QThread):
    """AI建议生成线程"""

    suggestionReady = pyqtSignal(str)

    def __init__(self, ai_service, text):
        super().__init__()
        self.ai_service = ai_service
        self.text = text

    def run(self):
        try:
            last_chars = self.text[-50:] if len(self.text) > 50 else self.text
            context = f"{self.text}\n[请续写内容，不要重复最后的文本：{last_chars}]"

            result = self.ai_service.generate_content(context, "tab续写")

            if result and last_chars and result.startswith(last_chars):
                result = result[len(last_chars) :]

            self.suggestionReady.emit(result)
        except Exception:
            pass  
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
            result = self.ai_service.generate_content(self.context, "tab续写")
            self.resultReady.emit(result)
        except Exception:
            pass  
            self.resultReady.emit("")

class SmartTextEdit(TextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_service = AIService()
        self._init_ai_modes()

        self.current_suggestion = ""
        self.suggestion_start_pos = None
        self.suggestion_active = False
        self.is_composing = False
        self.suggestion_thread = None
        self.is_showing_suggestion = False

        self.normal_color = self.palette().text().color()
        self.suggestion_color = QColor(169, 169, 169)  

        self.suggestion_timer = QTimer(self)
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.timeout.connect(self._request_suggestion)
        self._update_timer_interval(cfg.get(cfg.completionTime))  

        cfg.completionTime.valueChanged.connect(self._update_timer_interval)

        self.suggestion_format = QTextCharFormat()
        self.suggestion_format.setForeground(self.suggestion_color)

        self.completion_history = []
        self.max_history_size = 5

        self.cursorPositionChanged.connect(self._on_cursor_position_changed)

        self.destroyed.connect(self._cleanup_threads)

    def _cleanup_threads(self):
        """清理线程资源"""
        if self.suggestion_thread and self.suggestion_thread.isRunning():
            self.suggestion_thread.terminate()
            self.suggestion_thread.wait()

    def inputMethodEvent(self, event):
        """处理输入法事件"""
        self.is_composing = event.preeditString() != ""

        if self.is_composing and self.suggestion_active:
            self._clear_suggestion()
            self.suggestion_timer.stop() 

        super().inputMethodEvent(event)

    def _init_ai_modes(self):
        """初始化AI模式"""
        if (
            hasattr(self.ai_service, "AI_MODES")
            and "智能提示" not in self.ai_service.AI_MODES
        ):
            self.ai_service.AI_MODES["智能提示"] = {
                "display_name": "智能提示",
                "description": "根据当前输入智能提示后续内容",
                "system_prompt": "你是一位专业的编程助手。请根据用户提供的代码或文本片段，预测并补全后续内容。补全应当自然衔接，符合上下文逻辑。只输出补全的内容，不要重复已有的文本，不要添加任何解释。",
            }

    def _on_cursor_position_changed(self):
        """光标位置改变时的处理"""
        self.auto_completion_enabled = cfg.get(cfg.enableAutoCompletion)

        if not self.auto_completion_enabled:
            self._clear_suggestion()
            return

        if self.is_showing_suggestion or self.is_composing:
            return

        self._clear_suggestion()
        self.suggestion_timer.start()

    def _request_suggestion(self):
        """请求AI补全建议"""
        if not cfg.get(cfg.enableAutoCompletion) or self.is_composing:
            return

        current_text = self.toPlainText()
        if not current_text:
            return

        cursor = self.textCursor()
        position = cursor.position()
        context = current_text[:position]

        if len(context.strip()) < 5:
            return

        if self.suggestion_thread and self.suggestion_thread.isRunning():
            self.suggestion_thread.terminate()
            self.suggestion_thread.wait()

        try:
            self.suggestion_thread = SuggestionThread(self.ai_service, context)
            self.suggestion_thread.suggestionReady.connect(self._handle_suggestion)
            self.suggestion_thread.start()
        except Exception:
            pass 

    def _get_context(self, cursor):
        """获取当前上下文"""
        position = cursor.position()
        cursor.setPosition(0)
        cursor.setPosition(position, QTextCursor.KeepAnchor)
        return cursor.selectedText()

    def _handle_suggestion(self, suggestion):
        """处理AI建议"""
        if not suggestion or len(suggestion.strip()) == 0:
            self._clear_suggestion()
            return

        cursor = self.textCursor()
        position = cursor.position()

        self.suggestion_start_pos = position
        self.current_suggestion = suggestion
        self.suggestion_active = True

        self.viewport().update() 

    def _show_suggestion(self):
        """显示建议文本"""
        if not self.suggestion_active or not self.current_suggestion:
            return

        self.viewport().update()

    def paintEvent(self, event):
        """重写绘制事件以显示建议文本"""
        super().paintEvent(event)

        if self.suggestion_active and self.current_suggestion:
            painter = QPainter(self.viewport())
            cursor = self.textCursor()

            rect = self.cursorRect(cursor)

            painter.setFont(self.font())
            painter.setPen(self.suggestion_color)

            viewport_width = self.viewport().width()
            document_margin = self.document().documentMargin()

            first_line_x = int(rect.x())  
            subsequent_line_x = int(document_margin) 
            y = int(rect.y() + painter.fontMetrics().ascent())

            font_metrics = painter.fontMetrics()
            first_line_max_width = (
                viewport_width - first_line_x - 20
            ) 
            subsequent_line_max_width = (
                viewport_width - subsequent_line_x - 20
            )  

            suggestion_lines = []
            current_line = ""
            is_first_line = True

            for char in self.current_suggestion:
                test_line = current_line + char
                max_width = (
                    first_line_max_width if is_first_line else subsequent_line_max_width
                )

                if (
                    font_metrics.horizontalAdvance(test_line) > max_width
                    or char == "\n"
                ):
                    suggestion_lines.append((current_line, is_first_line))
                    current_line = "" if char == "\n" else char
                    is_first_line = False
                else:
                    current_line += char

            if current_line:
                suggestion_lines.append((current_line, is_first_line))

            max_lines = 5
            if len(suggestion_lines) > max_lines:
                suggestion_lines = suggestion_lines[:max_lines]
                suggestion_lines[-1] = (
                    suggestion_lines[-1][0] + "...",
                    suggestion_lines[-1][1],
                )

            line_height = font_metrics.height()
            for i, (line, is_first) in enumerate(suggestion_lines):
                x = int(first_line_x if is_first else subsequent_line_x)
                y_pos = int(y + i * line_height)
                painter.drawText(x, y_pos, line)

    def _clear_suggestion(self):
        """清除当前建议"""
        if not self.suggestion_active:
            return

        self.suggestion_active = False
        self.current_suggestion = ""
        self.suggestion_start_pos = None

        self.viewport().update()

    def _reset_suggestion_state(self):
        """重置所有建议相关的状态"""
        if self.is_showing_suggestion:
            return

        self.suggestion_active = False
        self.current_suggestion = ""
        self.suggestion_start_pos = None

    def keyPressEvent(self, event):
        """处理按键事件"""
        if self.is_composing:
            super().keyPressEvent(event)
            return

        if self.suggestion_active and self.current_suggestion:
            if event.key() == Qt.Key_Tab:
                self._accept_suggestion()
                event.accept()
                return
            elif event.key() == Qt.Key_Escape:
                self._clear_suggestion()
                event.accept()
                return

        super().keyPressEvent(event)

        cursor = self.textCursor()
        format = cursor.charFormat()
        format.setForeground(self.normal_color)
        cursor.mergeCharFormat(format)

        if event.key() not in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
            self.suggestion_timer.start() 
        format = cursor.charFormat()
        format.setForeground(self.normal_color)
        cursor.mergeCharFormat(format)

    def focusOutEvent(self, event):
        """失去焦点时清除建议"""
        if self.suggestion_active:
            self._clear_suggestion()
        super().focusOutEvent(event)

    def _accept_suggestion(self):
        """接受当前的补全建议"""
        if not self.suggestion_active or not self.current_suggestion:
            return

        try:
            cursor = self.textCursor()

            current_format = cursor.charFormat()

            normal_format = QTextCharFormat()
            normal_format.setForeground(self.normal_color)

            cursor.setCharFormat(normal_format)

            cursor.insertText(self.current_suggestion)

            context = self.toPlainText()[: self.suggestion_start_pos]
            self.completion_history.append(
                {"context": context, "completion": self.current_suggestion}
            )

            if len(self.completion_history) > self.max_history_size:
                self.completion_history.pop(0)

        finally:
            self._clear_suggestion()

    def _is_similar_context(self, context1, context2):
        """检查两个上下文是否相似"""
        if not context1 or not context2:
            return False

        last_chars1 = context1[-50:] if len(context1) > 50 else context1
        last_chars2 = context2[-50:] if len(context2) > 50 else context2

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

        max_length = max(len(last_chars1), len(last_chars2))
        if max_length == 0:
            return False

        distance = levenshtein_distance(last_chars1, last_chars2)
        similarity = 1 - (distance / max_length)

        return similarity > 0.8

    def _update_timer_interval(self, seconds):
        """
        更新计时器延迟时间
        @param seconds: 延迟秒数
        """
        milliseconds = int(seconds * 1000)  
        self.suggestion_timer.setInterval(milliseconds)
