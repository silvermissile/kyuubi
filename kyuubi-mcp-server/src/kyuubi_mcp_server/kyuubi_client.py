"""
Kyuubi 客户端封装
支持 PyHive 和 JayDeBeApi 两种客户端
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KyuubiClient:
    """
    Kyuubi 客户端
    支持两种连接方式：
    1. PyHive: 轻量级，直接使用 Thrift 协议，无需 Java 环境
    2. JayDeBeApi: 功能完整，通过 JDBC 连接，需要 Java 环境和 JDBC 驱动
    """

    # 客户端类型常量
    CLIENT_TYPE_PYHIVE = "pyhive"
    CLIENT_TYPE_JAYDEBEAPI = "jaydebeapi"

    def __init__(
        self,
        host: str,
        port: int = 10009,
        username: str = "",
        password: str = "",
        database: str = "default",
        auth_type: str = "NONE",
        client_type: str = "jaydebeapi",
        jdbc_driver_path: Optional[List[str]] = None,
        additional_params: Optional[Dict[str, str]] = None,
    ):
        """
        初始化 Kyuubi 客户端

        Args:
            host: Kyuubi 服务器地址
            port: Kyuubi 服务器端口（默认 10009）
            username: 用户名
            password: 密码
            database: 默认数据库
            auth_type: 认证类型 (NONE, PLAIN, CUSTOM, LDAP, KERBEROS)
            client_type: 客户端类型 ("pyhive" 或 "jaydebeapi")
            jdbc_driver_path: JDBC 驱动 JAR 文件路径（仅 JayDeBeApi 需要）
            additional_params: 额外的连接参数
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.auth_type = auth_type
        self.client_type = client_type.lower()
        self.jdbc_driver_path = jdbc_driver_path or []
        self.additional_params = additional_params or {}

        self._connection = None
        self._connected = False

        # 验证客户端类型
        if self.client_type not in [self.CLIENT_TYPE_PYHIVE, self.CLIENT_TYPE_JAYDEBEAPI]:
            raise ValueError(
                f"不支持的客户端类型: {self.client_type}. "
                f"请使用 'pyhive' 或 'jaydebeapi'"
            )

    def connect(self):
        """
        建立到 Kyuubi 的连接
        根据 client_type 选择使用 PyHive 或 JayDeBeApi
        """
        if self._connected and self._connection:
            logger.info("已经连接到 Kyuubi")
            return

        try:
            if self.client_type == self.CLIENT_TYPE_PYHIVE:
                self._connect_pyhive()
            elif self.client_type == self.CLIENT_TYPE_JAYDEBEAPI:
                self._connect_jaydebeapi()
            
            self._connected = True
            logger.info(
                f"✓ 成功连接到 Kyuubi at {self.host}:{self.port} "
                f"(客户端: {self.client_type})"
            )

        except Exception as e:
            logger.error(f"连接 Kyuubi 失败: {e}")
            raise ConnectionError(f"无法连接到 Kyuubi: {e}")

    def _connect_pyhive(self):
        """
        使用 PyHive 连接
        优点：轻量级，无需 Java 环境
        """
        try:
            from pyhive import hive
        except ImportError:
            raise ImportError(
                "PyHive 未安装。请运行: uv sync --extra pyhive"
            )

        try:
            logger.info(f"使用 PyHive 连接到 {self.host}:{self.port}")
            
            # 根据认证类型选择连接方式
            if self.auth_type in ["CUSTOM", "LDAP", "PLAIN"]:
                self._connection = hive.Connection(
                    host=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    database=self.database,
                    auth=self.auth_type,
                )
            elif self.auth_type == "KERBEROS":
                self._connection = hive.Connection(
                    host=self.host,
                    port=self.port,
                    auth="KERBEROS",
                    kerberos_service_name="kyuubi",
                    database=self.database,
                )
            else:  # NONE
                self._connection = hive.Connection(
                    host=self.host,
                    port=self.port,
                    username=self.username or "anonymous",
                    database=self.database,
                )
            
            logger.info("PyHive 连接建立成功")

        except Exception as e:
            logger.error(f"PyHive 连接失败: {e}")
            raise

    def _connect_jaydebeapi(self):
        """
        使用 JayDeBeApi (JDBC) 连接
        优点：功能完整，支持所有 JDBC 特性
        需要：Java 环境和 JDBC 驱动
        """
        try:
            import jaydebeapi
        except ImportError:
            raise ImportError(
                "JayDeBeApi 未安装。请运行: uv sync --extra jaydebeapi"
            )

        if not self.jdbc_driver_path:
            raise ValueError(
                "使用 JayDeBeApi 需要指定 JDBC 驱动路径 (jdbc_driver_path)"
            )

        try:
            jdbc_url = self._build_jdbc_url()
            logger.info(f"使用 JayDeBeApi 连接: {jdbc_url}")

            # 驱动类名
            driver_class = "org.apache.hive.jdbc.HiveDriver"

            # 连接参数
            conn_args = [self.username, self.password] if self.username else []

            # 建立连接
            self._connection = jaydebeapi.connect(
                driver_class,
                jdbc_url,
                conn_args,
                self.jdbc_driver_path,
            )

            logger.info("JayDeBeApi 连接建立成功")

        except Exception as e:
            logger.error(f"JayDeBeApi 连接失败: {e}")
            raise

    def _build_jdbc_url(self) -> str:
        """
        构建 JDBC 连接 URL（用于 JayDeBeApi）

        Returns:
            JDBC 连接字符串
        """
        # 基础 URL: jdbc:hive2://host:port/database
        jdbc_url = f"jdbc:hive2://{self.host}:{self.port}/{self.database}"

        # 添加认证参数
        params = []
        
        if self.auth_type != "NONE":
            params.append(f"auth={self.auth_type}")

        # 添加额外参数
        for key, value in self.additional_params.items():
            params.append(f"{key}={value}")

        # 拼接参数
        if params:
            jdbc_url += ";" + ";".join(params)

        return jdbc_url

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        执行 SQL 查询并返回结果

        Args:
            query: SQL 查询语句

        Returns:
            查询结果（列表，每行为字典）
        """
        if not self._connected:
            self.connect()

        try:
            cursor = self._connection.cursor()
            logger.info(f"执行查询: {query[:100]}...")

            # 执行查询
            cursor.execute(query)

            # 获取列名
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # 获取所有结果
            results = []
            rows = cursor.fetchall()
            
            for row in rows:
                # 将每行转换为字典
                row_dict = dict(zip(columns, row))
                results.append(row_dict)

            cursor.close()

            logger.info(f"查询执行成功，返回 {len(results)} 行")
            return results

        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise RuntimeError(f"查询执行失败: {e}")

    def get_databases(self) -> List[str]:
        """
        获取所有数据库列表

        Returns:
            数据库名称列表
        """
        try:
            results = self.execute_query("SHOW DATABASES")
            # 结果格式: [{'database_name': 'default'}, ...] 或 [{'databaseName': 'table1'}, ...]
            return [
                row.get("database_name", row.get("databaseName", row.get("namespace", "")))
                for row in results
            ]
        except Exception as e:
            logger.error(f"获取数据库列表失败: {e}")
            raise

    def get_tables(self, database: Optional[str] = None) -> List[str]:
        """
        获取指定数据库中的表列表

        Args:
            database: 数据库名称（默认使用当前数据库）

        Returns:
            表名列表
        """
        db = database or self.database
        try:
            query = f"SHOW TABLES IN {db}"
            results = self.execute_query(query)
            # 结果格式可能是: [{'tab_name': 'table1'}, ...] 或 [{'tableName': 'table1'}, ...]
            return [
                row.get("tab_name", row.get("tableName", ""))
                for row in results
            ]
        except Exception as e:
            logger.error(f"获取表列表失败: {e}")
            raise

    def describe_table(self, table: str, database: Optional[str] = None) -> List[Dict[str, str]]:
        """
        获取表的结构信息

        Args:
            table: 表名
            database: 数据库名称（可选）

        Returns:
            表结构信息列表
        """
        db = database or self.database
        try:
            query = f"DESCRIBE {db}.{table}"
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"描述表 {table} 失败: {e}")
            raise

    def get_table_sample(
        self, table: str, database: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取表的样本数据

        Args:
            table: 表名
            database: 数据库名称
            limit: 返回的行数

        Returns:
            样本数据
        """
        db = database or self.database
        try:
            query = f"SELECT * FROM {db}.{table} LIMIT {limit}"
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"获取表样本数据失败: {e}")
            raise

    def close(self):
        """
        关闭连接
        """
        if self._connection:
            try:
                self._connection.close()
                self._connected = False
                logger.info("连接已关闭")
            except Exception as e:
                logger.error(f"关闭连接时出错: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
