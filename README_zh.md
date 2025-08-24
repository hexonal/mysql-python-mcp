# MySQL Python MCP Server

[English](README.md) | 中文文档

一个基于Python的MySQL MCP服务器，提供安全的数据库操作功能，具备内置安全检查和基于AST的SQL解析。

## 功能特性

- 🔍 **查看数据库**: 列出MySQL实例中的所有数据库
- 📋 **查看表结构**: 列出当前数据库中的所有表
- 🔍 **表结构描述**: 详细描述表的结构信息
- 📊 **安全查询**: 执行SQL查询（默认仅支持SELECT语句）
- 🛡️ **安全限制**: 严格限制操作范围在配置的数据库内
- ⚙️ **可配置**: 支持通过环境变量启用更多操作
- 📋 **JSON输出**: 查询结果以结构化JSON格式返回，便于AI理解

## 安全特性

### 默认安全模式
- 仅允许 `SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN` 查询
- 禁止危险操作如 `DROP`, `DELETE`, `UPDATE`, `INSERT` 等
- 严格限制在配置的数据库范围内操作
- 防止SQL注入攻击

### 高级模式（可选）
通过设置环境变量 `MYSQL_ALLOW_DANGEROUS=true` 可以启用：
- 增删查改操作
- 更多数据库管理功能

## 配置

### 环境变量

| 变量名 | 描述 | 必需 |
|--------|------|------|
| `MYSQL_HOST` | MySQL主机地址和端口 (格式: host:port 或 host) | 是 |
| `MYSQL_USER` | MySQL用户名 | 是 |
| `MYSQL_PASSWORD` | MySQL密码 | 是 |
| `MYSQL_DATABASE` | 目标数据库名 | 是 |
| `MYSQL_ALLOW_DANGEROUS` | 是否允许危险操作 (true/false) | 否 (默认: false) |

### Claude Desktop 配置示例

在Claude Desktop的配置文件中添加：

```json
{
  "mcpServers": {
    "mysql": {
      "command": "uv",
      "args": [
        "--from",
        "git+https://github.com/your-repo/mysql-python-mcp.git",
        "mysql-python-mcp"
      ],
      "env": {
        "MYSQL_HOST": "your-mysql-host:3306",
        "MYSQL_USER": "your-username",
        "MYSQL_PASSWORD": "your-password",
        "MYSQL_DATABASE": "your-database"
      }
    }
  }
}
```

## 可用工具

### 1. list_databases
列出MySQL实例中的所有数据库（当前配置的数据库会被特别标注）。

### 2. list_tables  
列出当前配置数据库中的所有表。

### 3. describe_table
描述指定表的结构，包括字段名、类型、是否允许NULL、键信息等。

**参数:**
- `table_name` (string): 要描述的表名

### 4. execute_query
执行SQL查询语句，返回JSON格式结果。

**参数:**
- `query` (string): 要执行的SQL语句

**安全限制:**
- 默认仅允许查询操作（SELECT, SHOW, DESCRIBE, EXPLAIN）
- 自动检测和阻止危险操作
- 限制在配置的数据库范围内

**JSON输出格式:**
```json
{
  "status": "success",
  "message": "查询执行成功，返回 2 行结果",
  "columns": ["id", "name", "email"],
  "data": [
    {
      "id": 1,
      "name": "用户1", 
      "email": "user1@example.com"
    },
    {
      "id": 2,
      "name": "用户2",
      "email": "user2@example.com"
    }
  ]
}
```

## 安装和运行

### 使用 uv (推荐)

```bash
# 通过Git安装
uv add git+https://github.com/your-repo/mysql-python-mcp.git

# 或本地开发
uv add -e .
```

### 手动安装

```bash
# 克隆仓库
git clone <repository-url>
cd mysql-python-mcp

# 安装依赖
pip install -e .

# 运行服务器
python -m mysql_mcp
```

## 使用示例

### 查看所有数据库
```
工具: list_databases
```

### 查看当前数据库的表
```  
工具: list_tables
```

### 描述表结构
```
工具: describe_table
参数: {"table_name": "users"}
```

### 执行查询
```
工具: execute_query  
参数: {"query": "SELECT * FROM users LIMIT 10"}
```

## 开发

### 项目结构
```
mysql-python-mcp/
├── mysql_mcp/
│   ├── __init__.py          # MCP服务器主入口
│   ├── __main__.py          # 运行脚本
│   └── mysql_handler.py     # MySQL处理器
├── pyproject.toml           # 项目配置
└── README.md                # 项目说明
```

### 本地开发
```bash
# 克隆项目
git clone <repository-url>
cd mysql-python-mcp

# 安装开发依赖
uv sync --dev

# 运行测试
python standalone_test.py

# 代码格式化
black mysql_mcp/
isort mysql_mcp/

# 类型检查
mypy mysql_mcp/
```

## 许可证

MIT License

## 安全说明

⚠️ **重要安全提示**:
- 所有环境变量均为必需，不提供不安全的默认值
- 在生产环境中使用时，请确保MySQL用户权限最小化
- 定期更换数据库密码
- 不要在配置中使用管理员权限的数据库用户
- 建议在隔离环境中运行此MCP服务器
- 默认的安全模式已经提供了基本保护，但不能替代完整的安全策略

## 故障排除

### 常见问题

1. **连接失败**: 检查MySQL服务是否运行，网络连接是否正常
2. **环境变量错误**: 确认所有必需的环境变量已正确设置
3. **权限错误**: 确认MySQL用户具有访问指定数据库的权限
4. **查询被拒绝**: 检查查询是否包含被禁止的关键词，或考虑启用高级模式