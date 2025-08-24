#!/usr/bin/env python3
"""MCP服务器stdio模式自测脚本"""

import asyncio
import json
import os
import sys
import subprocess
from typing import Any, Dict

async def test_mcp_stdio():
    """测试MCP服务器的stdio通信"""
    
    print("🧪 开始MCP服务器stdio模式自测...")
    print("=" * 60)
    
    # 设置环境变量
    env = os.environ.copy()
    env.update({
        'MYSQL_HOST': 'mysql.ipv4.name:3306',
        'MYSQL_USER': 'root',
        'MYSQL_PASSWORD': 'Shi741069229!',
        'MYSQL_DATABASE': 'taskflow_service'
    })
    
    print("🌍 环境变量已设置")
    
    try:
        # 启动MCP服务器进程 (使用uvx)
        print("🚀 启动MCP服务器进程...")
        process = await asyncio.create_subprocess_exec(
            'uvx', '--from', 'git+https://github.com/hexonal/mysql-python-mcp', 'mysql-python-mcp',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        print("✅ MCP服务器进程已启动")
        
        # 测试初始化
        print("\n📋 测试1: 发送初始化消息...")
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        await send_message(process, init_message)
        response = await receive_message(process)
        
        # 检查stderr输出
        try:
            stderr_data = await asyncio.wait_for(process.stderr.read(4096), timeout=3.0)
            if stderr_data:
                stderr_text = stderr_data.decode('utf-8', errors='ignore')
                print(f"   stderr: {stderr_text}")
                
                # 读取更多stderr输出
                try:
                    more_stderr = await asyncio.wait_for(process.stderr.read(2048), timeout=1.0)
                    if more_stderr:
                        print(f"   stderr(续): {more_stderr.decode('utf-8', errors='ignore')}")
                except asyncio.TimeoutError:
                    pass
        except asyncio.TimeoutError:
            print("   stderr: (无输出)")
        
        if response and "result" in response:
            print("✅ 初始化成功")
            print(f"   服务器信息: {response['result'].get('serverInfo', {})}")
            
            # 发送initialized通知
            print("📨 发送initialized通知...")
            initialized_message = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            await send_message(process, initialized_message)
            
        else:
            print("❌ 初始化失败")
            print(f"   响应: {response}")
            
            # 检查进程状态
            if process.returncode is not None:
                print(f"   进程已退出，返回码: {process.returncode}")
            
            return False
        
        # 测试列出工具
        print("\n🔧 测试2: 列出可用工具...")
        tools_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": None
        }
        
        await send_message(process, tools_message)
        response = await receive_message(process)
        
        if response and "result" in response:
            tools = response["result"].get("tools", [])
            print(f"✅ 找到 {len(tools)} 个工具:")
            for tool in tools:
                print(f"   - {tool.get('name')}: {tool.get('description')}")
        else:
            print("⚠️ 列出工具失败，但继续测试工具调用")
            if response:
                print(f"   响应内容: {response}")
            else:
                print("   没有收到响应")
        
        # 测试工具调用
        test_tools = [
            ("list_databases", {}, "列出数据库"),
            ("list_tables", {}, "列出表"),
            ("describe_table", {"table_name": "tasks"}, "描述表结构"),
            ("execute_query", {"query": "SELECT 1 as test"}, "执行查询")
        ]
        
        for i, (tool_name, args, description) in enumerate(test_tools, 3):
            print(f"\n⚡ 测试{i}: {description} ({tool_name})...")
            
            call_message = {
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args
                }
            }
            
            await send_message(process, call_message)
            response = await receive_message(process)
            
            if response and "result" in response:
                result = response["result"]
                if "content" in result and result["content"]:
                    content = result["content"][0].get("text", "")
                    display_content = content[:200] + "..." if len(content) > 200 else content
                    print(f"✅ {description}成功")
                    print(f"   结果: {display_content}")
                    
                    # 验证JSON格式
                    try:
                        import json
                        parsed = json.loads(content)
                        status = parsed.get('status', '未知')
                        print(f"   📊 JSON格式: ✅ status={status}")
                        
                        if tool_name == "describe_table":
                            columns = parsed.get('columns', [])
                            print(f"      表字段数: {len(columns)}")
                    except json.JSONDecodeError:
                        print("   📊 JSON格式: ❌ 解析失败")
                else:
                    print(f"❌ {description}返回空结果")
            else:
                print(f"❌ {description}失败")
                if response:
                    print(f"   错误: {response.get('error', response)}")
        
        # 关闭连接
        print("\n🔚 关闭连接...")
        process.stdin.close()
        await process.wait()
        
        print("\n" + "=" * 60)
        print("🎉 MCP服务器stdio模式测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 确保进程被终止
        if 'process' in locals():
            try:
                process.terminate()
                await process.wait()
            except:
                pass

async def send_message(process: asyncio.subprocess.Process, message: Dict[str, Any]):
    """发送JSON-RPC消息到MCP服务器"""
    json_str = json.dumps(message)
    message_bytes = (json_str + '\n').encode('utf-8')
    process.stdin.write(message_bytes)
    await process.stdin.drain()

async def receive_message(process: asyncio.subprocess.Process) -> Dict[str, Any]:
    """从MCP服务器接收JSON-RPC消息"""
    try:
        # 设置超时
        line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        if line:
            message_str = line.decode('utf-8').strip()
            if message_str:
                return json.loads(message_str)
    except asyncio.TimeoutError:
        print("⚠️ 接收消息超时")
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON解析错误: {e}")
    except Exception as e:
        print(f"⚠️ 接收消息时发生错误: {e}")
    
    return {}

if __name__ == "__main__":
    success = asyncio.run(test_mcp_stdio())
    sys.exit(0 if success else 1)