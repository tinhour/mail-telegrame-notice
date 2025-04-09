import os
import yaml
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = os.getenv("CONFIG_FILE", "config.yaml")

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"配置文件 {CONFIG_FILE} 不存在，使用默认配置")
            return {
                "database": {
                    "host": os.getenv("DB_HOST", "localhost"),
                    "port": int(os.getenv("DB_PORT", "5432")),
                    "user": os.getenv("DB_USER", "postgres"),
                    "password": os.getenv("DB_PASSWORD", ""),
                    "dbname": os.getenv("DB_NAME", "monitoring")
                },
                "notifications": {
                    "email": {
                        "enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
                        "smtp_server": os.getenv("SMTP_SERVER", ""),
                        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                        "username": os.getenv("SMTP_USER", ""),
                        "password": os.getenv("SMTP_PASSWORD", ""),
                        "sender": os.getenv("EMAIL_SENDER", ""),
                        "recipients": os.getenv("EMAIL_RECIPIENTS", "").split(",")
                    },
                    "telegram": {
                        "enabled": os.getenv("TELEGRAM_ENABLED", "false").lower() == "true",
                        "token": os.getenv("TELEGRAM_TOKEN", ""),
                        "chat_ids": [int(id.strip()) for id in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if id.strip()]
                    }
                },
                "service_checks": {
                    "enabled": os.getenv("SERVICE_CHECKS_ENABLED", "true").lower() == "true",
                    "interval_minutes": int(os.getenv("SERVICE_CHECK_INTERVAL", "5")),
                    "endpoints": []
                },
                "system_monitoring": {
                    "enabled": os.getenv("SYSTEM_MONITORING_ENABLED", "true").lower() == "true",
                    "interval_minutes": int(os.getenv("SYSTEM_MONITORING_INTERVAL", "5")),
                    "thresholds": {
                        "cpu_percent": float(os.getenv("CPU_THRESHOLD", "80")),
                        "memory_percent": float(os.getenv("MEMORY_THRESHOLD", "80")),
                        "disk_percent": float(os.getenv("DISK_THRESHOLD", "85"))
                    }
                }
            }
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        raise

# 全局配置
CONFIG = load_config() 