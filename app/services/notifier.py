import logging
import smtplib
import telegram
import requests
import time
import asyncio
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
        
        # 记录通知配置
        logger.info(f"初始化通知服务: 邮件通知={'启用' if self.email_config['enabled'] else '禁用'}, "
                   f"Telegram通知={'启用' if self.telegram_config['enabled'] else '禁用'}")
        
        # 如果邮件通知启用，记录邮件配置
        if self.email_config["enabled"]:
            logger.info(f"邮件配置: 服务器={self.email_config['smtp_server']}, "
                       f"端口={self.email_config['smtp_port']}, "
                       f"发件人={self.email_config['sender']}, "
                       f"收件人={self.email_config['recipients']}")
        
        # 如果Telegram启用，初始化机器人
        if self.telegram_config["enabled"] and self.telegram_config["token"]:
            try:
                logger.info(f"正在初始化Telegram机器人，Token: {self.telegram_config['token'][:10]}..., "
                           f"聊天ID: {self.telegram_config['chat_ids']}")
                
                # 增加连接池参数和超时设置
                request_kwargs = {
                    'connection_pool_size': 16,  # 增大连接池大小
                    'connect_timeout': 15,       # 连接超时时间
                    'read_timeout': 15,          # 读取超时时间
                    'pool_timeout': 30,          # 池超时时间
                }
                
                self.telegram_bot = telegram.Bot(
                    token=self.telegram_config["token"],
                    request=telegram.request.HTTPXRequest(
                        **request_kwargs
                    )
                )
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
    
    async def _send_telegram_message(self, chat_id, text):
        """异步发送Telegram消息"""
        try:
            return await self.telegram_bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=None,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"异步发送Telegram消息出错: {str(e)}")
            raise e
    
    def send_telegram(self, subject, message):
        """发送Telegram通知"""
        if not self.telegram_config["enabled"]:
            logger.warning("Telegram通知未启用")
            return False
            
        if not self.telegram_initialized:
            # 尝试重新初始化Telegram机器人
            try:
                logger.info("Telegram机器人未初始化，尝试重新初始化...")
                request_kwargs = {
                    'connection_pool_size': 16,
                    'connect_timeout': 15,
                    'read_timeout': 15,
                    'pool_timeout': 30,
                }
                
                self.telegram_bot = telegram.Bot(
                    token=self.telegram_config["token"],
                    request=telegram.request.HTTPXRequest(
                        **request_kwargs
                    )
                )
                self.telegram_initialized = True
                logger.info("Telegram机器人重新初始化成功")
            except Exception as e:
                logger.error(f"Telegram机器人重新初始化失败: {str(e)}")
                return False
            
        # 添加重试逻辑
        max_retries = 3
        retry_delay = 2  # 初始重试延迟（秒）
        
        # 移除Markdown格式，避免格式错误导致发送失败
        full_message = f"{subject}\n\n{message}"
        
        # 顺序发送给每个聊天ID，添加重试机制
        success = False
        for chat_id in self.telegram_config["chat_ids"]:
            logger.info(f"尝试向Telegram聊天ID {chat_id} 发送消息")
            for attempt in range(max_retries):
                try:
                    # 使用事件循环执行异步发送函数
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        response = loop.run_until_complete(self._send_telegram_message(chat_id, full_message))
                        message_id = response.message_id if hasattr(response, 'message_id') else 'unknown'
                        logger.info(f"Telegram消息发送成功，消息ID: {message_id}")
                        success = True
                        break  # 成功发送后跳出重试循环
                    finally:
                        loop.close()
                        
                except telegram.error.TimedOut:
                    # 超时错误，进行重试
                    logger.warning(f"Telegram消息发送超时，正在重试 ({attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    
                except telegram.error.RetryAfter as e:
                    # 达到发送限制，需要等待
                    wait_time = e.retry_after + 1
                    logger.warning(f"Telegram速率限制，等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                    # 不计入重试次数
                    attempt -= 1
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Telegram消息发送异常: {error_msg}")
                    if "Pool timeout" in error_msg:
                        logger.warning(f"Telegram连接池超时，正在重试 ({attempt+1}/{max_retries})...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    elif "Chat not found" in error_msg:
                        logger.error(f"Telegram聊天ID {chat_id} 不存在，跳过此ID")
                        break  # 聊天不存在，跳过此ID
                    elif "Unauthorized" in error_msg:
                        logger.error("Telegram Bot Token无效，请检查配置")
                        self.telegram_initialized = False  # 标记为未初始化
                        return False  # 令牌无效，直接返回失败
                    else:
                        logger.error(f"其他Telegram错误: {error_msg}")
                        break  # 对于其他错误，不继续重试
        
        if success:
            # 防止Windows控制台编码问题，从日志中移除可能的表情符号
            safe_subject = self._remove_emojis(subject)
            logger.info(f"Telegram消息发送成功: {safe_subject}")
            return True
        else:
            logger.error(f"Telegram消息发送失败，已达到最大重试次数")
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