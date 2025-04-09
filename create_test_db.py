import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()

# 数据库连接信息
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "evm_tracker")

def create_database():
    """创建数据库"""
    # 连接到默认数据库
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname="postgres"
    )
    conn.autocommit = True
    
    try:
        with conn.cursor() as cursor:
            # 检查数据库是否存在
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
            if not cursor.fetchone():
                # 创建数据库
                cursor.execute(f"CREATE DATABASE {DB_NAME}")
                print(f"数据库 {DB_NAME} 已创建")
            else:
                print(f"数据库 {DB_NAME} 已存在")
    finally:
        conn.close()

def create_tables():
    """创建数据表"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    
    try:
        with conn.cursor() as cursor:
            # 创建系统设置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(100) NOT NULL UNIQUE,
                    value TEXT,
                    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("系统设置表已创建")
            
            # 插入测试数据
            test_data = [
                ("siteName", "EVM链上数据采集系统"),
                ("siteDescription", "区块链数据分析平台"),
                ("maintenanceMode", "false"),
                ("syncInterval", "60"),
                ("maxSyncJobs", "5"),
                ("dataRetentionDays", "20"),
                ("notificationEmail", "fangfeng335@qq.com"),
                ("enableEmailAlerts", "false"),
                ("enableTelegramAlerts", "false"),
                ("telegramBotToken", "7638015275:AAGuzFYTwgiihQ5iIrYXNJA-JE1ZPvGPWr4"),
                ("telegramChatId", "2006080530,-1002615732272"),
                ("telegramChannelId", "-1002615732272"),
                ("logLevel", "debug"),
                ("maxSyncBatchSize", "10000"),
                ("tokenPriceUpdateInterval", "1"),
                ("serviceCheckInterval", "5"),
                ("systemMonitoringInterval", "10"),
                ("cpuThreshold", "85"),
                ("memoryThreshold", "80"),
                ("diskThreshold", "90"),
                ("smtp_server", "smtp.qq.com"),
                ("smtp_port", "465"),
                ("smtp_username", "fangfeng335@qq.com"),
                ("smtp_password", "fqmterkgxiuwbhih"),
                ("smtp_sender", "fangfeng335@qq.com"),
                ("smtp_recipients", "250969751@qq.com,fangfeng335@qq.com")
            ]
            
            # 先清空表
            cursor.execute("TRUNCATE TABLE system_settings RESTART IDENTITY")
            conn.commit()
            print("系统设置表已清空")
            
            # 获取当前时间
            now = datetime.now()
            
            # 插入测试数据
            for key, value in test_data:
                cursor.execute(
                    """INSERT INTO system_settings 
                    (key, value, "createdAt", "updatedAt") 
                    VALUES (%s, %s, %s, %s)""",
                    (key, value, now, now)
                )
            conn.commit()
            print("测试数据已插入")
    finally:
        conn.close()

if __name__ == "__main__":
    create_database()
    create_tables()
    print("数据库初始化完成") 