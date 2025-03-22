import os
from PyQt5.QtCore import QObject, pyqtSignal


class AIService(QObject):
    # 定义信号，用于通知 UI 线程 AI 处理结果
    resultReady = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 从环境变量获取 API 密钥
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "your_api_key")
        self.client = None

        # 如果有 API 密钥，初始化 OpenAI 客户端
        if self.api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(
                    api_key=self.api_key, base_url="https://api.deepseek.com"
                )
            except ImportError:
                print("请先安装 OpenAI SDK: pip install openai")

    def generate_content(self, prompt, mode="generate"):
        """
        根据提示生成内容

        参数:
        - prompt: 用户输入的提示或要处理的文本
        - mode: 处理模式，可以是 "generate"(生成), "polish"(润色), "continue"(续写)

        返回:
        - 生成的文本内容
        """
        try:
            # 根据不同模式构建不同的提示词
            if mode == "润色":
                system_prompt = "你是一位文学编辑，请润色以下文本，使其更加优美流畅，但保持原意不变："
                full_prompt = f"{system_prompt}\n\n{prompt}"
            elif mode == "续写":
                system_prompt = "请基于以下文本继续写作，保持风格一致："
                full_prompt = f"{system_prompt}\n\n{prompt}"
            elif mode == "朋友圈文案":
                system_prompt = "请为我创作一段朋友圈文案，内容积极向上，有文艺气息："
                full_prompt = system_prompt
            elif mode == "一句诗":
                system_prompt = "请为我写一句富有诗意的句子，可以是原创的："
                full_prompt = system_prompt
            elif mode == "自定义":
                system_prompt = "你是一个有用的助手，擅长文字创作和润色。"
                full_prompt = prompt
            else:  # 默认生成模式
                system_prompt = "你是一个有用的助手，擅长文字创作和润色。"
                full_prompt = prompt

            if not self.client:
                raise Exception("API 客户端未初始化，请检查API密钥配置")

            response = self._call_deepseek_api(full_prompt, system_prompt)
            self.resultReady.emit(response)
            return response

        except Exception as e:
            error_msg = f"AI 处理出错: {str(e)}"
            self.errorOccurred.emit(error_msg)
            return error_msg

    def _call_deepseek_api(
        self, prompt, system_prompt="你是一个有用的助手，擅长文字创作和润色。"
    ):
        """使用 OpenAI SDK 调用 DeepSeek API"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                stream=False,
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"API 调用出错: {str(e)}")
