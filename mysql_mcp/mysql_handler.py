import os
import re
import asyncio
import aiomysql
import json
import sqlparse
import locale
from decimal import Decimal
from sqlparse import sql, tokens as T
from typing import List, Dict, Any, Optional
import logging


class DecimalEncoder(json.JSONEncoder):
    """自定义JSON编码器，用于处理Decimal类型"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # 将Decimal转换为float，如果需要保持精度可以转为string
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class MySQLHandler:
    """MySQL数据库处理器，提供安全的数据库操作"""
    
    def __init__(self):
        # 检测系统语言环境
        self.is_chinese = self._detect_chinese_locale()
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
    
    def _detect_chinese_locale(self) -> bool:
        """检测是否为中文语言环境"""
        try:
            # 尝试获取系统语言环境
            lang = locale.getdefaultlocale()[0]
            if lang and ('zh' in lang.lower() or 'chinese' in lang.lower()):
                return True
            
            # 检查环境变量
            for env_var in ['LANG', 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES']:
                lang_env = os.getenv(env_var, '')
                if lang_env and ('zh' in lang_env.lower() or 'chinese' in lang_env.lower()):
                    return True
            
            return False
        except Exception:
            # 如果检测失败，默认使用英文
            return False
    
    def _get_message(self, zh_msg: str, en_msg: str) -> str:
        """根据语言环境返回对应消息"""
        return zh_msg if self.is_chinese else en_msg
    
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
        """使用AST语法树检查查询是否安全"""
        # 如果允许危险操作，直接返回安全
        if self.allow_dangerous_operations:
            return True, ""
        
        try:
            # 解析SQL为AST
            parsed = sqlparse.parse(query)
            
            if not parsed:
                return False, "无法解析SQL查询"
            
            # 检查每个SQL语句
            for statement in parsed:
                is_safe, error_msg = self._check_statement_safety(statement)
                if not is_safe:
                    return False, error_msg
            
            return True, ""
            
        except Exception as e:
            # 如果解析失败，出于安全考虑拒绝查询
            return False, f"SQL解析失败，查询被拒绝: {str(e)}"
    
    def _check_statement_safety(self, statement: sql.Statement) -> tuple[bool, str]:
        """检查单个SQL语句的安全性"""
        # 获取语句类型（第一个非空白token）
        first_token = None
        for token in statement.tokens:
            if not token.is_whitespace:
                first_token = token
                break
        
        if not first_token:
            return False, "空的SQL语句"
        
        # 获取SQL命令关键字
        sql_keyword = self._extract_sql_keyword(first_token)
        
        # 定义允许的SQL命令
        safe_commands = {'SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN'}
        
        if sql_keyword not in safe_commands:
            error_msg = self._get_message(
                f"不允许的SQL命令: {sql_keyword}。仅允许SELECT、SHOW、DESCRIBE、EXPLAIN查询，除非在环境变量中启用危险操作。",
                f"Disallowed SQL command: {sql_keyword}. Only SELECT, SHOW, DESCRIBE, EXPLAIN queries are allowed unless dangerous operations are enabled via environment variable."
            )
            return False, error_msg
        
        # 对SELECT语句进行深度安全检查
        if sql_keyword == 'SELECT':
            return self._check_select_safety(statement)
        
        return True, ""
    
    def _extract_sql_keyword(self, token) -> str:
        """提取SQL关键字"""
        if hasattr(token, 'ttype') and token.ttype is T.Keyword.DML:
            return token.value.upper()
        elif hasattr(token, 'ttype') and token.ttype is T.Keyword:
            return token.value.upper()
        elif hasattr(token, 'tokens'):
            # 如果是复合token，递归查找关键字
            for sub_token in token.tokens:
                if not sub_token.is_whitespace:
                    return self._extract_sql_keyword(sub_token)
        
        # 兜底：直接取token值
        return str(token).upper().strip()
    
    def _check_select_safety(self, statement: sql.Statement) -> tuple[bool, str]:
        """检查SELECT语句的安全性"""
        statement_str = str(statement).upper()
        
        # 检查危险的SELECT操作
        dangerous_constructs = [
            ('INTO OUTFILE', 'SELECT INTO OUTFILE'),
            ('INTO DUMPFILE', 'SELECT INTO DUMPFILE'),
            ('LOAD_FILE(', '文件读取函数LOAD_FILE'),
            ('@@', '系统变量访问'),
        ]
        
        for construct, description in dangerous_constructs:
            if construct in statement_str:
                error_msg = self._get_message(
                    f"检测到危险的{description}操作，查询被拒绝",
                    f"Detected dangerous {description} operation, query rejected"
                )
                return False, error_msg
        
        # 检查UNION操作（可能用于注入）
        if 'UNION' in statement_str:
            # 检查UNION后是否有其他表（可能是注入尝试）
            # 这里采用保守策略：所有跨表UNION都被视为潜在危险
            error_msg = self._get_message(
                "检测到UNION操作，可能存在安全风险，查询被拒绝",
                "Detected UNION operation, potential security risk, query rejected"
            )
            return False, error_msg
        
        # 使用AST检查嵌套的危险操作
        return self._check_nested_dangerous_operations(statement)
    
    def _check_nested_dangerous_operations(self, statement: sql.Statement) -> tuple[bool, str]:
        """递归检查嵌套的危险操作，如UNION注入"""
        def check_token_recursively(token):
            # 检查当前token
            if hasattr(token, 'ttype'):
                if token.ttype is T.Keyword.DML:
                    keyword = token.value.upper()
                    dangerous_dml = {'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE'}
                    if keyword in dangerous_dml:
                        error_msg = self._get_message(
                            f"在SELECT语句中检测到危险的{keyword}操作",
                            f"Detected dangerous {keyword} operation in SELECT statement"
                        )
                        return False, error_msg
            
            # 递归检查子token
            if hasattr(token, 'tokens'):
                for sub_token in token.tokens:
                    is_safe, error_msg = check_token_recursively(sub_token)
                    if not is_safe:
                        return False, error_msg
            
            return True, ""
        
        # 检查语句中的所有token
        for token in statement.tokens:
            is_safe, error_msg = check_token_recursively(token)
            if not is_safe:
                return False, error_msg
        
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
                    error_msg = self._get_message(
                        f"表 '{table_name}' 不存在或无权限访问",
                        f"Table '{table_name}' does not exist or access denied"
                    )
                    error_result = {
                        "status": "error",
                        "message": error_msg
                    }
                    return json.dumps(error_result, ensure_ascii=False, cls=DecimalEncoder)
                
                # 构建结构化的JSON响应
                column_info = []
                for column in columns:
                    field, type_info, null, key, default, extra = column
                    column_info.append({
                        "field": field,
                        "type": type_info,
                        "null": null,
                        "key": key,
                        "default": default,
                        "extra": extra
                    })
                
                success_msg = self._get_message(
                    f"表 '{table_name}' 包含 {len(columns)} 个字段",
                    f"Table '{table_name}' contains {len(columns)} field(s)"
                )
                result = {
                    "status": "success",
                    "message": success_msg,
                    "table_name": table_name,
                    "columns": column_info
                }
                
                return json.dumps(result, ensure_ascii=False, cls=DecimalEncoder)
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
                rejected_msg = self._get_message("查询被拒绝", "Query rejected")
                return f"{rejected_msg}: {safety_msg}"
            
            # 数据库上下文检查
            is_valid_context, context_msg = self.validate_database_context(query)
            if not is_valid_context:
                rejected_msg = self._get_message("查询被拒绝", "Query rejected")
                return f"{rejected_msg}: {context_msg}"
            
            connection = await self.get_connection()
            async with connection.cursor() as cursor:
                await cursor.execute(query)
                
                # 如果是SELECT查询，获取结果
                if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
                    results = await cursor.fetchall()
                    
                    if not results:
                        no_results_msg = self._get_message("查询执行成功，但没有返回结果", "Query executed successfully, but no results returned")
                        return json.dumps({"status": "success", "message": no_results_msg, "data": []}, ensure_ascii=False, cls=DecimalEncoder)
                    
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
                            elif isinstance(value, Decimal):
                                # 将Decimal转换为float，保持数值精度
                                row_dict[col_name] = float(value)
                            elif hasattr(value, 'isoformat'):  # datetime对象
                                row_dict[col_name] = value.isoformat()
                            else:
                                row_dict[col_name] = value
                        data.append(row_dict)
                    
                    success_msg = self._get_message(
                        f"查询执行成功，返回 {len(data)} 行结果", 
                        f"Query executed successfully, returned {len(data)} row(s)"
                    )
                    return json.dumps({
                        "status": "success",
                        "message": success_msg,
                        "columns": columns,
                        "data": data
                    }, ensure_ascii=False, cls=DecimalEncoder)
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