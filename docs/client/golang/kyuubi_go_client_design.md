<!--
- Licensed to the Apache Software Foundation (ASF) under one or more
- contributor license agreements.  See the NOTICE file distributed with
- this work for additional information regarding copyright ownership.
- The ASF licenses this file to You under the Apache License, Version 2.0
- (the "License"); you may not use this file except in compliance with
- the License.  You may obtain a copy of the License at
-
-   http://www.apache.org/licenses/LICENSE-2.0
-
- Unless required by applicable law or agreed to in writing, software
- distributed under the License is distributed on an "AS IS" BASIS,
- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
- See the License for the specific language governing permissions and
- limitations under the License.
-->

# Kyuubi Go 客户端技术方案

## 1. 项目背景

### 1.1 原始需求

Kyuubi 是一个分布式多租户网关，为数据仓库和数据湖提供 Serverless SQL 能力。目前 Kyuubi 已经提供了 Java/Scala (JDBC)、Python (PyHive) 等客户端实现，但缺少 Go 语言的官方客户端支持。

### 1.2 实际使用场景

本技术方案的实际目标是为 **[genai-toolbox](https://github.com/googleapis/genai-toolbox)** 项目添加 Hive/Kyuubi 数据源支持。

**genai-toolbox 简介**:
- Google 开源的 MCP (Model Context Protocol) Toolbox 项目
- 用 **Go 语言**开发
- 为 LLM/AI Agent 提供数据库工具集成
- 已支持：MySQL, PostgreSQL, MongoDB, Redis, BigQuery, Spanner, Firestore, SQL Server, Oracle, TiDB 等
- 项目地址：https://github.com/googleapis/genai-toolbox

**集成目标**:
- 在 genai-toolbox 中添加 Kyuubi/Hive 作为新的数据源
- 允许 AI Agent 通过自然语言查询 Kyuubi 中的数据
- 与现有数据源保持一致的接口和体验

### 1.3 方案评估的新角度

由于实际场景是**集成到现有 Go 项目**，而不是开发独立客户端库，我们需要重新评估：
1. **直接集成 Go 库**（如 gohive）- 最自然的方案
2. **通过 Python 桥接**（PyHive/JayDeBeApi）- 复用现有成熟实现
3. **独立服务模式** - Python 服务 + HTTP/gRPC 接口

## 2. Kyuubi 架构分析

### 2.1 通信协议

Kyuubi 支持多种前端协议（通过 `kyuubi.frontend.protocols` 配置）：

| 协议类型 | 说明 | 成熟度 | 推荐指数 |
|---------|------|--------|---------|
| **THRIFT_BINARY** | HiveServer2 兼容的 Thrift 二进制协议 | 生产就绪 | ⭐⭐⭐⭐⭐ |
| **THRIFT_HTTP** | HiveServer2 兼容的 Thrift HTTP 协议 | 生产就绪 | ⭐⭐⭐⭐ |
| **REST** | Kyuubi 定义的 REST API | 实验性 | ⭐⭐⭐ |
| **MYSQL** | MySQL 兼容的文本协议 | 实验性 | ⭐⭐ |
| **TRINO** | Trino 兼容的 HTTP 协议 | 实验性 | ⭐⭐ |

**默认协议**: `THRIFT_BINARY` 和 `REST`

### 2.2 Thrift 服务接口 (TCLIService)

Kyuubi 基于 HiveServer2 的 Thrift 接口 `TCLIService`，主要方法包括：

```thrift
service TCLIService {
  // 会话管理
  TOpenSessionResp OpenSession(1:TOpenSessionReq req);
  TCloseSessionResp CloseSession(1:TCloseSessionReq req);
  TGetInfoResp GetInfo(1:TGetInfoReq req);
  
  // SQL 执行
  TExecuteStatementResp ExecuteStatement(1:TExecuteStatementReq req);
  
  // 操作管理
  TGetOperationStatusResp GetOperationStatus(1:TGetOperationStatusReq req);
  TCancelOperationResp CancelOperation(1:TCancelOperationReq req);
  TCloseOperationResp CloseOperation(1:TCloseOperationReq req);
  
  // 结果获取
  TGetResultSetMetadataResp GetResultSetMetadata(1:TGetResultSetMetadataReq req);
  TFetchResultsResp FetchResults(1:TFetchResultsReq req);
  
  // 元数据查询
  TGetCatalogsResp GetCatalogs(1:TGetCatalogsReq req);
  TGetSchemasResp GetSchemas(1:TGetSchemasReq req);
  TGetTablesResp GetTables(1:TGetTablesReq req);
  TGetColumnsResp GetColumns(1:TGetColumnsReq req);
  TGetFunctionsResp GetFunctions(1:TGetFunctionsReq req);
  
  // 其他
  TGetLogResp GetLog(1:TGetLogReq req);
}
```

### 2.3 协议版本

Kyuubi 支持 Hive Thrift 协议版本 V1-V10：
- **默认版本**: V10 (对应 `clientProtocolVersion=9`, Hive 2.3.0+)
- **兼容性**: 可降级支持更早版本的 HiveServer2

### 2.4 认证方式

- **NONE**: 无认证（开发测试）
- **PLAIN**: 用户名/密码认证（通过 SASL PLAIN 机制）
- **KERBEROS**: Kerberos 认证（生产环境推荐）
- **LDAP**: LDAP 认证
- **CUSTOM**: 自定义认证插件

## 3. Go 客户端技术方案选型

### 3.1 方案对比

参考 Python 客户端的实现，有两种主流方式：
1. **PyHive**: 直接使用 Thrift 协议连接（类似从头实现）
2. **JayDeBeApi**: 通过 JVM 复用 Java JDBC 驱动（复用已有实现）

对应到 Go 语言，我们也有多种方案选择：

#### 方案一：复用现有 Go HiveServer2 客户端库（最推荐 ⭐⭐⭐⭐⭐）

**技术栈**:
```
使用社区现有库
    ↓
github.com/beltran/gohive
    ↓
Thrift HiveServer2 Protocol
    ↓
Kyuubi Server
```

**核心依赖**:
- `github.com/beltran/gohive` - 成熟的 Go HiveServer2 客户端库

**优势**:
- ✅ **开箱即用**: 库已经实现了完整的 HiveServer2 协议
- ✅ **实现简单**: 只需几行代码即可连接和查询
- ✅ **维护成本低**: 由社区维护，无需自己维护 Thrift 代码
- ✅ **功能完整**: 支持认证、异步查询、连接池等
- ✅ **生产验证**: 已被多个项目使用验证

**劣势**:
- ❌ **依赖第三方**: 需要依赖社区库的更新
- ❌ **定制化受限**: 如需特殊功能需要等待上游支持或 fork

**适用场景**: 大部分生产场景，快速集成 Kyuubi

**实现示例**:
```go
import (
    "context"
    "github.com/beltran/gohive"
)

// 连接配置
configuration := gohive.NewConnectConfiguration()
configuration.Username = "user1"
configuration.Password = "password"

// 连接到 Kyuubi
conn, err := gohive.Connect("kyuubi-server", 10009, "NONE", configuration)
if err != nil {
    log.Fatal(err)
}
defer conn.Close()

// 创建游标
cursor := conn.Cursor()

// 执行查询
cursor.Exec(context.Background(), "SELECT * FROM table WHERE id > 100")
if cursor.Err != nil {
    log.Fatal(cursor.Err)
}

// 获取结果
for cursor.HasMore(context.Background()) {
    var row []interface{}
    cursor.FetchOne(context.Background(), &row)
    fmt.Println(row)
}
```

---

#### 方案二：通过 CGO/JNI 复用 Java JDBC 驱动（备选 ⭐⭐⭐）

**技术栈**:
```
Go 应用
    ↓
CGO + JNI
    ↓
Kyuubi JDBC Driver (Java)
    ↓
Kyuubi Server
```

**核心依赖**:
- CGO 和 JNI 绑定
- Java 运行时环境（JRE）
- `kyuubi-hive-jdbc-shaded.jar`

**优势**:
- ✅ **官方驱动**: 使用 Kyuubi 官方维护的 JDBC 驱动
- ✅ **功能完整**: 支持所有 JDBC 驱动的特性
- ✅ **稳定可靠**: JDBC 驱动经过充分测试

**劣势**:
- ❌ **引入 Java 依赖**: 需要 JRE 环境，增加部署复杂度
- ❌ **跨语言调用开销**: JNI 调用有性能开销
- ❌ **维护复杂**: CGO 代码维护成本高
- ❌ **构建复杂**: 交叉编译困难

**适用场景**: 已有 Java 环境的应用，需要使用 JDBC 特定功能

**参考实现**: 类似 Python 的 JayDeBeApi

---

#### 方案三：从头实现 Thrift 客户端（不推荐 ⭐⭐）

**技术栈**:
```
Go 应用（自己实现）
    ↓
github.com/apache/thrift
    ↓
TCLIService (HiveServer2)
    ↓
Kyuubi Server
```

**核心依赖**:
- `github.com/apache/thrift` - Apache Thrift Go 库
- 需要从 Hive Thrift IDL 文件生成 Go 代码

**优势**:
- ✅ **完全控制**: 可以完全定制功能和行为
- ✅ **性能可优化**: 可以针对特定场景优化
- ✅ **无外部依赖**: 不依赖第三方库

**劣势**:
- ❌ **实现复杂**: 需要处理所有 Thrift 协议细节
- ❌ **维护成本高**: 需要自己维护和更新
- ❌ **开发周期长**: 需要 3-6 个月完整实现
- ❌ **测试工作量大**: 需要全面的测试覆盖
- ❌ **认证复杂**: SASL/Kerberos 认证实现困难

**适用场景**: 有特殊定制需求、有充足开发资源、长期维护计划

**参考实现**: PyHive 的实现方式

---

#### 方案四：基于 REST API（备选 ⭐⭐⭐）

**技术栈**:
```
Go HTTP 客户端
    ↓
REST API (JSON)
    ↓
Kyuubi REST Service
    ↓
Kyuubi Server
```

**核心依赖**:
- 标准库 `net/http`
- `encoding/json`

**优势**:
- ✅ **实现简单**: 标准 HTTP/JSON，易于开发调试
- ✅ **无需代码生成**: 直接使用 HTTP 客户端
- ✅ **跨语言友好**: REST API 通用性强
- ✅ **调试方便**: 可使用 curl、Postman 测试

**劣势**:
- ❌ **实验性质**: REST API 在 Kyuubi 中标记为实验性
- ❌ **功能受限**: 可能不支持某些高级特性
- ❌ **性能较低**: JSON 序列化/反序列化开销
- ❌ **稳定性**: API 可能在未来版本变化

**适用场景**: 快速原型开发、轻量级应用、Web 服务集成

---

#### 方案五：基于 MySQL 协议（不推荐 ⭐）

**技术栈**:
```
Go MySQL Driver
    ↓
MySQL Wire Protocol
    ↓
Kyuubi MySQL Frontend
    ↓
Kyuubi Server
```

**核心依赖**:
- `github.com/go-sql-driver/mysql`

**优势**:
- ✅ **开箱即用**: 可直接使用 MySQL 驱动
- ✅ **标准 database/sql**: 符合 Go 数据库接口规范

**劣势**:
- ❌ **实验性质**: Kyuubi MySQL 协议为实验性
- ❌ **功能受限**: MySQL 协议无法支持全部 Spark SQL 特性
- ❌ **兼容性问题**: 可能存在协议兼容性问题

**适用场景**: 已有 MySQL 生态的应用快速迁移

---

#### 方案六：独立 Python MCP 服务（最优方案 ⭐⭐⭐⭐⭐）

**技术栈**:
```
LLM / AI Agent
    ↓
MCP Protocol (stdio/HTTP/SSE)
    ↓
Independent Python MCP Server
    ↓
PyHive / JayDeBeApi
    ↓
Kyuubi Server
```

**核心依赖**:
- Python 3.x
- PyHive 或 JayDeBeApi
- MCP Python SDK

**优势**:
- ✅ **最简单**: 纯 Python 开发，无需跨语言桥接
- ✅ **最易维护**: 独立服务，独立部署和升级
- ✅ **功能最强**: 100% Kyuubi 特性，使用官方客户端
- ✅ **生态最好**: Python 数据生态最成熟
- ✅ **无需改 genai-toolbox**: 不需要修改 Go 代码
- ✅ **MCP 原生**: 符合 MCP 架构设计理念
- ✅ **独立演进**: 可以独立开发、测试、发布

**劣势**:
- 需要独立部署和运维（实际上这也是优势）

**适用场景**: **所有场景的最佳选择**（除非必须集成到 genai-toolbox）

**MCP 架构示意**:
```
Claude Desktop / Cursor / 其他 MCP 客户端
              ↓
         MCP Protocol
              ↓
    Kyuubi MCP Server (Python)
         - PyHive/JayDeBeApi
         - 工具定义
         - 查询执行
              ↓
         Kyuubi/Hive
```

---

#### 方案七：Go + Python 桥接（genai-toolbox 集成 ⭐⭐⭐⭐）

**技术栈**:
```
genai-toolbox (Go)
    ↓
exec.Command / subprocess
    ↓
Python Script (PyHive/JayDeBeApi)
    ↓
Kyuubi Server
```

**核心依赖**:
- Python 3.x 运行时
- PyHive 或 JayDeBeApi
- Go 标准库 `os/exec`

**优势**:
- ✅ **复用成熟方案**: 直接使用 Kyuubi 官方支持的 Python 客户端
- ✅ **功能完整**: PyHive/JayDeBeApi 功能经过充分验证
- ✅ **开发极快**: 1-3 天即可完成集成
- ✅ **维护简单**: Python 客户端由 Kyuubi 官方维护
- ✅ **无需学习 Go Thrift**: 避免处理复杂的 Thrift 绑定
- ✅ **符合 genai-toolbox 模式**: 类似其他数据源的集成方式

**劣势**:
- ❌ **引入 Python 依赖**: 需要 Python 运行时环境
- ❌ **跨进程调用开销**: 比纯 Go 实现稍慢
- ❌ **部署复杂度**: 需要确保 Python 环境和依赖

**适用场景**: **为 genai-toolbox 添加 Kyuubi 支持（最佳方案）**

**实现示例**:
```go
package kyuubi

import (
    "context"
    "encoding/json"
    "os/exec"
)

// 通过 Python PyHive 执行查询
func QueryViaPyHive(query string, config Config) ([]map[string]interface{}, error) {
    // 调用 Python 脚本
    cmd := exec.CommandContext(
        context.Background(),
        "python3", 
        "scripts/kyuubi_query.py",
        "--host", config.Host,
        "--port", fmt.Sprint(config.Port),
        "--query", query,
    )
    
    output, err := cmd.Output()
    if err != nil {
        return nil, err
    }
    
    var result []map[string]interface{}
    json.Unmarshal(output, &result)
    return result, nil
}
```

---

### 3.2 推荐方案

#### 🏆 最优方案：独立 Python MCP 服务（方案六）⭐⭐⭐⭐⭐

**所有场景的最佳选择**

**推荐理由**:
1. ✅ **最简单**: 纯 Python 开发，2-4 天完成
2. ✅ **最易维护**: 独立服务，独立升级
3. ✅ **功能最强**: 100% Kyuubi 特性
4. ✅ **生态最好**: Python 数据生态最成熟
5. ✅ **架构最优**: 符合 MCP 设计理念
6. ✅ **无需修改 genai-toolbox**: 作为独立 MCP 服务使用

**关键优势**:
- 🎯 **语言无关**: MCP 协议本身就是语言无关的
- 🔧 **独立演进**: 可以独立开发、测试、发布、部署
- 📦 **开箱即用**: 直接使用 PyHive/JayDeBeApi 官方实现
- 🔒 **零维护**: 依赖由 Kyuubi 官方维护
- 🚀 **快速迭代**: Python 开发速度快，调试方便

**参考项目**:
- genai-toolbox 本身就是一个独立的 MCP server
- 其他数据源（MySQL, PostgreSQL）也都是独立服务

---

#### 次选方案：集成到 genai-toolbox（方案七：Python 桥接）⭐⭐⭐⭐

**仅当必须集成到 genai-toolbox 时使用**

**适用场景**:
- 必须作为 genai-toolbox 的一部分
- 需要统一配置和管理
- 团队要求统一技术栈

**权衡**:
- ⚖️ 开发复杂度：需要跨语言桥接
- ⚖️ 调试难度：跨进程调试
- ⚖️ 灵活性：受限于 genai-toolbox 架构

---

#### 备选方案：纯 Go 实现（方案一：gohive）⭐⭐⭐

**适用场景**:
- 不希望引入 Python 依赖
- 需要纯 Go 技术栈
- 对性能有极致要求（实际上差异不大）

**权衡**:
- ⚖️ 开发时间：1-2 周
- ⚖️ 维护成本：中等
- ⚖️ 功能完整性：95%

---

#### 不推荐方案

- **REST API（方案四）**：❌ 实验性质，功能受限
- **从头实现（方案三）**：❌ 4-5 个月开发周期，完全不合理
- **CGO+JNI（方案二）**：❌ 复杂度高，性能增益低

## 4. 最优方案：独立 Python MCP 服务

### 4.1 方案概述

**开发独立的 Python MCP 服务是最优方案**，原因如下：

1. **最简单**: 纯 Python 开发，无需跨语言桥接
2. **最强大**: 直接使用 PyHive/JayDeBeApi，100% 功能支持
3. **最易维护**: 独立服务，独立部署和升级
4. **架构最优**: 符合 MCP 协议设计理念（语言无关）
5. **无需修改 genai-toolbox**: 作为独立 MCP 服务，可被任何 MCP 客户端使用

**MCP 协议介绍**:
- MCP (Model Context Protocol) 是一个开放协议，用于 LLM 与外部工具的集成
- 协议本身是**语言无关**的（通过 stdio、HTTP、SSE 通信）
- genai-toolbox 是用 Go 实现的一个 MCP server，但你也可以用任何语言实现
- Claude Desktop、Cursor 等都支持 MCP

**架构对比**:

```
❌ 集成方案（不推荐）:
genai-toolbox (Go) 
  → Python 桥接脚本 
    → PyHive 
      → Kyuubi

✅ 独立服务（推荐）:
MCP Client (Claude/Cursor/etc) 
  → MCP Protocol 
    → Kyuubi MCP Server (Pure Python)
      → PyHive/JayDeBeApi 
        → Kyuubi
```

### 4.2 完整实现

#### 4.2.1 项目结构

```
kyuubi-mcp-server/
├── src/
│   ├── __init__.py
│   ├── server.py           # MCP 服务器主入口
│   ├── kyuubi_client.py    # Kyuubi 客户端封装
│   └── tools.py            # 工具定义
├── tests/
│   ├── test_kyuubi_client.py
│   └── test_tools.py
├── config/
│   └── kyuubi_config.yaml  # 数据源配置
├── requirements.txt
├── pyproject.toml
├── README.md
└── LICENSE
```

#### 4.2.2 核心代码实现

**文件**: `src/kyuubi_client.py`

```python
"""
Kyuubi 客户端封装
支持 PyHive 和 JayDeBeApi 两种方式
"""

from typing import List, Dict, Any, Optional
import logging

# 使用 PyHive（推荐）
from pyhive import hive

# 或使用 JayDeBeApi（JDBC 方式，功能更完整）
# import jaydebeapi

logger = logging.getLogger(__name__)


class KyuubiClient:
    """Kyuubi 客户端"""
    
    def __init__(
        self,
        host: str,
        port: int = 10009,
        username: str = "",
        password: str = "",
        database: str = "default",
        auth_type: str = "NONE",
        use_jdbc: bool = False,
        jdbc_driver_path: Optional[str] = None
    ):
        """
        初始化 Kyuubi 客户端
        
        Args:
            host: Kyuubi 服务器地址
            port: Kyuubi 服务器端口
            username: 用户名
            password: 密码
            database: 默认数据库
            auth_type: 认证类型 (NONE, CUSTOM, LDAP, KERBEROS)
            use_jdbc: 是否使用 JDBC 方式（JayDeBeApi）
            jdbc_driver_path: JDBC 驱动路径
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.auth_type = auth_type
        self.use_jdbc = use_jdbc
        self.jdbc_driver_path = jdbc_driver_path
        
        self._connection = None
    
    def connect(self):
        """建立连接"""
        if self.use_jdbc:
            self._connect_jdbc()
        else:
            self._connect_pyhive()
    
    def _connect_pyhive(self):
        """使用 PyHive 连接"""
        try:
            if self.auth_type in ["CUSTOM", "LDAP"]:
                self._connection = hive.Connection(
                    host=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    database=self.database,
                    auth=self.auth_type
                )
            elif self.auth_type == "KERBEROS":
                self._connection = hive.Connection(
                    host=self.host,
                    port=self.port,
                    auth="KERBEROS",
                    kerberos_service_name="kyuubi",
                    database=self.database
                )
            else:
                self._connection = hive.Connection(
                    host=self.host,
                    port=self.port,
                    username=self.username,
                    database=self.database
                )
            logger.info(f"Connected to Kyuubi at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Kyuubi: {e}")
            raise
    
    def _connect_jdbc(self):
        """使用 JayDeBeApi (JDBC) 连接"""
        import jaydebeapi
        
        try:
            jdbc_url = f"jdbc:hive2://{self.host}:{self.port}/{self.database}"
            
            if self.auth_type in ["CUSTOM", "LDAP"]:
                jdbc_url += f";auth={self.auth_type}"
            
            self._connection = jaydebeapi.connect(
                "org.apache.hive.jdbc.HiveDriver",
                jdbc_url,
                [self.username, self.password],
                self.jdbc_driver_path
            )
            logger.info(f"Connected to Kyuubi via JDBC at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Kyuubi via JDBC: {e}")
            raise
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        执行查询并返回结果
        
        Args:
            query: SQL 查询语句
            
        Returns:
            查询结果（列表，每行为字典）
        """
        if not self._connection:
            self.connect()
        
        try:
            cursor = self._connection.cursor()
            cursor.execute(query)
            
            # 获取列名
            columns = [desc[0] for desc in cursor.description]
            
            # 获取所有结果
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            
            logger.info(f"Query executed successfully, returned {len(results)} rows")
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_tables(self, database: Optional[str] = None) -> List[str]:
        """获取数据库中的表列表"""
        db = database or self.database
        query = f"SHOW TABLES IN {db}"
        results = self.execute_query(query)
        return [row['tab_name'] for row in results]
    
    def get_schema(self, table: str, database: Optional[str] = None) -> List[Dict[str, str]]:
        """获取表的 schema"""
        db = database or self.database
        query = f"DESCRIBE {db}.{table}"
        return self.execute_query(query)
    
    def get_databases(self) -> List[str]:
        """获取所有数据库"""
        results = self.execute_query("SHOW DATABASES")
        return [row['database_name'] for row in results]
    
    def close(self):
        """关闭连接"""
        if self._connection:
            self._connection.close()
            logger.info("Connection closed")
```

**文件**: `src/tools.py`

```python
"""
MCP 工具定义
"""

from typing import Any, Dict, List
from .kyuubi_client import KyuubiClient


class KyuubiTools:
    """Kyuubi MCP 工具集"""
    
    def __init__(self, client: KyuubiClient):
        self.client = client
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        获取所有工具定义（MCP 格式）
        """
        return [
            {
                "name": "kyuubi_query",
                "description": "Execute a SQL query on Kyuubi/Hive and return results",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SQL query to execute"
                        },
                        "database": {
                            "type": "string",
                            "description": "Optional database name"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "kyuubi_list_tables",
                "description": "List all tables in a Kyuubi/Hive database",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": "Database name (default: 'default')"
                        }
                    }
                }
            },
            {
                "name": "kyuubi_describe_table",
                "description": "Get the schema/structure of a table",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "description": "Table name"
                        },
                        "database": {
                            "type": "string",
                            "description": "Database name (optional)"
                        }
                    },
                    "required": ["table"]
                }
            },
            {
                "name": "kyuubi_list_databases",
                "description": "List all databases in Kyuubi/Hive",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            执行结果
        """
        if tool_name == "kyuubi_query":
            query = arguments.get("query")
            return self.client.execute_query(query)
        
        elif tool_name == "kyuubi_list_tables":
            database = arguments.get("database")
            return self.client.get_tables(database)
        
        elif tool_name == "kyuubi_describe_table":
            table = arguments["table"]
            database = arguments.get("database")
            return self.client.get_schema(table, database)
        
        elif tool_name == "kyuubi_list_databases":
            return self.client.get_databases()
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
```

**文件**: `src/server.py`

```python
"""
Kyuubi MCP 服务器
使用 MCP Python SDK
"""

import asyncio
import logging
from typing import Any
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from .kyuubi_client import KyuubiClient
from .tools import KyuubiTools

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kyuubi-mcp-server")

# 创建 MCP server 实例
app = Server("kyuubi-mcp-server")

# 全局变量（可以改为配置文件）
kyuubi_client = None
kyuubi_tools = None


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    列出所有可用工具
    """
    if not kyuubi_tools:
        return []
    
    tool_defs = kyuubi_tools.get_tool_definitions()
    
    tools = []
    for tool_def in tool_defs:
        tools.append(
            types.Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                inputSchema=tool_def["inputSchema"]
            )
        )
    
    return tools


@app.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    执行工具调用
    """
    if not kyuubi_tools:
        raise ValueError("Kyuubi client not initialized")
    
    try:
        # 执行工具
        result = kyuubi_tools.execute_tool(name, arguments or {})
        
        # 格式化结果
        import json
        result_text = json.dumps(result, indent=2, default=str)
        
        return [
            types.TextContent(
                type="text",
                text=result_text
            )
        ]
        
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]


async def main():
    """
    主函数：初始化客户端并启动服务器
    """
    global kyuubi_client, kyuubi_tools
    
    # TODO: 从配置文件读取
    kyuubi_client = KyuubiClient(
        host="localhost",
        port=10009,
        username="user1",
        password="password",
        database="default",
        auth_type="NONE"
    )
    
    kyuubi_tools = KyuubiTools(kyuubi_client)
    
    logger.info("Starting Kyuubi MCP Server...")
    
    # 通过 stdio 运行服务器
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="kyuubi-mcp-server",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
```

#### 4.2.3 配置文件

**文件**: `config/kyuubi_config.yaml`

```yaml
# Kyuubi 连接配置
kyuubi:
  host: kyuubi-server.example.com
  port: 10009
  username: user1
  password: ${KYUUBI_PASSWORD}  # 从环境变量读取
  database: default
  auth_type: PLAIN  # NONE, PLAIN, CUSTOM, LDAP, KERBEROS
  
  # 可选：使用 JDBC 方式
  use_jdbc: false
  jdbc_driver_path: /path/to/kyuubi-hive-jdbc-shaded.jar
```

**文件**: `requirements.txt`

```txt
# MCP SDK
mcp>=0.1.0

# Kyuubi 客户端（二选一）
pyhive[hive]>=0.6.5

# 或使用 JDBC 方式（功能更完整）
# JayDeBeApi>=1.2.3

# 工具库
PyYAML>=6.0
python-dotenv>=1.0.0
```

#### 4.2.4 使用方法

**1. 安装依赖**

```bash
pip install -r requirements.txt

# 如果需要 SASL 支持（Kerberos）
# Linux
sudo apt-get install -y cyrus-sasl-plain cyrus-sasl-devel cyrus-sasl-gssapi

# macOS
brew install cyrus-sasl
```

**2. 配置 MCP 客户端**

在 Claude Desktop 配置文件中添加：

**文件**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "kyuubi": {
      "command": "python",
      "args": ["-m", "kyuubi_mcp_server"],
      "env": {
        "KYUUBI_HOST": "kyuubi-server.example.com",
        "KYUUBI_PORT": "10009",
        "KYUUBI_USERNAME": "user1",
        "KYUUBI_PASSWORD": "password"
      }
    }
  }
}
```

**3. 启动服务**

```bash
# 直接运行
python -m src.server

