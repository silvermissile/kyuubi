# Kyuubi MCP Server

一个独立的 MCP (Model Context Protocol) 服务器，使用 JayDeBeApi 为 LLM/AI Agent 提供 Apache Kyuubi 数据访问能力。

## 特性

- ✅ **纯 Python 实现**：使用 JayDeBeApi 通过 JDBC 连接 Kyuubi
- ✅ **功能完整**：支持所有 Kyuubi/Hive 特性
- ✅ **易于维护**：依赖官方 JDBC 驱动，零额外维护成本
- ✅ **双协议支持**：支持 stdio 和 HTTP (SSE) 两种传输协议
- ✅ **MCP 协议**：可被任何 MCP 客户端使用（Claude Desktop, Cursor 等）
- ✅ **多种认证**：支持 NONE, PLAIN, LDAP, KERBEROS 等认证方式
- ✅ **灵活部署**：可作为桌面集成或独立 HTTP 服务器运行

## 快速开始

### 1. 环境要求

- Python 3.10+
- Java Runtime Environment (JRE) 8+
- Kyuubi JDBC 驱动 JAR 文件

### 2. 安装

使用 uv 管理依赖（推荐）：

```bash
# 安装 uv（如果还没有安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆或进入项目目录
cd kyuubi-mcp-server

# 使用 uv 安装依赖
uv sync
```

或使用 pip：

```bash
pip install -e .
```

### 3. 下载 Kyuubi JDBC 驱动

从 Maven Central 下载 Kyuubi Hive JDBC 驱动：

```bash
# 创建驱动目录
mkdir -p drivers

# 下载最新版本的 kyuubi-hive-jdbc-shaded JAR
# 示例（请根据实际版本调整）:
wget https://repo1.maven.org/maven2/org/apache/kyuubi/kyuubi-hive-jdbc-shaded/1.10.2/kyuubi-hive-jdbc-shaded-1.10.2.jar \
     -O drivers/kyuubi-hive-jdbc-shaded.jar
```

或手动从 Maven Central 下载：
https://mvnrepository.com/artifact/org.apache.kyuubi/kyuubi-hive-jdbc-shaded

### 4. 配置

复制配置文件模板：

```bash
cp env.example .env
```

编辑 `.env` 文件，配置 Kyuubi 连接信息：

```bash
# Kyuubi 服务器地址
KYUUBI_HOST=kyuubi-server.example.com
KYUUBI_PORT=10009
KYUUBI_DATABASE=default

# 认证配置
KYUUBI_AUTH_TYPE=PLAIN
KYUUBI_USERNAME=your_username
KYUUBI_PASSWORD=your_password

# JDBC 驱动路径（绝对路径）
KYUUBI_JDBC_DRIVER_PATH=/path/to/kyuubi-mcp-server/drivers/kyuubi-hive-jdbc-shaded.jar
```

### 5. 测试连接

```bash
# 使用 uv
uv run python -c "from kyuubi_mcp_server.kyuubi_client import KyuubiClient; \
client = KyuubiClient('localhost', 10009, jdbc_driver_path=['drivers/kyuubi-hive-jdbc-shaded.jar']); \
client.connect(); \
print('✓ 连接成功!'); \
client.close()"
```

### 6. 配置 MCP 客户端

#### Claude Desktop

编辑 Claude Desktop 配置文件：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

添加以下配置：

```json
{
  "mcpServers": {
    "kyuubi": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/kyuubi-mcp-server",
        "run",
        "kyuubi-mcp-server"
      ],
      "env": {
        "KYUUBI_HOST": "kyuubi-server.example.com",
        "KYUUBI_PORT": "10009",
        "KYUUBI_DATABASE": "default",
        "KYUUBI_AUTH_TYPE": "PLAIN",
        "KYUUBI_USERNAME": "your_username",
        "KYUUBI_PASSWORD": "your_password",
        "KYUUBI_JDBC_DRIVER_PATH": "/path/to/kyuubi-mcp-server/drivers/kyuubi-hive-jdbc-shaded.jar"
      }
    }
  }
}
```

#### Cursor

