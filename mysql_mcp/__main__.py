#!/usr/bin/env python3
"""MySQL MCP Server 主入口点"""

import sys
import asyncio
from . import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("服务器已停止")
        sys.exit(0)
    except Exception as e:
        print(f"启动服务器时发生错误: {e}")
        sys.exit(1)