# 或使用环境变量
export KYUUBI_HOST=localhost
export KYUUBI_PORT=10009
export KYUUBI_USERNAME=user1
export KYUUBI_PASSWORD=password

python -m src.server
```

**4. 在 Claude Desktop 中使用**

```
User: 请查询 sales 表中今天的销售数据

Claude 会调用: kyuubi_query
参数: {
  "query": "SELECT * FROM sales WHERE date = CURRENT_DATE"
}

User: 列出所有数据库

Claude 会调用: kyuubi_list_databases

User: 查看 users 表的结构

Claude 会调用: kyuubi_describe_table
参数: {
  "table": "users"
}
```

### 4.3 优势总结

| 优势项 | 说明 | 重要性 |
|-------|------|--------|
| **开发速度** | 2-4 天完成 | ⭐⭐⭐⭐⭐ |
| **维护成本** | 零维护（PyHive 官方维护） | ⭐⭐⭐⭐⭐ |
| **功能完整性** | 100% Kyuubi 特性 | ⭐⭐⭐⭐⭐ |
| **架构优雅** | 符合 MCP 设计理念 | ⭐⭐⭐⭐⭐ |
| **部署灵活** | 独立部署、升级 | ⭐⭐⭐⭐⭐ |
| **语言无关** | 任何 MCP 客户端都能用 | ⭐⭐⭐⭐⭐ |
| **调试方便** | 纯 Python，无跨语言问题 | ⭐⭐⭐⭐ |

### 4.4 与其他方案对比

| 对比项 | 独立 MCP 服务 | 集成到 genai-toolbox | 纯 Go 实现 |
|-------|--------------|---------------------|-----------|
| 开发时间 | **2-4 天** | 4-8 天 | 10-14 天 |
| 技术栈 | **纯 Python** | Go + Python | 纯 Go |
| 维护成本 | **零** | 低 | 中 |
| 部署方式 | **独立服务** | genai-toolbox 一部分 | 独立或集成 |
| 功能完整性 | **100%** | 100% | 95% |
| 调试难度 | **简单** | 中等（跨进程） | 简单 |
| 适用场景 | **通用** | 仅 genai-toolbox | 通用 |

**结论**: **独立 Python MCP 服务是最优选择**

## 5. 次选方案：集成到 genai-toolbox（Python 桥接）

如果**必须**将 Kyuubi 集成到 genai-toolbox 中（而不是作为独立 MCP 服务），可以参考以下方案。

### 5.1 方案概述

通过 Python 桥接，在 genai-toolbox 中集成 Kyuubi 支持。

**架构图**:
```
┌─────────────────────────────────────┐
│   genai-toolbox (Go Application)    │
│                                     │
│  ┌─────────────────────────────┐  │
│  │  Kyuubi Source Handler      │  │
│  │  (Go Code)                  │  │
│  └──────────┬──────────────────┘  │
│             │                       │
│             │ exec.Command          │
│             ▼                       │
│  ┌─────────────────────────────┐  │
│  │  Python Bridge Script       │  │
│  │  (kyuubi_bridge.py)         │  │
│  └──────────┬──────────────────┘  │
└─────────────┼───────────────────────┘
              │
              │ PyHive / JayDeBeApi
              ▼
     ┌────────────────────┐
     │  Kyuubi Server     │
     └────────────────────┘
