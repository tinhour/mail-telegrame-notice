import logging
import requests
import time
import json
from datetime import datetime

from app.config.settings import CONFIG
from app.services.notifier import notifier

logger = logging.getLogger(__name__)

class ServiceChecker:
    """服务检查器"""
    
    def __init__(self):
        self.config = CONFIG["service_checks"]
        self.endpoints = self.config.get("endpoints", [])
        self.timeout = 10
        self.status_history = {}
        self.default_interval = self.config.get("interval_minutes", 5)

    def run_checks(self):
        """运行检查"""
        if not self.config["enabled"]:
            logger.info("服务检查功能已禁用")
            return
        
        logger.info("开始服务状态检查...")
        check_time = datetime.now()
        
        for endpoint in self.endpoints:
            name = endpoint["name"]
            logger.info(f"检查服务: {name}")
            
            # 获取历史状态
            previous_status = self.status_history.get(name, {}).get("is_ok")
            
            # 模拟检查结果
            is_ok = True
            details = "服务正常"
            
            # 检测状态变化
            if previous_status is not None and previous_status != is_ok:
                status_change = "恢复正常" if is_ok else "变为异常"
                logger.info(f"服务 {name} 状态变化: {status_change}")
                
                # 发送通知
                message = f"服务 {name} {status_change}"
                level = "warning" if is_ok else "error"
                notifier.send_notification(f"服务状态变化: {name}", message, level)
            
            # 更新状态历史
            self.status_history[name] = {
                "is_ok": is_ok,
                "details": details,
                "last_check": check_time
            }
        
        logger.info("服务状态检查完成")
        
    def send_test_notification(self):
        """发送测试通知"""
        logger.info("发送测试通知...")
        
        # 发送测试通知
        test_message = "这是一条测试通知，测试邮件和Telegram通知功能。"
        result = notifier.send_notification("服务监控系统测试", test_message, "warning")
        logger.info(f"测试通知发送结果: {'成功' if result else '失败'}")
        
        return {"notification": result}

# 创建服务检查实例
service_checker = ServiceChecker() 