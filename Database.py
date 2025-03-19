import sqlite3
import time
from datetime import datetime
import pytz

# TODO: 备忘录信息的类别还没有定义，需要添加一个枚举类别。

class DatabaseManager:
    def __init__(self, db_name='smart_memo.db'):
        """初始化数据库管理器"""
        # 创建数据库连接
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        
        # 启用外键约束
        self.cursor.execute("PRAGMA foreign_keys = ON")

        # 设置时区为本地时区
        self.local_tz = pytz.timezone('Asia/Shanghai') # 本地时区
        
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
            fingerprint_data TEXT,   -- 可选字段
            avatar TEXT              -- 存储头像路径
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
        
        # 提交更改
        self.conn.commit()
    
    def create_user(self, username, password, face_data=None, fingerprint_data=None, avatar="resource/default_avatar.jpg"):
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
        
        encoded_fingerprint_data = None
        if fingerprint_data is not None:
            # 这里可以添加对指纹数据的处理/加密
            encoded_fingerprint_data = self.encrypt(str(fingerprint_data))
        
        try:
            self.cursor.execute("""
                INSERT INTO users 
                (username, password, face_data, fingerprint_data, avatar)
                VALUES (?, ?, ?, ?, ?)
            """, (username, hashed_pwd, encoded_face_data, encoded_fingerprint_data, avatar))
            
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
        
        self.cursor.execute("""
            INSERT INTO memos 
            (user_id, title, content, category)
            VALUES (?, ?, ?, ?)
        """, (user_id, encrypted_title, encrypted_content, category))
        self.conn.commit()
        print("备忘录创建成功")
        return self.cursor.lastrowid
    
    def get_certain_user(self, username):
        """获取特定用户信息"""
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = self.cursor.fetchone()
        user_dict = {
            "id": user_data[0],
            "username": user_data[1],
            "avatar": user_data[5]
        }
        return user_dict
    
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
        
    def update_user_avatar(self, user_id, avatar_path):
        """更新用户头像路径"""
        self.cursor.execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar_path, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
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
        hashed_pwd = self.hash(password)
        
        self.cursor.execute("SELECT id, username, avatar FROM users WHERE username = ? AND password = ?", 
                            (username, hashed_pwd))
        user_data = self.cursor.fetchone()
        
        if user_data:
            print(f"用户 {username} 登录成功")
            # 转换为字典格式，便于使用和理解
            user_dict = {
                "id": user_data[0],
                "username": user_data[1],
                "avatar": user_data[2]
            }
            return user_dict
        else:
            print("用户名或密码错误")
            return None
    
    def hash(self, text):
        """密码哈希函数（示例实现）"""
        # TODO: 实现真正的安全哈希
        return text[::-1]  # 简单反转演示
    
    def encrypt(self, text):
        """加密函数（示例实现）"""
        # TODO: 实现真正的加密
        return f"ENC_{text}"  # 示例加密
    
    def decrypt(self, encrypted_text):
        """解密函数（示例实现）"""
        # TODO: 实现真正的解密
        return encrypted_text[4:] if encrypted_text.startswith("ENC_") else encrypted_text
    
    def format_datetime(self, datetime_str):
        """格式化日期时间为易读格式"""
        if datetime_str:
            try:
                dt_obj = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                return dt_obj.strftime('%Y年%m月%d日 %H:%M:%S')
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
    db_name = 'test_smart_memo.db'
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
        print(f"""
        ID: {memo[0]}
        用户ID: {memo[1]}
        创建时间: {memo[2]}
        修改时间: {memo[3]}
        标题: {db.decrypt(memo[4])}
        内容: {db.decrypt(memo[5])}
        类别: {memo[6]}
        """)
        
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
        print(f"""
        ID: {updated_memo[0]}
        用户ID: {updated_memo[1]}
        创建时间: {updated_memo[2]}
        修改时间: {updated_memo[3]} 
        标题: {db.decrypt(updated_memo[4])}
        内容: {db.decrypt(updated_memo[5])}
        类别: {updated_memo[6]}
        """)
        
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