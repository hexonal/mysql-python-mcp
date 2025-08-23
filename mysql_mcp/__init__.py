#!/usr/bin/env python3

import asyncio
import logging
from typing import Any
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

app = Server("mysql-python-mcp")


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出可用的工具"""
    return [
        types.Tool(
            name="list_databases",
            description="列出MySQL实例中的所有数据库",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="list_tables", 
            description="列出当前数据库中的所有表",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="execute_query",
            description="执行SQL查询（仅支持SELECT语句，除非允许危险操作）",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要执行的SQL查询语句",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="describe_table",
            description="描述表结构",
            inputSchema={
                "type": "object", 
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "要描述的表名",
                    },
                },
                "required": ["table_name"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """处理工具调用"""
    from .mysql_handler import MySQLHandler
    
    handler = MySQLHandler()
    
    try:
        if name == "list_databases":
            databases = await handler.list_databases()
            result = "可用数据库:\n" + "\n".join(f"- {db}" for db in databases)
        elif name == "list_tables":
            tables = await handler.list_tables()  
            result = "当前数据库中的表:\n" + "\n".join(f"- {table}" for table in tables)
        elif name == "execute_query":
            query = arguments.get("query", "")
            result = await handler.execute_query(query)
        elif name == "describe_table":
            table_name = arguments.get("table_name", "")
            result = await handler.describe_table(table_name)
        else:
            raise ValueError(f"未知工具: {name}")
            
        return [types.TextContent(type="text", text=result)]
        
    except Exception as e:
        error_msg = f"执行工具 '{name}' 时发生错误: {str(e)}"
        return [types.TextContent(type="text", text=error_msg)]


async def main():
    """主入口点"""
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("mysql-mcp")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mysql-python-mcp",
                server_version="0.1.3",
                capabilities=app.get_capabilities(
                    experimental_capabilities={},
                ),
            ),
        )

# 由 __main__.py 处理启动逻辑