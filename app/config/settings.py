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

# 尝试导入psycopg2
try:
    import psycopg2
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logger.warning("无法导入psycopg2模块，数据库功能将被禁用")

def get_db_connection():
    """获取数据库连接"""
    if not DB_AVAILABLE:
        logger.warning("psycopg2模块不可用，无法连接数据库")
        return None
        
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            dbname=os.getenv("DB_NAME", "evm_tracker")
        )
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return None

def load_db_settings():
    """从数据库加载配置项"""
    if not DB_AVAILABLE:
        logger.warning("psycopg2模块不可用，无法从数据库加载配置")
        return {}
        
    settings = {}
    conn = get_db_connection()
    if not conn:
        logger.warning("无法从数据库加载配置，将使用配置文件")
        return settings
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT key, value FROM public.system_settings")
            for row in cursor.fetchall():
                key, value = row[0], row[1]
                settings[key] = value
                
        logger.info(f"成功从数据库加载配置: {len(settings)}项")
        for key, value in settings.items():
            if key not in ['smtp_password']:  # 不记录敏感信息
                logger.debug(f"已加载配置: {key} = {value}")
        return settings
    except Exception as e:
        logger.error(f"从数据库加载配置失败: {str(e)}")
        return {}
    finally:
        conn.close()

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

