#!/usr/bin/env python3
"""
测试脚本：验证 Kyuubi 连接是否正常

使用方法:
    python test_connection.py

或使用 uv:
    uv run python test_connection.py
"""

import os
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kyuubi_mcp_server.kyuubi_client import KyuubiClient


def test_connection():
    """测试 Kyuubi 连接"""
    print("=" * 60)
    print("Kyuubi MCP Server - 连接测试")
    print("=" * 60)

    # 从环境变量加载配置
    host = os.getenv("KYUUBI_HOST", "localhost")
    port = int(os.getenv("KYUUBI_PORT", "10009"))
    username = os.getenv("KYUUBI_USERNAME", "")
    password = os.getenv("KYUUBI_PASSWORD", "")
    database = os.getenv("KYUUBI_DATABASE", "default")
    auth_type = os.getenv("KYUUBI_AUTH_TYPE", "NONE")
    client_type = os.getenv("KYUUBI_CLIENT_TYPE", "jaydebeapi")
    jdbc_driver_path = os.getenv("KYUUBI_JDBC_DRIVER_PATH", "")

    # 打印配置信息
    print(f"\n配置信息:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {database}")
    print(f"  Auth Type: {auth_type}")
    print(f"  Client Type: {client_type}")
    print(f"  Username: {username or '(未设置)'}")
    print(f"  JDBC Driver: {jdbc_driver_path or '(未设置)'}")
    print()

    # 处理 JDBC 驱动路径
    jdbc_drivers = []
    if client_type.lower() == "jaydebeapi":
        # JayDeBeApi 需要 JDBC 驱动
        if not jdbc_driver_path:
            print("❌ 错误: 使用 JayDeBeApi 时，KYUUBI_JDBC_DRIVER_PATH 环境变量是必需的")
            print("\n请设置环境变量或使用 .env 文件:")
            print("  export KYUUBI_JDBC_DRIVER_PATH=/path/to/kyuubi-hive-jdbc-shaded.jar")
            print("\n或者使用 PyHive 客户端（无需 Java）:")
            print("  export KYUUBI_CLIENT_TYPE=pyhive")
            return False

        jdbc_drivers = [p.strip() for p in jdbc_driver_path.split(",") if p.strip()]

        # 检查驱动文件是否存在
        for driver_path in jdbc_drivers:
            if not Path(driver_path).exists():
                print(f"❌ 错误: JDBC 驱动文件不存在: {driver_path}")
                return False
    else:
        print("ℹ️  使用 PyHive 客户端（无需 JDBC 驱动）")

    try:
        # 创建客户端
        print(f"正在创建 Kyuubi 客户端（{client_type}）...")
        client = KyuubiClient(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            auth_type=auth_type,
            client_type=client_type,
            jdbc_driver_path=jdbc_drivers,
        )

        # 测试连接
        print("正在连接到 Kyuubi...")
        client.connect()
        print("✓ 连接成功!")

        # 测试查询：列出数据库
        print("\n正在测试查询...")
        databases = client.get_databases()
        print(f"✓ 找到 {len(databases)} 个数据库:")
        for db in databases[:10]:  # 只显示前10个
            print(f"  - {db}")
        if len(databases) > 10:
            print(f"  ... (还有 {len(databases) - 10} 个)")

        # 测试查询：列出表
        print(f"\n正在列出 '{database}' 数据库中的表...")
        tables = client.get_tables(database)
        print(f"✓ 找到 {len(tables)} 个表:")
        for table in tables[:10]:  # 只显示前10个
            print(f"  - {table}")
        if len(tables) > 10:
            print(f"  ... (还有 {len(tables) - 10} 个)")

        # 关闭连接
        client.close()
        print("\n✓ 连接已关闭")

        print("\n" + "=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        print("\n请检查:")
        print("  1. Kyuubi 服务器是否正在运行")
        print("  2. 主机名和端口号是否正确")
        print("  3. 用户名和密码是否正确")
        print("  4. JDBC 驱动路径是否正确")
        print("  5. 网络连接是否正常")
        return False


if __name__ == "__main__":
    # 尝试加载 .env 文件
    try:
        from dotenv import load_dotenv

        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            print(f"正在加载环境变量文件: {env_file}")
            load_dotenv(env_file)
        else:
            print("提示: 未找到 .env 文件，使用环境变量或默认值")
    except ImportError:
        pass

    # 运行测试
    success = test_connection()
    sys.exit(0 if success else 1)

