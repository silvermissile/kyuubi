"""
Kyuubi MCP 服务器
使用 fastmcp 提供与 LLM/AI Agent 交互的 MCP 接口
支持 stdio 和 HTTP 两种协议
"""

import argparse
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .kyuubi_client import KyuubiClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("kyuubi-mcp-server")

# 创建 FastMCP 应用实例
mcp = FastMCP("kyuubi-mcp-server")

# 全局变量：Kyuubi 客户端
kyuubi_client: Optional[KyuubiClient] = None


def init_kyuubi_client() -> KyuubiClient:
    """
    初始化 Kyuubi 客户端
    从环境变量加载配置
    """
    global kyuubi_client
    
    if kyuubi_client is not None:
        return kyuubi_client
    
    # 从环境变量加载配置
    config = {
        "host": os.getenv("KYUUBI_HOST", "localhost"),
        "port": int(os.getenv("KYUUBI_PORT", "10009")),
        "username": os.getenv("KYUUBI_USERNAME", ""),
        "password": os.getenv("KYUUBI_PASSWORD", ""),
        "database": os.getenv("KYUUBI_DATABASE", "default"),
        "auth_type": os.getenv("KYUUBI_AUTH_TYPE", "NONE"),
        "client_type": os.getenv("KYUUBI_CLIENT_TYPE", "jaydebeapi"),
        "jdbc_driver_path": os.getenv("KYUUBI_JDBC_DRIVER_PATH", ""),
    }
    
    logger.info("=" * 60)
    logger.info("初始化 Kyuubi MCP Server")
    logger.info("=" * 60)
    logger.info(f"Host: {config['host']}")
    logger.info(f"Port: {config['port']}")
    logger.info(f"Database: {config['database']}")
    logger.info(f"Auth Type: {config['auth_type']}")
    logger.info(f"Client Type: {config['client_type']}")
    logger.info("=" * 60)
    
    # 处理 JDBC 驱动路径
    jdbc_driver_path = []
    if config['client_type'].lower() == "jaydebeapi":
        # JayDeBeApi 需要 JDBC 驱动
        if not config['jdbc_driver_path']:
            logger.error("❌ 使用 JayDeBeApi 时，KYUUBI_JDBC_DRIVER_PATH 环境变量是必需的")
            raise ValueError(
                "使用 JayDeBeApi 时，KYUUBI_JDBC_DRIVER_PATH 环境变量是必需的。\n"
                "如果不想使用 Java，可以设置 KYUUBI_CLIENT_TYPE=pyhive"
            )
        
        jdbc_driver_path = [
            path.strip() 
            for path in config['jdbc_driver_path'].split(',')
            if path.strip()
        ]
        logger.info(f"JDBC Driver Path: {jdbc_driver_path}")
    else:
        logger.info("使用 PyHive 客户端（无需 JDBC 驱动）")
    
    # 创建客户端
    client = KyuubiClient(
        host=config['host'],
        port=config['port'],
        username=config['username'],
        password=config['password'],
        database=config['database'],
        auth_type=config['auth_type'],
        client_type=config['client_type'],
        jdbc_driver_path=jdbc_driver_path,
    )
    
    # 测试连接
    logger.info("正在测试连接到 Kyuubi...")
    client.connect()
    logger.info("✓ 成功连接到 Kyuubi")
    
    kyuubi_client = client
    return client


@mcp.tool()
def kyuubi_query(query: str) -> List[Dict[str, Any]]:
    """
    执行 SQL 查询并返回结果
    
    Args:
        query: 要执行的 SQL 查询语句（支持 Spark SQL 语法）
    
    Returns:
        查询结果（列表，每行为字典）
    """
    try:
        client = init_kyuubi_client()
        logger.info(f"执行查询: {query[:100]}...")
        result = client.execute_query(query)
        logger.info(f"查询返回 {len(result)} 行")
        return result
    except Exception as e:
        logger.error(f"查询执行失败: {e}")
        raise