```

### 4.2 实现步骤

#### 4.2.1 创建 Python 桥接脚本

**文件**: `scripts/kyuubi_bridge.py`

```python
#!/usr/bin/env python3
"""
Kyuubi Bridge for genai-toolbox
使用 PyHive 连接 Kyuubi 并执行查询
"""

import json
import sys
import argparse
from typing import List, Dict, Any

# 使用 PyHive（推荐）
from pyhive import hive

def execute_query(
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
    query: str,
    auth_type: str = "NONE"
) -> List[Dict[str, Any]]:
    """
    执行 SQL 查询并返回结果
    
    Args:
        host: Kyuubi 服务器地址
        port: Kyuubi 服务器端口
        username: 用户名
        password: 密码
        database: 数据库名
        query: SQL 查询语句
        auth_type: 认证类型（NONE, CUSTOM, LDAP, KERBEROS）
    
    Returns:
        查询结果列表（每行为一个字典）
    """
    try:
        # 建立连接
        if auth_type in ["CUSTOM", "LDAP"]:
            conn = hive.Connection(
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
                auth=auth_type
            )
        elif auth_type == "KERBEROS":
            # Kerberos 认证
            conn = hive.Connection(
                host=host,
                port=port,
                auth="KERBEROS",
                kerberos_service_name="kyuubi",
                database=database
            )
        else:
            # 无认证
            conn = hive.Connection(
                host=host,
                port=port,
                username=username,
                database=database
            )
        
        # 执行查询
        cursor = conn.cursor()
        cursor.execute(query)
        
        # 获取列名
        columns = [desc[0] for desc in cursor.description]
        
        # 获取结果
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        return results
        
    except Exception as e:
        # 返回错误信息
        return {
            "error": str(e),
            "type": type(e).__name__
        }

def get_tables(
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
    auth_type: str = "NONE"
) -> List[str]:
    """获取数据库中的表列表"""
    query = f"SHOW TABLES IN {database}"
    results = execute_query(host, port, username, password, database, query, auth_type)
    
    if isinstance(results, dict) and "error" in results:
        return results
    
    return [row['tab_name'] for row in results]

