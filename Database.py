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
import sys


def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 非打包环境，使用当前路径
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class DatabaseManager:

    def __init__(self, db_name="smart_memo.db"):
        """初始化数据库管理器"""
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

        self.cursor.execute("PRAGMA foreign_keys = ON")

        # 设置时区为本地时区
        self.local_tz = pytz.timezone("Asia/Shanghai")

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
            is_pinned BOOLEAN DEFAULT 0,
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_time DATETIME,
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

        # 创建用户标签表
        create_tag_table = """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tag_name TEXT NOT NULL,
            created_time DATETIME DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, tag_name)  -- 确保每个用户的标签不重复
        );
        """

        self.cursor.execute(create_user_table)
        self.cursor.execute(create_memo_table)
        self.cursor.execute(create_trigger)
        self.cursor.execute(create_todo_table)
        self.cursor.execute(create_tag_table)

        self.conn.commit()

    def create_user(
            self,
            username,
            password,
            face_data=None,
            avatar=resource_path("resource/images/default_avatar.jpg"),
    ):
        """创建用户（密码需要加密）"""

        hashed_pwd = self.hash(password)

        encoded_face_data = None
        if face_data is not None:
            encoded_face_data = self.encrypt(str(face_data))

        try:

            register_time = datetime.now(
                self.local_tz).strftime("%Y-%m-%d %H:%M:%S")
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
        """
        try:
            self.cursor.execute("SELECT * FROM memos WHERE id = ?",
                                (memo_id, ))
            memo = self.cursor.fetchone()

            if not memo:
                return None

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
            self.cursor.execute("DELETE FROM memos WHERE user_id = ?",
                                (user_id, ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"删除备忘录失败: {e}")
            return False

    def delete_memo(self, memo_id):
        """删除指定ID的备忘录"""
        try:
            self.cursor.execute("DELETE FROM memos WHERE id = ?", (memo_id, ))
            self.conn.commit()
            deleted_rows = self.cursor.rowcount
            return deleted_rows > 0
        except sqlite3.Error as e:
            print(f"删除备忘录失败: {e}")
            return False

    def add_todo(self, user_id, task, deadline, category="未分类"):
        """添加待办事项（带分类）"""
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

    def update_todo_pin_status(self, todo_id, is_pinned):
        """更新待办置顶状态"""
        try:
            self.cursor.execute(
                "UPDATE todos SET is_pinned = ? WHERE id = ?",
                (1 if is_pinned else 0, todo_id),
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"更新待办置顶状态失败: {e}")
            return False

    def update_todo_status(self, todo_id, is_done):
        """更新待办完成状态"""
        try:
            if is_done:
                # 标记为已完成，记录完成时间
                self.cursor.execute(
                    "UPDATE todos SET is_done = 1, completed_time = datetime('now', 'localtime') WHERE id = ?",
                    (todo_id, ),
                )
            else:
                # 标记为未完成，清除完成时间
                self.cursor.execute(
                    "UPDATE todos SET is_done = 0, completed_time = NULL WHERE id = ?",
                    (todo_id, ),
                )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"更新待办状态失败: {e}")
            return False

    def get_todos(self, user_id, show_completed=False, category_filter=None):
        """获取用户的待办事项"""
        try:
            query = """SELECT id, task, deadline, category, is_done, is_pinned, created_time, completed_time
                    FROM todos WHERE user_id = ?"""
            params = [user_id]

            if not show_completed:
                query += " AND is_done = 0"

            if category_filter:
                query += " AND category = ?"
                params.append(category_filter)

            # 排序优先级：置顶 > 未完成 > 截止日期
            query += " ORDER BY is_pinned DESC, is_done ASC, deadline ASC, created_time ASC"

            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取待办失败: {e}")
            return []

    def delete_todo(self, todo_id):
        """删除待办事项"""
        try:
            self.cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id, ))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"删除待办失败: {e}")
            return False

    def get_todo_categories(self, user_id):
        """获取用户的所有待办分类"""
        try:
            self.cursor.execute(
                "SELECT DISTINCT category FROM todos WHERE user_id = ?",
                (user_id, ))
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"获取分类失败: {e}")
            return []

    def get_certain_user(self, username):
        """获取特定用户信息"""
        self.cursor.execute("SELECT * FROM users WHERE username = ?",
                            (username, ))
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
        self.cursor.execute("SELECT COUNT(*) FROM memos WHERE user_id = ?",
                            (user_id, ))
        return self.cursor.fetchone()[0]

    def get_todo_count(self, user_id):
        self.cursor.execute("SELECT COUNT(*) FROM todos WHERE user_id = ?",
                            (user_id, ))
        return self.cursor.fetchone()[0]

    def check_password(self, username, password):
        """检查密码是否正确"""
        self.cursor.execute("SELECT password FROM users WHERE username = ?",
                            (username, ))
        result = self.cursor.fetchone()

        if not result:
            return False

        stored_password = result[0]
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
            return False

        # 使用相同参数重新计算哈希
        hash_obj = hashlib.pbkdf2_hmac("sha256",
                                       password.encode("utf-8"),
                                       salt,
                                       100000,
                                       dklen=64)

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
        """更新用户信息"""
        # 首先检查用户是否存在
        self.cursor.execute("SELECT id FROM users WHERE id = ?", (user_id, ))
        if not self.cursor.fetchone():
            print(f"用户ID {user_id} 不存在")
            return False

        if not kwargs:
            print("没有提供要更新的内容")
            return False

        allowed_fields = [
            "username",
            "password",
            "face_data",
            "fingerprint_data",
            "avatar",
        ]

        # 过滤非法字段
        update_fields = {
            k: v
            for k, v in kwargs.items() if k in allowed_fields
        }

        if not update_fields:
            print("没有提供有效的更新字段")
            return False

        if "password" in update_fields:
            update_fields["password"] = self.hash(update_fields["password"])

        if "face_data" in update_fields and update_fields[
                "face_data"] is not None:
            if update_fields["face_data"].startswith(
                    "{") or update_fields["face_data"].startswith("["):
                pass
            else:
                update_fields["face_data"] = self.encrypt(
                    str(update_fields["face_data"]))

        # 构建UPDATE语句
        placeholders = ", ".join(
            [f"{field} = ?" for field in update_fields.keys()])
        query = f"UPDATE users SET {placeholders} WHERE id = ?"

        values = list(update_fields.values())
        values.append(user_id)  # 添加WHERE子句的参数

        try:
            self.cursor.execute(query, values)
            self.conn.commit()

            self.cursor.execute("SELECT id FROM users WHERE id = ?",
                                (user_id, ))
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
            self.cursor.execute("SELECT * FROM memos WHERE user_id = ?",
                                (user_id, ))
        else:
            self.cursor.execute("SELECT * FROM memos")

        memos = self.cursor.fetchall()
        return memos

    def get_recent_memos(self, user_id, limit=10):
        """获取用户最近的备忘录"""
        try:
            self.cursor.execute(
                """
                SELECT id, user_id, created_time, modified_time, title, content, category 
                FROM memos 
                WHERE user_id = ?
                ORDER BY modified_time DESC
                LIMIT ?
                """, (user_id, limit))
            memos = self.cursor.fetchall()

            return [{
                'id': memo[0],
                'user_id': memo[1],
                'created_time': memo[2],
                'modified_time': memo[3],
                'title': self.decrypt(memo[4]),
                'content': self.decrypt(memo[5]),
                'category': memo[6]
            } for memo in memos]

        except Exception as e:
            print(f"获取用户最近备忘录失败: {str(e)}")
            return []

    def get_user_tags(self, user_id):
        """获取用户的所有标签"""
        try:
            self.cursor.execute(
                """SELECT id, tag_name, created_time 
                FROM tags 
                WHERE user_id = ? 
                ORDER BY created_time DESC""", (user_id, ))

            tags = self.cursor.fetchall()
            result = []

            for tag in tags:
                tag_dict = {
                    'id': tag[0],
                    'tag_name': tag[1],
                    'created_time': tag[2]
                }
                result.append(tag_dict)

            return result
        except sqlite3.Error as e:
            print(f"获取用户标签失败: {e}")
            return []

    def add_tag(self, user_id, tag_name):
        """为用户添加一个新标签"""
        try:
            # 标签名称标准化处理：去除首尾空格，转为小写
            tag_name = tag_name.strip()

            if not tag_name:
                print("标签名称不能为空")
                return False, None

            # 检查标签是否已存在
            self.cursor.execute(
                "SELECT id FROM tags WHERE user_id = ? AND tag_name = ?",
                (user_id, tag_name))

            existing_tag = self.cursor.fetchone()
            if existing_tag:
                print(f"标签 '{tag_name}' 已存在")
                return True, existing_tag[0]

            self.cursor.execute(
                "INSERT INTO tags (user_id, tag_name) VALUES (?, ?)",
                (user_id, tag_name))

            self.conn.commit()
            new_tag_id = self.cursor.lastrowid
            print(f"标签 '{tag_name}' 创建成功")
            return True, new_tag_id

        except sqlite3.Error as e:
            print(f"添加标签失败: {e}")
            return False, None

    def account_login(self, username, password):
        """用户登录，返回用户信息字典或None"""
        self.cursor.execute(
            "SELECT id, username, password, avatar, register_time FROM users WHERE username = ?",
            (username, ),
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
        salt = secrets.token_bytes(32)

        hash_obj = hashlib.pbkdf2_hmac(
            "sha256",
            text.encode("utf-8"),
            salt,
            100000,
            dklen=64,
        )

        salt_b64 = base64.b64encode(salt).decode("utf-8")
        hash_b64 = base64.b64encode(hash_obj).decode("utf-8")

        return f"{salt_b64}:{hash_b64}"

    def encrypt(self, text):
        """使用AES-256-CBC模式加密文本"""
        if text is None:
            return None

        plaintext = text.encode("utf-8")

        # 生成随机16字节IV
        iv = os.urandom(16)

        key = b"ThisIsA32ByteKeyForAES256Encrypt"

        cipher = Cipher(algorithms.AES(key),
                        modes.CBC(iv),
                        backend=default_backend())
        encryptor = cipher.encryptor()

        # PKCS7填充
        block_size = 16
        padding_length = block_size - (len(plaintext) % block_size)
        padding = bytes([padding_length]) * padding_length
        padded_data = plaintext + padding

        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        iv_b64 = base64.b64encode(iv).decode("utf-8")
        ciphertext_b64 = base64.b64encode(ciphertext).decode("utf-8")

        return f"{iv_b64}:{ciphertext_b64}"

    def decrypt(self, encrypted_text):
        """解密AES-256-CBC加密的文本"""
        if encrypted_text is None:
            return None

        # 兼容旧格式数据
        if encrypted_text.startswith("ENC_"):
            return encrypted_text[4:]

        try:
            iv_b64, ciphertext_b64 = encrypted_text.split(":")
            iv = base64.b64decode(iv_b64)
            ciphertext = base64.b64decode(ciphertext_b64)

            key = b"ThisIsA32ByteKeyForAES256Encrypt"

            cipher = Cipher(algorithms.AES(key),
                            modes.CBC(iv),
                            backend=default_backend())
            decryptor = cipher.decryptor()

            # 解密
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()

            # 填充
            padding_length = padded_data[-1]
            data = padded_data[:-padding_length]

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

    def get_all_memos_by_user(self, user_id):
        """获取用户的所有备忘录"""
        try:
            self.cursor.execute(
                """
                SELECT id, user_id, created_time, modified_time, title, content, category 
                FROM memos 
                WHERE user_id = ?
                ORDER BY modified_time DESC
                """, (user_id, ))
            memos = self.cursor.fetchall()

            return [{
                'id': memo[0],
                'user_id': memo[1],
                'created_time': memo[2],
                'modified_time': memo[3],
                'title': self.decrypt(memo[4]),
                'content': self.decrypt(memo[5]),
                'category': memo[6]
            } for memo in memos]

        except Exception as e:
            print(f"获取用户备忘录失败: {str(e)}")
            return []

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
