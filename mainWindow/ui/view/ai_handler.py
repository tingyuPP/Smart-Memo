# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QTextCursor
from PyQt5.QtWidgets import QApplication, QDialog

from qfluentwidgets import (
    InfoBar,
    InfoBarPosition,
    RoundMenu,
    Action,
    FluentIcon,
    CardWidget,
)

import locale
from datetime import datetime
import traceback

from services.ai_service import AIService
from mainWindow.ui.components.ai_handler.ai_dialog import AIDialog
from mainWindow.ui.components.ai_handler.ai_parser import AIResultParser


class AIHandler:
    """AI 功能处理类 - 处理AI功能调用、结果处理等"""

    _instance = None  # 单例模式的实例引用

    @classmethod
    def get_instance(cls, parent=None):
        """获取AIHandler单例实例"""
        if cls._instance is None:
            try:
                cls._instance = AIHandler(parent)
            except Exception:
                import traceback

                traceback.print_exc()
                cls._instance = cls._create_fallback_instance(parent)
        return cls._instance

    @classmethod
    def _create_fallback_instance(cls, parent):
        """创建降级版本的AIHandler实例"""
        handler = object.__new__(cls)
        handler.parent = parent

        handler.ai_service = AIService.__new__(AIService)
        handler.ai_service._memory_context = ""
        handler.ai_service.client = None
        return handler

    def __init__(self, parent: CardWidget):
        """初始化AIHandler"""
        # 如果已经存在实例，直接返回
        if AIHandler._instance is not None:
            return

        self.parent = parent
        self.ai_service = AIService()

        # 更新单例引用
        AIHandler._instance = self

    def show_ai_menu(self, text_edit):
        """显示AI功能菜单"""
        aiMenu = RoundMenu("AI编辑", self.parent)

        # 根据当前编辑器内容显示不同的菜单选项
        if not text_edit.toPlainText().strip():
            # 如果编辑器为空，显示内容生成选项
            aiMenu.addActions(
                [
                    Action(
                        "为我写一个朋友圈文案",
                        triggered=lambda: self.handle_ai_func("朋友圈文案", text_edit),
                    ),
                    Action(
                        "为我写一句诗",
                        triggered=lambda: self.handle_ai_func("一句诗", text_edit),
                    ),
                    Action(
                        "自定义",
                        triggered=lambda: self.handle_ai_func("自定义", text_edit),
                    ),
                ]
            )
        else:
            # 如果编辑器有内容，显示文本处理选项
            aiMenu.addActions(
                [
                    Action(
                        "润色", triggered=lambda: self.handle_ai_func("润色", text_edit)
                    ),
                    Action(
                        "续写", triggered=lambda: self.handle_ai_func("续写", text_edit)
                    ),
                ]
            )

        # 显示菜单
        aiMenu.exec_(QCursor.pos())

    def handle_ai_func(self, mode, text_edit):
        """处理AI功能"""
        # 获取当前选中的文本或全部文本
        cursor = text_edit.textCursor()
        text = (
            cursor.selectedText() if cursor.hasSelection() else text_edit.toPlainText()
        )

        # 创建并显示AI对话框
        dialog = AIDialog(mode, text, self.parent, ai_service=self.ai_service)
        result = dialog.exec_()

        # 处理结果
        if result == QDialog.Accepted and dialog.result_text:
            self._apply_ai_result(mode, cursor, dialog.result_text, text_edit)

    def _apply_ai_result(self, mode, cursor, result_text, text_edit):
        """应用AI处理结果到文本编辑器"""
        if mode == "润色":
            if cursor.hasSelection():
                cursor.insertText(result_text)
            else:
                text_edit.setText(result_text)

        elif mode == "续写":
            current_cursor = text_edit.textCursor()
            current_position = current_cursor.position()

            current_cursor.movePosition(QTextCursor.End)
            text_edit.setTextCursor(current_cursor)

            current_text = text_edit.toPlainText()

            if current_text:
                current_cursor.insertText(result_text)
            else:
                text_edit.setText(result_text)

        else:
            # 其他类型的生成内容
            if not text_edit.toPlainText().strip():
                text_edit.setText(result_text)
            else:
                current_cursor = text_edit.textCursor()
                current_cursor.movePosition(QTextCursor.End)
                text_edit.setTextCursor(current_cursor)
                current_cursor.insertText("\n\n" + result_text)

        # 显示成功消息
        self._show_success_message(mode)

    def _show_success_message(self, mode):
        """显示成功消息"""
        InfoBar.success(
            title="AI 处理完成",
            content=f"{mode}内容已应用",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.parent,
        )

    def extract_todos_from_memo(self, memo_content, user_id):
        """从备忘录内容中提取待办事项"""
        try:
            # 获取系统提示词
            system_prompt = self.ai_service.AI_MODES["待办提取"]["system_prompt"]

            # 设置本地化
            try:
                locale.setlocale(locale.LC_TIME, "zh_CN.UTF-8")
            except:
                try:
                    locale.setlocale(locale.LC_TIME, "zh_CN")
                except:
                    pass

            # 创建提取待办事项的提示词
            prompt = AIResultParser.create_todo_prompt(memo_content)

            # 生成内容
            result = self.ai_service.generate_content(
                system_prompt + prompt, mode="自定义"
            )

            # 解析结果
            return AIResultParser.parse_todo_result(result)

        except Exception as e:
            print(f"提取待办事项失败: {str(e)}")
            traceback.print_exc()
            return 0, []