def get_schema(
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
    table: str,
    auth_type: str = "NONE"
) -> List[Dict[str, str]]:
    """获取表的 schema"""
    query = f"DESCRIBE {database}.{table}"
    results = execute_query(host, port, username, password, database, query, auth_type)
    
    if isinstance(results, dict) and "error" in results:
        return results
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Kyuubi Bridge for genai-toolbox')
    parser.add_argument('--host', required=True, help='Kyuubi server host')
    parser.add_argument('--port', type=int, required=True, help='Kyuubi server port')
    parser.add_argument('--username', default='', help='Username')
    parser.add_argument('--password', default='', help='Password')
    parser.add_argument('--database', default='default', help='Database name')
    parser.add_argument('--auth', default='NONE', help='Auth type (NONE, CUSTOM, LDAP, KERBEROS)')
    parser.add_argument('--action', required=True, 
                       choices=['query', 'tables', 'schema'],
                       help='Action to perform')
    parser.add_argument('--query', help='SQL query to execute')
    parser.add_argument('--table', help='Table name (for schema action)')
    
    args = parser.parse_args()
    
    try:
        if args.action == 'query':
            if not args.query:
                raise ValueError("--query is required for 'query' action")
            result = execute_query(
                args.host, args.port, args.username, args.password,
                args.database, args.query, args.auth
            )
        elif args.action == 'tables':
            result = get_tables(
                args.host, args.port, args.username, args.password,
                args.database, args.auth
            )
        elif args.action == 'schema':
            if not args.table:
                raise ValueError("--table is required for 'schema' action")
            result = get_schema(
                args.host, args.port, args.username, args.password,
                args.database, args.table, args.auth
            )
        
        # 输出 JSON 结果
        print(json.dumps(result, default=str, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "type": type(e).__name__
        }
        print(json.dumps(error_result), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

#### 4.2.2 创建 Go 集成代码

**文件**: `internal/sources/kyuubi/kyuubi.go`

```go
package kyuubi

import (
    "context"
    "encoding/json"
    "fmt"
    "os/exec"
    "strings"
)

// Source 表示 Kyuubi 数据源
type Source struct {
    Host     string
    Port     int
    Username string
    Password string
    Database string
    AuthType string // NONE, CUSTOM, LDAP, KERBEROS
}

// Config 数据源配置
type Config struct {
    Host     string `yaml:"host"`
    Port     int    `yaml:"port"`
    Username string `yaml:"username"`
    Password string `yaml:"password"`
    Database string `yaml:"database"`
    AuthType string `yaml:"auth_type"`
}

// NewSource 创建新的 Kyuubi 数据源
func NewSource(config Config) (*Source, error) {
    // 设置默认值
    if config.Port == 0 {
        config.Port = 10009
    }
    if config.Database == "" {
        config.Database = "default"
    }
    if config.AuthType == "" {
        config.AuthType = "NONE"
    }
    
    return &Source{
        Host:     config.Host,
        Port:     config.Port,
        Username: config.Username,
        Password: config.Password,
        Database: config.Database,
        AuthType: config.AuthType,
    }, nil
}

// Query 执行 SQL 查询
func (s *Source) Query(ctx context.Context, query string) ([]map[string]interface{}, error) {
    // 构建 Python 命令
    args := []string{
        "scripts/kyuubi_bridge.py",
        "--host", s.Host,
        "--port", fmt.Sprint(s.Port),
        "--database", s.Database,
        "--auth", s.AuthType,
        "--action", "query",
        "--query", query,
    }
    
    if s.Username != "" {
        args = append(args, "--username", s.Username)
    }
    if s.Password != "" {
        args = append(args, "--password", s.Password)
    }
    
    // 执行 Python 脚本
    cmd := exec.CommandContext(ctx, "python3", args...)
    output, err := cmd.Output()
    if err != nil {
        // 尝试获取 stderr
        if exitErr, ok := err.(*exec.ExitError); ok {
            return nil, fmt.Errorf("python bridge error: %s", string(exitErr.Stderr))
        }
        return nil, fmt.Errorf("failed to execute python bridge: %w", err)
    }
    
    // 解析 JSON 结果
    var result []map[string]interface{}
    if err := json.Unmarshal(output, &result); err != nil {
        return nil, fmt.Errorf("failed to parse result: %w", err)
    }
    
    // 检查是否有错误
    if len(result) == 1 {
        if errMsg, ok := result[0]["error"].(string); ok {
            return nil, fmt.Errorf("query error: %s", errMsg)
        }
    }
    
    return result, nil
}

// GetTables 获取表列表
func (s *Source) GetTables(ctx context.Context) ([]string, error) {
    args := []string{
        "scripts/kyuubi_bridge.py",
        "--host", s.Host,
        "--port", fmt.Sprint(s.Port),
        "--database", s.Database,
        "--auth", s.AuthType,
        "--action", "tables",
    }
    
    if s.Username != "" {
        args = append(args, "--username", s.Username)
    }
    if s.Password != "" {
        args = append(args, "--password", s.Password)
    }
    
    cmd := exec.CommandContext(ctx, "python3", args...)
    output, err := cmd.Output()
    if err != nil {
        return nil, fmt.Errorf("failed to get tables: %w", err)
    }
    
    var result []string
    if err := json.Unmarshal(output, &result); err != nil {
        return nil, fmt.Errorf("failed to parse tables: %w", err)
    }
    
    return result, nil
}

// GetSchema 获取表的 schema
func (s *Source) GetSchema(ctx context.Context, table string) ([]map[string]string, error) {
    args := []string{
        "scripts/kyuubi_bridge.py",
        "--host", s.Host,
        "--port", fmt.Sprint(s.Port),
        "--database", s.Database,
        "--auth", s.AuthType,
        "--action", "schema",
        "--table", table,
    }
    
    if s.Username != "" {
        args = append(args, "--username", s.Username)
    }
    if s.Password != "" {
        args = append(args, "--password", s.Password)
    }
    
    cmd := exec.CommandContext(ctx, "python3", args...)
    output, err := cmd.Output()
    if err != nil {
        return nil, fmt.Errorf("failed to get schema: %w", err)
    }
    
    var result []map[string]string
    if err := json.Unmarshal(output, &result); err != nil {
        return nil, fmt.Errorf("failed to parse schema: %w", err)
    }
    
    return result, nil
}

// TestConnection 测试连接
func (s *Source) TestConnection(ctx context.Context) error {
    _, err := s.Query(ctx, "SELECT 1")
    return err
}
```

#### 4.2.3 配置文件示例

**文件**: `tools.yaml`

```yaml
sources:
  my-kyuubi:
    kind: kyuubi
    host: kyuubi-server.example.com
    port: 10009
    username: user1
    password: password123
    database: default
    auth_type: PLAIN  # NONE, PLAIN, CUSTOM, LDAP, KERBEROS
    
  my-kerberized-kyuubi:
    kind: kyuubi
    host: secure-kyuubi.example.com
    port: 10009
    database: production
    auth_type: KERBEROS

tools:
  query-sales-data:
    kind: kyuubi-sql
    source: my-kyuubi
    description: Query sales data from Kyuubi
    parameters:
      - name: start_date
        type: string
        description: Start date (YYYY-MM-DD)
      - name: end_date
        type: string
        description: End date (YYYY-MM-DD)
    statement: |
      SELECT 
        date,
        SUM(amount) as total_sales,
        COUNT(*) as transaction_count
      FROM sales
      WHERE date BETWEEN '{{.start_date}}' AND '{{.end_date}}'
      GROUP BY date
      ORDER BY date
```

#### 4.2.4 依赖管理

**文件**: `requirements.txt`

```txt
# Kyuubi/Hive 客户端依赖
pyhive[hive]>=0.6.5

# 或者使用 JayDeBeApi（如果需要 JDBC 方式）
# JayDeBeApi>=1.2.3
```

**安装脚本**: `scripts/setup_kyuubi.sh`

```bash
#!/bin/bash
# 安装 Kyuubi 依赖

echo "Installing Kyuubi Python dependencies..."

# 安装 Python 依赖
pip3 install -r requirements.txt

# 如果需要 SASL 支持（Kerberos 等）
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get install -y cyrus-sasl-plain cyrus-sasl-devel cyrus-sasl-gssapi cyrus-sasl-md5
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew install cyrus-sasl
fi

echo "Kyuubi dependencies installed successfully!"
```

### 4.3 使用示例

#### 4.3.1 基础查询

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    "genai-toolbox/internal/sources/kyuubi"
)

func main() {
    // 创建 Kyuubi 数据源
    source, err := kyuubi.NewSource(kyuubi.Config{
        Host:     "kyuubi-server",
        Port:     10009,
        Username: "user1",
        Password: "password",
        Database: "default",
        AuthType: "PLAIN",
    })
    if err != nil {
        log.Fatal(err)
    }
    
    // 执行查询
    ctx := context.Background()
    results, err := source.Query(ctx, 
        "SELECT * FROM users WHERE age > 18 LIMIT 10")
    if err != nil {
        log.Fatal(err)
    }
    
    // 打印结果
    for _, row := range results {
        fmt.Println(row)
    }
}
```

#### 4.3.2 集成到 genai-toolbox 工具

```go
// 实现 genai-toolbox 的 Tool 接口
type KyuubiTool struct {
    source    *kyuubi.Source
    statement string
    params    []Parameter
}

func (t *KyuubiTool) Execute(ctx context.Context, args map[string]interface{}) (interface{}, error) {
    // 替换参数
    query := t.renderQuery(args)
    
    // 执行查询
    return t.source.Query(ctx, query)
}

func (t *KyuubiTool) renderQuery(args map[string]interface{}) string {
    // 使用模板渲染查询
    // 例如: SELECT * FROM table WHERE date = '{{.date}}'
    // ...
}
```

### 4.4 优势总结

使用 Python 桥接方案为 genai-toolbox 添加 Kyuubi 支持具有以下优势：

| 优势项 | 说明 |
|-------|------|
| **开发速度** | 1-3 天即可完成基础集成 |
| **功能完整性** | 100% 支持 Kyuubi 所有特性 |
| **维护成本** | 零维护成本（依赖官方 PyHive） |
| **稳定性** | PyHive 经过充分验证，生产就绪 |
| **认证支持** | 完整支持 PLAIN, LDAP, KERBEROS 等 |
| **错误处理** | 继承 PyHive 的完善错误处理 |
| **兼容性** | 完全兼容 Kyuubi 和 HiveServer2 |

### 4.5 性能考虑

**跨进程调用开销**:
- 每次查询需要启动 Python 进程：~50-100ms
- 对于 AI Agent 场景（通常秒级响应），这个开销完全可以接受
- 可以通过连接池优化（保持 Python 进程运行）

**优化方案（可选）**:
- 使用 Python HTTP 服务器模式（避免重复启动进程）
- 实现连接池和会话复用
- 缓存查询结果

## 5. 备选方案：使用 gohive 库的详细实现

### 5.1 gohive 库介绍

[gohive](https://github.com/beltran/gohive) 是一个成熟的 Go 语言 HiveServer2 客户端库，完全兼容 Kyuubi。

**项目信息**:
- GitHub: https://github.com/beltran/gohive
- Star: 100+
- 协议: Apache 2.0
- 维护状态: 活跃维护中

**核心特性**:
- ✅ 支持 HiveServer2 Thrift 协议
- ✅ 支持多种认证方式（NONE, PLAIN, KERBEROS, LDAP）
- ✅ 支持同步和异步查询
- ✅ 支持游标操作
- ✅ 支持 SASL 认证
- ✅ 线程安全
- ✅ 连接池支持

### 5.2 快速开始

#### 5.2.1 安装依赖

```bash
# 安装 gohive 库
go get github.com/beltran/gohive

# 如果需要 Kerberos 认证，还需要安装
go get github.com/jcmturner/gokrb5/v8
```

#### 4.2.2 基础连接示例

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    "github.com/beltran/gohive"
)

func main() {
    // 创建连接配置
    configuration := gohive.NewConnectConfiguration()
    configuration.Username = "user1"
    configuration.Password = "password"
    
    // 连接到 Kyuubi（使用 PLAIN 认证）
    conn, err := gohive.Connect("kyuubi-server", 10009, "NONE", configuration)
    if err != nil {
        log.Fatal("连接失败:", err)
    }
    defer conn.Close()
    
    // 创建游标
    cursor := conn.Cursor()
    
    // 执行查询
    ctx := context.Background()
    cursor.Exec(ctx, "SELECT id, name, age FROM users WHERE age > 18")
    if cursor.Err != nil {
        log.Fatal("查询失败:", cursor.Err)
    }
    
    // 获取结果
    for cursor.HasMore(ctx) {
        var id int64
        var name string
        var age int
        cursor.FetchOne(ctx, &id, &name, &age)
        if cursor.Err != nil {
            log.Fatal("获取结果失败:", cursor.Err)
        }
        fmt.Printf("ID: %d, Name: %s, Age: %d\n", id, name, age)
    }
}
```

#### 4.2.3 使用会话配置

```go
// 创建连接配置，设置 Kyuubi 和 Spark 参数
configuration := gohive.NewConnectConfiguration()
configuration.Username = "user1"
configuration.Password = "password"

// 添加 Kyuubi 和 Spark 配置
configuration.SessionConfig = map[string]string{
    // Kyuubi 引擎配置
    "kyuubi.engine.share.level": "USER",
    "kyuubi.engine.type": "SPARK_SQL",
    
    // Spark 配置
    "spark.executor.memory": "2g",
    "spark.executor.cores": "2",
    "spark.sql.shuffle.partitions": "200",
}

// 连接到 Kyuubi
conn, err := gohive.Connect("kyuubi-server", 10009, "NONE", configuration)
```

#### 4.2.4 Kerberos 认证

```go
import (
    "github.com/beltran/gohive"
    "github.com/beltran/gohive/gosasl"
)

func main() {
    // Kerberos 配置
    configuration := gohive.NewConnectConfiguration()
    configuration.Service = "kyuubi"  // Kerberos 服务名称
    configuration.KerberosServiceName = "kyuubi"
    configuration.KerberosRealm = "EXAMPLE.COM"
    
    // 使用 keytab 文件
    configuration.KerberosConfig = "/etc/krb5.conf"
    configuration.KerberosKeytab = "/path/to/user.keytab"
    configuration.Username = "user@EXAMPLE.COM"
    
    // 连接到 Kyuubi（使用 KERBEROS 认证）
    conn, err := gohive.Connect("kyuubi-server", 10009, "KERBEROS", configuration)
    if err != nil {
        log.Fatal("连接失败:", err)
    }
    defer conn.Close()
    
    // ... 执行查询
}
```

### 4.3 高级用法

#### 4.3.1 异步查询

```go
// 提交异步查询
cursor := conn.Cursor()
cursor.Exec(context.Background(), "SELECT COUNT(*) FROM large_table")

// 检查查询状态
for {
    status := cursor.Poll(context.Background())
    fmt.Printf("查询状态: %s\n", status.State)
    
    if status.State == "FINISHED" {
        break
    } else if status.State == "ERROR" {
        log.Fatal("查询失败")
    }
    
    time.Sleep(2 * time.Second)
}

// 获取结果
var count int64
cursor.FetchOne(context.Background(), &count)
fmt.Printf("总行数: %d\n", count)
```

#### 4.3.2 批量获取结果

```go
// 执行查询
cursor.Exec(context.Background(), "SELECT * FROM large_table")

// 批量获取结果（每次 1000 行）
for cursor.HasMore(context.Background()) {
    // 准备批量数据容器
    rows := make([][]interface{}, 0, 1000)
    
    // 批量获取
    for i := 0; i < 1000 && cursor.HasMore(context.Background()); i++ {
        var row []interface{}
        cursor.FetchOne(context.Background(), &row)
        rows = append(rows, row)
    }
    
    // 处理批量数据
    processBatch(rows)
}
```

#### 4.3.3 参数化查询（防止 SQL 注入）

```go
// 注意: gohive 不直接支持参数化查询
// 需要手动转义参数或使用 prepared statement

// 方法1: 手动转义
func escapeString(s string) string {
    return strings.ReplaceAll(s, "'", "''")
}

userName := escapeString(userInput)
sql := fmt.Sprintf("SELECT * FROM users WHERE name = '%s'", userName)
cursor.Exec(context.Background(), sql)

// 方法2: 使用占位符（如果 Spark SQL 支持）
// 这需要查看 Spark SQL 是否支持 prepared statement
```

### 4.4 封装增强库

为了提供更好的用户体验，可以基于 gohive 封装一个更友好的 Kyuubi 客户端库：

```go
// kyuubi/client.go
package kyuubi

import (
    "context"
    "fmt"
    "time"
    
    "github.com/beltran/gohive"
)

// Client Kyuubi 客户端封装
type Client struct {
    conn   *gohive.Connection
    config *Config
}

// Config 客户端配置
type Config struct {
    Host     string            // Kyuubi 服务器地址
    Port     int               // Kyuubi 服务器端口（默认 10009）
    Username string            // 用户名
    Password string            // 密码
    AuthType string            // 认证类型: NONE, PLAIN, KERBEROS, LDAP
    Database string            // 默认数据库
    
    // Kerberos 配置
    KerberosService   string  // Kerberos 服务名
    KerberosRealm     string  // Kerberos 域
    KerberosKeytab    string  // Keytab 文件路径
    KerberosConfig    string  // krb5.conf 路径
    
    // 会话配置
    SessionConfig map[string]string
    
    // 超时配置
    ConnectTimeout time.Duration
    QueryTimeout   time.Duration
}

// NewClient 创建 Kyuubi 客户端
func NewClient(config *Config) (*Client, error) {
    // 设置默认值
    if config.Port == 0 {
        config.Port = 10009
    }
    if config.AuthType == "" {
        config.AuthType = "NONE"
    }
    
    // 创建 gohive 配置
    hiveConfig := gohive.NewConnectConfiguration()
    hiveConfig.Username = config.Username
    hiveConfig.Password = config.Password
    hiveConfig.Database = config.Database
    hiveConfig.SessionConfig = config.SessionConfig
    
    // 配置 Kerberos
    if config.AuthType == "KERBEROS" {
        hiveConfig.Service = config.KerberosService
        hiveConfig.KerberosServiceName = config.KerberosService
        hiveConfig.KerberosRealm = config.KerberosRealm
        hiveConfig.KerberosKeytab = config.KerberosKeytab
        hiveConfig.KerberosConfig = config.KerberosConfig
    }
    
    // 连接到 Kyuubi
    conn, err := gohive.Connect(
        config.Host,
        config.Port,
        config.AuthType,
        hiveConfig,
    )
    if err != nil {
        return nil, fmt.Errorf("连接 Kyuubi 失败: %w", err)
    }
    
    return &Client{
        conn:   conn,
        config: config,
    }, nil
}

// Query 执行查询并返回结果集
func (c *Client) Query(ctx context.Context, sql string) (*ResultSet, error) {
    cursor := c.conn.Cursor()
    cursor.Exec(ctx, sql)
    if cursor.Err != nil {
        return nil, fmt.Errorf("执行查询失败: %w", cursor.Err)
    }
    
    return &ResultSet{
        cursor: cursor,
        ctx:    ctx,
    }, nil
}

// Exec 执行 DML 语句（INSERT, UPDATE, DELETE）
func (c *Client) Exec(ctx context.Context, sql string) error {
    cursor := c.conn.Cursor()
    cursor.Exec(ctx, sql)
    return cursor.Err
}

// Close 关闭连接
func (c *Client) Close() error {
    return c.conn.Close()
}

// ResultSet 查询结果集
type ResultSet struct {
    cursor *gohive.Cursor
    ctx    context.Context
}

// Next 移动到下一行
func (rs *ResultSet) Next() bool {
    return rs.cursor.HasMore(rs.ctx)
}

// Scan 扫描当前行到变量
func (rs *ResultSet) Scan(dest ...interface{}) error {
    rs.cursor.FetchOne(rs.ctx, dest...)
    return rs.cursor.Err
}

// Close 关闭结果集
func (rs *ResultSet) Close() error {
    // gohive 的 cursor 不需要显式关闭
    return nil
}
```

**使用封装后的客户端**:

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    "your-module/kyuubi"
)

