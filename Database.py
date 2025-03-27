import sqlite3
import time
from datetime import datetime
import pytz
import hashlib
import secrets
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os


# TODO: 备忘录信息的类别还没有定义，需要添加一个枚举类别。


class DatabaseManager:
    def __init__(self, db_name="smart_memo.db"):
        """初始化数据库管理器"""
        # 创建数据库连接
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

        # 启用外键约束
        self.cursor.execute("PRAGMA foreign_keys = ON")

        # 设置时区为本地时区
        self.local_tz = pytz.timezone("Asia/Shanghai")  # 本地时区

        # 初始化数据库表
        self._initialize_database()

    def _initialize_database(self):
        """创建必要的表和触发器"""
        # 创建用户表
        create_user_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,  -- 存储加密后的密码
            face_data TEXT,          -- 可选字段
            avatar TEXT,              -- 存储头像路径
            register_time DATETIME DEFAULT (datetime('now', 'localtime'))  -- 用户注册时间
        );
        """

        # 创建备忘录表
        create_memo_table = """
        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            created_time DATETIME DEFAULT (datetime('now', 'localtime')),
            modified_time DATETIME DEFAULT (datetime('now', 'localtime')),
            title TEXT NOT NULL,     -- 加密存储
            content TEXT NOT NULL,   -- 加密存储
            category TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """

        # 创建待办表
        create_todo_table = """
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            deadline DATETIME NOT NULL,
            category TEXT DEFAULT '未分类',
            is_done BOOLEAN DEFAULT FALSE,
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """

        # 创建修改时间触发器 - 使用localtime
        create_trigger = """
        CREATE TRIGGER IF NOT EXISTS update_memo_time 
        AFTER UPDATE ON memos 
        BEGIN
            UPDATE memos SET modified_time = datetime('now', 'localtime') WHERE id = OLD.id;
        END;
        """

        # 执行SQL语句
        self.cursor.execute(create_user_table)
        self.cursor.execute(create_memo_table)
        self.cursor.execute(create_trigger)
        self.cursor.execute(create_todo_table)

        # 提交更改
        self.conn.commit()

    def create_user(
        self,
        username,
        password,
        face_data=None,
        avatar="resource/default_avatar.jpg",
    ):
        """创建用户（密码需要加密）

        参数:
            username: 用户名
            password: 密码（将被加密存储）
            face_data: 人脸识别数据（可选）
            fingerprint_data: 指纹识别数据（可选）
            avatar: 用户头像路径（可选）

        返回:
            bool: 创建成功返回True，失败返回False
        """
        # 密码加密
        hashed_pwd = self.hash(password)

        # 处理生物识别数据（如果有的话）
        encoded_face_data = None
        if face_data is not None:
            # 这里可以添加对人脸数据的处理/加密
            encoded_face_data = self.encrypt(str(face_data))

        try:

            register_time = datetime.now(self.local_tz).strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                """
                INSERT INTO users 
                (username, password, face_data, avatar, register_time)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    username,
                    hashed_pwd,
                    encoded_face_data,
                    avatar,
                    register_time,
                ),
            )

            self.conn.commit()
            print(f"用户 {username} 创建成功")
            return True
        except sqlite3.IntegrityError:
            print("用户名已存在")
            return False
        except Exception as e:
            print(f"创建用户时出错: {e}")
            return False

    def create_memo(self, user_id, title, content, category):
        """创建备忘录"""
        # 实际应加密标题和内容
        encrypted_title = self.encrypt(title)
        encrypted_content = self.encrypt(content)

        self.cursor.execute(
            """
            INSERT INTO memos 
            (user_id, title, content, category)
            VALUES (?, ?, ?, ?)
        """,
            (user_id, encrypted_title, encrypted_content, category),
        )
        self.conn.commit()
        print("备忘录创建成功")
        return self.cursor.lastrowid

    def get_memo_by_id(self, memo_id):
        """
        根据备忘录ID获取完整的备忘录信息

        参数:
            memo_id: 备忘录ID

        返回:
            dict: 包含备忘录完整信息的字典，解密后的数据
            {
                'id': 备忘录ID,
                'user_id': 用户ID,
                'created_time': 创建时间,
                'modified_time': 修改时间,
                'title': 解密后的标题,
                'content': 解密后的内容,
                'category': 类别
            }
            如果不存在返回None
        """
        try:
            self.cursor.execute("SELECT * FROM memos WHERE id = ?", (memo_id,))
            memo = self.cursor.fetchone()

            if not memo:
                return None

            # 返回解密后的数据
            return {
                "id": memo[0],
                "user_id": memo[1],
                "created_time": memo[2],
                "modified_time": memo[3],
                "title": self.decrypt(memo[4]),
                "content": self.decrypt(memo[5]),
                "category": memo[6],
            }
        except Exception as e:
            print(f"获取备忘录数据时出错: {str(e)}")
            return None

    def delete_memos_by_user(self, user_id):
        """删除用户的所有备忘录"""
        try:
            self.cursor.execute("DELETE FROM memos WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"删除备忘录失败: {e}")
            return False

    def delete_memo(self, memo_id):
        """删除指定ID的备忘录

        参数:
            memo_id: 备忘录ID

        返回:
            bool: 删除成功返回True，失败返回False
        """
        try:
            self.cursor.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
            self.conn.commit()
            deleted_rows = self.cursor.rowcount
            return deleted_rows > 0
        except sqlite3.Error as e:
            print(f"删除备忘录失败: {e}")
            return False

    def add_todo(self, user_id, task, deadline, category="未分类"):
        """添加待办事项（带分类）

        Args:
            user_id: 用户ID
            task: 任务内容
            deadline: 截止时间 (格式: 'YYYY-MM-DD HH:MM')
            category: 任务分类 (默认'未分类')

        Returns:
            int: 新创建的待办ID
        """
        try:
            self.cursor.execute(
                """INSERT INTO todos 
                (user_id, task, deadline, category) 
                VALUES (?, ?, ?, ?)""",
                (user_id, task, deadline, category),
            )
            self.conn.commit()
            print("待办创建成功")
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"添加待办失败: {e}")
            return None

    def get_todos(self, user_id, show_completed=False, category_filter=None):
        """获取用户的待办事项

        Args:
            user_id: 用户ID
            show_completed: 是否显示已完成事项
            category_filter: 按分类筛选 (None表示不过滤)

        Returns:
            list: 待办事项列表，每个元素为元组:
                (id, task, deadline, category, is_done, created_time)
        """
        try:
            query = """SELECT id, task, deadline, category, is_done, created_time 
                    FROM todos WHERE user_id = ?"""
            params = [user_id]

            if not show_completed:
                query += " AND is_done = 0"

            if category_filter:
                query += " AND category = ?"
                params.append(category_filter)

            query += " ORDER BY deadline, created_time"

            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取待办失败: {e}")
            return []

    def update_todo_status(self, todo_id, is_done):
        """更新待办完成状态

        Args:
            todo_id: 待办ID
            is_done: 是否完成 (True/False)

        Returns:
            bool: 是否更新成功
        """
        try:
            self.cursor.execute(
                "UPDATE todos SET is_done = ? WHERE id = ?", (int(is_done), todo_id)
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"更新待办状态失败: {e}")
            return False

    def delete_todo(self, todo_id):
        """删除待办事项

        Args:
            todo_id: 待办ID

        Returns:
            bool: 是否删除成功
        """
        try:
            self.cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"删除待办失败: {e}")
            return False

    def get_todo_categories(self, user_id):
        """获取用户的所有待办分类

        Args:
            user_id: 用户ID

        Returns:
            list: 分类名称列表
        """
        try:
            self.cursor.execute(
                "SELECT DISTINCT category FROM todos WHERE user_id = ?", (user_id,)
            )
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"获取分类失败: {e}")
            return []

    def get_certain_user(self, username):
        """获取特定用户信息"""
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = self.cursor.fetchone()
        user_dict = {
            "id": user_data[0],
            "username": user_data[1],
            "avatar": user_data[4],
            "register_time": user_data[5],
        }
        return user_dict

    def get_users_with_face_data(self):
        """获取所有具有人脸识别数据的用户"""
        self.cursor.execute(
            "SELECT id, username, face_data, register_time FROM users WHERE face_data IS NOT NULL"
        )
        users = self.cursor.fetchall()

        # 将元组列表转换为字典列表
        result = []
        for user in users:
            user_dict = {
                "id": user[0],
                "username": user[1],
                "face_data": user[2],
                "register_time": user[3],
            }
            result.append(user_dict)

        return result

    def get_memo_count(self, user_id):
        """获取用户的备忘录数量"""
        self.cursor.execute("SELECT COUNT(*) FROM memos WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()[0]

    def check_password(self, username, password):
        """检查密码是否正确"""
        self.cursor.execute(
            "SELECT password FROM users WHERE username = ?", (username,)
        )
        result = self.cursor.fetchone()

        if not result:
            return False

        stored_password = result[0]

        # 验证密码
        return self.verify_password(password, stored_password)

    def verify_password(self, password, stored_password):
        """验证密码是否与存储的哈希匹配"""
        import hashlib
        import base64

        # 从存储的字符串中分离盐和哈希
        try:
            salt_b64, hash_b64 = stored_password.split(":")
            salt = base64.b64decode(salt_b64)
            stored_hash = base64.b64decode(hash_b64)
        except (ValueError, base64.Error):
            # 如果格式不正确或解码失败，返回False
            return False

        # 使用相同参数重新计算哈希
        hash_obj = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 100000, dklen=64
        )

        # 使用安全的比较方法，防止时序攻击
        import hmac

        return hmac.compare_digest(hash_obj, stored_hash)

    def update_memo(self, memo_id, title=None, content=None, category=None):
        """更新备忘录内容"""
        update_parts = []
        values = []

        if title is not None:
            encrypted_title = self.encrypt(title)
            update_parts.append("title = ?")
            values.append(encrypted_title)

        if content is not None:
            encrypted_content = self.encrypt(content)
            update_parts.append("content = ?")
            values.append(encrypted_content)

        if category is not None:
            update_parts.append("category = ?")
            values.append(category)

        if not update_parts:
            print("没有提供要更新的内容")
            return False

        query = f"UPDATE memos SET {', '.join(update_parts)} WHERE id = ?"
        values.append(memo_id)

        self.cursor.execute(query, values)
        self.conn.commit()

        if self.cursor.rowcount > 0:
            print(f"备忘录 ID {memo_id} 更新成功")
            return True
        else:
            print(f"备忘录 ID {memo_id} 不存在或未更改")
            return False

    def update_user(self, user_id, **kwargs):
        """
        更新用户信息

        参数:
            user_id: 要更新的用户ID
            **kwargs: 需要更新的字段和值的键值对
                    可以包含: username, password, face_data, fingerprint_data, avatar

        返回:
            bool: 更新成功返回True，失败返回False
        """
        # 首先检查用户是否存在
        self.cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not self.cursor.fetchone():
            print(f"用户ID {user_id} 不存在")
            return False

        if not kwargs:
            print("没有提供要更新的内容")
            return False

        # 可更新字段的白名单
        allowed_fields = [
            "username",
            "password",
            "face_data",
            "fingerprint_data",
            "avatar",
        ]

        # 过滤非法字段
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not update_fields:
            print("没有提供有效的更新字段")
            return False

        # 特殊处理密码字段 - 如果更新密码，需要先加密
        if "password" in update_fields:
            update_fields["password"] = self.hash(update_fields["password"])

        # 特殊处理生物识别数据 - 如果提供，需要加密
        if "face_data" in update_fields and update_fields["face_data"] is not None:
            # 如果是JSON格式的特征数据，可能很大，避免加密
            if update_fields["face_data"].startswith("{") or update_fields[
                "face_data"
            ].startswith("["):
                # 直接保存JSON数据，不加密
                pass
            else:
                # 对路径等简单数据进行加密
                update_fields["face_data"] = self.encrypt(
                    str(update_fields["face_data"])
                )

        if (
            "fingerprint_data" in update_fields
            and update_fields["fingerprint_data"] is not None
        ):
            update_fields["fingerprint_data"] = self.encrypt(
                str(update_fields["fingerprint_data"])
            )

        # 构建UPDATE语句
        placeholders = ", ".join([f"{field} = ?" for field in update_fields.keys()])
        query = f"UPDATE users SET {placeholders} WHERE id = ?"

        # 创建参数列表
        values = list(update_fields.values())
        values.append(user_id)  # 添加WHERE子句的参数

        # 执行更新
        try:
            self.cursor.execute(query, values)
            self.conn.commit()

            # 重新检查用户而不依赖rowcount
            self.cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if self.cursor.fetchone():
                print(f"用户ID {user_id} 更新成功")
                return True
            else:
                print(f"更新后无法找到用户ID {user_id}")
                return False
        except Exception as e:
            print(f"更新用户时出错: {e}")
            return False

    def get_memos(self, user_id=None):
        """获取备忘录列表，可选按用户ID过滤"""
        if user_id:
            self.cursor.execute("SELECT * FROM memos WHERE user_id = ?", (user_id,))
        else:
            self.cursor.execute("SELECT * FROM memos")

        memos = self.cursor.fetchall()
        return memos

    def account_login(self, username, password):
        """用户登录，返回用户信息字典或None"""
        # 首先根据用户名查找用户
        self.cursor.execute(
            "SELECT id, username, password, avatar, register_time FROM users WHERE username = ?",
            (username,),
        )
        user_data = self.cursor.fetchone()

        if not user_data:
            print(f"用户 {username} 不存在")
            return None

        # 验证密码
        stored_password = user_data[2]
        if self.verify_password(password, stored_password):
            print(f"用户 {username} 登录成功")
            # 转换为字典格式，便于使用和理解
            user_dict = {
                "id": user_data[0],
                "username": user_data[1],
                "avatar": user_data[3],
                "register_time": user_data[4],
            }
            return user_dict
        else:
            print("密码错误")
            return None

    def hash(self, text):
        # 生成一个随机盐值
        salt = secrets.token_bytes(32)  # 使用32字节(256位)的随机盐

        # 使用PBKDF2-HMAC-SHA256算法，迭代100,000次
        hash_obj = hashlib.pbkdf2_hmac(
            "sha256",  # 哈希算法
            text.encode("utf-8"),  # 密码编码为bytes
            salt,  # 盐值
            100000,  # 迭代次数
            dklen=64,  # 派生密钥长度为64字节(512位)
        )

        # 将盐和哈希结果编码为base64字符串
        salt_b64 = base64.b64encode(salt).decode("utf-8")
        hash_b64 = base64.b64encode(hash_obj).decode("utf-8")

        # 返回格式为"salt:hash"的字符串
        return f"{salt_b64}:{hash_b64}"

    def encrypt(self, text):
        """
        使用AES-256-CBC模式加密文本

        参数:
            text: 要加密的文本

        返回:
            str: base64编码的加密数据，格式为 'iv:ciphertext'
        """

        # 检查输入
        if text is None:
            return None

        # 将文本转换为字节
        plaintext = text.encode("utf-8")

        # 生成随机16字节IV
        iv = os.urandom(16)

        # 加密密钥，使用固定密钥（生产环境应从安全存储中获取）
        key = b"ThisIsA32ByteKeyForAES256Encrypt"
        # print("len:",len(key))

        # 创建加密对象
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # PKCS7填充
        block_size = 16
        padding_length = block_size - (len(plaintext) % block_size)
        padding = bytes([padding_length]) * padding_length
        padded_data = plaintext + padding

        # 加密
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # 编码为Base64字符串（IV和密文）
        iv_b64 = base64.b64encode(iv).decode("utf-8")
        ciphertext_b64 = base64.b64encode(ciphertext).decode("utf-8")

        # 返回格式为 "iv:ciphertext" 的字符串
        return f"{iv_b64}:{ciphertext_b64}"

    def decrypt(self, encrypted_text):
        """
        解密AES-256-CBC加密的文本

        参数:
            encrypted_text: 格式为 'iv:ciphertext' 的加密文本

        返回:
            str: 解密后的原始文本
        """
        # 检查输入
        if encrypted_text is None:
            return None

        # 兼容旧格式数据
        if encrypted_text.startswith("ENC_"):
            return encrypted_text[4:]

        try:
            # 分离IV和密文
            iv_b64, ciphertext_b64 = encrypted_text.split(":")
            iv = base64.b64decode(iv_b64)
            ciphertext = base64.b64decode(ciphertext_b64)

            # 解密密钥，与加密使用相同的密钥
            key = b"ThisIsA32ByteKeyForAES256Encrypt"

            # 创建解密对象
            cipher = Cipher(
                algorithms.AES(key), modes.CBC(iv), backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # 解密
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()

            # 移除PKCS7填充
            padding_length = padded_data[-1]
            data = padded_data[:-padding_length]

            # 将字节转换回文本
            return data.decode("utf-8")
        except Exception as e:
            print(f"解密错误: {e}")
            return encrypted_text  # 返回原始文本作为降级处理

    def format_datetime(self, datetime_str):
        """格式化日期时间为易读格式"""
        if datetime_str:
            try:
                dt_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                return dt_obj.strftime("%Y年%m月%d日 %H:%M:%S")
            except ValueError:
                return datetime_str
        return datetime_str

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


# 使用测试
if __name__ == "__main__":
    import time
    import os

    # 删除旧的测试数据库
    db_name = "smart_memo.db"
    if os.path.exists(db_name):
        os.remove(db_name)
        print(f"已删除旧的测试数据库 {db_name}")

    # 创建全新的测试数据库
    db = DatabaseManager(db_name)

    try:
        # 创建测试用户
        success = db.create_user("test_user", "secure_password")
        if not success:
            print("创建用户失败！")
            exit(1)

        # 创建测试备忘录
        memo_id = db.create_memo(1, "购物清单", "1. 牛奶\n2. 鸡蛋", "个人")
        print(f"创建的备忘录ID: {memo_id}")

        # 查询初始数据
        memos = db.get_memos(user_id=1)
        if not memos:
            print("没有找到备忘录！")
            exit(1)

        memo = memos[0]

        print("\n创建后的备忘录数据：")
        print(
            f"""
        ID: {memo[0]}
        用户ID: {memo[1]}
        创建时间: {memo[2]}
        修改时间: {memo[3]}
        标题: {db.decrypt(memo[4])}
        内容: {db.decrypt(memo[5])}
        类别: {memo[6]}
        """
        )

        # 保存原始修改时间以便后续比较
        original_modified_time = memo[3]

        # 等待一段时间
        print("等待2秒后修改备忘录...")
        time.sleep(2)

        # 修改备忘录并检查是否成功
        success = db.update_memo(memo_id, content="1. 牛奶\n2. 鸡蛋\n3. 面包")
        if not success:
            print(f"修改备忘录 ID {memo_id} 失败！")

        # 查询更新后的数据
        memos = db.get_memos(user_id=1)
        if not memos:
            print("无法获取更新后的备忘录！")
            exit(1)

        updated_memo = memos[0]

        print("\n修改后的备忘录数据：")
        print(
            f"""
        ID: {updated_memo[0]}
        用户ID: {updated_memo[1]}
        创建时间: {updated_memo[2]}
        修改时间: {updated_memo[3]} 
        标题: {db.decrypt(updated_memo[4])}
        内容: {db.decrypt(updated_memo[5])}
        类别: {updated_memo[6]}
        """
        )

        # 验证修改时间是否有变化
        if original_modified_time != updated_memo[3]:
            print("\n✅ 成功：修改时间已更新!")
        else:
            print("\n❌ 失败：修改时间未更新!")

        print(f"原始修改时间: {original_modified_time}")
        print(f"更新后修改时间: {updated_memo[3]}")

    finally:
        # 关闭连接
        db.close()
