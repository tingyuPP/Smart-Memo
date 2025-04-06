import os
import traceback
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from config import cfg  # 导入配置


class AIService(QObject):
    resultReady = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)

    # 模型配置
    MODEL_CONFIGS = {
        "deepseek-chat": {
            "display_name": "DeepSeek-V3",
            "base_url": "https://api.deepseek.com/v1",
            "max_tokens": 4096,
            "provider": "deepseek",
            "description": "DeepSeek 通用对话模型，支持中英双语",
            "model_id": "deepseek-chat",
        },
        "gpt-4o": {
            "display_name": "GPT-4o",
            "base_url": "https://api.openai.com/v1",
            "max_tokens": 8192,
            "provider": "openai",
            "description": "OpenAI最强大的模型",
            "model_id": "gpt-4o",
        },
        "glm-4-flash": {
            "display_name": "GLM-4-Flash",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "max_tokens": 4096,
            "provider": "zhipuai",
            "description": "GLM-4-Flash，支持中英双语",
            "model_id": "glm-4-flash",
        },
        "custom": {
            "display_name": "自定义模型",
            "base_url": "",  # 用户自定义
            "max_tokens": 4096,
            "provider": "custom",
            "description": "自定义API设置",
            "model_id": "",  # 用户自定义
        },
    }

    # 定义 AI 模式配置
    AI_MODES = {
        "润色": {
            "display_name":
            "润色笔记",
            "description":
            "AI 将对您的备忘录内容进行润色，使其更加清晰、专业，同时保持原意不变。",
            "system_prompt":
            "你是一位专业的文字编辑，擅长优化笔记和备忘录内容。请润色以下文本，使其更加清晰、结构化和易于理解，同时保持原意不变。可以改进表达方式，纠正语法错误，优化段落结构，但不要添加新的信息或改变核心内容。直接输出润色后的文本，不要添加任何解释、前言或结语。",
        },
        "续写": {
            "display_name":
            "扩展笔记",
            "description":
            "AI 将基于您的备忘录内容进行扩展，补充相关细节和想法。",
            "system_prompt":
            """你是一位专业的内容创作者，擅长扩展和丰富笔记内容。你的任务是续写文本，必须遵循以下规则：

1. 从用户文本的末尾处开始续写
2. 严格禁止重复用户已写的任何内容
3. 只输出全新的续写部分
4. 保持文风一致，自然衔接
5. 不要添加任何解释或说明

重要：你的输出中绝对不能包含任何与用户文本重复的片段。""",
        },
        "朋友圈文案": {
            "display_name":
            "社交分享版本",
            "description":
            "AI 将基于您的备忘录内容，创作一段适合分享到社交媒体的精简版本。",
            "system_prompt":
            "你是一位社交媒体内容专家。文案应当保留原始内容的核心信息，但更加生动有趣，字数控制在100字以内。如果没有提供备忘录内容，请创作一段积极向上、富有启发性的短文案，适合日常分享。只输出最终文案内容，不要添加任何解释、前言或结语。",
        },
        "一句诗": {
            "display_name":
            "诗意总结",
            "description":
            "AI 将为您的备忘录创作一句富有诗意的总结或标题。",
            "system_prompt":
            "你是一位擅长文字凝练的诗人。请为以下备忘录内容创作一句富有诗意的总结句或标题，能够捕捉内容的核心精神或主题。这句话应当简洁优美，富有意境，可以作为备忘录的点睛之笔或灵感来源。如果没有提供备忘录内容，请创作一句关于思考、记录或生活感悟的诗意句子。只输出这一句话，不要添加任何解释、前言或结语。",
        },
        "自定义": {
            "display_name":
            "自定义助手",
            "description":
            "请输入您的提示词，AI 将根据您的要求处理备忘录内容。",
            "system_prompt":
            "你是一个专业的备忘录助手，擅长帮助用户处理和优化各类笔记内容。请根据用户的提示词处理相关内容，注重实用性和清晰度。你的回答应当简洁明了，便于用户在备忘录中使用。只输出最终处理后的内容，不要添加任何解释、前言或结语。如果用户的指令不明确，请尽量理解用户的意图，提供最有帮助的回应。",
        },
        "tab续写": {
            "display_name":
            "智能续写",
            "description":
            "根据当前输入智能续写内容",
            "system_prompt":
            "你是一位专业的文字助手。请根据用户提供的文本片段，续写后续内容。续写应当简短（不超过30个字），自然衔接，保持风格一致。严格避免重复用户已有的文本，只输出全新的内容。不要添加任何解释。",
        },
        "待办提取": {
            "display_name":
            "提取待办事项",
            "description":
            "AI 将分析备忘录内容，识别并提取其中的待办事项",
            "system_prompt":
            """你是一位专业的任务管理助手。请分析以下文本内容，识别其中可能的待办事项。
待办事项通常包含需要完成的任务，可能有截止日期。

对于每个识别出的待办事项，请提供以下信息：
1. 任务内容
2. 截止日期（如果有）
3. 任务类别（如果能推断出）

关于截止日期的智能推断：
- 如果文本中明确提到了具体时间（如"18:00"、"下午3点"等），请使用该时间
- 对于相对时间表达，请特别注意：
  * "下周"、"下个星期"表示从当前日期算起的下一个星期
  * "下个月"表示从当前日期算起的下一个月
  * "明年"表示从当前日期算起的下一年
  * 例如，如果今天是2025-03-31（星期一），那么：
    - "下周三"应该是2025-04-09，而不是本周三（2025-04-02）
    - "下个月15日"应该是2025-04-15，而不是本月15日
- 请务必正确解析"今日"、"明日"、"后天"、"下周"、"下个月"等相对时间表达
- 请使用"YYYY-MM-DD HH:MM"格式返回日期和时间
- 重要：如果任务明显是当天的事情（如吃饭、散步等），请使用当天日期，而不是未来日期

关于类别的智能推断：
- 系统只支持以下四种类别，请务必从这四个类别中选择一个：
  * "工作" - 适用于工作相关任务，如会议、报告、项目等
  * "学习" - 适用于学习相关任务，如读书、课程、考试等
  * "生活" - 适用于日常生活任务，如饮食、购物、家务、运动、健身等
  * "其他" - 适用于不属于以上三类的任务
- 请确保category字段只使用以上四个值之一

请以JSON数组格式返回结果，格式为：
[
  {
    "task": "任务内容",
    "deadline": "YYYY-MM-DD HH:MM",
    "category": "类别"  // 必须是"工作"、"学习"、"生活"或"其他"之一
  }
]

如果实在无法推断截止日期，请将deadline设为null。
如果没有识别出任何待办事项，请返回空数组 []。""",
        },
    }

    def __init__(self):
        super().__init__()

        self._memory_context = ""
        self._max_memory_tokens = 2000

        self.api_key = cfg.get(cfg.apiKey)

        self.client = None
        self._init_api_client()

    def _init_api_client(self):
        """初始化API客户端"""
        try:
            api_key = cfg.get(cfg.apiKey)
            self.api_key = api_key
            if not api_key:
                self.client = None
                return

            model = cfg.get(cfg.aiModel)

            if model == "deepseek-chat":
                from openai import OpenAI

                self.client = OpenAI(api_key=api_key,
                                     base_url="https://api.deepseek.com/v1")
            elif model == "gpt-4o":
                from openai import OpenAI

                self.client = OpenAI(api_key=api_key)
            elif model == "glm-4-flash":
                from zhipuai import ZhipuAI

                self.client = ZhipuAI(api_key=api_key)
            elif model == "custom":
                from openai import OpenAI

                base_url = cfg.get(cfg.customBaseUrl)
                if not base_url:
                    self.client = None
                    return
                self.client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                self.client = None

        except Exception as e:
            import traceback

            traceback.print_exc()
            self.client = None

    def _get_base_url(self, model):
        """根据模型返回对应的 API 基础 URL"""
        config = self.MODEL_CONFIGS.get(model)
        if config:
            return config["base_url"]
        return "https://api.deepseek.com/v1"

    def _get_max_tokens(self, model):
        """获取模型的最大 token 限制"""
        config = self.MODEL_CONFIGS.get(model)
        if config:
            return config["max_tokens"]
        return 4096

    def build_memory_context(self, user_id, db):
        """构建用户的记忆上下文"""
        try:
            memos = db.get_all_memos_by_user(user_id)

            if not memos:
                self._memory_context = ""
                return

            context_parts = []

            for memo in memos:
                memo_id = memo["id"]
                title = memo["title"]
                content = memo["content"]
                category = memo["category"]

                memo_context = f"标题: {title}\n分类: {category}\n内容: {content}\n"
                context_parts.append(memo_context)

            max_context_length = 4000
            combined_context = "\n---\n".join(context_parts)

            if len(combined_context) > max_context_length:
                truncated_parts = []
                current_length = 0

                for part in reversed(context_parts):
                    if current_length + len(part) <= max_context_length:
                        truncated_parts.insert(0, part)
                        current_length += len(part)
                    else:
                        break

                combined_context = "\n---\n".join(truncated_parts)

        except Exception as e:
            import traceback

            print(traceback.format_exc())
            self._memory_context = ""

    def _get_enhanced_prompt(self, mode, user_prompt, aux_prompt=""):
        """获取增强的提示词，统一处理所有模式的记忆上下文"""
        mode_config = self.AI_MODES.get(mode, self.AI_MODES.get("自定义"))
        system_prompt = mode_config["system_prompt"]

        if mode == "续写":
            enhanced_prompt = f"{system_prompt}\n\n已有内容：\n{user_prompt}"
            if aux_prompt:
                enhanced_prompt += f"\n\n额外要求：{aux_prompt}"
            enhanced_prompt += "\n\n请续写（不要重复上面的内容）："
        elif mode == "润色":
            enhanced_prompt = f"{system_prompt}\n\n{user_prompt}"
            if aux_prompt:
                enhanced_prompt += f"\n\n额外要求：{aux_prompt}"
        elif mode in ["朋友圈文案", "一句诗"]:
            enhanced_prompt = f"{system_prompt}\n\n备忘录内容：{user_prompt}"
            if aux_prompt:
                enhanced_prompt += f"\n\n额外要求：{aux_prompt}"
        elif mode == "tab续写":
            enhanced_prompt = f"{system_prompt}\n\n已有内容：\n{user_prompt}\n\n请续写（不要重复上面的内容）："
        else:
            enhanced_prompt = f"{system_prompt}\n\n{user_prompt}"

        if hasattr(self, "_memory_context") and self._memory_context:
            memory_prompt = f"""
            以下是用户之前创建的备忘录内容，你可以参考这些内容来更好地理解用户的需求和风格:
            
            {self._memory_context}
            
            请基于以上内容，更好地理解用户的风格和偏好。在大多数情况下，不要直接引用这些内容。
但如果用户明确要求引用或者上下文高度相关时，可以适当引用，但需要明确指出这是来自用户之前的笔记。
            """
            enhanced_prompt = f"{memory_prompt}\n\n{enhanced_prompt}"

        return enhanced_prompt

    def process_with_ai(self, mode, prompt):
        """处理AI请求"""
        try:
            full_prompt = self._get_enhanced_prompt(mode, prompt)
            response = self._call_deepseek_api(full_prompt)
            return response

        except Exception as e:
            raise Exception(f"AI 处理出错: {str(e)}")

    def generate_content(self, prompt, mode="generate", aux_prompt=""):
        """生成内容"""
        try:
            self._init_api_client()

            if not self.client:
                error_msg = "AI服务未初始化，请在设置中配置有效的API密钥"
                self.errorOccurred.emit(error_msg)
                return error_msg

            mode_config = self.AI_MODES.get(mode, self.AI_MODES.get("自定义"))
            system_prompt = mode_config["system_prompt"]

            if hasattr(self, "_memory_context"):
                if self._memory_context:
                    memory_prompt = f"""
以下是用户之前创建的备忘录内容，你可以参考这些内容来更好地理解用户的需求和风格:

{self._memory_context}

请基于以上内容，更好地理解用户的风格和偏好。在大多数情况下，不要直接引用这些内容。
但如果用户明确要求引用或者上下文高度相关时，可以适当引用，但需要明确指出这是来自用户之前的笔记。
"""
                    system_prompt = f"{memory_prompt}\n\n{system_prompt}"

            if mode == "续写":
                full_prompt = f"{prompt}"
                if aux_prompt:
                    full_prompt += f"\n\n额外要求：{aux_prompt}"
            elif mode == "润色":
                full_prompt = f"{prompt}"
                if aux_prompt:
                    full_prompt += f"\n\n额外要求：{aux_prompt}"
            elif mode in ["朋友圈文案", "一句诗"]:
                full_prompt = f"备忘录内容：{prompt}"
                if aux_prompt:
                    full_prompt += f"\n\n额外要求：{aux_prompt}"
            else:
                full_prompt = prompt

            model = cfg.get(cfg.aiModel)
            model_config = self.MODEL_CONFIGS.get(model, {})

            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": full_prompt})

            model_id = model_config.get("model_id") if model_config else model

            response = self.client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.7,
                max_tokens=self._get_max_tokens(model),
            )

            generated_content = response.choices[0].message.content

            return generated_content

        except Exception as e:
            error_msg = f"AI处理出错: {str(e)}"
            self.errorOccurred.emit(error_msg)
            return error_msg

    def _call_deepseek_api(self, prompt, system_prompt="你是一个有用的助手，擅长文字创作和润色。"):
        """调用 AI API"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ]

            model = cfg.get(cfg.aiModel)
            model_config = self.MODEL_CONFIGS.get(model)

            model_id = model_config.get("model_id") if model_config else model

            response = self.client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.7,
                max_tokens=self._get_max_tokens(model),
                stream=False,
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"API 调用出错: {str(e)}")

    def _call_deepseek_api_stream(self, prompt, system_prompt=""):
        """调用DeepSeek API进行流式响应

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            流式响应对象
        """
        try:
            model = cfg.get(cfg.aiModel)
            model_config = self.MODEL_CONFIGS.get(model, {})

            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            model_id = model_config.get("model_id") if model_config else model

            stream = self.client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.7,
                max_tokens=self._get_max_tokens(model),
                stream=True,
            )

            return stream

        except Exception as e:
            raise Exception(f"API 流式调用出错: {str(e)}")

    def generate_content_stream(self, prompt, mode="generate", aux_prompt=""):
        """使用流式响应生成内容，适用于实时显示生成过程"""
        try:
            mode_config = self.AI_MODES.get(mode, self.AI_MODES.get("自定义"))
            system_prompt = mode_config["system_prompt"]

            if hasattr(self, "_memory_context") and self._memory_context:
                memory_prompt = f"""
