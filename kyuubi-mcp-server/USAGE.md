# Kyuubi MCP Server - 使用指南

## 🚀 启动方式

Kyuubi MCP Server 支持两种传输协议：

### 1. stdio 模式（推荐用于 Claude Desktop / Cursor）

stdio 模式通过标准输入/输出进行通信，适合集成到桌面应用。

```bash
# 方式 1: 使用默认设置
uv run kyuubi-mcp-server

# 方式 2: 显式指定 stdio 模式
uv run kyuubi-mcp-server --transport stdio

# 方式 3: 使用 python -m 方式
uv run python -m kyuubi_mcp_server.server --transport stdio
```

### 2. HTTP 模式（适合远程访问）

HTTP 模式启动一个 HTTP 服务器，支持远程访问。

```bash
# 使用默认地址和端口 (0.0.0.0:8000)
uv run kyuubi-mcp-server --transport http

# 指定自定义地址和端口
uv run kyuubi-mcp-server --transport http --host 127.0.0.1 --port 9000

# 监听所有网络接口，端口 3000
uv run kyuubi-mcp-server --transport http --host 0.0.0.0 --port 3000
```

## 📝 命令行参数

```bash
kyuubi-mcp-server [OPTIONS]

选项:
  --transport {stdio,http}  MCP 传输协议 (默认: stdio)
  --host HOST              HTTP 服务器地址 (默认: 0.0.0.0)
  --port PORT              HTTP 服务器端口 (默认: 8000)
  -h, --help               显示帮助信息
```

## 🔧 配置方式

### 环境变量配置

所有配置通过环境变量设置：

```bash
# 必需配置
export KYUUBI_HOST=localhost
export KYUUBI_PORT=10009
export KYUUBI_JDBC_DRIVER_PATH=/path/to/kyuubi-hive-jdbc-shaded.jar

# 可选配置
export KYUUBI_DATABASE=default
export KYUUBI_AUTH_TYPE=NONE
export KYUUBI_USERNAME=
export KYUUBI_PASSWORD=
```

### 使用 .env 文件（推荐）

创建 `.env` 文件：

```bash
cp env.example .env
nano .env
```

编辑内容：

```bash
KYUUBI_HOST=kyuubi-server.example.com
KYUUBI_PORT=10009
KYUUBI_DATABASE=default
KYUUBI_AUTH_TYPE=PLAIN
KYUUBI_USERNAME=your_username
KYUUBI_PASSWORD=your_password
KYUUBI_JDBC_DRIVER_PATH=/absolute/path/to/drivers/kyuubi-hive-jdbc-shaded.jar
```

然后直接运行：

```bash
uv run kyuubi-mcp-server
```

`.env` 文件会自动加载。

## 🎯 使用场景

### 场景 1: Claude Desktop 集成 (stdio)

**配置文件**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "kyuubi": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/kyuubi-mcp-server",
        "run",
        "kyuubi-mcp-server",
        "--transport",
        "stdio"
      ],
      "env": {
        "KYUUBI_HOST": "localhost",
        "KYUUBI_PORT": "10009",
        "KYUUBI_JDBC_DRIVER_PATH": "/path/to/driver.jar"
      }
    }
  }
}
```

重启 Claude Desktop 即可使用。

### 场景 2: Cursor 集成 (stdio)

在 Cursor 设置中添加类似配置（具体配置方式请参考 Cursor 文档）。

### 场景 3: 独立 HTTP 服务器

启动 HTTP 服务器供多个客户端访问：

```bash
# 启动服务
uv run kyuubi-mcp-server --transport http --host 0.0.0.0 --port 8000
```

**服务访问地址**:
- 本地: `http://localhost:8000`
- 远程: `http://<server-ip>:8000`

**API 端点**:
- SSE (Server-Sent Events): `http://<server-ip>:8000/sse`
- Messages: `http://<server-ip>:8000/messages`

### 场景 4: Docker 部署 (HTTP)

创建 `Dockerfile`:

