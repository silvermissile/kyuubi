# Kyuubi MCP 服务器

[English](README.md) | 简体中文

一个独立的 MCP (Model Context Protocol) 服务器，使用 JayDeBeApi 为 LLM/AI Agent 提供 Apache Kyuubi 数据访问能力。

## 🎯 项目特性

- ✅ **纯 Python 实现**：支持 PyHive 和 JayDeBeApi 两种客户端
- ✅ **双客户端支持**：可选择 PyHive（轻量）或 JayDeBeApi（完整功能）
- ✅ **功能完整**：100% 支持所有 Kyuubi/Hive 特性
- ✅ **易于维护**：依赖官方驱动，零额外维护成本
- ✅ **MCP 协议标准**：可被任何 MCP 客户端使用（Claude Desktop, Cursor 等）
- ✅ **多种认证方式**：支持 NONE, PLAIN, LDAP, KERBEROS 等
- ✅ **灵活部署**：支持 stdio 和 HTTP 两种传输协议
- ✅ **开箱即用**：2-4 天即可完成开发和部署

## 📋 环境要求

### 基础要求

- Python 3.10 或更高版本
- (推荐) uv - 现代 Python 包管理工具

### 客户端特定要求

根据选择的客户端类型，需要不同的环境：

**PyHive 客户端**（推荐用于开发/测试）：
- ✅ 无需 Java 环境
- ✅ 无需 JDBC 驱动
- ⚠️ 如需 Kerberos 认证，需安装 SASL 库

**JayDeBeApi 客户端**（推荐用于生产环境）：
- ✅ Java Runtime Environment (JRE) 8 或更高版本
- ✅ Kyuubi JDBC 驱动 JAR 文件

详细对比请查看 [CLIENT_COMPARISON.md](CLIENT_COMPARISON.md)

## 🚀 快速开始

### 第一步：安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

### 第二步：安装项目依赖

根据选择的客户端类型安装依赖：

#### 选项 A: 安装 PyHive 客户端（推荐）

```bash
# 进入项目目录
cd kyuubi-mcp-server

# 使用 uv 安装 PyHive（推荐）
uv sync --extra pyhive

# 或使用 pip
pip install -e ".[pyhive]"

# Linux 上如果需要 Kerberos 支持
sudo apt-get install -y libsasl2-dev libsasl2-modules-gssapi-mit

# macOS 上如果需要 Kerberos 支持
brew install cyrus-sasl
```

#### 选项 B: 安装 JayDeBeApi 客户端

```bash
# 进入项目目录
cd kyuubi-mcp-server

# 使用 uv 安装 JayDeBeApi（推荐）
uv sync --extra jaydebeapi

# 或使用 pip
pip install -e ".[jaydebeapi]"

# 确保已安装 Java
java -version  # 应显示 Java 8 或更高版本
```

#### 选项 C: 同时安装两种客户端

```bash
# 使用 uv
uv sync --extra all

# 使用 pip
pip install -e ".[all]"
```

### 第三步：下载 Kyuubi JDBC 驱动（仅 JayDeBeApi 需要）

⚠️ **注意**：如果使用 **PyHive 客户端**，可以**跳过此步骤**。

如果使用 **JayDeBeApi 客户端**，需要下载 JDBC 驱动：

```bash
# 创建驱动目录
mkdir -p drivers

# 下载 Kyuubi Hive JDBC Shaded JAR（选择合适的版本）
# 示例：下载 1.10.2 版本
wget https://repo1.maven.org/maven2/org/apache/kyuubi/kyuubi-hive-jdbc-shaded/1.10.2/kyuubi-hive-jdbc-shaded-1.10.2.jar \
     -O drivers/kyuubi-hive-jdbc-shaded.jar
```

