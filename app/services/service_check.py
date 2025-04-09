import logging
import requests
import time
from datetime import datetime

from app.config.settings import CONFIG
from app.services.notifier import notifier

logger = logging.getLogger(__name__)

class ServiceChecker:
    """服务检查器，定时检查指定的服务端点状态"""
    
    def __init__(self):
        self.config = CONFIG["service_checks"]
        self.endpoints = self.config.get("endpoints", [])
        self.timeout = 10  # 请求超时时间（秒）
        self.status_history = {}  # 存储服务状态历史
        self.default_interval = self.config.get("interval_minutes", 5)  # 默认检查间隔（分钟）
    
    def add_endpoint(self, name, url, expected_status=200, expected_content=None, headers=None, method="GET", body=None, interval_minutes=None):
        """
        添加服务检查端点
        
        Args:
            name: 服务名称
            url: 服务URL
            expected_status: 预期HTTP状态码
            expected_content: 预期返回内容（字符串或None）
            headers: 请求头（字典或None）
            method: 请求方法（GET或POST）
            body: 请求体（用于POST请求）
            interval_minutes: 检查间隔时间（分钟）
        """
        endpoint = {
            "name": name,
            "url": url,
            "expected_status": expected_status,
            "expected_content": expected_content,
            "headers": headers or {},
            "method": method.upper(),
            "body": body,
            "interval_minutes": interval_minutes or self.default_interval
        }
        self.endpoints.append(endpoint)
        logger.info(f"添加服务检查端点: {name} - {url} ({method}), 检查间隔: {endpoint['interval_minutes']}分钟")
    
    def get_endpoint_interval(self, endpoint):
        """
        获取端点的检查间隔时间
        
        Args:
            endpoint: 端点配置或端点名称
            
        Returns:
            int: 检查间隔时间（分钟）
        """
        if isinstance(endpoint, dict):
            return endpoint.get("interval_minutes", self.default_interval)
        elif isinstance(endpoint, str):
            # 通过名称查找端点
            for ep in self.endpoints:
                if ep["name"] == endpoint:
                    return ep.get("interval_minutes", self.default_interval)
        return self.default_interval
    
    def check_service(self, endpoint):
        """
        检查单个服务状态
        
        Args:
            endpoint: 服务端点配置
            
        Returns:
            (bool, str): (是否正常, 详细信息)
        """
        name = endpoint["name"]
        url = endpoint["url"]
        method = endpoint.get("method", "GET").upper()
        expected_status = endpoint.get("expected_status", 200)
        expected_content = endpoint.get("expected_content")
        headers = endpoint.get("headers", {})
        body = endpoint.get("body")
        
        start_time = time.time()
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body if isinstance(body, dict) else None, 
                                         data=body if not isinstance(body, dict) else None, timeout=self.timeout)
            else:
                return False, f"不支持的请求方法: {method}"
                
            response_time = time.time() - start_time
            
            # 检查状态码
            status_ok = response.status_code == expected_status
            
            # 检查返回内容
            content_ok = True
            if expected_content and expected_content not in response.text:
                content_ok = False
            
            if status_ok and content_ok:
                return True, f"服务正常 ({response.status_code}, {response_time:.2f}s)"
            else:
                fail_reason = []
                if not status_ok:
                    fail_reason.append(f"状态码 {response.status_code} (预期 {expected_status})")
                if not content_ok:
                    fail_reason.append("返回内容不符合预期")
                
                return False, f"服务异常: {', '.join(fail_reason)}"
                
        except requests.RequestException as e:
            return False, f"服务请求异常: {str(e)}"
    
    def check_endpoint_by_name(self, name):
        """
        通过名称检查指定的端点
        
        Args:
            name: 端点名称
            
        Returns:
            (bool, str): (是否正常, 详细信息) 或 (False, "端点不存在")
        """
        for endpoint in self.endpoints:
            if endpoint["name"] == name:
                return self.check_service(endpoint)
        return False, "端点不存在"
    
    def run_checks(self):
        """运行所有服务检查"""
        if not self.config["enabled"]:
            logger.info("服务检查功能已禁用")
            return
        
        logger.info("开始服务状态检查...")
        check_time = datetime.now()
        
        for endpoint in self.endpoints:
            name = endpoint["name"]
            url = endpoint["url"]
            method = endpoint.get("method", "GET")
            
            logger.info(f"检查服务: {name} ({method} {url})")
            is_ok, details = self.check_service(endpoint)
            
            # 获取该服务的历史状态
            previous_status = self.status_history.get(name, {}).get("is_ok")
            
            # 更新状态历史
            self.status_history[name] = {
                "is_ok": is_ok,
                "details": details,
                "last_check": check_time
            }
            
            # 服务状态变化或服务出错时发送通知
            if previous_status is not None and previous_status != is_ok:
                status_change = "恢复正常" if is_ok else "变为异常"
                message = f"服务 {name} ({method} {url}) {status_change}\n详情: {details}"
                level = "info" if is_ok else "error"
                notifier.send_notification(f"服务状态变化: {name}", message, level)
            elif previous_status is None and not is_ok:
                # 首次检查就发现服务异常时发送通知
                message = f"服务 {name} ({method} {url}) 异常\n详情: {details}"
                notifier.send_notification(f"服务异常: {name}", message, "error")
            
            logger.info(f"服务 {name} 检查结果: {'正常' if is_ok else '异常'} - {details}")
        
        logger.info("服务状态检查完成")
    
    def get_status_summary(self):
        """获取所有服务的状态摘要"""
        if not self.status_history:
            return "无服务检查记录"
        
        summary = []
        for name, status in self.status_history.items():
            state = "正常" if status["is_ok"] else "异常"
            last_check = status["last_check"].strftime("%Y-%m-%d %H:%M:%S")
            summary.append(f"{name}: {state} (上次检查: {last_check})")
        
        return "\n".join(summary)


# 创建服务检查实例
service_checker = ServiceChecker() 