func main() {
    // 创建客户端
    client, err := kyuubi.NewClient(&kyuubi.Config{
        Host:     "kyuubi-server",
        Port:     10009,
        Username: "user1",
        Password: "password",
        AuthType: "PLAIN",
        Database: "default",
        SessionConfig: map[string]string{
            "kyuubi.engine.share.level": "USER",
            "spark.executor.memory": "2g",
        },
    })
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()
    
    // 执行查询
    rs, err := client.Query(context.Background(), 
        "SELECT id, name, age FROM users WHERE age > 18")
    if err != nil {
        log.Fatal(err)
    }
    defer rs.Close()
    
    // 遍历结果
    for rs.Next() {
        var id int64
        var name string
        var age int
        if err := rs.Scan(&id, &name, &age); err != nil {
            log.Fatal(err)
        }
        fmt.Printf("ID: %d, Name: %s, Age: %d\n", id, name, age)
    }
}
```

### 4.5 实现 database/sql 驱动

为了更好地集成 Go 生态，可以基于 gohive 实现 `database/sql` 驱动：

```go
// kyuubi/driver.go
package kyuubi

import (
    "database/sql"
    "database/sql/driver"
    "github.com/beltran/gohive"
)

func init() {
    sql.Register("kyuubi", &Driver{})
}

type Driver struct{}

func (d *Driver) Open(dsn string) (driver.Conn, error) {
    config, err := parseDSN(dsn)
    if err != nil {
        return nil, err
    }
    
    // 使用 gohive 创建连接
    hiveConfig := gohive.NewConnectConfiguration()
    hiveConfig.Username = config.Username
    hiveConfig.Password = config.Password
    hiveConfig.SessionConfig = config.SessionConfig
    
    conn, err := gohive.Connect(config.Host, config.Port, config.AuthType, hiveConfig)
    if err != nil {
        return nil, err
    }
    
    return &Conn{conn: conn}, nil
}

// DSN 格式: kyuubi://user:pass@host:port/db?param=value
func parseDSN(dsn string) (*Config, error) {
    // ... 解析 DSN 字符串
}
```

## 5. 方案对比：gohive vs 从头实现

| 对比项 | gohive 库 | 从头实现 Thrift 客户端 |
|-------|----------|---------------------|
| 开发时间 | **1-2 周** | 3-6 个月 |
| 维护成本 | **低** | 高 |
| 功能完整性 | **完整** | 需逐步实现 |
| 性能 | **优秀** | 可优化但需时间 |
| 社区支持 | **有** | 需自行维护 |
| 代码量 | **几百行** | 数千行 |
| 测试覆盖 | **已验证** | 需全面测试 |
| Kerberos 支持 | **内置** | 需自行实现（复杂） |
| 学习曲线 | **平缓** | 陡峭 |
| 风险 | **低** | 中高 |

## 6. 基于 gohive 的完整项目示例

项目结构：

```
kyuubi-go-client/
├── cmd/
│   └── example/              # 示例程序
│       ├── basic.go          # 基础查询示例
│       ├── kerberos.go       # Kerberos 认证示例
│       └── async.go          # 异步查询示例
├── pkg/
│   └── kyuubi/               # Kyuubi 客户端封装
│       ├── client.go         # 客户端主类
│       ├── config.go         # 配置管理
│       ├── driver.go         # database/sql 驱动
│       ├── resultset.go      # 结果集处理
│       └── errors.go         # 错误处理
├── examples/                 # 完整示例
│   ├── basic_query/
│   ├── batch_insert/
│   └── connection_pool/
├── go.mod
├── go.sum
├── README.md
├── README_CN.md
└── LICENSE
```

## 7. 从头实现 Thrift 客户端的详细方案（仅作参考）

如果出于特殊需求（如深度定制、极致性能优化等）必须从头实现，可参考以下方案。**但对于大部分场景，强烈推荐使用方案一（gohive 库）。**

### 7.1 项目结构

```
kyuubi-go-client/
├── cmd/
│   └── example/              # 示例程序
│       └── main.go
├── pkg/
│   ├── thrift/               # Thrift 生成的代码
│   │   └── TCLIService/      # 从 Hive Thrift IDL 生成
│   │       ├── t_c_l_i_service.go
│   │       └── ttypes.go
│   ├── client/               # 客户端核心实现
│   │   ├── connection.go     # 连接管理
│   │   ├── session.go        # 会话管理
│   │   ├── statement.go      # 语句执行
│   │   ├── resultset.go      # 结果集处理
│   │   └── config.go         # 配置管理
│   ├── auth/                 # 认证实现
│   │   ├── plain.go          # PLAIN SASL 认证
│   │   ├── kerberos.go       # Kerberos 认证
│   │   └── sasl.go           # SASL 框架
│   └── types/                # 类型转换
│       └── converter.go      # Thrift 类型到 Go 类型转换
├── internal/
│   └── utils/                # 内部工具
├── examples/                 # 使用示例
│   ├── basic_query.go
│   ├── async_query.go
│   └── kerberos_auth.go
├── go.mod
├── go.sum
├── README.md
├── README_CN.md
└── LICENSE
```

### 7.2 核心组件设计

#### 7.2.1 连接管理 (Connection)

```go
// Connection 表示到 Kyuubi 服务器的连接
type Connection struct {
    host            string              // Kyuubi 服务器地址
    port            int                 // Kyuubi 服务器端口
    username        string              // 用户名
    password        string              // 密码
    config          *Config             // 配置参数
    transport       thrift.TTransport   // Thrift 传输层
    protocol        thrift.TProtocol    // Thrift 协议层
    client          *TCLIService.Client // Thrift 客户端
    session         *Session            // 当前会话
    isClosed        bool                // 连接状态
    mutex           sync.Mutex          // 并发控制
}

// 连接配置
type Config struct {
    // 基础配置
    ProtocolVersion  int32              // 协议版本（默认 10）
    ConnectTimeout   time.Duration      // 连接超时
    SocketTimeout    time.Duration      // 读写超时
    MaxMessageSize   int32              // 最大消息大小
    
    // 传输配置
    TransportMode    string             // binary/http
    HTTPPath         string             // HTTP 模式下的路径
    
    // 认证配置
    AuthType         string             // NONE/PLAIN/KERBEROS/LDAP
    Principal        string             // Kerberos 主体
    Keytab           string             // Keytab 文件路径
    
    // 会话配置
    SessionConf      map[string]string  // 会话级别配置（如 Spark 配置）
    
    // 高可用配置
    ServiceDiscovery bool               // 是否启用服务发现
    ZKQuorum         string             // ZooKeeper 地址
    ZKNamespace      string             // ZooKeeper 命名空间
    
    // 连接池配置
    MaxIdleConns     int                // 最大空闲连接数
    MaxOpenConns     int                // 最大打开连接数
    ConnMaxLifetime  time.Duration      // 连接最大生命周期
}

// 核心方法
func NewConnection(host string, port int, config *Config) (*Connection, error)
func (c *Connection) Connect() error
func (c *Connection) Close() error
func (c *Connection) IsConnected() bool
func (c *Connection) NewSession() (*Session, error)
```

#### 4.2.2 会话管理 (Session)

```go
// Session 表示一个 Kyuubi 会话
type Session struct {
    handle       *TCLIService.TSessionHandle  // 会话句柄
    connection   *Connection                   // 所属连接
    config       map[string]string             // 会话配置
    isClosed     bool                          // 会话状态
    mutex        sync.Mutex                    // 并发控制
}

// 核心方法
func (s *Session) ExecuteStatement(sql string, async bool) (*Statement, error)
func (s *Session) ExecuteStatementWithTimeout(sql string, timeout time.Duration) (*Statement, error)
func (s *Session) GetInfo(infoType TCLIService.TGetInfoType) (string, error)
func (s *Session) GetCatalogs() (*ResultSet, error)
func (s *Session) GetSchemas(catalogName, schemaPattern string) (*ResultSet, error)
func (s *Session) GetTables(catalogName, schemaPattern, tablePattern string, tableTypes []string) (*ResultSet, error)
func (s *Session) GetColumns(catalogName, schemaPattern, tablePattern, columnPattern string) (*ResultSet, error)
func (s *Session) Close() error
```

#### 4.2.3 语句执行 (Statement)

```go
// Statement 表示一个 SQL 语句的执行
type Statement struct {
    handle        *TCLIService.TOperationHandle  // 操作句柄
    session       *Session                        // 所属会话
    sql           string                          // SQL 语句
    isAsync       bool                            // 是否异步执行
    state         OperationState                  // 操作状态
    resultSet     *ResultSet                      // 结果集
    mutex         sync.Mutex                      // 并发控制
}

// 操作状态枚举
type OperationState int32
const (
    INITIALIZED OperationState = 0
    RUNNING     OperationState = 1
    FINISHED    OperationState = 2
    CANCELED    OperationState = 3
    CLOSED      OperationState = 4
    ERROR       OperationState = 5
    UNKNOWN     OperationState = 6
    PENDING     OperationState = 7
)