在 Cursor 设置中添加 MCP 服务器配置（类似 Claude Desktop）。

### 7. 使用

重启 Claude Desktop 或 Cursor，现在你可以通过自然语言与 Kyuubi 交互：

```
用户: 列出所有数据库

用户: 查询 sales 表中今天的销售数据

用户: 查看 users 表的结构

用户: 统计每个地区的订单数量
```

## 可用工具

MCP 服务器提供以下工具：

| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `kyuubi_query` | 执行 SQL 查询 | `query`: SQL 语句 |
| `kyuubi_list_databases` | 列出所有数据库 | 无 |
| `kyuubi_list_tables` | 列出数据库中的表 | `database`: 数据库名（可选） |
| `kyuubi_describe_table` | 获取表结构 | `table`: 表名, `database`: 数据库名（可选） |
| `kyuubi_table_sample` | 获取表样本数据 | `table`: 表名, `limit`: 行数（默认10） |

## 认证配置

### PLAIN 认证（用户名/密码）

```bash
KYUUBI_AUTH_TYPE=PLAIN
KYUUBI_USERNAME=your_username
KYUUBI_PASSWORD=your_password
```

### LDAP 认证

```bash
KYUUBI_AUTH_TYPE=LDAP
KYUUBI_USERNAME=your_ldap_username
KYUUBI_PASSWORD=your_ldap_password
```

### Kerberos 认证

```bash
KYUUBI_AUTH_TYPE=KERBEROS
# Kerberos 认证需要额外配置 krb5.conf 和 keytab 文件
# 详见 Kyuubi 官方文档
```

### 无认证（开发测试）

```bash
KYUUBI_AUTH_TYPE=NONE
```

## 开发

### 运行测试

```bash
# 使用 uv
uv run pytest

# 或使用 pip
pytest
```

### 代码格式化

```bash
# 使用 black 格式化代码
uv run black src/

# 类型检查
uv run mypy src/
```

### 手动测试

```bash
# 直接运行服务器（stdio 模式）
uv run kyuubi-mcp-server

# 或
uv run python -m kyuubi_mcp_server.server
```

## 项目结构

```
kyuubi-mcp-server/
├── src/
│   └── kyuubi_mcp_server/
│       ├── __init__.py          # 包初始化
│       ├── server.py            # MCP 服务器主入口
│       ├── kyuubi_client.py     # Kyuubi 客户端（JayDeBeApi）
│       └── tools.py             # 工具定义
├── drivers/                     # JDBC 驱动目录
│   └── kyuubi-hive-jdbc-shaded.jar
├── pyproject.toml               # 项目配置（uv）
├── env.example                  # 配置模板
└── README.md                    # 本文件
```

## 故障排除

### 1. JDBC 驱动未找到

**错误**: `java.lang.ClassNotFoundException: org.apache.hive.jdbc.HiveDriver`

**解决**: 确保 `KYUUBI_JDBC_DRIVER_PATH` 指向正确的 JAR 文件路径（绝对路径）。

### 2. 连接被拒绝

**错误**: `Connection refused`

**解决**: 
- 检查 Kyuubi 服务器是否正在运行
- 确认主机名和端口号正确
- 检查网络连接和防火墙规则

### 3. 认证失败

**错误**: `Authentication failed`

**解决**:
- 检查用户名和密码是否正确
- 确认 `KYUUBI_AUTH_TYPE` 配置正确
- 查看 Kyuubi 服务器日志

### 4. Java 环境问题

**错误**: JVM 相关错误

**解决**:
- 确保安装了 Java 8+ 运行环境
- 检查 `JAVA_HOME` 环境变量是否设置正确

## 参考资源

- [Kyuubi 官方文档](https://kyuubi.readthedocs.io/)
- [JayDeBeApi 文档](https://kyuubi.readthedocs.io/en/v1.10.2/client/python/jaydebeapi.html)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [Kyuubi JDBC Driver](https://mvnrepository.com/artifact/org.apache.kyuubi/kyuubi-hive-jdbc-shaded)

## 许可证

Apache License 2.0

## 贡献

欢迎提交 Issue 和 Pull Request！

## 作者

Kyuubi Community

