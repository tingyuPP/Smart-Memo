# coding:utf-8
from obs import ObsClient
import os
import traceback
import tempfile
import uuid
import datetime


class CloudStorageManager:
    """云存储管理器，处理文件上传和URL生成"""

    @staticmethod
    def get_temp_file_path(prefix="memo", suffix=".png"):
        """生成临时文件路径"""
        temp_dir = tempfile.gettempdir()
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"{prefix}_{unique_id}_{timestamp}{suffix}"
        return os.path.join(temp_dir, file_name), file_name

    @staticmethod
    def upload_to_obs(file_path, file_name=None):
        """上传文件到华为云OBS并返回URL"""
        try:
            # 华为云OBS配置
            ak = "FTCMA0RFFEFYAHZCTUNR"
            sk = "DtOPu5ExOARQuMZHAGewDVzryaH1ht7gSWlflsJ5"
            endpoint = "obs.cn-east-3.myhuaweicloud.com"
            server = f"https://{endpoint}"
            bucket_name = "mypicturebed"

            # 如果没有提供文件名，则从路径中提取
            if not file_name:
                file_name = os.path.basename(file_path)

            # 创建OBS客户端
            obs_client = ObsClient(
                access_key_id=ak, secret_access_key=sk, server=server
            )

            try:
                # 读取文件内容
                with open(file_path, "rb") as f:
                    file_content = f.read()

                # 上传到OBS
                object_key = f"memo_share/{file_name}"
                resp = obs_client.putObject(bucket_name, object_key, file_content)

                # 检查上传是否成功
                if resp.status < 300:
                    # 返回可访问的URL - 使用虚拟主机风格URL
                    image_url = f"https://{bucket_name}.{endpoint}/{object_key}"
                    return image_url
                else:
                    print(f"上传失败: {resp.errorCode} - {resp.errorMessage}")
                    return None
            finally:
                # 关闭OBS客户端
                obs_client.close()

        except Exception as e:
            print(f"上传到OBS时发生错误: {str(e)}")
            print(traceback.format_exc())
            return None
