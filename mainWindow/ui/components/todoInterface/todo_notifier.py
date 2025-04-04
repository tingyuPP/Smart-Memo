# coding:utf-8
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import threading
import asyncio
from datetime import datetime, timedelta
import re
from desktop_notifier import DesktopNotifier, Button, Urgency
from Database import DatabaseManager


class TodoNotifier(QObject):
    """待办事项提醒系统"""

    # 信号定义
    status_changed = pyqtSignal(int, bool)  # 更新状态信号
    query_todos = pyqtSignal(int)  # 请求待办数据信号
    todos_result = pyqtSignal(list)  # 待办数据结果信号
    # 新增用于触发通知发送的信号
    notification_request = pyqtSignal(
        int, str, str, str
    )  # (todo_id, task, deadline, category)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.notifier = DesktopNotifier()
        self.check_interval = 60  # 检查间隔（秒）
        self._running = False
        self._thread = None
        self.notified_ids = set()  # 已通知的待办ID，避免重复通知
        self.current_todos = []  # 缓存待办数据
        self._lock = threading.Lock()  # 添加线程锁保护共享数据

        # 初始化日志
        import logging

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("TodoNotifier")

        # 连接信号到槽函数
        self.notification_request.connect(self.send_notification_in_main_thread)

    def start(self):
        """启动提醒系统"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        self.logger.info("通知系统已启动")

    def stop(self):
        """停止提醒系统"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        self.logger.info("通知系统已停止")

    def reset_notifications(self):
        """重置已通知状态，允许重新发送通知"""
        with self._lock:
            self.notified_ids.clear()
        self.logger.info("通知状态已重置")

    def handle_db_query(self, user_id):
        """处理数据库查询请求 - 在主线程中执行"""
        try:
            db = DatabaseManager()  # 在主线程创建新的连接
            todos = db.get_todos(user_id, show_completed=False)
            self.todos_result.emit(todos)
            db.close()
            self.logger.debug(f"成功查询到 {len(todos)} 条待办事项")
        except Exception as e:
            self.logger.error(f"查询待办事项失败: {e}")
            self.todos_result.emit([])

    def _run_async_loop(self):
        """运行异步事件循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._check_todos_loop())
        except Exception as e:
            self.logger.error(f"通知循环出错: {e}")
        finally:
            loop.close()
            self.logger.info("通知循环已终止")

    async def _check_todos_loop(self):
        """定期检查待办事项"""
        while self._running:
            # 发送信号请求数据
            self.query_todos.emit(self.user_id)
            # 等待一小段时间以确保数据返回
            await asyncio.sleep(0.5)
            # 检查待办
            await self._process_todos()
            # 等待下一个检查周期
            await asyncio.sleep(self.check_interval)

    async def _process_todos(self):
        """处理待办数据"""
        try:
            now = datetime.now()

            # 使用线程锁保护对共享数据的访问
            todos_to_process = []
            with self._lock:
                todos_to_process = list(self.current_todos)

            for todo in todos_to_process:
                todo_id, task, deadline_str, category, is_done = todo[:5]

                # 跳过已完成的待办
                if is_done:
                    continue

                # 跳过已通知的待办
                with self._lock:
                    if todo_id in self.notified_ids:
                        continue

                # 解析截止时间
                try:
                    # 尝试不同的日期格式
                    formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d"]
                    deadline_dt = None

                    for date_format in formats:
                        try:
                            deadline_dt = datetime.strptime(deadline_str, date_format)
                            # 如果只有日期部分，设置时间为当天结束
                            if date_format == "%Y-%m-%d":
                                deadline_dt = deadline_dt.replace(hour=23, minute=59)
                            break
                        except ValueError:
                            continue

                    if not deadline_dt:
                        # 尝试更灵活的解析
                        try:
                            # 提取日期部分
                            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", deadline_str)
                            # 提取时间部分
                            time_match = re.search(
                                r"(\d{1,2})[:.：](\d{2})", deadline_str
                            )

                            if date_match and time_match:
                                date_str = date_match.group(1)
                                hour, minute = int(time_match.group(1)), int(
                                    time_match.group(2)
                                )
                                deadline_dt = datetime.strptime(
                                    f"{date_str} {hour:02d}:{minute:02d}",
                                    "%Y-%m-%d %H:%M",
                                )
                            elif date_match:
                                deadline_dt = datetime.strptime(
                                    f"{date_match.group(1)} 23:59", "%Y-%m-%d %H:%M"
                                )
                            else:
                                raise ValueError(f"无法解析日期: {deadline_str}")
                        except:
                            self.logger.error(f"无法解析截止时间: {deadline_str}")
                            continue

                    time_left = deadline_dt - now

                    # 通知触发条件
                    if -timedelta(minutes=30) <= time_left <= timedelta(minutes=15):
                        # 使用信号发送通知请求到主线程
                        self.notification_request.emit(
                            todo_id, task, deadline_str, category
                        )

                        # 安全地更新已通知集合
                        with self._lock:
                            self.notified_ids.add(todo_id)

                        self.logger.info(f"添加通知: {task}, 剩余时间: {time_left}")

                except Exception as e:
                    self.logger.error(f"解析截止时间错误: {deadline_str}, {e}")
                    continue

        except Exception as e:
            self.logger.error(f"处理待办事项时出错: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    @pyqtSlot(int, str, str, str)
    def send_notification_in_main_thread(self, todo_id, task, deadline, category):
        """在主线程中发送通知（通过信号调用）"""
        try:
            # 创建通知选项
            def mark_as_done():
                # 只发送信号，让主线程处理数据库操作
                self.status_changed.emit(todo_id, True)
                self.logger.info(f"用户通过通知将待办标记为完成: {task}")

            def dismiss():
                self.logger.info(f"用户已忽略提醒: {task}")

            buttons = [
                Button(title="标记为完成", on_pressed=mark_as_done, identifier="done"),
                Button(title="稍后提醒", on_pressed=dismiss, identifier="dismiss"),
            ]

            time_str = deadline.split(" ")[1] if " " in deadline else deadline

            # 检查是否已过期
            try:
                deadline_dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
                now = datetime.now()
                is_overdue = now > deadline_dt
                title = (
                    f"⚠️ 待办已过期: {category}"
                    if is_overdue
                    else f"📌 待办提醒: {category}"
                )
            except:
                title = f"📌 待办提醒: {category}"

            # 创建一个新的事件循环来运行异步通知方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 在新的事件循环中运行异步方法
                loop.run_until_complete(
                    self.notifier.send(
                        title=title,
                        message=f"{task}\n截止时间: {time_str}",
                        buttons=buttons,
                        urgency=Urgency.Critical,
                        timeout=30,
                    )
                )
            finally:
                loop.close()

            self.logger.info(f"成功发送通知: {task}")

        except Exception as e:
            self.logger.error(f"发送通知时出错: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
