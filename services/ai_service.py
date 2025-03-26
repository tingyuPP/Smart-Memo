import os
from PyQt5.QtCore import QObject, pyqtSignal, QThread

class AIService(QObject):
    # 定义信号，用于通知 UI 线程 AI 处理结果
    resultReady = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)
    
    # 定义 AI 模式配置
    AI_MODES = {
        "润色": {
            "display_name": "润色笔记",
            "description": "AI 将对您的备忘录内容进行润色，使其更加清晰、专业，同时保持原意不变。",
            "system_prompt": "你是一位专业的文字编辑，擅长优化笔记和备忘录内容。请润色以下文本，使其更加清晰、结构化和易于理解，同时保持原意不变。可以改进表达方式，纠正语法错误，优化段落结构，但不要添加新的信息或改变核心内容。直接输出润色后的文本，不要添加任何解释、前言或结语。"
        },
        "续写": {
            "display_name": "扩展笔记",
            "description": "AI 将基于您的备忘录内容进行扩展，补充相关细节和想法。",
            "system_prompt": "你是一位专业的内容创作者，擅长扩展和丰富笔记内容。请基于以下已有内容续写后续内容，保持风格一致。扩展内容应当与原文自然衔接，有逻辑性。请不要偏离原始主题，确保扩展内容与原始备忘录的目的一致。直接输出续写的内容，不要添加任何解释、前言或结语。严格避免重复用户已有的文本，只输出新增的内容。"
        },
        "朋友圈文案": {
            "display_name": "社交分享版本",
            "description": "AI 将基于您的备忘录内容，创作一段适合分享到社交媒体的精简版本。",
            "system_prompt": "你是一位社交媒体内容专家。文案应当保留原始内容的核心信息，但更加生动有趣，字数控制在100字以内。如果没有提供备忘录内容，请创作一段积极向上、富有启发性的短文案，适合日常分享。只输出最终文案内容，不要添加任何解释、前言或结语。"
        },
        "一句诗": {
            "display_name": "诗意总结",
            "description": "AI 将为您的备忘录创作一句富有诗意的总结或标题。",
            "system_prompt": "你是一位擅长文字凝练的诗人。请为以下备忘录内容创作一句富有诗意的总结句或标题，能够捕捉内容的核心精神或主题。这句话应当简洁优美，富有意境，可以作为备忘录的点睛之笔或灵感来源。如果没有提供备忘录内容，请创作一句关于思考、记录或生活感悟的诗意句子。只输出这一句话，不要添加任何解释、前言或结语。"
        },
        "自定义": {
            "display_name": "自定义助手",
            "description": "请输入您的提示词，AI 将根据您的要求处理备忘录内容。",
            "system_prompt": "你是一个专业的备忘录助手，擅长帮助用户处理和优化各类笔记内容。请根据用户的提示词处理相关内容，注重实用性和清晰度。你的回答应当简洁明了，便于用户在备忘录中使用。只输出最终处理后的内容，不要添加任何解释、前言或结语。如果用户的指令不明确，请尽量理解用户的意图，提供最有帮助的回应。"
        },
        "tab续写": {
            "display_name": "智能续写",
            "description": "根据当前输入智能续写内容",
            "system_prompt": "你是一位专业的文字助手。请根据用户提供的文本片段，续写后续内容。续写应当简短（不超过30个字），自然衔接，保持风格一致。严格避免重复用户已有的文本，只输出全新的内容。不要添加任何解释。"
        }
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从环境变量获取 API 密钥
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "sk-a4b80e93111b4425bf0a42ffd4e58b43")
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

    def generate_content(self, prompt, mode="generate", aux_prompt=""):
        """
        根据提示生成内容

        参数:
        - prompt: 用户输入的提示或要处理的文本
        - mode: 处理模式，可以是 "generate"(生成), "polish"(润色), "continue"(续写)
        - aux_prompt: 用户输入的辅助提示词（可选）

        返回:
        - 生成的文本内容
        """
        try:
            # 获取模式配置
            mode_config = self.AI_MODES.get(mode, self.AI_MODES.get("自定义"))
            system_prompt = mode_config["system_prompt"]
            
            if mode == "tab续写":
                # tab续写模式保持不变
                sentences = prompt.split('。')
                context = '。'.join(sentences[-3:-1]) + '。' if len(sentences) > 2 else prompt
                system_prompt = "你是一位专业的文字助手。请根据以下文本上下文续写内容。要求：1. 续写内容必须与上文自然衔接；2. 严格避免重复已有的句子和表达；3. 保持相同的写作风格；4. 生成内容简短（不超过30字）。只输出续写的内容，不要重复已有文本，不要添加任何解释。"
                full_prompt = f"上文内容：{context}\n请续写："
            else:
                # 处理其他模式，加入辅助提示词
                if aux_prompt:
                    if mode == "续写":
                        full_prompt = f"{system_prompt}\n\n已有内容：\n{prompt}\n\n额外要求：{aux_prompt}"
                    elif mode == "润色":
                        full_prompt = f"{system_prompt}\n\n需要润色的内容：\n{prompt}\n\n额外要求：{aux_prompt}"
                    elif mode in ["朋友圈文案", "一句诗"]:
                        full_prompt = f"{system_prompt}\n\n备忘录内容：{prompt}\n\n额外要求：{aux_prompt}"
                    else:  # 自定义模式
                        full_prompt = f"{prompt}\n\n额外要求：{aux_prompt}"
                else:
                    # 没有辅助提示词时保持原有逻辑
                    if mode == "续写":
                        full_prompt = f"{system_prompt}\n\n已有内容：\n{prompt}"
                    elif mode == "润色":
                        full_prompt = f"{system_prompt}\n\n{prompt}"
                    elif mode in ["朋友圈文案", "一句诗"]:
                        full_prompt = f"{system_prompt}\n\n备忘录内容：{prompt}"
                    else:  # 自定义模式
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

    def _call_deepseek_api_stream(self, prompt, system_prompt="你是一个有用的助手，擅长文字创作和润色。"):
        """使用流式响应调用 DeepSeek API"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # 创建流式响应
            stream = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                stream=True  # 启用流式响应
            )
            
            return stream
        
        except Exception as e:
            raise Exception(f"API 流式调用出错: {str(e)}")

    def generate_content_stream(self, prompt, mode="generate", aux_prompt=""):
        """
        使用流式响应生成内容
        
        参数:
        - prompt: 用户输入的提示或要处理的文本
        - mode: 处理模式
        - aux_prompt: 用户输入的辅助提示词（可选）
        
        返回:
        - 流式响应对象
        """
        try:
            # 获取模式配置
            mode_config = self.AI_MODES.get(mode, self.AI_MODES.get("自定义"))
            system_prompt = mode_config["system_prompt"]
            
            # 构建完整提示词
            if mode == "续写":
                full_prompt = f"{system_prompt}\n\n已有内容：\n{prompt}"
                if aux_prompt:
                    full_prompt += f"\n\n额外要求：{aux_prompt}"
                full_prompt += "\n\n请续写（不要重复上面的内容）："
            elif mode == "润色":
                full_prompt = f"{system_prompt}\n\n{prompt}"
                if aux_prompt:
                    full_prompt += f"\n\n额外要求：{aux_prompt}"
            elif mode in ["朋友圈文案", "一句诗"]:
                full_prompt = f"{system_prompt}\n\n备忘录内容：{prompt}"
                if aux_prompt:
                    full_prompt += f"\n\n额外要求：{aux_prompt}"
            else:  # 自定义模式
                full_prompt = prompt
            
            if not self.client:
                raise Exception("API 客户端未初始化，请检查API密钥配置")
                
            return self._call_deepseek_api_stream(full_prompt, system_prompt)
        
        except Exception as e:
            error_msg = f"AI 流式处理出错: {str(e)}"
            self.errorOccurred.emit(error_msg)
            raise Exception(error_msg)

class AIWorkerThread(QThread):
    """统一的AI工作线程"""
    resultReady = pyqtSignal(str)  # 用于普通响应
    chunkReceived = pyqtSignal(str)  # 用于流式响应
    finished = pyqtSignal()  # 流式响应完成信号
    error = pyqtSignal(str)
    
    def __init__(self, ai_service, mode, text, streaming=False):
        super().__init__()
        self.ai_service = ai_service
        self.mode = mode
        self.text = text
        self.streaming = streaming
        self._stop_requested = False
    
    def run(self):
        try:
            if self.streaming:
                stream = self.ai_service.generate_content_stream(self.text, self.mode)
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
            else:
                result = self.ai_service.generate_content(self.text, self.mode)
                self.resultReady.emit(result)
                
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        self._stop_requested = True
