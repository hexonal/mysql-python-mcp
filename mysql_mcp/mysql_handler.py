import os
import re
import asyncio
import aiomysql
import json
from typing import List, Dict, Any, Optional
import logging


class MySQLHandler:
    """MySQL数据库处理器，提供安全的数据库操作"""
    
    def __init__(self):
        mysql_host = os.getenv('MYSQL_HOST')
        if not mysql_host:
            raise ValueError("MYSQL_HOST环境变量未设置")
        
        if ':' in mysql_host:
            self.host, port_str = mysql_host.split(':', 1)
            self.port = int(port_str)
        else:
            self.host = mysql_host
            self.port = 3306
            
        self.user = os.getenv('MYSQL_USER')
        if not self.user:
            raise ValueError("MYSQL_USER环境变量未设置")
            
        self.password = os.getenv('MYSQL_PASSWORD')
        if not self.password:
            raise ValueError("MYSQL_PASSWORD环境变量未设置")
            
        self.database = os.getenv('MYSQL_DATABASE')
        if not self.database:
            raise ValueError("MYSQL_DATABASE环境变量未设置")
            
        self.allow_dangerous_operations = os.getenv('MYSQL_ALLOW_DANGEROUS', 'false').lower() == 'true'
        
        # 危险操作的关键词列表
        self.dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE',
            'REPLACE', 'GRANT', 'REVOKE', 'FLUSH', 'RESET', 'START', 'STOP',
            'KILL', 'CHANGE', 'SET', 'LOAD', 'LOCK', 'UNLOCK'
        ]
        
        self.logger = logging.getLogger(__name__)
    
    async def get_connection(self) -> aiomysql.Connection:
        """获取数据库连接"""
        try:
            connection = await aiomysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                autocommit=False,
                charset='utf8mb4'
            )
            return connection
        except Exception as e:
            self.logger.error(f"连接数据库失败: {e}")
            raise Exception(f"无法连接到数据库: {str(e)}")
    
    def is_query_safe(self, query: str) -> tuple[bool, str]:
        """检查查询是否安全"""
        # 如果允许危险操作，直接返回安全
        if self.allow_dangerous_operations:
            return True, ""
        
        # 清理查询语句（移除注释和多余空格）
        cleaned_query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)  # 移除注释
        cleaned_query = re.sub(r'--.*?$', '', cleaned_query, flags=re.MULTILINE)  # 移除行注释
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query.strip())  # 规范化空格
        query_upper = cleaned_query.upper()
        
        # 检查查询是否以安全的关键词开头
        safe_start_keywords = ['SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'DESC']
        
        # 获取第一个词（即SQL命令）
        first_word = query_upper.split()[0] if query_upper.split() else ""
        
        if first_word not in safe_start_keywords:
            return False, f"不允许的SQL命令: {first_word}。仅允许SELECT、SHOW、DESCRIBE、EXPLAIN查询，除非在环境变量中启用危险操作。"
        
        # 对于SELECT查询，进行额外的安全检查，防止子查询中的危险操作
        if first_word == 'SELECT':
            # 检查是否包含危险的SQL函数或语句
            dangerous_patterns = [
                r'\bINTO\s+OUTFILE\b',      # SELECT INTO OUTFILE
                r'\bINTO\s+DUMPFILE\b',     # SELECT INTO DUMPFILE  
                r'\bLOAD_FILE\s*\(',        # LOAD_FILE函数
                r'\bUNION\s+.*\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b', # UNION注入
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, query_upper, re.IGNORECASE):
                    return False, f"检测到潜在危险的SQL模式，查询被拒绝。"
        
        return True, ""
    
    def validate_database_context(self, query: str) -> tuple[bool, str]:
        """验证查询是否在允许的数据库上下文中执行"""
        query_upper = query.strip().upper()
        
        # 检查是否尝试切换数据库
        if 'USE ' in query_upper:
            return False, f"不允许切换数据库。只能在配置的数据库 '{self.database}' 中操作。"
        
        # 检查是否尝试访问其他数据库
        # 这个检查比较复杂，这里做简单的模式匹配
        database_patterns = [
            r'\b(?:FROM|JOIN|INTO|UPDATE)\s+([^\s\.]+)\.', # 表名前有数据库名
            r'\bUSE\s+([^\s;]+)',  # USE database
        ]
        
        for pattern in database_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if match.lower() != self.database.lower():
                    return False, f"不允许访问其他数据库 '{match}'。只能在配置的数据库 '{self.database}' 中操作。"
        
        return True, ""
    
    async def list_databases(self) -> List[str]:
        """列出所有数据库（仅显示当前用户有权限的）"""
        connection = None
        try:
            connection = await self.get_connection()
            async with connection.cursor() as cursor:
                await cursor.execute("SHOW DATABASES")
                databases = await cursor.fetchall()
                db_list = [db[0] for db in databases]
                # 突出显示当前配置的数据库
                result = []
                for db in db_list:
                    if db == self.database:
                        result.append(f"{db} (当前配置的数据库)")
                    else:
                        result.append(db)
                return result
        except Exception as e:
            self.logger.error(f"列出数据库失败: {e}")
            raise Exception(f"获取数据库列表失败: {str(e)}")
        finally:
            if connection:
                await connection.ensure_closed()
    
    async def list_tables(self) -> List[str]:
        """列出当前数据库中的所有表"""
        connection = None
        try:
            connection = await self.get_connection()
            async with connection.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                tables = await cursor.fetchall()
                return [table[0] for table in tables]
        except Exception as e:
            self.logger.error(f"列出表失败: {e}")
            raise Exception(f"获取表列表失败: {str(e)}")
        finally:
            if connection:
                await connection.ensure_closed()
    
    async def describe_table(self, table_name: str) -> str:
        """描述表结构"""
        connection = None
        try:
            # 验证表名（防止SQL注入）
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
                raise Exception("无效的表名格式")
            
            connection = await self.get_connection()
            async with connection.cursor() as cursor:
                await cursor.execute(f"DESCRIBE `{table_name}`")
                columns = await cursor.fetchall()
                
                if not columns:
                    return f"表 '{table_name}' 不存在或无权限访问"
                
                # 格式化输出
                result = f"表 '{table_name}' 的结构:\n"
                result += "-" * 80 + "\n"
                result += f"{'字段名':<20} {'类型':<20} {'允许NULL':<10} {'键':<10} {'默认值':<15} {'额外':<15}\n"
                result += "-" * 80 + "\n"
                
                for column in columns:
                    field, type_info, null, key, default, extra = column
                    default_str = str(default) if default is not None else "NULL"
                    result += f"{field:<20} {type_info:<20} {null:<10} {key:<10} {default_str:<15} {extra:<15}\n"
                
                return result
        except Exception as e:
            self.logger.error(f"描述表结构失败: {e}")
            raise Exception(f"获取表 '{table_name}' 结构失败: {str(e)}")
        finally:
            if connection:
                await connection.ensure_closed()
    
    async def execute_query(self, query: str) -> str:
        """执行SQL查询"""
        connection = None
        try:
            # 安全性检查
            is_safe, safety_msg = self.is_query_safe(query)
            if not is_safe:
                return f"查询被拒绝: {safety_msg}"
            
            # 数据库上下文检查
            is_valid_context, context_msg = self.validate_database_context(query)
            if not is_valid_context:
                return f"查询被拒绝: {context_msg}"
            
            connection = await self.get_connection()
            async with connection.cursor() as cursor:
                await cursor.execute(query)
                
                # 如果是SELECT查询，获取结果
                if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
                    results = await cursor.fetchall()
                    
                    if not results:
                        return json.dumps({"status": "success", "message": "查询执行成功，但没有返回结果", "data": []}, ensure_ascii=False)
                    
                    # 获取列名
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    # 转换为字典列表格式
                    data = []
                    for row in results:
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i] if i < len(columns) else f"column_{i}"
                            # 处理特殊类型
                            if value is None:
                                row_dict[col_name] = None
                            elif hasattr(value, 'isoformat'):  # datetime对象
                                row_dict[col_name] = value.isoformat()
                            else:
                                row_dict[col_name] = value
                        data.append(row_dict)
                    
                    return json.dumps({
                        "status": "success",
                        "message": f"查询执行成功，返回 {len(data)} 行结果",
                        "columns": columns,
                        "data": data
                    }, ensure_ascii=False)
                else:
                    # 对于非SELECT查询（如果允许的话）
                    affected_rows = cursor.rowcount
                    await connection.commit()
                    return f"查询执行成功，影响了 {affected_rows} 行。"
                    
        except Exception as e:
            if connection:
                await connection.rollback()
            self.logger.error(f"执行查询失败: {e}")
            return f"查询执行失败: {str(e)}"
        finally:
            if connection:
                await connection.ensure_closed()