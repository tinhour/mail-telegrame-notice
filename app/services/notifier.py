import logging
import smtplib
import telegram
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config.settings import CONFIG

logger = logging.getLogger(__name__)

class NotificationService:
    """通知服务，负责发送邮件和Telegram消息"""
    
    def __init__(self):
        self.config = CONFIG["notifications"]
        self.email_config = self.config["email"]
        self.telegram_config = self.config["telegram"]
        self.telegram_bot = None
        self.telegram_initialized = False
        
        # 如果Telegram启用，初始化机器人
        if self.telegram_config["enabled"] and self.telegram_config["token"]:
            try:
                self.telegram_bot = telegram.Bot(token=self.telegram_config["token"])
                self.telegram_initialized = True
                logger.info("Telegram机器人初始化成功")
            except Exception as e:
                logger.error(f"Telegram机器人初始化失败: {str(e)}")
                self.telegram_bot = None
                self.telegram_initialized = False
    
    def send_notification(self, subject, message, level="info"):
        """
        发送通知
        
        Args:
            subject: 通知主题
            message: 通知内容
            level: 通知级别 (info, warning, error)
        """
        email_success = False
        telegram_success = False
        
        # 根据通知级别设置前缀
        prefix = {
            "info": "📢 信息",
            "warning": "⚠️ 警告",
            "error": "🚨 错误"
        }.get(level, "📢 信息")
        
        full_subject = f"{prefix}: {subject}"
        
        # 尝试发送邮件
        if self.email_config["enabled"]:
            email_success = self.send_email(full_subject, message)
            logger.info(f"邮件通知发送{'成功' if email_success else '失败'}: {subject}")
        
        # 尝试发送Telegram消息
        if self.telegram_config["enabled"]:
            telegram_success = self.send_telegram(full_subject, message)
            logger.info(f"Telegram通知发送{'成功' if telegram_success else '失败'}: {subject}")
        
        # 如果两个渠道都失败，记录错误
        if not email_success and not telegram_success:
            logger.error(f"所有通知渠道都失败: {subject}")
            
        return email_success or telegram_success
    
    def send_email(self, subject, message):
        """发送邮件通知"""
        if not self.email_config["enabled"]:
            return False
            
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = self.email_config["sender"]
            msg["To"] = ", ".join(self.email_config["recipients"])
            msg["Subject"] = subject
            
            # 添加邮件内容
            msg.attach(MIMEText(message, "plain"))
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"]) as server:
                server.starttls()
                server.login(self.email_config["username"], self.email_config["password"])
                server.send_message(msg)
                
            logger.info(f"邮件发送成功: {subject}")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            return False
    
    def send_telegram(self, subject, message):
        """发送Telegram通知"""
        if not self.telegram_config["enabled"] or not self.telegram_initialized:
            logger.warning("Telegram通知未启用或机器人未初始化")
            return False
            
        try:
            full_message = f"*{subject}*\n\n{message}"
            
            for chat_id in self.telegram_config["chat_ids"]:
                self.telegram_bot.send_message(
                    chat_id=chat_id,
                    text=full_message,
                    parse_mode="Markdown"
                )
                
            logger.info(f"Telegram消息发送成功: {subject}")
            return True
        except Exception as e:
            logger.error(f"Telegram消息发送失败: {str(e)}")
            return False


# 创建通知服务实例
notifier = NotificationService() 