def update_config_with_db_settings(config, db_settings):
    """使用数据库设置更新配置"""
    if not db_settings:
        return config
    
    # 更新Telegram配置
    if 'enableTelegramAlerts' in db_settings:
        enabled = parse_value(db_settings['enableTelegramAlerts'])
        config['notifications']['telegram']['enabled'] = enabled
        logger.info(f"已从数据库设置Telegram通知: {'启用' if enabled else '禁用'}")
    
    if 'telegramBotToken' in db_settings:
        config['notifications']['telegram']['token'] = db_settings['telegramBotToken']
        logger.info("已从数据库设置Telegram Bot Token")
    
    if 'telegramChatId' in db_settings:
        chat_ids = db_settings['telegramChatId'].split(',')
        parsed_chat_ids = []
        for id in chat_ids:
            try:
                parsed_chat_ids.append(int(id.strip()))
            except ValueError:
                logger.warning(f"无法解析Telegram聊天ID: {id}")
        
        if parsed_chat_ids:
            config['notifications']['telegram']['chat_ids'] = parsed_chat_ids
            logger.info(f"已从数据库设置Telegram Chat IDs: {parsed_chat_ids}")
    
    # 更新邮件配置
    if 'enableEmailAlerts' in db_settings:
        enabled = parse_value(db_settings['enableEmailAlerts'])
        config['notifications']['email']['enabled'] = enabled
        logger.info(f"已从数据库设置邮件通知: {'启用' if enabled else '禁用'}")
    
    # 支持两种命名格式的SMTP配置
    # 格式1: smtp_server, smtp_port, etc.
    if 'smtp_server' in db_settings:
        config['notifications']['email']['smtp_server'] = db_settings['smtp_server']
        logger.info(f"已从数据库设置SMTP服务器: {db_settings['smtp_server']}")
    
    if 'smtp_port' in db_settings:
        config['notifications']['email']['smtp_port'] = parse_value(db_settings['smtp_port'])
        logger.info(f"已从数据库设置SMTP端口: {db_settings['smtp_port']}")
    
    if 'smtp_username' in db_settings:
        config['notifications']['email']['username'] = db_settings['smtp_username']
        logger.info(f"已从数据库设置SMTP用户名: {db_settings['smtp_username']}")
    
    if 'smtp_password' in db_settings:
        config['notifications']['email']['password'] = db_settings['smtp_password']
        logger.info("已从数据库设置SMTP密码")
    
    if 'smtp_sender' in db_settings:
        config['notifications']['email']['sender'] = db_settings['smtp_sender']
        logger.info(f"已从数据库设置SMTP发件人: {db_settings['smtp_sender']}")
    
    if 'smtp_recipients' in db_settings:
        config['notifications']['email']['recipients'] = parse_value(db_settings['smtp_recipients'])
        logger.info(f"已从数据库设置SMTP收件人: {db_settings['smtp_recipients']}")
    
    # 格式2: smtpServer, smtpPort, etc.
    if 'smtpServer' in db_settings:
        config['notifications']['email']['smtp_server'] = db_settings['smtpServer']
    
    if 'smtpPort' in db_settings:
        config['notifications']['email']['smtp_port'] = parse_value(db_settings['smtpPort'])
    
    if 'smtpUser' in db_settings:
        config['notifications']['email']['username'] = db_settings['smtpUser']
    
    if 'smtpPassword' in db_settings:
        config['notifications']['email']['password'] = db_settings['smtpPassword']
    
    if 'emailSender' in db_settings:
        config['notifications']['email']['sender'] = db_settings['emailSender']
    
    if 'emailRecipients' in db_settings:
        config['notifications']['email']['recipients'] = parse_value(db_settings['emailRecipients'])
    
    # 如果存在notificationEmail但没有设置recipients，使用它作为收件人
    if 'notificationEmail' in db_settings and not config['notifications']['email']['recipients']:
        config['notifications']['email']['recipients'] = [db_settings['notificationEmail']]
        logger.info(f"使用notificationEmail作为收件人: {db_settings['notificationEmail']}")
    
    # 更新服务检查配置
    if 'serviceCheckInterval' in db_settings:
        config['service_checks']['interval_minutes'] = parse_value(db_settings['serviceCheckInterval'])
        logger.info(f"已从数据库设置服务检查间隔: {db_settings['serviceCheckInterval']}分钟")
    
    # 更新系统监控配置
    if 'systemMonitoringInterval' in db_settings:
        config['system_monitoring']['interval_minutes'] = parse_value(db_settings['systemMonitoringInterval'])
        logger.info(f"已从数据库设置系统监控间隔: {db_settings['systemMonitoringInterval']}分钟")
    
    if 'cpuThreshold' in db_settings:
        config['system_monitoring']['thresholds']['cpu_percent'] = parse_value(db_settings['cpuThreshold'])
        logger.info(f"已从数据库设置CPU阈值: {db_settings['cpuThreshold']}%")
    
    if 'memoryThreshold' in db_settings:
        config['system_monitoring']['thresholds']['memory_percent'] = parse_value(db_settings['memoryThreshold'])
        logger.info(f"已从数据库设置内存阈值: {db_settings['memoryThreshold']}%")
    
    if 'diskThreshold' in db_settings:
        config['system_monitoring']['thresholds']['disk_percent'] = parse_value(db_settings['diskThreshold'])
        logger.info(f"已从数据库设置磁盘阈值: {db_settings['diskThreshold']}%")
    
    # 确保通知配置正确
    logger.info(f"邮件通知配置: 启用={config['notifications']['email']['enabled']}, 服务器={config['notifications']['email']['smtp_server']}, 端口={config['notifications']['email']['smtp_port']}")
    logger.info(f"Telegram通知配置: 启用={config['notifications']['telegram']['enabled']}, 机器人已初始化={config['notifications']['telegram'].get('bot_initialized', False)}")
    
    logger.info("完成数据库配置加载和应用")
    return config

def load_config(skip_db_settings=False):
    """
    加载配置文件
    
    Args:
        skip_db_settings: 是否跳过从数据库加载配置，默认为False
    """
    try:
        # 首先加载默认配置或文件配置
        default_config = {
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
        
        # 从数据库加载配置并覆盖现有配置（如果不跳过数据库配置加载）
        if not skip_db_settings:
            db_settings = load_db_settings()
            config = update_config_with_db_settings(config, db_settings)
        else:
            logger.info("已跳过从数据库加载配置")
        
        return config
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        raise

# 全局配置
CONFIG = load_config() 