// 核心方法
func (s *Statement) GetStatus() (OperationState, error)
func (s *Statement) WaitForCompletion(pollInterval time.Duration) error
func (s *Statement) Cancel() error
func (s *Statement) GetResultSet() (*ResultSet, error)
func (s *Statement) GetLog() ([]string, error)
func (s *Statement) Close() error
```

#### 4.2.4 结果集处理 (ResultSet)

```go
// ResultSet 表示查询结果集
type ResultSet struct {
    statement     *Statement                      // 所属语句
    metadata      *TCLIService.TTableSchema      // 结果集元数据
    columns       []Column                        // 列信息
    rows          []Row                           // 当前缓冲的行数据
    currentRow    int                             // 当前行索引
    hasMore       bool                            // 是否还有更多数据
    fetchSize     int                             // 每次获取的行数
    mutex         sync.Mutex                      // 并发控制
}

// 列信息
type Column struct {
    Name      string       // 列名
    Type      DataType     // 数据类型
    Position  int          // 列位置
    Precision int32        // 精度
    Scale     int32        // 小数位数
    Comment   string       // 列注释
}

// 行数据
type Row struct {
    Values []interface{}  // 列值
}

// 数据类型映射
type DataType int32
const (
    BOOLEAN   DataType = 0
    TINYINT   DataType = 1
    SMALLINT  DataType = 2
    INT       DataType = 3
    BIGINT    DataType = 4
    FLOAT     DataType = 5
    DOUBLE    DataType = 6
    STRING    DataType = 7
    TIMESTAMP DataType = 8
    BINARY    DataType = 9
    ARRAY     DataType = 10
    MAP       DataType = 11
    STRUCT    DataType = 12
    DECIMAL   DataType = 13
    // ... 更多类型
)

// 核心方法
func (rs *ResultSet) Next() bool
func (rs *ResultSet) Scan(dest ...interface{}) error
func (rs *ResultSet) GetColumns() []Column
func (rs *ResultSet) GetValue(columnIndex int) (interface{}, error)
func (rs *ResultSet) GetString(columnIndex int) (string, error)
func (rs *ResultSet) GetInt(columnIndex int) (int64, error)
func (rs *ResultSet) GetFloat(columnIndex int) (float64, error)
func (rs *ResultSet) GetBool(columnIndex int) (bool, error)
func (rs *ResultSet) Close() error
```

#### 4.2.5 认证实现 (Authentication)

```go
// PLAIN SASL 认证（用户名/密码）
type PlainSASLTransport struct {
    transport  thrift.TTransport
    username   string
    password   string
}

func NewPlainSASLTransport(trans thrift.TTransport, username, password string) *PlainSASLTransport
func (p *PlainSASLTransport) Open() error

// Kerberos 认证
type KerberosSASLTransport struct {
    transport    thrift.TTransport
    principal    string      // 服务主体
    keytab       string      // Keytab 文件路径
    krb5Config   string      // krb5.conf 配置文件
}

func NewKerberosSASLTransport(trans thrift.TTransport, config *KerberosConfig) *KerberosSASLTransport
func (k *KerberosSASLTransport) Open() error
```

### 7.3 核心流程实现

#### 7.3.1 连接建立流程

```go
// 1. 创建连接
conn, err := NewConnection("kyuubi-server", 10009, &Config{
    Username:        "user1",
    Password:        "password",
    ProtocolVersion: 10,
    AuthType:        "PLAIN",
    ConnectTimeout:  30 * time.Second,
    SessionConf: map[string]string{
        "kyuubi.engine.share.level": "USER",
        "spark.sql.shuffle.partitions": "200",
    },
})

// 2. 建立连接
if err := conn.Connect(); err != nil {
    log.Fatal(err)
}
defer conn.Close()

// 内部实现步骤:
// a. 创建 TSocket
// b. 创建 TBinaryProtocol
// c. 根据认证类型包装 SASL Transport
// d. 打开 Transport
// e. 创建 TCLIService.Client
// f. 调用 OpenSession RPC
// g. 保存 SessionHandle
```

#### 4.3.2 SQL 执行流程（同步）

```go
// 1. 创建会话
session, err := conn.NewSession()
if err != nil {
    log.Fatal(err)
}
defer session.Close()

// 2. 执行 SQL（同步模式）
stmt, err := session.ExecuteStatement("SELECT * FROM table WHERE id > 100", false)
if err != nil {
    log.Fatal(err)
}
defer stmt.Close()

// 3. 获取结果集
rs, err := stmt.GetResultSet()
if err != nil {
    log.Fatal(err)
}
defer rs.Close()

// 4. 遍历结果
for rs.Next() {
    var id int64
    var name string
    if err := rs.Scan(&id, &name); err != nil {
        log.Fatal(err)
    }
    fmt.Printf("ID: %d, Name: %s\n", id, name)
}

// 内部实现步骤:
// a. 调用 ExecuteStatement RPC（runAsync=false）
// b. 等待操作完成（同步模式会阻塞）
// c. 调用 GetResultSetMetadata RPC 获取列信息
// d. 调用 FetchResults RPC 获取数据
// e. 将 Thrift 类型转换为 Go 类型
```

#### 4.3.3 SQL 执行流程（异步）

```go
// 1. 执行 SQL（异步模式）
stmt, err := session.ExecuteStatement("SELECT COUNT(*) FROM large_table", true)
if err != nil {
    log.Fatal(err)
}
defer stmt.Close()

// 2. 轮询状态直到完成
for {
    state, err := stmt.GetStatus()
    if err != nil {
        log.Fatal(err)
    }
    
    if state == FINISHED {
        break
    } else if state == ERROR || state == CANCELED {
        log.Fatal("Statement failed")
    }
    
    // 获取执行日志
    logs, _ := stmt.GetLog()
    for _, line := range logs {
        fmt.Println(line)
    }
    
    time.Sleep(1 * time.Second)
}

// 3. 获取结果
rs, err := stmt.GetResultSet()
// ... 处理结果

// 内部实现步骤:
// a. 调用 ExecuteStatement RPC（runAsync=true）
// b. 立即返回 OperationHandle
// c. 定期调用 GetOperationStatus RPC 查询状态
// d. 可选调用 GetLog RPC 获取执行日志
// e. 状态为 FINISHED 后调用 FetchResults RPC
```

### 7.4 依赖库选择

#### 7.4.1 核心依赖

| 依赖库 | 版本 | 用途 | 许可证 |
|-------|------|------|-------|
| `github.com/apache/thrift` | v0.19.0+ | Thrift 协议支持 | Apache 2.0 |
| `github.com/jcmturner/gokrb5/v8` | v8.4.4+ | Kerberos 认证 | Apache 2.0 |

#### 4.4.2 可选依赖

| 依赖库 | 版本 | 用途 | 许可证 |
|-------|------|------|-------|
| `github.com/go-zookeeper/zk` | v1.0.3+ | 服务发现（ZooKeeper） | BSD 3-Clause |
| `go.uber.org/zap` | v1.26.0+ | 结构化日志 | MIT |
| `github.com/stretchr/testify` | v1.8.4+ | 单元测试 | MIT |

### 7.5 Thrift 代码生成

#### 7.5.1 获取 Thrift IDL 文件

Hive 的 TCLIService Thrift 定义文件位于：
```
https://github.com/apache/hive/blob/master/service-rpc/if/TCLIService.thrift
```

还需要依赖的其他 .thrift 文件：
- `hive_service.thrift`
- `fb303.thrift`

#### 4.5.2 生成 Go 代码

```bash
# 安装 Thrift 编译器
# macOS
brew install thrift

# Linux
apt-get install thrift-compiler

# 生成 Go 代码
thrift --gen go:package_prefix=github.com/your-org/kyuubi-go-client/pkg/thrift/ \
       TCLIService.thrift

# 生成的代码会放在 gen-go 目录下
# 需要将其移动到项目的 pkg/thrift 目录
```

#### 4.5.3 应用 Kyuubi 特定补丁

参考 Python 客户端的补丁文件 `python/scripts/thrift-patches/TCLIService.patch`，
可能需要为 Kyuubi 特定功能添加一些补丁。

## 5. database/sql 驱动实现（可选）

为了更好地集成 Go 生态，可以实现符合 `database/sql` 标准接口的驱动。

### 5.1 驱动注册

```go
package kyuubi

import (
    "database/sql"
    "database/sql/driver"
)

func init() {
    sql.Register("kyuubi", &KyuubiDriver{})
}

// KyuubiDriver 实现 driver.Driver 接口
type KyuubiDriver struct{}

func (d *KyuubiDriver) Open(dsn string) (driver.Conn, error) {
    // 解析 DSN
    config, err := ParseDSN(dsn)
    if err != nil {
        return nil, err
    }
    
    // 创建连接
    conn, err := NewConnection(config.Host, config.Port, config)
    if err != nil {
        return nil, err
    }
    
    // 建立连接
    if err := conn.Connect(); err != nil {
        return nil, err
    }
    
    return &KyuubiConn{conn: conn}, nil
}
```

### 5.2 DSN 格式

```
kyuubi://[username[:password]@]host:port[/catalog][?param1=value1&param2=value2]

示例：
kyuubi://user1:pass123@kyuubi-server:10009/default?auth=PLAIN&timeout=30s
kyuubi://kyuubi-server:10009/spark_catalog.db1?auth=KERBEROS&principal=user@REALM
```

### 5.3 使用示例

```go
import (
    "database/sql"
    _ "github.com/your-org/kyuubi-go-client"
)

func main() {
    // 打开连接
    db, err := sql.Open("kyuubi", 
        "kyuubi://user1:pass@localhost:10009/default?auth=PLAIN")
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()
    
    // 执行查询
    rows, err := db.Query("SELECT id, name FROM users WHERE age > ?", 18)
    if err != nil {
        log.Fatal(err)
    }
    defer rows.Close()
    
    // 遍历结果
    for rows.Next() {
        var id int
        var name string
        if err := rows.Scan(&id, &name); err != nil {
            log.Fatal(err)
        }
        fmt.Printf("ID: %d, Name: %s\n", id, name)
    }
}
```

## 6. 高级特性实现

### 6.1 连接池

```go
// 连接池管理
type ConnectionPool struct {
    config        *Config
    idleConns     chan *Connection
    activeConns   map[*Connection]bool
    maxIdle       int
    maxOpen       int
    connLifetime  time.Duration
    mutex         sync.Mutex
}

func NewConnectionPool(config *Config) *ConnectionPool
func (p *ConnectionPool) Get() (*Connection, error)
func (p *ConnectionPool) Put(conn *Connection)
func (p *ConnectionPool) Close() error
```

### 6.2 高可用支持（ZooKeeper 服务发现）

```go
// ZooKeeper 服务发现
type ZKServiceDiscovery struct {
    zkQuorum    string
    zkNamespace string
    conn        *zk.Conn
}

func (zk *ZKServiceDiscovery) DiscoverServers() ([]string, error) {
    // 从 ZooKeeper 获取可用的 Kyuubi 服务器列表
    // 路径格式: /<namespace>/serverUri=<host>:<port>;version=<version>;sequence=<seq>
}

func (zk *ZKServiceDiscovery) SelectServer(servers []string) string {
    // 负载均衡策略：随机选择
}
```

### 6.3 重试机制

```go
// 重试配置
type RetryConfig struct {
    MaxRetries      int
    InitialInterval time.Duration
    MaxInterval     time.Duration
    Multiplier      float64
}

// 带重试的执行
func (s *Statement) ExecuteWithRetry(retryConfig *RetryConfig) error {
    var lastErr error
    interval := retryConfig.InitialInterval
    
    for i := 0; i <= retryConfig.MaxRetries; i++ {
        err := s.execute()
        if err == nil {
            return nil
        }
        
        // 判断是否可重试的错误
        if !isRetryableError(err) {
            return err
        }
        
        lastErr = err
        time.Sleep(interval)
        interval = time.Duration(float64(interval) * retryConfig.Multiplier)
        if interval > retryConfig.MaxInterval {
            interval = retryConfig.MaxInterval
        }
    }
    
    return lastErr
}
```

### 6.4 查询超时

```go
// 带超时的查询执行
func (s *Session) ExecuteStatementWithTimeout(sql string, timeout time.Duration) (*Statement, error) {
    stmt, err := s.ExecuteStatement(sql, true)
    if err != nil {
        return nil, err
    }
    
    // 创建超时上下文
    ctx, cancel := context.WithTimeout(context.Background(), timeout)
    defer cancel()
    
    // 等待完成或超时
    done := make(chan error, 1)
    go func() {
        done <- stmt.WaitForCompletion(1 * time.Second)
    }()
    
    select {
    case err := <-done:
        return stmt, err
    case <-ctx.Done():
        stmt.Cancel()
        return nil, fmt.Errorf("query timeout after %v", timeout)
    }
}
```

### 6.5 批量操作

```go
// 批量插入（通过 INSERT INTO ... VALUES 语句）
func (s *Session) BatchInsert(table string, columns []string, rows [][]interface{}) error {
    // 构建批量 INSERT 语句
    // INSERT INTO table (col1, col2) VALUES (?, ?), (?, ?), ...
}

