import logging
import smtplib
import requests
import time
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
        
        # 记录通知配置
        logger.info(f"初始化通知服务: 邮件通知={'启用' if self.email_config['enabled'] else '禁用'}, "
                   f"Telegram通知={'启用' if self.telegram_config['enabled'] else '禁用'}")
        
        # 如果邮件通知启用，记录邮件配置
        if self.email_config["enabled"]:
            logger.info(f"邮件配置: 服务器={self.email_config['smtp_server']}, "
                       f"端口={self.email_config['smtp_port']}, "
                       f"发件人={self.email_config['sender']}, "
                       f"收件人={self.email_config['recipients']}")
        
        # 如果Telegram启用，记录配置
        if self.telegram_config["enabled"] and self.telegram_config["token"]:
            logger.info(f"正在初始化Telegram配置，Token: {self.telegram_config['token'][:10]}..., "
                      f"聊天ID: {self.telegram_config['chat_ids']}")
    
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
            # 记录日志时移除可能的表情符号
            safe_subject = self._remove_emojis(subject)
            logger.info(f"邮件通知发送{'成功' if email_success else '失败'}: {safe_subject}")
        
        # 尝试发送Telegram消息
        if self.telegram_config["enabled"]:
            telegram_success = self.send_telegram(full_subject, message)
            # 记录日志时移除可能的表情符号
            safe_subject = self._remove_emojis(subject)
            logger.info(f"Telegram通知发送{'成功' if telegram_success else '失败'}: {safe_subject}")
        
        # 如果两个渠道都失败，记录错误
        if not email_success and not telegram_success:
            # 记录日志时移除可能的表情符号
            safe_subject = self._remove_emojis(subject)
            logger.error(f"所有通知渠道都失败: {safe_subject}")
            
        return email_success or telegram_success
    
    def send_email(self, subject, message):
        """发送邮件通知"""
        if not self.email_config["enabled"]:
            logger.warning("邮件通知未启用")
            return False
        
        if not self.email_config["smtp_server"] or not self.email_config["sender"]:
            logger.error("邮件配置不完整，无法发送")
            return False
            
        if not self.email_config["recipients"]:
            logger.error("邮件收件人未配置，无法发送")
            return False
            
        # 记录发送尝试
        safe_subject = self._remove_emojis(subject)
        logger.info(f"尝试发送邮件: 主题='{safe_subject}', 收件人={self.email_config['recipients']}")
        
        try:
            # 创建MIMEText对象
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.email_config["sender"]
            msg['To'] = ", ".join(self.email_config["recipients"])
            
            # 添加消息正文
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # 记录SMTP连接信息
            logger.info(f"连接SMTP服务器: {self.email_config['smtp_server']}:{self.email_config['smtp_port']}")
            
            # 连接SMTP服务器
            if self.email_config["smtp_port"] == 465:
                logger.info("使用SSL安全连接")
                server = smtplib.SMTP_SSL(self.email_config["smtp_server"], self.email_config["smtp_port"], timeout=30)
            else:
                logger.info("使用普通连接并启用TLS")
                server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"], timeout=30)
                server.starttls()  # 启用TLS
            
            # 登录
            if self.email_config["username"] and self.email_config["password"]:
                logger.info(f"使用用户名 {self.email_config['username']} 登录SMTP服务器")
                server.login(self.email_config["username"], self.email_config["password"])
            else:
                logger.info("未配置SMTP用户名或密码，使用匿名登录")
            
            # 发送邮件
            logger.info(f"开始发送邮件: 从 {self.email_config['sender']} 到 {self.email_config['recipients']}")
            server.sendmail(
                self.email_config["sender"],
                self.email_config["recipients"],
                msg.as_string()
            )
            server.quit()
            
            # 记录日志时移除可能的表情符号
            logger.info(f"邮件发送成功: {safe_subject}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP认证失败: {str(e)}. 请检查用户名和密码。")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP连接错误: {str(e)}. 请检查服务器地址和端口。")
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP服务器断开连接: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP异常: {str(e)}")
            return False
        except Exception as e:
            # 记录日志时移除可能的表情符号
            logger.error(f"邮件发送失败: {str(e)}")
            return False

    def send_telegram(self, subject, message):
        """
        使用直接HTTP请求发送Telegram通知，避免异步问题
        """
        if not self.telegram_config["enabled"]:
            logger.warning("Telegram通知未启用")
            return False
            
        if not self.telegram_config["token"]:
            logger.error("Telegram Bot Token未配置")
            return False
            
        if not self.telegram_config["chat_ids"]:
            logger.error("Telegram聊天ID未配置")
            return False
        
        # 移除Markdown格式，避免格式错误导致发送失败
        full_message = f"{subject}\n\n{message}"
        
        # 设置重试参数
        max_retries = 3
        retry_delay = 2
        
        # 尝试向所有聊天ID发送消息
        sent_to_any = False
        
        for chat_id in self.telegram_config["chat_ids"]:
            logger.info(f"尝试向Telegram聊天ID {chat_id} 发送消息")
            
            for attempt in range(max_retries):
                try:
                    # 使用HTTP请求直接调用Telegram API
                    api_url = f"https://api.telegram.org/bot{self.telegram_config['token']}/sendMessage"
                    data = {
                        "chat_id": chat_id,
                        "text": full_message,
                        "disable_web_page_preview": True
                    }
                    
                    response = requests.post(api_url, json=data, timeout=30)
                    response_data = response.json()
                    
                    if response.status_code == 200 and response_data.get("ok"):
                        message_id = response_data.get("result", {}).get("message_id", "unknown")
                        logger.info(f"Telegram消息发送成功，消息ID: {message_id}")
                        sent_to_any = True
                        break
                    else:
                        error_description = response_data.get("description", "未知错误")
                        logger.error(f"Telegram API错误: {error_description}")
                        
                        # 检查是否是已知错误
                        if "chat not found" in error_description.lower():
                            logger.error(f"Telegram聊天ID {chat_id} 不存在，跳过此ID")
                            break
                        elif "unauthorized" in error_description.lower():
                            logger.error("Telegram Bot Token无效，请检查配置")
                            return False
                            
                        # 其他错误，尝试重试
                        logger.warning(f"Telegram消息发送失败，正在重试 ({attempt+1}/{max_retries})...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        
                except requests.RequestException as e:
                    logger.error(f"Telegram HTTP请求错误: {str(e)}")
                    logger.warning(f"Telegram消息发送失败，正在重试 ({attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
        
        # 如果至少成功发送给一个接收者，就算成功
        if sent_to_any:
            # 防止Windows控制台编码问题，从日志中移除可能的表情符号
            safe_subject = self._remove_emojis(subject)
            logger.info(f"Telegram消息发送成功: {safe_subject}")
            return True
        else:
            logger.error(f"Telegram消息发送失败，未能发送给任何接收者")
            return False
    
    def _remove_emojis(self, text):
        """移除文本中的表情符号，防止日志记录时出现编码问题"""
        if not text:
            return ""
        
        # 尝试移除常见的表情符号前缀
        emoji_prefixes = ['📢', '⚠️', '🚨', '✅', '❌']
        result = text
        for prefix in emoji_prefixes:
            if prefix in result:
                result = result.replace(prefix, '')
        
        # 返回清理后的文本，确保前后没有多余空格
        return result.strip()


# 创建通知服务实例
notifier = NotificationService()