@mcp.tool()
def kyuubi_list_databases() -> List[str]:
    """
    列出 Kyuubi/Hive 中所有可用的数据库
    
    Returns:
        数据库名称列表
    """
    try:
        client = init_kyuubi_client()
        logger.info("列出所有数据库")
        result = client.get_databases()
        logger.info(f"找到 {len(result)} 个数据库")
        return result
    except Exception as e:
        logger.error(f"列出数据库失败: {e}")
        raise


@mcp.tool()
def kyuubi_list_tables(database: Optional[str] = None) -> List[str]:
    """
    列出指定数据库中的所有表
    
    Args:
        database: 数据库名称（可选，默认使用配置的数据库）
    
    Returns:
        表名列表
    """
    try:
        client = init_kyuubi_client()
        db = database or client.database
        logger.info(f"列出数据库 '{db}' 中的表")
        result = client.get_tables(database)
        logger.info(f"找到 {len(result)} 个表")
        return result
    except Exception as e:
        logger.error(f"列出表失败: {e}")
        raise


@mcp.tool()
def kyuubi_describe_table(table: str, database: Optional[str] = None) -> List[Dict[str, str]]:
    """
    获取表的结构信息（列名、数据类型、注释等）
    
    Args:
        table: 表名
        database: 数据库名称（可选）
    
    Returns:
        表结构信息列表
    """
    try:
        client = init_kyuubi_client()
        db = database or client.database
        logger.info(f"描述表 '{db}.{table}'")
        result = client.describe_table(table, database)
        logger.info(f"表 '{table}' 有 {len(result)} 列")
        return result
    except Exception as e:
        logger.error(f"描述表失败: {e}")
        raise


@mcp.tool()
def kyuubi_table_sample(
    table: str, 
    database: Optional[str] = None, 
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    获取表的样本数据，用于快速了解表内容
    
    Args:
        table: 表名
        database: 数据库名称（可选）
        limit: 返回的行数（默认 10 行）
    
    Returns:
        样本数据
    """
    try:
        client = init_kyuubi_client()
        db = database or client.database
        logger.info(f"获取表 '{db}.{table}' 的样本数据（限制 {limit} 行）")
        result = client.get_table_sample(table, database, limit)
        logger.info(f"返回 {len(result)} 行样本数据")
        return result
    except Exception as e:
        logger.error(f"获取样本数据失败: {e}")
        raise


def parse_args():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(
        description="Kyuubi MCP Server - 为 AI Agent 提供 Kyuubi 数据访问能力"
    )
    
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "http"],
        default="stdio",
        help="MCP 传输协议 (默认: stdio)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="HTTP 服务器地址 (仅当 transport=http 时有效，默认: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP 服务器端口 (仅当 transport=http 时有效，默认: 8000)"
    )
    
    return parser.parse_args()


def main():
    """
    主函数：启动 MCP 服务器
    """
    # 解析命令行参数
    args = parse_args()
    
    try:
        # 尝试加载 .env 文件
        try:
            from dotenv import load_dotenv
            load_dotenv()
            logger.info("✓ 已加载 .env 文件")
        except ImportError:
            logger.info("未安装 python-dotenv，跳过 .env 文件加载")
        
        # 初始化 Kyuubi 客户端（测试连接）
        init_kyuubi_client()
        
        # 根据传输协议启动服务器
        if args.transport == "stdio":
            logger.info("=" * 60)
            logger.info("启动 MCP 服务器 (stdio 模式)")
            logger.info("=" * 60)
            mcp.run(transport="stdio")
            
        elif args.transport == "http":
            logger.info("=" * 60)
            logger.info(f"启动 MCP 服务器 (HTTP 模式)")
            logger.info(f"地址: http://{args.host}:{args.port}")
            logger.info("=" * 60)
            mcp.run(transport="sse", host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        logger.info("\n收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 清理资源
        if kyuubi_client:
            kyuubi_client.close()
            logger.info("已关闭 Kyuubi 连接")


if __name__ == "__main__":
    main()
