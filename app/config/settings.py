import os
import yaml
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
# 修复Windows控制台编码问题
import sys
if sys.platform == 'win32':
    import codecs
    # 强制使用utf-8编码
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
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

def parse_value(value):
    """解析配置值，将字符串转换为合适的数据类型"""
    if value is None:
        return None
    
    # 处理布尔值
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    
    # 处理数字
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        # 处理逗号分隔的列表
        if ',' in value:
            return [item.strip() for item in value.split(',') if item.strip()]
        
        # 保持原始字符串
        return value

def load_config():
    """加载配置文件"""
    try:
        # 首先加载默认配置
        default_config = {
            "notifications": {
                "email": {
                    "enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
                    "smtp_server": os.getenv("SMTP_SERVER", ""),
                    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                    "username": os.getenv("SMTP_USER", ""),
                    "password": os.getenv("SMTP_PASSWORD", ""),
                    "sender": os.getenv("EMAIL_SENDER", ""),
                    "recipients": [r for r in os.getenv("EMAIL_RECIPIENTS", "").split(",") if r]
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
            }
        }
        
        # 如果配置文件存在，从文件加载配置
        config = default_config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    # 合并配置文件中的配置
                    config = yaml_config
                    logger.info(f"已从文件加载配置: {CONFIG_FILE}")
        else:
            logger.warning(f"配置文件 {CONFIG_FILE} 不存在，使用默认配置")
        
        # 记录配置信息
        logger.info(f"邮件通知配置: 启用={config['notifications']['email']['enabled']}, 服务器={config['notifications']['email']['smtp_server']}")
        logger.info(f"Telegram通知配置: 启用={config['notifications']['telegram']['enabled']}")
        logger.info(f"服务检查配置: 启用={config['service_checks']['enabled']}, 间隔={config['service_checks']['interval_minutes']}分钟")
        
        return config
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        raise

# 加载全局配置
CONFIG = load_config() 