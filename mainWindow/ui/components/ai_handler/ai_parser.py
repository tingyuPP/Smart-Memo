# coding:utf-8
import json
import re
from datetime import datetime, timedelta


class AIResultParser:
    """AI结果解析类，处理各种AI响应的解析功能"""

    @staticmethod
    def parse_todo_result(result):
        """解析AI返回的待办事项结果"""
        try:
            # 尝试解析JSON格式
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

            # 如果JSON解析失败，尝试文本格式解析
            todos = []
            lines = result.strip().split("\n")

            for line in lines:
                if not line.strip():
                    continue

                # 匹配格式为 "任务内容，截止日期：xxx，类别：xxx" 的行
                todo_match = re.search(
                    r"[*\-•]?\s*(.+?)(?:，|,|\s+)(?:截止日期|截止时间|deadline)[:：]?\s*(.+?)(?:，|,|\s+)(?:类别|分类|category)[:：]?\s*(.+?)$",
                    line,
                    re.IGNORECASE,
                )

                if todo_match:
                    task = todo_match.group(1).strip()
                    deadline = todo_match.group(2).strip()
                    category = todo_match.group(3).strip()

                    # 处理相对日期
                    if deadline and any(
                        word in deadline
                        for word in ["今天", "明天", "后天", "下周", "下个月"]
                    ):
                        now = datetime.now()

                        if "今天" in deadline:
                            deadline_date = now.strftime("%Y-%m-%d")
                        elif "明天" in deadline:
                            deadline_date = (now + timedelta(days=1)).strftime(
                                "%Y-%m-%d"
                            )
                        elif "后天" in deadline:
                            deadline_date = (now + timedelta(days=2)).strftime(
                                "%Y-%m-%d"
                            )
                        elif "下周" in deadline:
                            deadline_date = (now + timedelta(days=7)).strftime(
                                "%Y-%m-%d"
                            )
                        elif "下个月" in deadline:
                            deadline_date = (now + timedelta(days=30)).strftime(
                                "%Y-%m-%d"
                            )

                        # 提取时间部分
                        time_match = re.search(r"(\d{1,2})[:.：](\d{1,2})", deadline)
                        if time_match:
                            hour = int(time_match.group(1))
                            minute = int(time_match.group(2))
                            deadline = f"{deadline_date} {hour:02d}:{minute:02d}"
                        else:
                            deadline = f"{deadline_date} 09:00"

                    todos.append(
                        {"task": task, "deadline": deadline, "category": category}
                    )
                else:
                    # 处理没有明确格式的行
                    task_match = re.search(r"[*\-•]?\s*(.+)", line)
                    if task_match:
                        task = task_match.group(1).strip()
                        # 避免解析标题行
                        if task and not task.startswith(("待办事项", "Todo", "任务")):
                            todos.append(
                                {
                                    "task": task,
                                    "deadline": "无截止日期",
                                    "category": "其他",
                                }
                            )

            return len(todos), todos

        except Exception as e:
            print(f"解析待办事项失败: {str(e)}")
            return 0, []

    @staticmethod
    def create_todo_prompt(memo_content):
        """创建待办事项提取的提示词"""
        try:
            # 获取当前日期和星期
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")

            weekday_names = [
                "星期一",
                "星期二",
                "星期三",
                "星期四",
                "星期五",
                "星期六",
                "星期日",
            ]
            weekday = weekday_names[now.weekday()]

            # 创建提示词
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
            return prompt
        except Exception as e:
            print(f"创建提示词失败: {str(e)}")
            return ""
