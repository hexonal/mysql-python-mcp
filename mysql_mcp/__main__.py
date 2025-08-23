#!/usr/bin/env python3
"""MySQL MCP Server 主入口点"""

import sys
import asyncio
from . import main as async_main

def main():
    """同步主入口函数"""
    try:
        print("Starting MySQL MCP Server...", file=sys.stderr)
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("服务器已停止", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"启动服务器时发生错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()