#!/usr/bin/env python3
"""测试AST安全检查的准确性"""

import os
import sys
import asyncio

# 设置环境变量
os.environ['MYSQL_HOST'] = 'mysql.ipv4.name:3306'
os.environ['MYSQL_USER'] = 'root'
os.environ['MYSQL_PASSWORD'] = 'Shi741069229!'
os.environ['MYSQL_DATABASE'] = 'taskflow_service'

# 导入MySQLHandler
sys.path.append('/Users/flink/PycharmProjects/mysql-python-mcp')

async def test_ast_security():
    """测试AST安全检查的准确性"""
    
    # 先安装sqlparse
    try:
        import sqlparse
    except ImportError:
        print("安装sqlparse...")
        import subprocess
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'sqlparse'])
        import sqlparse
    
    # 直接导入MySQLHandler类，避免FastMCP依赖
    import sys
    sys.path.insert(0, '/Users/flink/PycharmProjects/mysql-python-mcp/mysql_mcp')
    from mysql_handler import MySQLHandler
    
    handler = MySQLHandler()
    
    print("🧪 测试AST安全检查...")
    print("=" * 60)
    
    # 测试用例：应该通过的安全查询
    safe_queries = [
        "SELECT id, user_id, task_biz_id, task_type, enable_multi_model, generate_count, created_at, updated_at FROM tasks WHERE id = 79",
        "SELECT * FROM tasks WHERE updated_at > '2023-01-01'",
        "SELECT created_at, updated_at FROM tasks ORDER BY updated_at DESC",
        "SHOW TABLES",
        "DESCRIBE tasks", 
        "EXPLAIN SELECT * FROM tasks WHERE id = 1",
        "SELECT COUNT(*) as updated_count FROM tasks",
        "SELECT CONCAT('Task: ', task_type) as task_info FROM tasks"
    ]
    
    # 测试用例：应该被拒绝的危险查询
    dangerous_queries = [
        "UPDATE tasks SET status = 'completed' WHERE id = 1",
        "DELETE FROM tasks WHERE id = 1",
        "DROP TABLE tasks",
        "INSERT INTO tasks (name) VALUES ('test')",
        "SELECT * FROM tasks INTO OUTFILE '/tmp/data.txt'",
        "SELECT LOAD_FILE('/etc/passwd')",
        "SELECT @@version",
        "SELECT * FROM tasks UNION SELECT * FROM users",
        "SELECT * FROM tasks; DROP TABLE tasks;",
        "CREATE TABLE test (id INT)"
    ]
    
    print("✅ 测试应该通过的安全查询:")
    print("-" * 40)
    
    safe_passed = 0
    for i, query in enumerate(safe_queries, 1):
        is_safe, error_msg = handler.is_query_safe(query)
        if is_safe:
            print(f"{i:2d}. ✅ PASS: {query[:60]}...")
            safe_passed += 1
        else:
            print(f"{i:2d}. ❌ FAIL: {query[:60]}...")
            print(f"     错误: {error_msg}")
    
    print(f"\n安全查询通过率: {safe_passed}/{len(safe_queries)}")
    
    print("\n🛡️ 测试应该被拒绝的危险查询:")
    print("-" * 40)
    
    danger_blocked = 0
    for i, query in enumerate(dangerous_queries, 1):
        is_safe, error_msg = handler.is_query_safe(query)
        if not is_safe:
            print(f"{i:2d}. ✅ BLOCKED: {query[:50]}...")
            print(f"     原因: {error_msg}")
            danger_blocked += 1
        else:
            print(f"{i:2d}. ❌ ALLOWED: {query[:50]}... (应该被阻止!)")
    
    print(f"\n危险查询阻止率: {danger_blocked}/{len(dangerous_queries)}")
    
    # 总结
    print("\n" + "=" * 60)
    print("🎯 AST安全检查测试总结:")
    print(f"   ✅ 安全查询通过: {safe_passed}/{len(safe_queries)} ({safe_passed/len(safe_queries)*100:.1f}%)")
    print(f"   🛡️ 危险查询阻止: {danger_blocked}/{len(dangerous_queries)} ({danger_blocked/len(dangerous_queries)*100:.1f}%)")
    
    success_rate = (safe_passed + danger_blocked) / (len(safe_queries) + len(dangerous_queries)) * 100
    print(f"   🎉 整体准确率: {success_rate:.1f}%")
    
    if success_rate >= 95:
        print("\n🏆 AST安全检查表现优秀！")
        return True
    elif success_rate >= 80:
        print("\n👍 AST安全检查表现良好！")
        return True
    else:
        print("\n⚠️ AST安全检查需要改进")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ast_security())
    sys.exit(0 if success else 1)