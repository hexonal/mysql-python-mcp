#!/usr/bin/env python3

import os
import json
import asyncio
from typing import List
from fastmcp import FastMCP
from .mysql_handler import MySQLHandler

# 创建FastMCP应用
mcp = FastMCP("MySQL Database Server")

@mcp.tool()
async def list_databases() -> str:
    """列出MySQL实例中的所有数据库"""
    handler = MySQLHandler()
    try:
        databases = await handler.list_databases()
        result = {
            "status": "success",
            "message": f"找到 {len(databases)} 个数据库",
            "databases": databases
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        error_result = {
            "status": "error", 
            "message": f"获取数据库列表失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False)

@mcp.tool()
async def list_tables() -> str:
    """列出当前数据库中的所有表"""
    handler = MySQLHandler()
    try:
        tables = await handler.list_tables()
        result = {
            "status": "success",
            "message": f"找到 {len(tables)} 个表",
            "tables": tables
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"获取表列表失败: {str(e)}"
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
        error_result = {
            "status": "error",
            "message": f"描述表 '{table_name}' 失败: {str(e)}"
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
        error_result = {
            "status": "error",
            "message": f"执行查询失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False)

# FastMCP服务器已配置，可通过mcp.run()启动