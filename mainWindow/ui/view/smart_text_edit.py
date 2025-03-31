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
            # 在提示词中明确指出不要重复最后的内容
            last_chars = self.text[-50:] if len(self.text) > 50 else self.text
            context = f"{self.text}\n[请续写内容，不要重复最后的文本：{last_chars}]"

            # 使用tab续写模式
            result = self.ai_service.generate_content(context, "tab续写")

            # 检查结果是否重复了最后的内容
            if result and last_chars and result.startswith(last_chars):
                result = result[len(last_chars) :]

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
            result = self.ai_service.generate_content(self.context, "tab续写")
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
        self.is_composing = False
        self.suggestion_thread = None
        self.is_showing_suggestion = False

        # 设置颜色
        self.normal_color = self.palette().text().color()
        self.suggestion_color = QColor(169, 169, 169)  # 浅灰色

        # 使用 QTimer 并从配置中获取延迟时间（将秒转换为毫秒）
        self.suggestion_timer = QTimer(self)
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.timeout.connect(self._request_suggestion)
        self._update_timer_interval(cfg.get(cfg.completionTime))  # 初始化时设置延迟时间

        # 监听配置变化
        cfg.completionTime.valueChanged.connect(self._update_timer_interval)

        # 设置建议文本的格式
        self.suggestion_format = QTextCharFormat()
        self.suggestion_format.setForeground(self.suggestion_color)

        # 添加补全历史缓存
        self.completion_history = []
        self.max_history_size = 5

        # 连接光标位置变化信号
        self.cursorPositionChanged.connect(self._on_cursor_position_changed)

        # 确保线程安全退出
        self.destroyed.connect(self._cleanup_threads)

    def _cleanup_threads(self):
        """清理线程资源"""
        if self.suggestion_thread and self.suggestion_thread.isRunning():
            self.suggestion_thread.terminate()
            self.suggestion_thread.wait()

    def inputMethodEvent(self, event):
        """处理输入法事件"""
        # 更新输入法组合状态
        self.is_composing = event.preeditString() != ""

        # 如果正在输入，清除当前建议
        if self.is_composing and self.suggestion_active:
            self._clear_suggestion()
            self.suggestion_timer.stop()  # 停止建议计时器

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
        # 检查是否启用了自动补全
        self.auto_completion_enabled = cfg.get(cfg.enableAutoCompletion)

        if not self.auto_completion_enabled:
            # 如果禁用了自动补全，清除当前建议并返回
            self._clear_suggestion()
            return

        if self.is_showing_suggestion or self.is_composing:
            return

        # 取消当前的建议
        self._clear_suggestion()
        # 启动计时器（使用已设置的延迟时间）
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

        # 使用新线程前终止旧线程
        if self.suggestion_thread and self.suggestion_thread.isRunning():
            self.suggestion_thread.terminate()
            self.suggestion_thread.wait()

        try:
            self.suggestion_thread = SuggestionThread(self.ai_service, context)
            self.suggestion_thread.suggestionReady.connect(self._handle_suggestion)
            self.suggestion_thread.start()
        except Exception as e:
            print(f"创建建议线程失败: {str(e)}")

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

        # 获取当前光标
        cursor = self.textCursor()
        position = cursor.position()

        # 设置建议状态
        self.suggestion_start_pos = position
        self.current_suggestion = suggestion
        self.suggestion_active = True

        # 显示建议
        self.viewport().update()  # 触发重绘

    def _show_suggestion(self):
        """显示建议文本"""
        if not self.suggestion_active or not self.current_suggestion:
            return

        # 触发重绘来显示建议文本
        self.viewport().update()

    def paintEvent(self, event):
        """重写绘制事件以显示建议文本"""
        super().paintEvent(event)

        if self.suggestion_active and self.current_suggestion:
            painter = QPainter(self.viewport())
            cursor = self.textCursor()

            # 获取当前光标位置的矩形区域
            rect = self.cursorRect(cursor)

            # 设置字体和颜色
            painter.setFont(self.font())
            painter.setPen(self.suggestion_color)

            # 获取视口宽度和左边距
            viewport_width = self.viewport().width()
            document_margin = self.document().documentMargin()

            # 计算文本位置 - 转换为整数
            first_line_x = int(rect.x())  # 第一行从光标位置开始
            subsequent_line_x = int(document_margin)  # 后续行从左边距开始
            y = int(rect.y() + painter.fontMetrics().ascent())

            # 计算每行最大字符数
            font_metrics = painter.fontMetrics()
            first_line_max_width = (
                viewport_width - first_line_x - 20
            )  # 第一行留出右边距
            subsequent_line_max_width = (
                viewport_width - subsequent_line_x - 20
            )  # 后续行留出右边距

            # 处理建议文本的换行显示
            suggestion_lines = []
            current_line = ""
            is_first_line = True

            for char in self.current_suggestion:
                test_line = current_line + char
                max_width = (
                    first_line_max_width if is_first_line else subsequent_line_max_width
                )

                # 如果添加这个字符会超出宽度，或者是换行符
                if (
                    font_metrics.horizontalAdvance(test_line) > max_width
                    or char == "\n"
                ):
                    suggestion_lines.append((current_line, is_first_line))
                    current_line = "" if char == "\n" else char
                    is_first_line = False
                else:
                    current_line += char

            # 添加最后一行
            if current_line:
                suggestion_lines.append((current_line, is_first_line))

            # 限制显示的行数，避免遮挡太多内容
            max_lines = 5
            if len(suggestion_lines) > max_lines:
                suggestion_lines = suggestion_lines[:max_lines]
                suggestion_lines[-1] = (
                    suggestion_lines[-1][0] + "...",
                    suggestion_lines[-1][1],
                )

            # 绘制每一行建议文本
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

        # 触发重绘以清除建议文本
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
        # 如果正在输入中文，不处理建议相关的按键
        if self.is_composing:
            super().keyPressEvent(event)
            return

        if self.suggestion_active and self.current_suggestion:
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

        # 处理实际的按键输入
        super().keyPressEvent(event)

        # 确保新输入的文本使用正常颜色
        cursor = self.textCursor()
        format = cursor.charFormat()
        format.setForeground(self.normal_color)
        cursor.mergeCharFormat(format)

        # 如果不是特殊键，重置建议计时器
        if event.key() not in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
            self.suggestion_timer.start()  # 使用已设置的延迟时间
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
            # 获取当前光标
            cursor = self.textCursor()

            # 保存当前的格式
            current_format = cursor.charFormat()

            # 创建一个新的格式，使用正常颜色
            normal_format = QTextCharFormat()
            normal_format.setForeground(self.normal_color)

            # 应用正常颜色格式
            cursor.setCharFormat(normal_format)

            # 插入建议文本
            cursor.insertText(self.current_suggestion)

            # 记录这次补全的上下文和结果
            context = self.toPlainText()[: self.suggestion_start_pos]
            self.completion_history.append(
                {"context": context, "completion": self.current_suggestion}
            )

            # 限制历史记录大小
            if len(self.completion_history) > self.max_history_size:
                self.completion_history.pop(0)

        finally:
            self._clear_suggestion()

    def _is_similar_context(self, context1, context2):
        """检查两个上下文是否相似"""
        # 如果任一字符串为空，返回False
        if not context1 or not context2:
            return False

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

        # 计算最大长度，如果为0则返回False
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
        milliseconds = int(seconds * 1000)  # 将秒转换为毫秒
        self.suggestion_timer.setInterval(milliseconds)
