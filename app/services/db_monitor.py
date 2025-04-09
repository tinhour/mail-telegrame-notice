import logging
import psycopg2
import time
from datetime import datetime

from app.config.settings import CONFIG
from app.services.notifier import notifier

logger = logging.getLogger(__name__)

class DatabaseMonitor:
    """数据库监控器，检查数据库连接状态"""
    
    def __init__(self):
        self.db_config = CONFIG["database"]
        self.last_status = None  # 上次检查的状态
        self.last_check_time = None  # 上次检查的时间
        self.last_notification_time = None  # 上次通知的时间
        self.notification_cooldown = 1800  # 通知冷却时间（秒），避免频繁发送
    
    def get_db_connection(self):
        """获取数据库连接"""
        try:
            conn = psycopg2.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                dbname=self.db_config["dbname"],
                connect_timeout=5  # 连接超时时间
            )
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            return None
    
    def check_connection(self):
        """检查数据库连接状态"""
        logger.info("开始检查数据库连接...")
        start_time = time.time()
        conn = self.get_db_connection()
        
        current_time = datetime.now()
        self.last_check_time = current_time
        
        if conn:
            # 测试执行简单查询
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                
                response_time = time.time() - start_time
                conn.close()
                
                # 连接成功
                logger.info(f"数据库连接正常 ({response_time:.2f}s)")
                
                # 如果之前状态是失败，现在恢复了，发送恢复通知
                if self.last_status is False:
                    self._send_recovery_notification(response_time)
                
                self.last_status = True
                return True, f"数据库连接正常 ({response_time:.2f}s)"
            except Exception as e:
                conn.close()
                logger.error(f"数据库查询失败: {str(e)}")
                self._send_error_notification(str(e))
                self.last_status = False
                return False, f"数据库查询失败: {str(e)}"
        else:
            # 连接失败
            self._send_error_notification("无法建立数据库连接")
            self.last_status = False
            return False, "无法建立数据库连接"
    
    def _send_error_notification(self, error_details):
        """发送数据库错误通知"""
        # 检查是否在冷却期内
        if self.last_notification_time:
            time_since_last = (datetime.now() - self.last_notification_time).total_seconds()
            if time_since_last < self.notification_cooldown:
                logger.info(f"数据库错误通知处于冷却期内，跳过发送 (剩余 {self.notification_cooldown - time_since_last:.0f}秒)")
                return
        
        subject = "数据库连接异常"
        message = f"""
数据库连接出现问题，请检查数据库服务是否正常运行。

数据库信息:
- 主机: {self.db_config['host']}
- 端口: {self.db_config['port']}
- 数据库: {self.db_config['dbname']}

错误详情: {error_details}

发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        success = notifier.send_notification(subject, message, "error")
        if success:
            logger.info("数据库错误通知已发送")
        else:
            logger.warning("数据库错误通知发送失败")
        
        self.last_notification_time = datetime.now()
    
    def _send_recovery_notification(self, response_time):
        """发送数据库恢复通知"""
        subject = "数据库连接已恢复"
        message = f"""
数据库连接已恢复正常。

数据库信息:
- 主机: {self.db_config['host']}
- 端口: {self.db_config['port']}
- 数据库: {self.db_config['dbname']}

响应时间: {response_time:.2f}秒
恢复时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        success = notifier.send_notification(subject, message, "info")
        if success:
            logger.info("数据库恢复通知已发送")
        else:
            logger.warning("数据库恢复通知发送失败")


# 创建数据库监控实例
db_monitor = DatabaseMonitor() 