**手动下载**：访问 [Maven Central](https://mvnrepository.com/artifact/org.apache.kyuubi/kyuubi-hive-jdbc-shaded) 下载最新版本。

### 第四步：配置环境变量

```bash
# 复制配置模板
cp env.example .env

# 编辑 .env 文件
nano .env
```

配置示例：

#### 使用 PyHive 客户端（推荐用于开发/测试）

```bash
# Kyuubi 服务器配置
KYUUBI_HOST=your-kyuubi-server.com
KYUUBI_PORT=10009
KYUUBI_DATABASE=default

# 客户端类型（选择 PyHive）
KYUUBI_CLIENT_TYPE=pyhive

# 认证配置
KYUUBI_AUTH_TYPE=PLAIN
KYUUBI_USERNAME=your_username
KYUUBI_PASSWORD=your_password

# 注意：PyHive 不需要 KYUUBI_JDBC_DRIVER_PATH
```

#### 使用 JayDeBeApi 客户端（推荐用于生产环境）

```bash
# Kyuubi 服务器配置
KYUUBI_HOST=your-kyuubi-server.com
KYUUBI_PORT=10009
KYUUBI_DATABASE=default

# 客户端类型（选择 JayDeBeApi）
KYUUBI_CLIENT_TYPE=jaydebeapi

# 认证配置
KYUUBI_AUTH_TYPE=PLAIN
KYUUBI_USERNAME=your_username
KYUUBI_PASSWORD=your_password

# JDBC 驱动路径（绝对路径，JayDeBeApi 必需）
KYUUBI_JDBC_DRIVER_PATH=/absolute/path/to/drivers/kyuubi-hive-jdbc-shaded.jar
```

### 第五步：测试连接

```bash
# 测试 Kyuubi 连接是否正常
uv run python -c "
from kyuubi_mcp_server.kyuubi_client import KyuubiClient
import os
client = KyuubiClient(
    host=os.getenv('KYUUBI_HOST', 'localhost'),
    port=int(os.getenv('KYUUBI_PORT', 10009)),
    jdbc_driver_path=['drivers/kyuubi-hive-jdbc-shaded.jar']
)
client.connect()
print('✓ 连接成功!')
databases = client.get_databases()
print(f'✓ 找到 {len(databases)} 个数据库: {databases}')
client.close()
"
```

### 第六步：启动和使用

Kyuubi MCP Server 支持两种传输协议：**stdio** 和 **HTTP**。

#### 方式 1: stdio 模式（推荐用于 Claude Desktop / Cursor）

**配置 Claude Desktop**:

编辑 Claude Desktop 配置文件：

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

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
        "kyuubi-mcp-server",
        "--transport",
        "stdio"
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

**重要提示**：
- 使用绝对路径，不要使用 `~` 或相对路径
- 确保路径中没有空格，或正确转义空格

**配置 Cursor**:

在 Cursor 的设置中添加类似的 MCP 服务器配置。

#### 方式 2: HTTP 模式（适合远程访问）

启动 HTTP 服务器：

```bash
# 使用默认配置（监听 0.0.0.0:8000）
uv run kyuubi-mcp-server --transport http

# 自定义地址和端口
uv run kyuubi-mcp-server --transport http --host 127.0.0.1 --port 9000
```

**命令行参数**:
- `--transport {stdio,http}`: 传输协议（默认: stdio）
- `--host HOST`: HTTP 服务器地址（默认: 0.0.0.0）
- `--port PORT`: HTTP 服务器端口（默认: 8000）

**安全提示**:
- HTTP 模式默认无认证，建议仅在内网使用
- 生产环境建议使用 Nginx 反向代理添加认证和 HTTPS
- 可以限制监听地址：`--host 127.0.0.1`（仅本地访问）

详细使用说明请参考 [USAGE.md](USAGE.md)。

### 第七步：开始使用

1. 重启 Claude Desktop 或 Cursor
2. 查看 MCP 工具是否正常加载
3. 开始与 Kyuubi 交互！

## 💬 使用示例

重启客户端后，你可以通过自然语言与 Kyuubi 交互：

```
👤 用户: 列出所有数据库

🤖 Claude: [调用 kyuubi_list_databases 工具]
返回: ["default", "sales", "analytics"]

👤 用户: 查询 sales 表中今天的销售数据

🤖 Claude: [调用 kyuubi_query 工具]
SELECT * FROM sales WHERE date = CURRENT_DATE

👤 用户: 统计每个地区的订单总额，按金额降序排列

🤖 Claude: [调用 kyuubi_query 工具]
SELECT region, SUM(amount) as total 
FROM orders 
GROUP BY region 
ORDER BY total DESC

👤 用户: 查看 users 表的结构

🤖 Claude: [调用 kyuubi_describe_table 工具]
返回表的列信息...
```

## 🛠️ 可用工具

| 工具名称 | 功能描述 | 参数说明 |
|---------|---------|---------|
| `kyuubi_query` | 执行 SQL 查询（支持 Spark SQL） | `query`: SQL 查询语句 |
| `kyuubi_list_databases` | 列出所有可用数据库 | 无 |
| `kyuubi_list_tables` | 列出指定数据库的所有表 | `database`: 数据库名（可选） |
| `kyuubi_describe_table` | 获取表的结构信息 | `table`: 表名<br>`database`: 数据库名（可选） |
| `kyuubi_table_sample` | 获取表的样本数据 | `table`: 表名<br>`database`: 数据库名（可选）<br>`limit`: 返回行数（默认10） |

## 🔐 认证配置

### 无认证（开发测试环境）

```bash
KYUUBI_AUTH_TYPE=NONE
```

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
# 需要额外配置 krb5.conf 和 keytab 文件
# 详见 Kyuubi 官方文档
```

## 🐛 故障排除

### 问题 1：找不到 JDBC 驱动

**错误信息**：
```
java.lang.ClassNotFoundException: org.apache.hive.jdbc.HiveDriver
```

**解决方法**：
1. 确认 JAR 文件存在：`ls -la drivers/kyuubi-hive-jdbc-shaded.jar`
2. 使用绝对路径：`KYUUBI_JDBC_DRIVER_PATH=/absolute/path/to/driver.jar`
3. 检查 JAR 文件是否损坏：`jar -tf drivers/kyuubi-hive-jdbc-shaded.jar | grep HiveDriver`

### 问题 2：连接被拒绝

**错误信息**：
```
Connection refused
```

**解决方法**：
1. 检查 Kyuubi 服务是否运行：`telnet kyuubi-host 10009`
2. 确认主机名和端口号正确
3. 检查防火墙规则
4. 查看 Kyuubi 服务器日志

### 问题 3：认证失败

**错误信息**：
```
Authentication failed
```

**解决方法**：
1. 确认用户名和密码正确
2. 检查 `KYUUBI_AUTH_TYPE` 配置
3. 查看 Kyuubi 服务器端认证配置
4. 检查 Kyuubi 日志：`tail -f /path/to/kyuubi/logs/kyuubi-server.log`

### 问题 4：Java 环境问题

**错误信息**：
```
JVM 相关错误
```

**解决方法**：
1. 检查 Java 版本：`java -version`（需要 8+）
2. 设置 `JAVA_HOME`：`export JAVA_HOME=/path/to/java`
3. 检查 JVM 内存设置

### 问题 5：MCP 服务器未启动

**检查方法**：
1. 查看 Claude Desktop 日志（Help → View Logs）
2. 手动测试服务器：`uv run kyuubi-mcp-server`
3. 检查环境变量配置是否正确

## 📁 项目结构

```
kyuubi-mcp-server/
├── src/
│   └── kyuubi_mcp_server/
│       ├── __init__.py          # 包初始化文件
│       ├── server.py            # MCP 服务器主入口
│       ├── kyuubi_client.py     # Kyuubi 客户端封装（JayDeBeApi）
│       ├── tools.py             # MCP 工具定义
│       └── py.typed             # 类型标注文件
├── drivers/                     # JDBC 驱动目录
│   └── kyuubi-hive-jdbc-shaded.jar
├── pyproject.toml               # 项目配置（uv/pip）
├── env.example                  # 环境变量配置模板
├── README.md                    # 英文文档
├── README_CN.md                 # 中文文档（本文件）
└── LICENSE                      # 许可证文件
```

## 🔧 开发指南

### 运行测试

```bash
# 使用 uv
uv run pytest

# 使用 pytest-asyncio 测试异步代码
uv run pytest -v
```

### 代码格式化

```bash
# 使用 black 格式化代码
uv run black src/

# 检查代码风格
uv run black --check src/
```

### 类型检查

```bash
# 使用 mypy 进行类型检查
uv run mypy src/
```

### 手动测试服务器

```bash
# 直接运行 MCP 服务器（stdio 模式）
uv run kyuubi-mcp-server

# 或使用模块方式运行
uv run python -m kyuubi_mcp_server.server
```

### 添加新工具

1. 在 `tools.py` 中的 `get_tool_definitions()` 添加工具定义
2. 在 `execute_tool()` 中实现工具逻辑
3. 在 `kyuubi_client.py` 中添加必要的客户端方法
4. 更新文档

## 📚 参考资源

- [Kyuubi 官方文档](https://kyuubi.readthedocs.io/)
- [JayDeBeApi 使用指南](https://kyuubi.readthedocs.io/en/v1.10.2/client/python/jaydebeapi.html)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [Kyuubi JDBC Driver 下载](https://mvnrepository.com/artifact/org.apache.kyuubi/kyuubi-hive-jdbc-shaded)
- [uv 文档](https://github.com/astral-sh/uv)

## 📄 许可证

Apache License 2.0

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 👥 作者

Kyuubi Community

## 🙏 致谢

- [Apache Kyuubi](https://kyuubi.apache.org/) - 提供强大的 SQL 网关
- [Anthropic](https://www.anthropic.com/) - 开发 MCP 协议
- [JayDeBeApi](https://github.com/baztian/jaydebeapi) - Python JDBC 桥接库

---

如有问题，请提交 Issue 或加入 Kyuubi 社区讨论。

