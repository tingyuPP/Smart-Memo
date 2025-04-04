# coding:utf-8
from PyQt5.QtCore import QThread, pyqtSignal


class AIWorkerThread(QThread):
    """处理AI内容生成的工作线程"""

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

    chunkReceived = pyqtSignal(str)  # 收到文本块时发出
    finished = pyqtSignal()  # 完成时发出
    error = pyqtSignal(str)  # 错误时发出

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

            full_response = ""

            # 处理每个响应块
            for chunk in stream:
                # 检查是否请求停止
                if self._stop_requested:
                    break

                # 提取内容
                if hasattr(chunk.choices[0].delta, "content"):
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        self.chunkReceived.emit(content)

            # 如果未请求停止，发出完成信号
            if not self._stop_requested:
                self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        """请求停止流式响应处理"""
        self._stop_requested = True
