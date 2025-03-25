import re
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextCharFormat, QColor, QFont
from qfluentwidgets import TextEdit


class MarkdownTextEdit(TextEdit):
    """
    实现类似Typora的Markdown实时预览编辑器
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置基本属性
        self.setAcceptRichText(True)
        self.setUndoRedoEnabled(True)

        # 创建一个定时器用于延迟渲染
        self.render_timer = QTimer()
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self.render_markdown)

        # 连接信号
        self.textChanged.connect(self.on_text_changed)

        # 设置一些标志
        self._is_rendering = False
        self._current_cursor_position = 0

        # 添加基础样式
        self.document().setDefaultStyleSheet(
            """
            h1, h2, h3, h4, h5, h6 { 
                color: #0066cc;
                margin-top: 12px;
                margin-bottom: 12px;
            }
            h1 { font-size: 24px; }
            h2 { font-size: 22px; }
            h3 { font-size: 20px; }
            h4 { font-size: 18px; }
            h5 { font-size: 16px; }
            h6 { font-size: 14px; }
            code {
                background-color: #f1f1f1;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: Consolas, monospace;
            }
            pre {
                background-color: #f5f5f5;
                padding: 8px;
                border-radius: 5px;
                overflow-x: auto;
            }
            blockquote {
                margin-left: 20px;
                padding-left: 10px;
                border-left: 3px solid #ccc;
                color: #555;
            }
            img {
                max-width: 100%;
            }
            a {
                color: #0066cc;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            ul, ol {
                margin-left: 20px;
            }
        """
        )

    def on_text_changed(self):
        """文本更改时启动渲染定时器"""
        if not self._is_rendering:
            self._current_cursor_position = self.textCursor().position()
            self.render_timer.start(500)  # 延迟500毫秒渲染，避免频繁渲染

    def render_markdown(self):
        """渲染Markdown内容"""
        if self._is_rendering:
            return

        self._is_rendering = True

        # 保存当前光标位置
        cursor_position = self.textCursor().position()

        # 获取纯文本
        markdown_text = self.toPlainText()

        # 将Markdown转换为HTML (使用python-markdown库)
        try:
            import markdown

            html_content = markdown.markdown(
                markdown_text,
                extensions=[
                    "extra",  # 包含表格等扩展
                    "codehilite",  # 代码高亮
                    "nl2br",  # 换行转换为<br>
                    "sane_lists",  # 更智能的列表处理
                ],
            )

            # 使用setHtml会重置所有内容，所以我们需要保存和恢复光标位置
            self.setHtml(html_content)

            # 恢复光标位置
            cursor = self.textCursor()
            cursor.setPosition(min(cursor_position, len(self.toPlainText())))
            self.setTextCursor(cursor)

        except ImportError:
            # 如果没有markdown库，使用基本的正则表达式替换
            html_content = self._basic_markdown_to_html(markdown_text)
            self.setHtml(html_content)

        self._is_rendering = False

    def _basic_markdown_to_html(self, text):
        """基本的Markdown到HTML转换（不依赖外部库）"""
        # 这是一个简化版本，仅支持基本的Markdown语法

        # 转义HTML字符
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 标题
        text = re.sub(r"^# (.*?)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.*?)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
        text = re.sub(r"^### (.*?)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)

        # 粗体和斜体
        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)

        # 列表
        text = re.sub(r"^- (.*?)$", r"<ul><li>\1</li></ul>", text, flags=re.MULTILINE)

        # 链接
        text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', text)

        # 代码块
        text = re.sub(
            r"```(.*?)```", r"<pre><code>\1</code></pre>", text, flags=re.DOTALL
        )

        # 行内代码
        text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)

        # 引用
        text = re.sub(
            r"^> (.*?)$", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE
        )

        # 水平线
        text = re.sub(r"^---$", r"<hr>", text, flags=re.MULTILINE)

        # 段落
        text = re.sub(r"([^\n])\n([^\n])", r"\1<br>\2", text)

        return text

    def keyPressEvent(self, event):
        """处理按键事件"""
        super().keyPressEvent(event)
        # 根据需要可添加特殊按键处理
