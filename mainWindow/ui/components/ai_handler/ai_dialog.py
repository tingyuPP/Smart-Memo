# coding:utf-8
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSize
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QApplication,
    QWidget,
    QWIDGETSIZE_MAX,
    QDialog,
)
from PyQt5.QtGui import QTextCursor

from qfluentwidgets import (
    TextEdit,
    PrimaryPushButton,
    StateToolTip,
    InfoBar,
    InfoBarPosition,
    FluentIcon,
    BodyLabel,
    Dialog,
    IconWidget,
    isDarkTheme,
)

from mainWindow.ui.components.ai_handler.ai_threads import AIWorkerThread, AIStreamWorkerThread


class AIDialog(Dialog):
    """AI 处理对话框"""

    def __init__(self, mode, text="", parent=None, ai_service=None):
        self.mode = mode
        self.input_text = text
        self.result_text = ""
        self.state_tooltip = None
        self.worker_thread = None

        self.ai_service = ai_service

        title = self.get_mode_display_name()
        content = ""

        super().__init__(title, content, parent=parent)

        # 设置对话框尺寸和行为
        self.resize(650, 500)
        self.setMaximumSize(16777215, 16777215)
        self.setFixedSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self.setResizeEnabled(True)

        # 配置标题栏
        self.titleBar.show()

        if hasattr(self.titleBar, "setDoubleClickEnabled"):
            self.titleBar.setDoubleClickEnabled(True)

        if hasattr(self.titleBar, "minBtn"):
            self.titleBar.minBtn.show()
        if hasattr(self.titleBar, "maxBtn"):
            self.titleBar.maxBtn.show()
        if hasattr(self.titleBar, "closeBtn"):
            self.titleBar.closeBtn.show()

        if hasattr(self.titleBar, "setTitle"):
            self.titleBar.setTitle(title)

        if hasattr(self, "windowTitleLabel"):
            self.windowTitleLabel.setVisible(False)

        # 设置用户界面
        self.setup_ui()

        # 应用自定义样式
        self.apply_custom_style()

        # 启用流式响应
        self.use_streaming = True

    def setup_ui(self):
        """设置用户界面"""
        if hasattr(self, "buttonGroup"):
            self.buttonGroup.setParent(None)
            self.buttonGroup.deleteLater()

        if hasattr(self, "contentLabel"):
            self.contentLabel.setVisible(False)

        # 头部区域 - 图标和描述
        header_layout = QHBoxLayout()

        mode_icon = self.get_mode_icon()
        self.icon_widget = IconWidget(mode_icon, self)
        self.icon_widget.setFixedSize(32, 32)
        header_layout.addWidget(self.icon_widget)

        description = self.get_mode_description()
        desc_label = BodyLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setObjectName("aiDialogDescLabel")

        header_layout.addWidget(desc_label, 1)

        self.textLayout.addLayout(header_layout)

        # 分隔线
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setObjectName("aiDialogSeparator")
        self.textLayout.addWidget(separator)
        self.textLayout.addSpacing(10)

        # 辅助提示词输入区域 (根据模式显示)
        if self.mode not in ["tab续写", "自定义"]:
            aux_layout = QHBoxLayout()
            aux_label = BodyLabel("辅助提示词(可选):")
            aux_label.setMinimumWidth(100)
            self.aux_edit = TextEdit()
            self.aux_edit.setPlaceholderText("在这里输入额外的提示或要求...")
            self.aux_edit.setMaximumHeight(60)
            self.aux_edit.setObjectName("aiDialogAuxEdit")
            aux_layout.addWidget(aux_label)
            aux_layout.addWidget(self.aux_edit)
            self.textLayout.addLayout(aux_layout)

        # 自定义模式的提示词输入区域
        if self.mode == "自定义":
            prompt_layout = QHBoxLayout()
            prompt_label = BodyLabel("提示词:")
            prompt_label.setMinimumWidth(100)
            self.prompt_edit = TextEdit()
            self.prompt_edit.setPlaceholderText("请输入 AI 提示词...")
            self.prompt_edit.setMaximumHeight(80)
            self.prompt_edit.setObjectName("aiDialogPromptEdit")
            prompt_layout.addWidget(prompt_label)
            prompt_layout.addWidget(self.prompt_edit)
            self.textLayout.addLayout(prompt_layout)

        # 结果显示区域
        result_layout = QVBoxLayout()
        result_header = QHBoxLayout()

        result_label = BodyLabel("生成结果:")
        result_label.setObjectName("aiDialogResultLabel")
        result_header.addWidget(result_label)

        result_header.addStretch(1)
        result_layout.addLayout(result_header)

        self.result_edit = TextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("AI 生成的内容将显示在这里...")
        self.result_edit.setMinimumHeight(200)
        self.result_edit.setObjectName("aiDialogResultEdit")
        result_layout.addWidget(self.result_edit)

        self.textLayout.addLayout(result_layout)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        self.generate_button = PrimaryPushButton("生成")
        self.generate_button.setIcon(FluentIcon.SEND)
        self.generate_button.setEnabled(True)
        self.generate_button.clicked.connect(self.generate_content)

        self.use_button = PrimaryPushButton("使用结果")
        self.use_button.setIcon(FluentIcon.ACCEPT)
        self.use_button.setEnabled(False)
        self.use_button.clicked.connect(self.accept)

        self.cancel_button = PrimaryPushButton("取消")
        self.cancel_button.setIcon(FluentIcon.CLOSE)
        self.cancel_button.clicked.connect(self.reject)

        self.stop_button = PrimaryPushButton("停止生成")
        self.stop_button.setIcon(FluentIcon.CANCEL)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_generation)

        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.use_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.stop_button)

        self.textLayout.addLayout(button_layout)

        # 连接AI服务信号
        if self.ai_service:
            self.ai_service.resultReady.connect(self.handle_ai_result)
            self.ai_service.errorOccurred.connect(self.handle_ai_error)

    def apply_custom_style(self):
        """应用自定义样式"""
        if isDarkTheme():
            self.setStyleSheet(
                """
                #aiDialogTitleLabel {
                    color: #60cdff;
                    margin-bottom: 5px;
                }
                
                #aiDialogDescLabel {
                    color: #cccccc;
                    margin-bottom: 10px;
                }
                
                #aiDialogSeparator {
                    background-color: #444444;
                    margin: 5px 0;
                }
                
                #aiDialogResultEdit, #aiDialogAuxEdit, #aiDialogPromptEdit {
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 8px;
                    background-color: #333333;
                }
                
                #aiDialogResultLabel {
                    font-weight: bold;
                    color: #e0e0e0;
                }
            """
            )
        else:
            self.setStyleSheet(
                """
                #aiDialogTitleLabel {
                    color: #0078d4;
                    margin-bottom: 5px;
                }
                
                #aiDialogDescLabel {
                    color: #666666;
                    margin-bottom: 10px;
                }
                
                #aiDialogSeparator {
                    background-color: #e0e0e0;
                    margin: 5px 0;
                }
                
                #aiDialogResultEdit, #aiDialogAuxEdit, #aiDialogPromptEdit {
                    border: 1px solid #d0d0d0;
                    border-radius: 5px;
                    padding: 8px;
                    background-color: #fafafa;
                }
                
                #aiDialogResultLabel {
                    font-weight: bold;
                    color: #333333;
                }
            """
            )

    def get_mode_icon(self):
        """根据模式获取对应的图标"""
        icon_map = {
            "一句诗": FluentIcon.EDIT,
            "摘要": FluentIcon.DOCUMENT,
            "续写": FluentIcon.PENCIL_INK,
            "tab续写": FluentIcon.PENCIL_INK,
            "自定义": FluentIcon.ROBOT,
            "提取待办": FluentIcon.CHECKBOX,
            "润色": FluentIcon.BRUSH,
            "翻译": FluentIcon.LANGUAGE,
            "朋友圈文案": FluentIcon.GLOBE,
        }

        return icon_map.get(self.mode, FluentIcon.ROBOT)

    def get_mode_display_name(self):
        """获取模式的显示名称"""
        mode_names = {
            "润色": "润色",
            "续写": "续写",
            "朋友圈文案": "朋友圈文案生成",
            "一句诗": "诗句生成",
            "自定义": "自定义生成",
        }
        return mode_names.get(self.mode, self.mode)

    def get_mode_description(self):
        """获取模式的描述文本"""
        descriptions = {
            "润色": "AI 将对您的文本进行润色，使其更加优美流畅，同时保持原意不变。",
            "续写": "AI 将基于您的文本继续写作，保持风格一致。",
            "朋友圈文案": "AI 将为您生成一段适合发布在朋友圈的文案，内容积极向上，有文艺气息。",
            "一句诗": "AI 将为您创作一句富有诗意的句子。",
            "自定义": "请输入您的提示词，AI 将根据您的要求生成内容。",
        }
        return descriptions.get(self.mode, "AI 将根据您的需求生成内容。")

    def show_loading_state(self):
        """显示加载状态"""
        try:
            if hasattr(self, "state_tooltip") and self.state_tooltip:
                try:
                    self.state_tooltip.close()
                except:
                    pass
                self.state_tooltip = None

            self.state_tooltip = StateToolTip(
                title="正在处理", content="AI 正在生成内容...", parent=self
            )

            dialog_rect = self.geometry()
            tooltip_size = self.state_tooltip.size()

            x = (dialog_rect.width() - tooltip_size.width()) // 2
            y = (dialog_rect.height() - tooltip_size.height()) // 2

            self.state_tooltip.move(x, y)
            self.state_tooltip.show()
            QApplication.processEvents()

        except Exception as e:
            print(f"显示加载状态时出错: {str(e)}")
            self.state_tooltip = None

    def generate_content(self):
        """生成内容"""
        self.disable_all_inputs()
        self.show_loading_state()

        aux_prompt = self.aux_edit.toPlainText() if hasattr(self, "aux_edit") else ""

        if self.mode == "自定义":
            text = self.prompt_edit.toPlainText()
            if not text:
                self.handle_ai_error("请输入提示词")
                return
        elif self.mode in ["润色", "续写"]:
            text = self.input_text
            if not text.strip():
                self.handle_ai_error("请输入需要处理的文本")
                return
        else:
            text = ""

        self.result_edit.clear()
        self.result_text = ""

        self.stop_any_running_threads()

        if self.use_streaming:
            self.worker_thread = AIStreamWorkerThread(
                self.ai_service,
                self.mode,
                text,
                aux_prompt=aux_prompt,
            )
            self.worker_thread.chunkReceived.connect(self.handle_stream_chunk)
            self.worker_thread.finished.connect(self.handle_stream_finished)
            self.worker_thread.error.connect(self.handle_ai_error)
            self.stop_button.setEnabled(True)
        else:
            self.worker_thread = AIWorkerThread(
                self.ai_service,
                self.mode,
                text,
                aux_prompt=aux_prompt,
            )
            self.worker_thread.finished.connect(self.handle_ai_result)
            self.worker_thread.error.connect(self.handle_ai_error)

        self.worker_thread.start()

    def stop_generation(self):
        """停止生成过程"""
        if self.worker_thread and isinstance(self.worker_thread, AIStreamWorkerThread):
            self.worker_thread.stop()
            self.stop_button.setEnabled(False)

            self.generate_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            if hasattr(self, "prompt_edit"):
                self.prompt_edit.setReadOnly(False)

            if hasattr(self, "state_tooltip") and self.state_tooltip:
                try:
                    self.state_tooltip.setContent("生成已停止")
                    self.state_tooltip.setState(True)
                    QApplication.processEvents()
                except:
                    pass
                finally:
                    QTimer.singleShot(1000, lambda: self.safely_close_tooltip())

    def stop_any_running_threads(self):
        """停止任何正在运行的线程"""
        if self.worker_thread and self.worker_thread.isRunning():
            if isinstance(self.worker_thread, AIStreamWorkerThread):
                self.worker_thread.stop()
            self.worker_thread.terminate()
            self.worker_thread.wait()

    @pyqtSlot(str)
    def handle_stream_chunk(self, chunk):
        """处理流式响应的文本块"""
        try:
            self.result_text += chunk

            self.result_edit.setText(self.result_text)

            cursor = self.result_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.result_edit.setTextCursor(cursor)

        except Exception as e:
            print(f"处理流数据块时出错: {str(e)}")

    @pyqtSlot()
    def handle_stream_finished(self):
        """处理流式响应完成"""
        try:
            self.generate_button.setEnabled(True)
            self.use_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            if hasattr(self, "prompt_edit"):
                self.prompt_edit.setReadOnly(False)

            if hasattr(self, "state_tooltip") and self.state_tooltip:
                try:
                    self.state_tooltip.setContent("处理完成")
                    self.state_tooltip.setState(True)
                    QApplication.processEvents()
                except:
                    pass
                finally:
                    QTimer.singleShot(1000, lambda: self.safely_close_tooltip())

        except Exception as e:
            print(f"处理流完成时出错: {str(e)}")

    def disable_all_inputs(self):
        """禁用所有输入控件"""
        self.generate_button.setEnabled(False)
        self.use_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        if hasattr(self, "prompt_edit"):
            self.prompt_edit.setReadOnly(True)

    def safely_close_tooltip(self):
        """安全关闭提示框"""
        if hasattr(self, "state_tooltip") and self.state_tooltip:
            try:
                self.state_tooltip.close()
            except:
                pass
            self.state_tooltip = None

    @pyqtSlot(str)
    def handle_ai_error(self, error_message):
        """处理 AI 生成错误"""
        try:
            self.result_edit.setText(f"错误: {error_message}")
            self.generate_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            if hasattr(self, "prompt_edit"):
                self.prompt_edit.setReadOnly(False)

            if hasattr(self, "state_tooltip") and self.state_tooltip:
                try:
                    self.state_tooltip.setContent(f"处理失败: {error_message}")
                    self.state_tooltip.setState(True)
                    QApplication.processEvents()
                except:
                    pass
                finally:
                    QTimer.singleShot(1000, lambda: self.safely_close_tooltip())

        except Exception as e:
            print(f"处理AI错误时出错: {str(e)}")

    @pyqtSlot(str)
    def handle_ai_result(self, result):
        """处理 AI 生成结果"""
        try:
            self.result_text = result
            self.result_edit.setText(result)

            self.generate_button.setEnabled(True)
            self.use_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            if hasattr(self, "prompt_edit"):
                self.prompt_edit.setReadOnly(False)

            if hasattr(self, "state_tooltip") and self.state_tooltip:
                try:
                    self.state_tooltip.setContent("处理完成")
                    self.state_tooltip.setState(True)
                    QApplication.processEvents()
                except:
                    pass
                finally:
                    QTimer.singleShot(1000, lambda: self.safely_close_tooltip())

        except Exception as e:
            print(f"处理AI结果时出错: {str(e)}")

    def closeEvent(self, event):
        """关闭对话框时清理资源"""
        self.stop_any_running_threads()

        if self.state_tooltip:
            try:
                self.state_tooltip.close()
            except:
                pass
            self.state_tooltip = None

        self.generate_button.setEnabled(True)
        self.use_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if hasattr(self, "prompt_edit"):
            self.prompt_edit.setReadOnly(False)

        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()