```dockerfile
FROM python:3.10-slim

# 安装 Java
RUN apt-get update && \
    apt-get install -y openjdk-11-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装依赖
RUN uv sync

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "kyuubi-mcp-server", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

构建和运行：

```bash
# 构建镜像
docker build -t kyuubi-mcp-server .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e KYUUBI_HOST=kyuubi-server.example.com \
  -e KYUUBI_PORT=10009 \
  -e KYUUBI_JDBC_DRIVER_PATH=/app/drivers/kyuubi-hive-jdbc-shaded.jar \
  -v /path/to/drivers:/app/drivers \
  kyuubi-mcp-server
```

### 场景 5: Systemd 服务 (HTTP)

创建服务文件 `/etc/systemd/system/kyuubi-mcp-server.service`:

```ini
[Unit]
Description=Kyuubi MCP Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/kyuubi-mcp-server
Environment="KYUUBI_HOST=localhost"
Environment="KYUUBI_PORT=10009"
Environment="KYUUBI_JDBC_DRIVER_PATH=/path/to/driver.jar"
ExecStart=/usr/local/bin/uv run kyuubi-mcp-server --transport http --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start kyuubi-mcp-server
sudo systemctl enable kyuubi-mcp-server
sudo systemctl status kyuubi-mcp-server
```

## 🧪 测试和调试

### 测试连接

```bash
# 测试 Kyuubi 连接
uv run python test_connection.py
```

### 手动测试 stdio 模式

```bash
# 启动服务器
uv run kyuubi-mcp-server --transport stdio

# 服务器会等待 stdin 输入，可以发送 JSON-RPC 消息测试
```

### 手动测试 HTTP 模式

```bash
# 启动服务器
uv run kyuubi-mcp-server --transport http --port 8000

# 在另一个终端测试
curl http://localhost:8000/sse
```

### 查看日志

日志会输出到标准错误流（stderr），包含以下信息：

- ✅ 连接状态
- 📋 工具调用
- 🔍 查询执行
- ❌ 错误信息

调整日志级别：

```bash
# 设置日志级别为 DEBUG
export LOG_LEVEL=DEBUG
uv run kyuubi-mcp-server
```

## 🔒 安全建议

### 1. stdio 模式

- ✅ 安全：仅本地通信
- ✅ 适合：桌面应用集成
- ⚠️ 注意：确保配置文件权限正确

### 2. HTTP 模式

- ⚠️ 警告：默认无认证
- 🔒 建议：
  - 仅在内网使用，或使用防火墙限制访问
  - 使用反向代理（如 Nginx）添加认证
  - 启用 HTTPS
  - 限制监听地址（如 `--host 127.0.0.1`）

#### 使用 Nginx 添加认证

`/etc/nginx/sites-available/kyuubi-mcp`:

```nginx
server {
    listen 443 ssl;
    server_name mcp.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Basic Auth
    auth_basic "Kyuubi MCP Server";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## 📊 性能优化

### 连接池（待实现）

当前版本使用单连接，未来版本将支持连接池：

```python
# 配置连接池大小
export KYUUBI_POOL_SIZE=10
export KYUUBI_POOL_MAX_OVERFLOW=20
```

### 超时设置

```bash
# 查询超时（秒）
export KYUUBI_QUERY_TIMEOUT=300
```

## 🐛 故障排除

### 问题: HTTP 模式端口被占用

```bash
# 查找占用端口的进程
lsof -i :8000

# 使用其他端口
uv run kyuubi-mcp-server --transport http --port 9000
```

### 问题: 无法访问 HTTP 服务

```bash
# 检查服务是否运行
curl http://localhost:8000/sse

# 检查防火墙
sudo ufw status
sudo ufw allow 8000

# 检查监听地址
netstat -tlnp | grep 8000
```

### 问题: stdio 模式无响应

- 检查 Claude Desktop 日志
- 确认配置文件 JSON 格式正确
- 使用绝对路径
- 重启 Claude Desktop

## 📚 更多资源

- [完整文档](README_CN.md)
- [快速开始](QUICKSTART_CN.md)
- [项目总结](PROJECT_SUMMARY.md)
- [Kyuubi 官方文档](https://kyuubi.readthedocs.io/)
- [FastMCP 文档](https://github.com/jlowin/fastmcp)

---

有问题？提交 [Issue](https://github.com/apache/kyuubi/issues)

