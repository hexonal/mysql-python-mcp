#!/usr/bin/env python3

import os
import json
import asyncio
import locale
from typing import List
from fastmcp import FastMCP
from .mysql_handler import MySQLHandler

# 检测语言环境
def _detect_chinese_locale() -> bool:
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
        return False

def _get_message(zh_msg: str, en_msg: str) -> str:
    """根据语言环境返回对应消息"""
    return zh_msg if _detect_chinese_locale() else en_msg

# 创建FastMCP应用
mcp = FastMCP("MySQL Database Server")

@mcp.tool()
async def list_databases() -> str:
    """列出MySQL实例中的所有数据库"""
    handler = MySQLHandler()
    try:
        databases = await handler.list_databases()
        message = _get_message(
            f"找到 {len(databases)} 个数据库",
            f"Found {len(databases)} database(s)"
        )
        result = {
            "status": "success",
            "message": message,
            "databases": databases
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        message = _get_message(
            f"获取数据库列表失败: {str(e)}",
            f"Failed to get database list: {str(e)}"
        )
        error_result = {
            "status": "error", 
            "message": message
        }
        return json.dumps(error_result, ensure_ascii=False)

@mcp.tool()
async def list_tables() -> str:
    """列出当前数据库中的所有表"""
    handler = MySQLHandler()
    try:
        tables = await handler.list_tables()
        message = _get_message(
            f"找到 {len(tables)} 个表",
            f"Found {len(tables)} table(s)"
        )
        result = {
            "status": "success",
            "message": message,
            "tables": tables
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        message = _get_message(
            f"获取表列表失败: {str(e)}",
            f"Failed to get table list: {str(e)}"
        )
        error_result = {
            "status": "error",
            "message": message
        }
        return json.dumps(error_result, ensure_ascii=False)

@mcp.tool()
async def describe_table(table_name: str) -> str:
    """描述指定表的结构信息
    
    Args:
        table_name: 要描述的表名
    """
    handler = MySQLHandler()
    try:
        result = await handler.describe_table(table_name)
        return result
    except Exception as e:
        message = _get_message(
            f"描述表 '{table_name}' 失败: {str(e)}",
            f"Failed to describe table '{table_name}': {str(e)}"
        )
        error_result = {
            "status": "error",
            "message": message
        }
        return json.dumps(error_result, ensure_ascii=False)

@mcp.tool()
async def execute_query(query: str) -> str:
    """执行SQL查询（默认仅支持SELECT查询，可通过环境变量启用更多操作）
    
    Args:
        query: 要执行的SQL查询语句
    """
    handler = MySQLHandler()
    try:
        result = await handler.execute_query(query)
        return result
    except Exception as e:
        message = _get_message(
            f"执行查询失败: {str(e)}",
            f"Failed to execute query: {str(e)}"
        )
        error_result = {
            "status": "error",
            "message": message
        }
        return json.dumps(error_result, ensure_ascii=False)

# FastMCP服务器已配置，可通过mcp.run()启动