// 批量查询（PreparedStatement 模式）
func (s *Session) PrepareBatch(sql string, batchSize int) (*PreparedBatch, error) {
    // 创建预编译批量执行器
}
```

### 6.6 结果集游标

```go
// 服务器端游标支持
type Cursor struct {
    resultSet   *ResultSet
    fetchSize   int
    orientation FetchOrientation
}

type FetchOrientation int32
const (
    FETCH_NEXT     FetchOrientation = 0
    FETCH_PRIOR    FetchOrientation = 1
    FETCH_FIRST    FetchOrientation = 3
    FETCH_LAST     FetchOrientation = 4
)

func (c *Cursor) SetFetchSize(size int)
func (c *Cursor) FetchNext() error
func (c *Cursor) FetchPrior() error
```

## 7. 错误处理

### 7.1 错误类型定义

```go
// Kyuubi 错误类型
type KyuubiError struct {
    Code       ErrorCode
    Message    string
    SQLState   string
    Cause      error
}

type ErrorCode int32
const (
    // 连接错误
    ErrConnectionFailed    ErrorCode = 1001
    ErrAuthenticationFailed ErrorCode = 1002
    ErrSessionClosed       ErrorCode = 1003
    
    // 执行错误
    ErrSQLSyntaxError      ErrorCode = 2001
    ErrOperationCanceled   ErrorCode = 2002
    ErrOperationTimeout    ErrorCode = 2003
    
    // 系统错误
    ErrInternalError       ErrorCode = 9001
    ErrUnsupportedOperation ErrorCode = 9002
)

func (e *KyuubiError) Error() string
func (e *KyuubiError) Is(target error) bool
func (e *KyuubiError) Unwrap() error
```

### 7.2 错误处理示例

```go
stmt, err := session.ExecuteStatement(sql, false)
if err != nil {
    var kyuubiErr *KyuubiError
    if errors.As(err, &kyuubiErr) {
        switch kyuubiErr.Code {
        case ErrSQLSyntaxError:
            log.Printf("SQL syntax error: %s", kyuubiErr.Message)
        case ErrOperationTimeout:
            log.Printf("Query timeout")
        default:
            log.Printf("Kyuubi error: %v", kyuubiErr)
        }
    }
    return err
}
```

## 8. 日志和监控

### 8.1 日志接口

```go
// 可插拔的日志接口
type Logger interface {
    Debug(msg string, fields ...Field)
    Info(msg string, fields ...Field)
    Warn(msg string, fields ...Field)
    Error(msg string, fields ...Field)
}

// 默认使用标准库 log
type StdLogger struct{}

// 可以使用 zap、logrus 等第三方日志库
func SetLogger(logger Logger)
```

### 8.2 指标收集

```go
// 客户端指标
type Metrics struct {
    // 连接指标
    ActiveConnections   int64
    TotalConnections    int64
    FailedConnections   int64
    
    // 查询指标
    TotalQueries        int64
    SuccessfulQueries   int64
    FailedQueries       int64
    QueryDuration       time.Duration
    
    // 网络指标
    BytesSent           int64
    BytesReceived       int64
}

func GetMetrics() *Metrics
```

### 8.3 调试模式

```go
// 启用调试模式，记录所有 Thrift RPC 调用
config := &Config{
    Debug: true,
    LogLevel: "DEBUG",
}

// 输出示例：
// [DEBUG] Calling OpenSession: user=test, config={spark.executor.memory=2g}
// [DEBUG] OpenSession response: sessionHandle=xxx, status=SUCCESS
// [DEBUG] Calling ExecuteStatement: sql=SELECT * FROM table
```

## 9. 测试策略

### 9.1 单元测试

```go
// 使用 Mock 测试各个组件
func TestSession_ExecuteStatement(t *testing.T) {
    mockClient := &MockTCLIServiceClient{}
    session := &Session{
        client: mockClient,
    }
    
    mockClient.On("ExecuteStatement", mock.Anything).Return(&TExecuteStatementResp{
        Status: &TStatus{StatusCode: SUCCESS_STATUS},
        OperationHandle: &TOperationHandle{...},
    }, nil)
    
    stmt, err := session.ExecuteStatement("SELECT 1", false)
    assert.NoError(t, err)
    assert.NotNil(t, stmt)
}
```

### 9.2 集成测试

```go
// 需要真实的 Kyuubi 服务器
func TestIntegration_BasicQuery(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test")
    }
    
    conn, err := NewConnection("localhost", 10009, &Config{
        Username: "test",
        Password: "test",
    })
    require.NoError(t, err)
    
    err = conn.Connect()
    require.NoError(t, err)
    defer conn.Close()
    
    session, err := conn.NewSession()
    require.NoError(t, err)
    defer session.Close()
    
    stmt, err := session.ExecuteStatement("SELECT 1 as num", false)
    require.NoError(t, err)
    defer stmt.Close()
    
    rs, err := stmt.GetResultSet()
    require.NoError(t, err)
    
    assert.True(t, rs.Next())
    var num int
    err = rs.Scan(&num)
    assert.NoError(t, err)
    assert.Equal(t, 1, num)
}
```

### 9.3 性能测试

```go
// Benchmark 测试
func BenchmarkQuery_Small(b *testing.B) {
    conn := setupConnection(b)
    defer conn.Close()
    
    session, _ := conn.NewSession()
    defer session.Close()
    
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        stmt, _ := session.ExecuteStatement("SELECT 1", false)
        rs, _ := stmt.GetResultSet()
        rs.Next()
        rs.Close()
        stmt.Close()
    }
}
```

## 10. 文档和示例

### 10.1 快速开始示例

```go
package main

import (
    "fmt"
    "log"
    
    kyuubi "github.com/your-org/kyuubi-go-client/pkg/client"
)

func main() {
    // 创建连接配置
    config := &kyuubi.Config{
        Username:        "user1",
        Password:        "password",
        ProtocolVersion: 10,
        AuthType:        "PLAIN",
        SessionConf: map[string]string{
            "kyuubi.engine.share.level": "USER",
        },
    }
    
    // 连接到 Kyuubi
    conn, err := kyuubi.NewConnection("localhost", 10009, config)
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()
    
    if err := conn.Connect(); err != nil {
        log.Fatal(err)
    }
    
    // 创建会话
    session, err := conn.NewSession()
    if err != nil {
        log.Fatal(err)
    }
    defer session.Close()
    
    // 执行查询
    stmt, err := session.ExecuteStatement(
        "SELECT name, age FROM users WHERE age > 18", 
        false,
    )
    if err != nil {
        log.Fatal(err)
    }
    defer stmt.Close()
    
    // 获取结果
    rs, err := stmt.GetResultSet()
    if err != nil {
        log.Fatal(err)
    }
    defer rs.Close()
    
    // 遍历结果
    for rs.Next() {
        var name string
        var age int
        if err := rs.Scan(&name, &age); err != nil {
            log.Fatal(err)
        }
        fmt.Printf("Name: %s, Age: %d\n", name, age)
    }
}
```

### 10.2 Kerberos 认证示例

```go
config := &kyuubi.Config{
    Username:        "user@EXAMPLE.COM",
    AuthType:        "KERBEROS",
    Principal:       "kyuubi/host@EXAMPLE.COM",
    Keytab:          "/path/to/user.keytab",
    SessionConf: map[string]string{
        "kyuubi.engine.share.level": "USER",
    },
}

conn, err := kyuubi.NewConnection("kyuubi-server", 10009, config)
// ... 其余代码相同
```

### 10.3 异步查询示例

```go
// 提交异步查询
stmt, err := session.ExecuteStatement(
    "SELECT COUNT(*) FROM large_table",
    true, // 异步模式
)
if err != nil {
    log.Fatal(err)
}
defer stmt.Close()

// 监控执行状态
ticker := time.NewTicker(2 * time.Second)
defer ticker.Stop()

for {
    select {
    case <-ticker.C:
        state, err := stmt.GetStatus()
        if err != nil {
            log.Fatal(err)
        }
        
        fmt.Printf("Query state: %s\n", state)
        
        // 获取执行日志
        logs, _ := stmt.GetLog()
        for _, line := range logs {
            fmt.Println(line)
        }
        
        if state == kyuubi.FINISHED {
            goto RESULTS
        } else if state == kyuubi.ERROR {
            log.Fatal("Query failed")
        }
    }
}

RESULTS:
// 获取结果
rs, err := stmt.GetResultSet()
// ... 处理结果
```

### 10.4 database/sql 驱动示例

```go
import (
    "database/sql"
    _ "github.com/your-org/kyuubi-go-client"
)

func main() {
    // 打开连接
    db, err := sql.Open("kyuubi", 
        "kyuubi://user:pass@localhost:10009/default?auth=PLAIN")
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()
    
    // 设置连接池
    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)
    db.SetConnMaxLifetime(time.Hour)
    
    // 查询单行
    var count int
    err = db.QueryRow("SELECT COUNT(*) FROM users").Scan(&count)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Total users: %d\n", count)
    
    // 查询多行
    rows, err := db.Query("SELECT id, name FROM users LIMIT 10")
    if err != nil {
        log.Fatal(err)
    }
    defer rows.Close()
    
    for rows.Next() {
        var id int
        var name string
        if err := rows.Scan(&id, &name); err != nil {
            log.Fatal(err)
        }
        fmt.Printf("User %d: %s\n", id, name)
    }
    
    // 执行 DML
    result, err := db.Exec("INSERT INTO users (name, age) VALUES (?, ?)", 
        "Alice", 25)
    if err != nil {
        log.Fatal(err)
    }
    rowsAffected, _ := result.RowsAffected()
    fmt.Printf("Inserted %d row(s)\n", rowsAffected)
}
```

## 11. 部署和发布

### 11.1 版本管理

采用语义化版本：`MAJOR.MINOR.PATCH`

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向后兼容的功能新增
- **PATCH**: 向后兼容的问题修复

### 11.2 发布清单

- [ ] 完成单元测试覆盖率 > 80%
- [ ] 通过集成测试
- [ ] 完成性能基准测试
- [ ] 更新 CHANGELOG
- [ ] 更新文档和示例
- [ ] 创建 GitHub Release
- [ ] 发布到 pkg.go.dev

### 11.3 CI/CD 流程

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
        with:
          go-version: '1.21'
      
      - name: Run tests
        run: go test -v -race -coverprofile=coverage.txt ./...
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  integration-test:
    runs-on: ubuntu-latest
    services:
      kyuubi:
        image: apache/kyuubi:latest
        ports:
          - 10009:10009
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
      
      - name: Run integration tests
        run: go test -v -tags=integration ./...
```

## 12. 实施路线图

### 12.1 首选路线（Python 桥接 for genai-toolbox）⭐⭐⭐⭐⭐

#### 第一阶段：核心集成（1-3 天）

**目标**: 完成基本的 Kyuubi 数据源集成

**任务清单**:
- [ ] 创建 Python 桥接脚本 (`scripts/kyuubi_bridge.py`)
- [ ] 实现 Go wrapper代码 (`internal/sources/kyuubi/`)
- [ ] 添加配置文件支持 (`tools.yaml`)
- [ ] 基础功能测试（连接、查询）

**预计时间**: 1-3 天  
**难度**: ⭐⭐  
**投入**: 1 名开发者  
**产出**: 可工作的 Kyuubi 数据源

#### 第二阶段：功能完善（2-3 天）

**目标**: 完善功能和文档

**任务清单**:
- [ ] 支持多种认证方式（PLAIN, LDAP, KERBEROS）
- [ ] 错误处理优化
- [ ] 元数据查询（GetTables, GetSchema）
- [ ] 编写使用文档和示例
- [ ] 集成测试

**预计时间**: 2-3 天  
**难度**: ⭐⭐⭐  
**投入**: 1 名开发者  
**产出**: 功能完整的实现

#### 第三阶段：优化和发布（1-2 天）

**目标**: 性能优化和正式发布

**任务清单**:
- [ ] 性能测试和优化
- [ ] 完善文档
- [ ] CI/CD 集成
- [ ] PR 到 genai-toolbox 主仓库

**预计时间**: 1-2 天  
**难度**: ⭐⭐  
**投入**: 1 名开发者  
**产出**: 生产就绪的版本

**总计**: **4-8 天，1 名开发者**

---

### 12.2 备选路线（基于 gohive）

#### 第一阶段：快速集成（1-2 周）

**目标**: 完成基础封装和测试

