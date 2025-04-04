from datetime import datetime
import os
import tempfile
import uuid
import time
import json
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (CardWidget, IconWidget, TitleLabel, BodyLabel,
                            SettingCardGroup, TransparentDropDownToolButton,
                            RoundMenu, Action, InfoBar, InfoBarPosition,
                            FluentIcon, CaptionLabel, PrimaryPushSettingCard,
                            Dialog)
from obs import ObsClient
from Database import DatabaseManager


class CloudCard(CardWidget):

    def __init__(self, icon, title, content, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.user_id = parent.user_data["id"]
        self.iconWidget = IconWidget(icon)
        self.titleLabel = BodyLabel(title, self)
        self.contentLabel = CaptionLabel(content, self)
        self.menuButton = TransparentDropDownToolButton(FluentIcon.MORE, self)
        self.menu = RoundMenu(parent=self.menuButton)
        self.menu.addAction(
            Action(FluentIcon.SEND, "上传至云端", triggered=self.upload_to_cloud))
        self.menu.addAction(
            Action(
                FluentIcon.CLOUD_DOWNLOAD,
                "下载至本地",
                triggered=self.download_to_local,
            ))
        self.menuButton.setMenu(self.menu)
        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        self.setFixedHeight(73)
        self.iconWidget.setFixedSize(16, 16)
        self.contentLabel.setTextColor("#606060", "#d2d2d2")

        self.hBoxLayout.setContentsMargins(15, 11, 11, 11)
        self.hBoxLayout.setSpacing(15)
        self.hBoxLayout.addWidget(self.iconWidget)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.addWidget(self.contentLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)
        self.hBoxLayout.addLayout(self.vBoxLayout)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.menuButton, 0, Qt.AlignRight)

    def upload_to_cloud(self):
        """将备忘录数据上传到云端备份"""
        try:
            w1 = InfoBar.info(
                title="备份中",
                content="正在准备备份数据...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=1000,  # 持续显示，直到手动关闭
                parent=self.parent,
            )
            w1.show()
            # 从数据库获取备忘录数据
            self.db = DatabaseManager()
            memos = self.db.get_memos(user_id=self.user_id)

            if not memos:
                InfoBar.warning(
                    title="无数据",
                    content="没有找到需要备份的备忘录数据",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=3000,
                    parent=self.parent,
                )
                return

            # 更新状态消息
            w2 = InfoBar.info(
                title="备份中",
                content=f"正在备份{len(memos)}条备忘录到云端...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=1000,
                parent=self.parent,
            )
            w2.show()
            # 解析备忘录数据
            memo_list = []
            for memo in memos:
                memo_id = memo[0]
                user_id = memo[1]
                created_time = memo[2]
                modified_time = memo[3]
                title = self.db.decrypt(memo[4])
                content = self.db.decrypt(memo[5])
                category = memo[6]
                memo_dict = {
                    "memo_id": memo_id,
                    "user_id": user_id,
                    "created_time": created_time,
                    "modified_time": modified_time,
                    "title": title,
                    "content": content,
                    "category": category,
                }
                memo_list.append(memo_dict)

            success, backup_url = self._upload_memos_to_obs(memo_list)
            w1.close()
            w2.close()

        except Exception as e:
            import traceback

            print(f"备份过程出错: {str(e)}")
            print(traceback.format_exc())

            w1.close()
            w2.close()
            InfoBar.error(
                title="备份失败",
                content=f"备份过程中出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )
        finally:
            if hasattr(self, "db") and self.db:
                self.db.close()

    def _upload_memos_to_obs(self, memo_list):
        """上传备忘录数据到华为云OBS备份"""
        try:
            # 华为云OBS配置
            ak = "FTCMA0RFFEFYAHZCTUNR"
            sk = "DtOPu5ExOARQuMZHAGewDVzryaH1ht7gSWlflsJ5"
            endpoint = "obs.cn-east-3.myhuaweicloud.com"
            server = f"https://{endpoint}"
            bucket_name = "mypicturebed"  # 使用同一个bucket

            # 创建OBS客户端
            obs_client = ObsClient(access_key_id=ak,
                                   secret_access_key=sk,
                                   server=server)

            try:
                import json
                import time

                computer_id = self.get_computer_id()

                timestamp = int(time.time())
                user_id = self.user_id
                register_time = str(self.parent.user_data["register_time"])
                register_time = register_time.replace(" ",
                                                      "_").replace(":", "-")
                backup_filename = f"memo_backup_{computer_id}_{user_id}_{register_time}_{timestamp}.json"

                memo_json = json.dumps(memo_list, ensure_ascii=False, indent=2)

                object_key = f"memo_backups/{backup_filename}"
                resp = obs_client.putObject(bucket_name, object_key,
                                            memo_json.encode("utf-8"))

                if resp.status < 300:
                    backup_url = f"https://{bucket_name}.{endpoint}/{object_key}"

                    InfoBar.success(
                        title="备份成功",
                        content=f"成功备份{len(memo_list)}条备忘录到云端",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=3000,
                        parent=self.parent,
                    )

                    return True, backup_url
                else:
                    print(f"上传失败: {resp.errorCode} - {resp.errorMessage}")

                    InfoBar.error(
                        title="备份失败",
                        content=f"备份失败: {resp.errorMessage}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=3000,
                        parent=self.parent,
                    )

                    return False, None
            finally:
                obs_client.close()

        except Exception as e:
            print(f"上传到OBS时发生错误: {str(e)}")
            import traceback

            print(traceback.format_exc())

            InfoBar.error(
                title="备份失败",
                content=f"备份过程中出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

            return False, None

    def get_computer_id(self):
        """获取计算机的唯一标识符"""
        return uuid.UUID(int=uuid.getnode()).hex[-12:]

    def download_to_local(self):
        """下载云端备份文件到本地"""
        try:
            self.download_info_bar = InfoBar.info(
                title="下载中",
                content="正在查询云端备份文件...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,
                parent=self.parent,
            )

            self._query_cloud_backups()

        except Exception as e:
            import traceback

            print(f"下载备份过程出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            InfoBar.error(
                title="下载失败",
                content=f"下载备份过程中出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

    def _query_cloud_backups(self):
        """查询云端备份文件"""
        try:
            ak = "FTCMA0RFFEFYAHZCTUNR"
            sk = "DtOPu5ExOARQuMZHAGewDVzryaH1ht7gSWlflsJ5"
            endpoint = "obs.cn-east-3.myhuaweicloud.com"
            server = f"https://{endpoint}"
            bucket_name = "mypicturebed"

            obs_client = ObsClient(access_key_id=ak,
                                   secret_access_key=sk,
                                   server=server)

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()
                self.download_info_bar = InfoBar.info(
                    title="下载中",
                    content="正在查询备份文件...",
                    orient=Qt.Horizontal,
                    isClosable=False,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=-1,
                    parent=self.parent,
                )

            prefix = f"memo_backups/memo_backup_"
            resp = obs_client.listObjects(bucket_name, prefix=prefix)

            if resp.status < 300:
                user_id = self.user_id
                current_computer_id = self.get_computer_id()

                user_backups = []
                other_device_backups = []

                for content in resp.body.contents:
                    object_key = content.key

                    filename = os.path.basename(object_key)
                    parts = filename.split("_")

                    if len(parts) >= 6 and parts[0] == "memo" and parts[
                            1] == "backup":
                        file_computer_id = parts[2]
                        file_user_id = parts[3]

                        # 获取文件名的末尾部分（时间戳.json）
                        timestamp_part = parts[-1]

                        register_time_parts = parts[4:-1]
                        file_register_time = "_".join(register_time_parts)

                        current_register_time = str(
                            self.parent.user_data.get("register_time",
                                                      "unknown"))
                        current_register_time = (current_register_time.replace(
                            " ", "_").replace(":", "-").replace("/", "-"))

                        if (str(file_user_id) == str(user_id) and
                                file_register_time == current_register_time):
                            timestamp = int(timestamp_part.split(".")[0])
                            backup_info = {
                                "key":
                                object_key,
                                "timestamp":
                                timestamp,
                                "last_modified":
                                content.lastModified,
                                "size":
                                content.size,
                                "computer_id":
                                file_computer_id,
                                "is_current_device":
                                file_computer_id == current_computer_id,
                            }

                            if file_computer_id == current_computer_id:
                                user_backups.append(backup_info)
                            else:
                                other_device_backups.append(backup_info)

                all_backups = user_backups + other_device_backups

                if not all_backups:
                    if hasattr(self,
                               "download_info_bar") and self.download_info_bar:
                        self.download_info_bar.close()

                    InfoBar.warning(
                        title="未找到备份",
                        content="云端没有找到您的备份文件",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=3000,
                        parent=self.parent,
                    )
                    return

                # 按时间戳排序，找出最新的备份
                all_backups.sort(key=lambda x: x["timestamp"], reverse=True)
                latest_backup = all_backups[0]

                if hasattr(self,
                           "download_info_bar") and self.download_info_bar:
                    backup_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(latest_backup["timestamp"]))

                    device_info = ("当前设备" if latest_backup["is_current_device"]
                                   else "其他设备")

                    self.download_info_bar.close()
                    self.download_info_bar = InfoBar.info(
                        title="下载中",
                        content=
                        f"找到最新备份 ({backup_time}, {device_info})，正在下载...",
                        orient=Qt.Horizontal,
                        isClosable=False,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=-1,
                        parent=self.parent,
                    )

                # 下载最新的备份文件
                QTimer.singleShot(
                    500,
                    lambda: self._download_backup_file(obs_client, bucket_name,
                                                       latest_backup),
                )
            else:
                raise Exception(
                    f"查询失败: {resp.errorCode} - {resp.errorMessage}")

        except Exception as e:
            import traceback

            print(f"查询云端备份出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            InfoBar.error(
                title="查询失败",
                content=f"查询云端备份时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

            if "obs_client" in locals():
                obs_client.close()

    def _download_backup_file(self, obs_client, bucket_name, backup_info):
        """下载指定的备份文件"""
        try:
            object_key = backup_info["key"]

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()
                self.download_info_bar = InfoBar.info(
                    title="下载中",
                    content="正在下载备份文件...",
                    orient=Qt.Horizontal,
                    isClosable=False,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=-1,
                    parent=self.parent,
                )

            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, os.path.basename(object_key))

            resp = obs_client.getObject(bucket_name,
                                        object_key,
                                        downloadPath=temp_file)

            if resp.status < 300:
                if hasattr(self,
                           "download_info_bar") and self.download_info_bar:
                    self.download_info_bar.close()
                    self.download_info_bar = InfoBar.info(
                        title="下载中",
                        content="备份下载完成，正在解析数据...",
                        orient=Qt.Horizontal,
                        isClosable=False,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=-1,
                        parent=self.parent,
                    )

                # 解析下载的JSON文件
                QTimer.singleShot(
                    500,
                    lambda: self._parse_backup_file(temp_file, backup_info))
            else:
                raise Exception(
                    f"下载失败: {resp.errorCode} - {resp.errorMessage}")

        except Exception as e:
            import traceback

            print(f"下载备份文件出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            InfoBar.error(
                title="下载失败",
                content=f"下载备份文件时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

        finally:
            obs_client.close()

    def show_confirm_dialog(self, title, content, on_yes, on_no=None):
        dialog = Dialog(title, content, parent=self.parent.mainWindow)

        dialog.yesButton.setText("确定")
        dialog.cancelButton.setText("取消")

        dialog.yesSignal.connect(on_yes)
        if on_no:
            dialog.cancelSignal.connect(on_no)

        dialog.exec()

    def _parse_backup_file(self, file_path, backup_info):
        try:
            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            with open(file_path, "r", encoding="utf-8") as f:
                memo_list = json.load(f)

            backup_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(backup_info["timestamp"]))
            memo_count = len(memo_list)

            backup_summary = {
                "backup_time": backup_time,
                "memo_count": memo_count,
                "user_id": self.user_id,
                "backup_file": os.path.basename(file_path),
                "backup_size": backup_info["size"],
                "memo_categories": {},
            }

            for memo in memo_list:
                category = memo.get("category", "未分类")
                if category not in backup_summary["memo_categories"]:
                    backup_summary["memo_categories"][category] = 0
                backup_summary["memo_categories"][category] += 1

            # 将备份文件保存到本地下载目录
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.exists(downloads_dir):
                downloads_dir = os.path.dirname(file_path)  # 使用临时目录

            # 创建一个带时间戳的备份文件名
            local_filename = f"memo_backup_{self.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            local_filepath = os.path.join(downloads_dir, local_filename)

            import shutil

            shutil.copy2(file_path, local_filepath)

            if hasattr(self, "download_info_bar") and self.download_info_bar:
                self.download_info_bar.close()

            InfoBar.success(
                title="下载成功",
                content=f"成功下载{memo_count}条备忘录数据，保存在: {local_filepath}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self.parent,
            )

            dialog_content = (
                f"是否要导入下载的{memo_count}条备忘录数据？\n"
                f"备份时间: {backup_time}\n"
                f'分类统计: {", ".join([f"{k}: {v}条" for k, v in backup_summary["memo_categories"].items()])}'
            )

            # 保存备份列表引用，以便在回调中使用
            self.temp_memo_list = memo_list

            self.show_confirm_dialog(
                "导入数据",
                dialog_content,
                on_yes=lambda: self._import_backup_data(self.temp_memo_list),
            )

        except Exception as e:
            import traceback

            print(f"解析备份文件出错: {str(e)}")
            print(traceback.format_exc())

            InfoBar.error(
                title="解析失败",
                content=f"解析备份文件时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

    def _import_backup_data(self, memo_list):
        """导入备份数据到本地数据库，替换所有现有数据"""
        try:
            self.import_info_bar = InfoBar.info(
                title="导入中",
                content=f"正在准备导入{len(memo_list)}条备忘录数据...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,
                parent=self.parent,
            )

            db = DatabaseManager()

            current_memos = db.get_memos(user_id=self.user_id)
            current_count = len(current_memos) if current_memos else 0

            self.db = db
            self.current_count = current_count
            self.import_memo_list = memo_list

            dialog_content = f"此操作将删除您现有的{current_count}条备忘录，并导入备份中的{len(memo_list)}条备忘录。\n确定要继续吗？"

            self.show_confirm_dialog(
                "替换确认",
                dialog_content,
                on_yes=self._do_import_backup_data,
                on_no=self._cancel_import,
            )

        except Exception as e:
            import traceback

            print(f"导入备份数据出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()

            InfoBar.error(
                title="导入失败",
                content=f"导入备份数据时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

            if hasattr(self, "db") and self.db:
                self.db.close()

    def _cancel_import(self):
        """取消导入操作"""
        if hasattr(self, "import_info_bar") and self.import_info_bar:
            self.import_info_bar.close()

        InfoBar.info(
            title="导入取消",
            content="您已取消导入备份数据",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=3000,
            parent=self.parent,
        )

        if hasattr(self, "db") and self.db:
            self.db.close()

    def _do_import_backup_data(self):
        """执行实际的导入操作"""
        try:
            # 获取之前保存的数据
            db = self.db
            current_count = self.current_count
            memo_list = self.import_memo_list

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()
                self.import_info_bar = InfoBar.info(
                    title="导入中",
                    content="正在删除现有备忘录...",
                    orient=Qt.Horizontal,
                    isClosable=False,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=-1,
                    parent=self.parent,
                )

            # 删除用户的所有备忘录
            db.delete_memos_by_user(self.user_id)

            # 导入统计
            imported_count = 0

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()
                self.import_info_bar = InfoBar.info(
                    title="导入中",
                    content="正在导入备份数据...",
                    orient=Qt.Horizontal,
                    isClosable=False,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=-1,
                    parent=self.parent,
                )

            # 逐条导入备忘录
            for i, memo in enumerate(memo_list):
                if i % (len(memo_list) // 5 or 1) == 0:
                    if hasattr(self,
                               "import_info_bar") and self.import_info_bar:
                        progress = int((i / len(memo_list)) * 100)
                        self.import_info_bar.close()
                        self.import_info_bar = InfoBar.info(
                            title="导入中",
                            content=f"正在导入数据...{progress}%",
                            orient=Qt.Horizontal,
                            isClosable=False,
                            position=InfoBarPosition.BOTTOM_RIGHT,
                            duration=-1,
                            parent=self.parent,
                        )

                title = memo.get("title", "")
                content = memo.get("content", "")
                category = memo.get("category", "")

                db.create_memo(self.user_id, title, content, category)
                imported_count += 1

            db.close()

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()

            InfoBar.success(
                title="导入成功",
                content=f"已删除{current_count}条现有备忘录，导入{imported_count}条备份备忘录",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self.parent,
            )

            if hasattr(self.parent, "mainWindow") and hasattr(
                    self.parent.mainWindow, "refresh_memo_list"):
                self.parent.mainWindow.refresh_memo_list()

            if hasattr(self.parent, "infoCard") and hasattr(
                    self.parent.infoCard, "memoCountLabel"):
                self.parent.infoCard.memoCountLabel.setText(
                    str(imported_count))

        except Exception as e:
            import traceback

            print(f"导入备份数据出错: {str(e)}")
            print(traceback.format_exc())

            if hasattr(self, "import_info_bar") and self.import_info_bar:
                self.import_info_bar.close()

            InfoBar.error(
                title="导入失败",
                content=f"导入备份数据时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self.parent,
            )

        finally:
            if hasattr(self, "db") and self.db:
                self.db.close()
