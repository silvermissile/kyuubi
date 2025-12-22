# Kyuubi 客户端对比：PyHive vs JayDeBeApi

本项目支持两种 Kyuubi 客户端：**PyHive** 和 **JayDeBeApi**。您可以根据实际需求选择合适的客户端。

## 🔍 快速对比

| 特性 | PyHive | JayDeBeApi |
|-----|--------|-----------|
| **通信协议** | Thrift (直接) | JDBC (通过 JVM) |
| **Java 依赖** | ❌ 无需 Java | ✅ 需要 JRE 8+ |
| **JDBC 驱动** | ❌ 不需要 | ✅ 需要下载 |
| **安装复杂度** | ⭐⭐⭐⭐⭐ 简单 | ⭐⭐⭐ 中等 |
| **性能** | ⭐⭐⭐⭐ 快 | ⭐⭐⭐ 一般 |
| **功能完整性** | ⭐⭐⭐ 基本完整 | ⭐⭐⭐⭐⭐ 100% |
| **适用场景** | 开发/测试/简单查询 | 生产/复杂场景 |

## 📋 详细对比

### PyHive

#### 优点 ✅

1. **无需 Java 环境**
   - 纯 Python 实现
   - 部署更轻量
   - 容器镜像更小

2. **安装简单**
   ```bash
   # 只需安装 Python 依赖
   uv sync --extra pyhive
   ```

3. **性能更好**
   - 直接使用 Thrift 协议
   - 无 JVM 开销
   - 启动更快

4. **调试方便**
   - 纯 Python 调试
   - 无跨语言问题

#### 缺点 ❌

1. **可能缺少部分高级特性**
   - 某些 JDBC 特有功能不支持
   - 复杂类型支持可能有限

2. **SASL/Kerberos 配置复杂**
   - 需要额外安装系统依赖
   ```bash
   # Linux
   sudo apt-get install libsasl2-dev
   
   # macOS
   brew install cyrus-sasl
   ```

3. **连接池支持较弱**
   - 需要自己实现连接池

#### 使用场景 🎯

- ✅ 开发和测试环境
- ✅ 无 Java 环境的场景
- ✅ 简单查询和探索
- ✅ 容器化部署（减小镜像大小）
- ✅ 性能敏感场景
- ❌ 需要完整 JDBC 特性
- ❌ 复杂认证（Kerberos）

---

### JayDeBeApi

#### 优点 ✅

1. **功能完整**
   - 100% JDBC 特性支持
   - 与 Kyuubi JDBC 驱动完全兼容
   - 支持所有数据类型

2. **官方支持**
   - Kyuubi 官方文档推荐
   - 使用官方 JDBC 驱动
   - 更新和维护有保障

3. **认证支持完善**
   - 支持所有认证方式
   - Kerberos 配置成熟
   - SSL/TLS 支持完整

4. **连接池成熟**
   - 可使用 JDBC 连接池
   - 企业级特性

#### 缺点 ❌

1. **需要 Java 环境**
   - 必须安装 JRE 8+
   - 部署复杂度增加
   - 容器镜像增大 ~200MB

2. **需要下载 JDBC 驱动**
   - 手动下载 JAR 文件
   - 管理驱动版本

3. **性能开销**
   - 通过 JVM 桥接
   - 启动较慢
   - 内存占用更大

4. **调试困难**
   - 跨语言调试
   - JVM 错误信息可能不清晰

#### 使用场景 🎯

- ✅ 生产环境
- ✅ 需要完整 JDBC 特性
- ✅ 复杂认证（Kerberos）
- ✅ 企业级应用
- ✅ 已有 Java 环境
- ❌ 轻量级部署
- ❌ 无 Java 环境
- ❌ 性能极致优化

---

## 🚀 如何选择

### 推荐：PyHive

**适合以下情况**：
- 开发和测试
- 简单的数据查询和探索
- 希望快速部署
- 无 Java 环境
- 对性能敏感

**配置方式**：
```bash
# 1. 安装依赖
uv sync --extra pyhive

# 2. 设置环境变量
export KYUUBI_CLIENT_TYPE=pyhive
export KYUUBI_HOST=localhost
export KYUUBI_PORT=10009
# 注意：不需要设置 KYUUBI_JDBC_DRIVER_PATH

# 3. 运行
uv run kyuubi-mcp-server
```

### 推荐：JayDeBeApi

**适合以下情况**：
- 生产环境
- 需要完整功能
- 复杂认证场景
- 已有 Java 环境
- 对功能完整性要求高

**配置方式**：
```bash
# 1. 安装 Java
sudo apt-get install openjdk-11-jre  # Linux
brew install openjdk@11              # macOS

# 2. 下载 JDBC 驱动
wget https://repo1.maven.org/maven2/org/apache/kyuubi/kyuubi-hive-jdbc-shaded/1.10.2/kyuubi-hive-jdbc-shaded-1.10.2.jar \
     -O drivers/kyuubi-hive-jdbc-shaded.jar

# 3. 安装依赖
uv sync --extra jaydebeapi

# 4. 设置环境变量
export KYUUBI_CLIENT_TYPE=jaydebeapi
export KYUUBI_HOST=localhost
export KYUUBI_PORT=10009
export KYUUBI_JDBC_DRIVER_PATH=/path/to/drivers/kyuubi-hive-jdbc-shaded.jar

# 5. 运行
uv run kyuubi-mcp-server
```

---

## 📦 安装指南

### 安装 PyHive 客户端