- [ ] 集成 gohive 库
- [ ] 封装 Kyuubi 客户端类
- [ ] 实现基础查询功能
- [ ] 添加配置管理
- [ ] 编写基础示例
- [ ] 单元测试

**预计时间**: 1-2 周
**难度**: ⭐⭐
**投入**: 1 名开发者

#### 第二阶段：功能完善（2-3 周）

**目标**: 完善功能和生产特性

- [ ] Kerberos 认证集成
- [ ] 错误处理优化
- [ ] 异步查询支持
- [ ] 日志和监控
- [ ] 完整的使用文档
- [ ] 集成测试

**预计时间**: 2-3 周
**难度**: ⭐⭐⭐
**投入**: 1-2 名开发者

#### 第三阶段：生态集成（2-3 周）

**目标**: 集成 Go 生态

- [ ] 实现 database/sql 驱动
- [ ] 连接池优化
- [ ] 性能优化和基准测试
- [ ] CI/CD 流程
- [ ] 发布到 pkg.go.dev
- [ ] 完善文档和示例

**预计时间**: 2-3 周
**难度**: ⭐⭐⭐
**投入**: 1-2 名开发者

**总计**: 5-8 周，1-2 名开发者

---

### 12.2 备选路线（从头实现，不推荐）

#### 第一阶段：核心功能（MVP）

**目标**: 实现基本的连接和查询功能

- [ ] Thrift 代码生成和集成
- [ ] 连接管理（Connection）
- [ ] 会话管理（Session）
- [ ] 同步 SQL 执行
- [ ] 结果集遍历
- [ ] PLAIN 认证
- [ ] 基础错误处理
- [ ] 单元测试

**预计时间**: 6-8 周
**难度**: ⭐⭐⭐⭐
**投入**: 2-3 名开发者

#### 第二阶段：高级特性

**目标**: 增强功能和生产可用性

- [ ] 异步 SQL 执行
- [ ] 操作状态轮询
- [ ] Kerberos 认证（复杂）
- [ ] 连接池
- [ ] 重试机制
- [ ] 查询超时
- [ ] 元数据查询
- [ ] 集成测试

**预计时间**: 6-8 周
**难度**: ⭐⭐⭐⭐⭐
**投入**: 2-3 名开发者

#### 第三阶段：生态集成

- [ ] database/sql 驱动实现
- [ ] 完整文档和示例
- [ ] 性能基准测试

**预计时间**: 4-6 周
**难度**: ⭐⭐⭐
**投入**: 2 名开发者

**总计**: 16-22 周（4-5 个月），2-3 名开发者

---

### 12.3 方案对比总结

| 对比项 | 方案一（gohive） | 方案三（从头实现） |
|-------|-----------------|------------------|
| **开发周期** | 5-8 周 | 16-22 周 |
| **开发人员** | 1-2 人 | 2-3 人 |
| **技术难度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **维护成本** | 低 | 高 |
| **风险** | 低 | 中高 |
| **ROI** | 高 | 低 |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐ |

**结论**: **强烈推荐方案一（基于 gohive）**，除非有特殊的定制需求。

## 13. 参考资源

### 13.1 官方文档

- [Kyuubi 官方文档](https://kyuubi.readthedocs.io/)
- [Kyuubi GitHub](https://github.com/apache/kyuubi)
- [HiveServer2 Thrift Interface](https://github.com/apache/hive/tree/master/service-rpc)
- [Apache Thrift](https://thrift.apache.org/)

### 13.2 现有客户端实现

- **Java JDBC 驱动**: `kyuubi-hive-jdbc` 模块
  - 路径: `/kyuubi-hive-jdbc/src/main/java/`
  - 关键类: `KyuubiConnection`, `KyuubiStatement`, `KyuubiResultSet`

- **Python 客户端**: PyHive
  - 路径: `/python/pyhive/`
  - 关键文件: `hive.py`, `TCLIService/`

- **REST 客户端**: Java REST Client
  - 路径: `/kyuubi-rest-client/src/main/java/`

### 13.3 相关项目

**推荐使用**:
- [**gohive**](https://github.com/beltran/gohive) - ⭐ 推荐！成熟的 HiveServer2 Go 客户端（**本方案首选**）
  - GitHub: https://github.com/beltran/gohive
  - 支持所有 HiveServer2 功能
  - 完全兼容 Kyuubi

**其他参考**:
- [impala-go-client](https://github.com/bippio/go-impala) - Impala 的 Go 客户端（类似架构）
- [presto-go-client](https://github.com/prestodb/presto-go-client) - Presto 的官方 Go 客户端
- [trino-go-client](https://github.com/trinodb/trino-go-client) - Trino 的官方 Go 客户端

### 13.4 技术参考

- [Thrift: The Missing Guide](https://diwakergupta.github.io/thrift-missing-guide/)
- [SASL Authentication](https://www.ietf.org/rfc/rfc4422.txt)
- [Go database/sql Tutorial](https://go.dev/doc/database/sql-tutorial)
- [Writing a database driver in Go](https://github.com/golang/go/wiki/SQLDrivers)

## 14. 总结与建议

本技术方案针对 **为 AI Agent / LLM 提供 Kyuubi 访问能力** 的实际场景，深入分析了多种实现方式。

### 14.1 方案推荐

#### 🏆 最优方案：独立 Python MCP 服务（⭐⭐⭐⭐⭐）

**强烈推荐，适用于所有场景**

**推荐理由**:
1. ✅ **极速交付**: 4-8 天完成完整集成
2. ✅ **零维护成本**: PyHive 由 Kyuubi 官方维护
3. ✅ **功能100%**: 支持所有 Kyuubi 特性
4. ✅ **风险最低**: 使用官方推荐的成熟方案
5. ✅ **完美契合**: AI Agent 场景对跨进程开销不敏感

**类比**: 
- 类似 Python 的 PyHive - 使用官方支持的客户端
- 类似 Python 的 JayDeBeApi - 通过桥接复用 Java 驱动
- **最佳实践**: 在 Go 项目中复用 Python 生态的成熟实现

**genai-toolbox 特定优势**:
- ✅ 与现有数据源集成模式一致
- ✅ AI Agent 场景性能需求合理（秒级响应）
- ✅ 服务器部署，Python 环境易获得
- ✅ 可快速迭代和验证

---

#### 备选方案：纯 Go 实现（gohive）⭐⭐⭐⭐

**适用场景**:
- 不希望引入 Python 依赖
- 需要极致性能（毫秒级）
- 纯 Go 技术栈要求

**权衡**:
- 开发时间：1-2 周（比 Python 桥接慢 2-3 倍）
- 维护成本：中等（需要跟进社区更新）
- 功能完整性：95%（可能缺少部分新特性）
- 性能提升：~100ms（对 AI Agent 场景意义不大）

---

#### 不推荐：REST API（⭐⭐）

**不推荐理由**:
- ❌ Kyuubi REST API 为实验性质
- ❌ 功能受限，部分高级特性不支持
- ❌ API 可能在未来版本变化

---

#### 绝不推荐：从头实现（❌）

**完全不适合集成项目**:
- ❌ 4-5 个月开发周期
- ❌ 投入产出比极低
- ❌ 维护成本高
- ❌ 已有现成方案

### 14.2 Python 桥接方案的核心优势

| 优势维度 | 说明 | genai-toolbox 契合度 |
|---------|------|---------------------|
| **开发速度** | 4-8 天完成 | ⭐⭐⭐⭐⭐ 符合快速迭代需求 |
| **功能完整性** | 100% Kyuubi 特性 | ⭐⭐⭐⭐⭐ AI Agent 需要完整功能 |
| **维护成本** | 零成本（官方维护） | ⭐⭐⭐⭐⭐ 减轻团队负担 |
| **稳定性** | 生产验证 | ⭐⭐⭐⭐⭐ 关键优势 |
| **认证支持** | 完整支持所有认证 | ⭐⭐⭐⭐⭐ 企业环境必需 |
| **性能** | 秒级响应 | ⭐⭐⭐⭐ AI Agent 可接受 |
| **部署复杂度** | 需要 Python 环境 | ⭐⭐⭐⭐ 服务器端易满足 |

### 14.3 实施路线图（Python 桥接）

```
第1天: 创建 Python 桥接脚本
   ├─ kyuubi_bridge.py 基础框架
   ├─ 实现 execute_query 函数
   └─ 本地测试连接

第2-3天: 实现 Go wrapper
   ├─ internal/sources/kyuubi/kyuubi.go
   ├─ 实现 Query, GetTables, GetSchema
   └─ 集成测试

第4-5天: 认证和错误处理
   ├─ 支持 PLAIN, LDAP, KERBEROS
   ├─ 完善错误处理
   └─ 边界情况测试

第6-7天: 文档和示例
   ├─ 编写 README
   ├─ 配置示例
   └─ 使用示例

第8天: PR 准备
   ├─ 代码审查
   ├─ CI/CD 集成
   └─ 提交 PR
```

### 14.4 对比分析

#### Python 桥接 vs Pure Go (gohive)

| 对比项 | Python 桥接 | Pure Go (gohive) | 差异 |
|-------|------------|-----------------|------|
| **开发时间** | 4-8 天 | 10-14 天 | 🏆 快 2-3 倍 |
| **维护成本** | 零（官方维护） | 中等（社区维护） | 🏆 零维护 |
| **功能完整性** | 100% | 95% | 🏆 更完整 |
| **性能（AI Agent）** | 1-2秒 | 0.9-1.8秒 | ⚖️ 差异<200ms |
| **部署依赖** | Python + PyHive | 纯 Go | ⚖️ Python依赖 |
| **调试难度** | 中等 | 低 | ⚖️ 跨进程调试 |
| **社区支持** | Kyuubi 官方 | 第三方社区 | 🏆 官方支持 |

**结论**: 对于 genai-toolbox 集成，**Python 桥接是明显的最优选择**。

### 14.5 参考案例

#### Python 生态的最佳实践

| Python 客户端 | genai-toolbox 对应方案 | 开发时间 | 推荐度 |
|--------------|----------------------|---------|--------|
| **PyHive** → | **Python 桥接** | 4-8天 | ⭐⭐⭐⭐⭐ |
| **JayDeBeApi** → | Python 桥接（备选） | 4-8天 | ⭐⭐⭐⭐ |
| **纯实现** → | gohive 库 | 10-14天 | ⭐⭐⭐ |
| **从头写** → | 不考虑 | 4-5个月 | ❌ |

**启示**: 
1. Python 用户 99% 选择 PyHive/JayDeBeApi，而不是自己实现
2. Go 项目应该复用 Python 生态的成熟方案
3. AI Agent 场景不需要极致性能，稳定性和功能完整性更重要

### 14.6 行动建议

#### 立即行动（第1周）

1. **Day 1-2**: 创建 POC
   ```bash
   # 1. 创建 Python 桥接脚本
   # 2. 测试连接 Kyuubi
   # 3. 验证基础查询
   ```

2. **Day 3-5**: 实现 Go wrapper
   ```go
   // 1. 实现 Source 结构体
   // 2. 实现 Query 方法
   // 3. 集成测试
   ```

3. **Day 6-7**: 文档和示例
   ```yaml
   # 1. 编写 tools.yaml 配置
   # 2. 创建使用示例
   # 3. 测试不同认证方式
   ```

#### 中期规划（第2-4周）

1. **Week 2**: 功能完善和测试
2. **Week 3**: 性能优化（如需要）
3. **Week 4**: 提交 PR 到 genai-toolbox

#### 长期维护

1. ✅ **零维护**: PyHive 由 Kyuubi 官方维护
2. ✅ **被动更新**: 仅需跟进 PyHive 版本
3. ✅ **社区支持**: 问题直接向 Kyuubi 社区反馈

### 14.7 最终建议

**🎯 强烈建议使用 Python 桥接方案**

**理由总结**:
1. ⚡ **最快**: 4-8天完成，是 gohive 方案的 2-3 倍快
2. 🔒 **最稳**: 使用官方维护的 PyHive，生产验证
3. 💰 **最省**: 零维护成本，长期投入最低
4. 🎯 **最全**: 100% 功能支持，无缺失
5. ✨ **最优**: 完美契合 genai-toolbox 和 AI Agent 场景

**参考文档**:
- PyHive 官方文档：https://kyuubi.readthedocs.io/en/v1.10.2/client/python/pyhive.html
- JayDeBeApi 官方文档：https://kyuubi.readthedocs.io/en/v1.10.2/client/python/jaydebeapi.html
- genai-toolbox 项目：https://github.com/googleapis/genai-toolbox

---

**文档版本**: v1.0  
**最后更新**: 2024-12-22  
**作者**: Kyuubi Go Client Development Team

