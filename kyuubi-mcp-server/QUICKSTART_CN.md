# 快速开始指南

本指南将帮助您在 5 分钟内完成 Kyuubi MCP Server 的安装和配置。

## 📋 前置条件

- ✅ Python 3.10+
- ✅ Java 8+ (JRE)
- ✅ 可访问的 Kyuubi 服务器

## 🚀 五分钟快速开始

### 步骤 1: 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 步骤 2: 安装项目依赖

```bash
cd kyuubi-mcp-server
uv sync
```

### 步骤 3: 下载 JDBC 驱动

```bash
# 创建驱动目录
mkdir -p drivers

# 下载 Kyuubi JDBC 驱动（选择合适的版本）
# 示例：v1.10.2
wget https://repo1.maven.org/maven2/org/apache/kyuubi/kyuubi-hive-jdbc-shaded/1.10.2/kyuubi-hive-jdbc-shaded-1.10.2.jar \
     -O drivers/kyuubi-hive-jdbc-shaded.jar

# 或手动下载：https://mvnrepository.com/artifact/org.apache.kyuubi/kyuubi-hive-jdbc-shaded
```

### 步骤 4: 配置环境变量

```bash
# 复制配置模板
cp env.example .env

# 编辑 .env 文件（使用你喜欢的编辑器）
nano .env
```

**最小配置示例**：

```bash
KYUUBI_HOST=your-kyuubi-server.com
KYUUBI_PORT=10009
KYUUBI_JDBC_DRIVER_PATH=/绝对路径/to/kyuubi-mcp-server/drivers/kyuubi-hive-jdbc-shaded.jar
```

**完整配置示例**（带认证）：

```bash
KYUUBI_HOST=your-kyuubi-server.com
KYUUBI_PORT=10009
KYUUBI_DATABASE=default
KYUUBI_AUTH_TYPE=PLAIN
KYUUBI_USERNAME=your_username
KYUUBI_PASSWORD=your_password
KYUUBI_JDBC_DRIVER_PATH=/绝对路径/to/kyuubi-mcp-server/drivers/kyuubi-hive-jdbc-shaded.jar
```

⚠️ **重要提示**：
- 必须使用**绝对路径**，不要使用 `~` 或相对路径
- `KYUUBI_JDBC_DRIVER_PATH` 是必需的

### 步骤 5: 测试连接

```bash
# 加载环境变量并测试
source .env  # 如果使用 bash/zsh
uv run python test_connection.py
```

**预期输出**：

```
==========================================================
Kyuubi MCP Server - 连接测试
==========================================================

配置信息:
  Host: your-kyuubi-server.com
  Port: 10009
  Database: default
  ...

正在连接到 Kyuubi...
✓ 连接成功!

正在测试查询...
✓ 找到 3 个数据库:
  - default
  - sales
  - analytics

✓ 所有测试通过!
```

### 步骤 6: 配置 Claude Desktop

**macOS**: 编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: 编辑 `%APPDATA%\Claude\claude_desktop_config.json`

添加以下配置：

```json
{
  "mcpServers": {
    "kyuubi": {
      "command": "uv",
      "args": [
        "--directory",
        "/绝对路径/to/kyuubi-mcp-server",
        "run",
        "kyuubi-mcp-server"
      ],
      "env": {
        "KYUUBI_HOST": "your-kyuubi-server.com",
        "KYUUBI_PORT": "10009",
        "KYUUBI_DATABASE": "default",
        "KYUUBI_AUTH_TYPE": "PLAIN",
        "KYUUBI_USERNAME": "your_username",
        "KYUUBI_PASSWORD": "your_password",
        "KYUUBI_JDBC_DRIVER_PATH": "/绝对路径/to/drivers/kyuubi-hive-jdbc-shaded.jar"
      }
    }
  }
}
```

⚠️ **替换以下内容**：
- `/绝对路径/to/kyuubi-mcp-server` → 你的实际项目路径
- `/绝对路径/to/drivers/kyuubi-hive-jdbc-shaded.jar` → 实际驱动路径
- 其他连接参数

### 步骤 7: 开始使用

1. **重启 Claude Desktop**
2. **查看 MCP 工具**：在 Claude 中应该能看到 Kyuubi 相关的工具
3. **测试查询**：

```
你: 列出所有数据库

你: 查询 sales 表中今天的数据

你: 统计每个地区的订单数量
```

## 🎯 常用命令

```bash
# 安装依赖
uv sync

# 测试连接
uv run python test_connection.py

# 手动运行服务器（调试用）
uv run kyuubi-mcp-server

# 查看日志（如果有问题）
# Claude Desktop: Help → View Logs
```

## 🔍 故障排除速查

### 问题: 找不到 JDBC 驱动

```bash
# 检查文件是否存在
ls -la drivers/kyuubi-hive-jdbc-shaded.jar

# 检查路径是否为绝对路径
echo $KYUUBI_JDBC_DRIVER_PATH
```

### 问题: 连接被拒绝

```bash
# 测试网络连接
telnet your-kyuubi-server.com 10009

# 或使用 nc
nc -zv your-kyuubi-server.com 10009
```

### 问题: 认证失败

- 检查用户名和密码是否正确
- 确认 `KYUUBI_AUTH_TYPE` 设置正确（NONE, PLAIN, LDAP, KERBEROS）
- 查看 Kyuubi 服务器日志

### 问题: Claude Desktop 看不到工具

1. 检查配置文件语法是否正确（JSON 格式）
2. 使用绝对路径，不要使用 `~`
3. 重启 Claude Desktop
4. 查看 Claude Desktop 日志：Help → View Logs

## 📚 下一步

- 阅读 [完整文档](README_CN.md)
- 查看 [配置选项](env.example)
- 了解 [可用工具](README_CN.md#-可用工具)

## 💡 提示

1. **使用绝对路径**：在配置 Claude Desktop 时，始终使用绝对路径
2. **环境变量优先**：Claude Desktop 配置中的 `env` 会覆盖 `.env` 文件
3. **测试连接**：在配置 Claude Desktop 前，先用 `test_connection.py` 测试
4. **查看日志**：遇到问题时，第一时间查看 Claude Desktop 日志

## 🆘 需要帮助？

- [GitHub Issues](https://github.com/apache/kyuubi/issues)
- [Kyuubi 官方文档](https://kyuubi.readthedocs.io/)
- [完整文档](README_CN.md)

---

祝您使用愉快！🎉