```bash
# 方式 1: 使用 uv（推荐）
uv sync --extra pyhive

# 方式 2: 使用 pip
pip install -e ".[pyhive]"

# Linux 上如果需要 SASL 支持（Kerberos）
sudo apt-get install -y libsasl2-dev libsasl2-modules-gssapi-mit

# macOS 上如果需要 SASL 支持
brew install cyrus-sasl
```

### 安装 JayDeBeApi 客户端

```bash
# 方式 1: 使用 uv（推荐）
uv sync --extra jaydebeapi

# 方式 2: 使用 pip
pip install -e ".[jaydebeapi]"

# 确保安装了 Java
java -version  # 应显示 Java 8 或更高版本
```

### 同时安装两种客户端

```bash
# 使用 uv
uv sync --extra all

# 使用 pip
pip install -e ".[all]"
```

---

## ⚙️ 配置示例

### 使用 PyHive（.env 配置）

```bash
# .env 文件
KYUUBI_HOST=kyuubi-server.example.com
KYUUBI_PORT=10009
KYUUBI_DATABASE=default
KYUUBI_AUTH_TYPE=PLAIN
KYUUBI_USERNAME=user1
KYUUBI_PASSWORD=password123
KYUUBI_CLIENT_TYPE=pyhive
# 注意：不需要 KYUUBI_JDBC_DRIVER_PATH
```

### 使用 JayDeBeApi（.env 配置）

```bash
# .env 文件
KYUUBI_HOST=kyuubi-server.example.com
KYUUBI_PORT=10009
KYUUBI_DATABASE=default
KYUUBI_AUTH_TYPE=PLAIN
KYUUBI_USERNAME=user1
KYUUBI_PASSWORD=password123
KYUUBI_CLIENT_TYPE=jaydebeapi
KYUUBI_JDBC_DRIVER_PATH=/absolute/path/to/drivers/kyuubi-hive-jdbc-shaded.jar
```

---

## 🧪 测试连接

```bash
# 设置客户端类型
export KYUUBI_CLIENT_TYPE=pyhive    # 或 jaydebeapi

# 运行测试脚本
uv run python test_connection.py
```

**预期输出**：

```
==============================================================
Kyuubi MCP Server - 连接测试
==============================================================

配置信息:
  Host: localhost
  Port: 10009
  Database: default
  Auth Type: NONE
  Client Type: pyhive          # 或 jaydebeapi
  ...

正在创建 Kyuubi 客户端（pyhive）...
正在连接到 Kyuubi...
✓ 连接成功!

✓ 找到 3 个数据库
✓ 找到 15 个表

✓ 所有测试通过!
```

---

## 🔧 故障排除

### PyHive 问题

#### 问题 1: ImportError: No module named 'thrift'

**解决**：
```bash
uv sync --extra pyhive
```

#### 问题 2: TTransportException: Could not connect

**检查**：
- Kyuubi 服务是否运行
- 主机名和端口是否正确
- 防火墙规则

#### 问题 3: SASL authentication failed (Kerberos)

**解决**：
```bash
# Linux
sudo apt-get install -y libsasl2-dev libsasl2-modules-gssapi-mit

# macOS
brew install cyrus-sasl

# 重新安装 PyHive
uv sync --extra pyhive --reinstall
```

### JayDeBeApi 问题

#### 问题 1: java.lang.ClassNotFoundException: org.apache.hive.jdbc.HiveDriver

**解决**：
```bash
# 确认 JDBC 驱动路径正确
ls -la $KYUUBI_JDBC_DRIVER_PATH

# 使用绝对路径
export KYUUBI_JDBC_DRIVER_PATH=/absolute/path/to/driver.jar
```

#### 问题 2: JVM cannot be started

**解决**：
```bash
# 检查 Java 安装
java -version

# 设置 JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

---

## 📊 性能对比

| 指标 | PyHive | JayDeBeApi |
|-----|--------|-----------|
| **启动时间** | ~500ms | ~2s (JVM 启动) |
| **连接建立** | ~200ms | ~500ms |
| **简单查询** | ~50ms | ~80ms |
| **大结果集** | ~1s | ~1.5s |
| **内存占用** | ~30MB | ~150MB (含 JVM) |
| **镜像大小** | ~100MB | ~300MB |

*注：以上数据为参考值，实际性能取决于具体环境*

---

## 🎯 最佳实践

### 开发环境

```bash
# 使用 PyHive（快速迭代）
KYUUBI_CLIENT_TYPE=pyhive
```

### 生产环境

```bash
# 使用 JayDeBeApi（稳定可靠）
KYUUBI_CLIENT_TYPE=jaydebeapi
```

### Docker 部署

**PyHive（轻量镜像）**：
```dockerfile
FROM python:3.10-slim
# 无需安装 Java
RUN apt-get update && apt-get install -y libsasl2-dev
# ...
```

**JayDeBeApi（完整功能）**：
```dockerfile
FROM python:3.10
# 安装 Java
RUN apt-get update && apt-get install -y openjdk-11-jre-headless
# ...
```

---

## 📚 更多资源

- [PyHive GitHub](https://github.com/dropbox/PyHive)
- [JayDeBeApi GitHub](https://github.com/baztian/jaydebeapi)
- [Kyuubi 官方文档 - PyHive](https://kyuubi.readthedocs.io/en/latest/client/python/pyhive.html)
- [Kyuubi 官方文档 - JayDeBeApi](https://kyuubi.readthedocs.io/en/latest/client/python/jaydebeapi.html)

---

**总结**：
- 🚀 **快速开始**：选择 PyHive
- 🏭 **生产环境**：选择 JayDeBeApi
- 🔄 **灵活切换**：两种客户端可以通过环境变量轻松切换