以下是用户之前创建的备忘录内容，你可以参考这些内容来更好地理解用户的需求和风格:

{self._memory_context}

请基于以上内容，更好地理解用户的风格和偏好。在大多数情况下，不要直接引用这些内容。
但如果用户明确要求引用或者上下文高度相关时，可以适当引用，但需要明确指出这是来自用户之前的笔记。
"""
                system_prompt = f"{memory_prompt}\n\n{system_prompt}"

            if mode == "续写":
                full_prompt = f"{prompt}"
                if aux_prompt:
                    full_prompt += f"\n\n额外要求：{aux_prompt}"
            elif mode == "润色":
                full_prompt = f"{prompt}"
                if aux_prompt:
                    full_prompt += f"\n\n额外要求：{aux_prompt}"
            elif mode in ["朋友圈文案", "一句诗"]:
                full_prompt = f"备忘录内容：{prompt}"
                if aux_prompt:
                    full_prompt += f"\n\n额外要求：{aux_prompt}"
            else:
                full_prompt = prompt

            if not self.client:
                self._init_api_client()

            if not self.client:
                raise Exception("API 客户端未初始化，请检查API密钥配置")

            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": full_prompt})

            model = cfg.get(cfg.aiModel)
            model_config = self.MODEL_CONFIGS.get(model, {})
            model_id = model_config.get("model_id") if model_config else model

            stream = self.client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.7,
                max_tokens=self._get_max_tokens(model),
                stream=True,
            )

            return stream

        except Exception as e:
            error_msg = f"AI 流式处理出错: {str(e)}"
            self.errorOccurred.emit(error_msg)
            raise Exception(error_msg)


class AIWorkerThread(QThread):
    """统一的AI工作线程"""

    resultReady = pyqtSignal(str)
    chunkReceived = pyqtSignal(str)
    finished = pyqtSignal()
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
                stream = self.ai_service.generate_content_stream(
                    self.text, self.mode)
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
