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
        
    def add_endpoint(self, name, url, expected_status=200, expected_content=None, headers=None, 
                     method="GET", body=None, interval_minutes=None, json_check=None):
        """添加服务检查端点"""
        # 检查是否已存在同名端点
        for existing_endpoint in self.endpoints:
            if existing_endpoint["name"] == name:
                logger.info(f"端点已存在，跳过添加: {name}")
                return
                
        endpoint = {
            "name": name,
            "url": url,
            "expected_status": expected_status,
            "expected_content": expected_content,
            "headers": headers or {},
            "method": method.upper(),
            "body": body,
            "interval_minutes": interval_minutes or self.default_interval,
            "json_check": json_check
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

    def _check_json_path(self, json_data, path, expected_value):
        """
        检查JSON数据中指定路径的值是否匹配预期
        
        Args:
            json_data: JSON数据（字典）
            path: 数据路径，格式如 "result.stats[0].blockchain"
            expected_value: 预期值
            
        Returns:
            bool: 是否匹配
        """
        try:
            # 解析路径
            parts = path.split('.')
            current = json_data
            
            for part in parts:
                # 处理数组索引，如 stats[0]
                if '[' in part and ']' in part:
                    key, idx_str = part.split('[', 1)
                    idx = int(idx_str.split(']')[0])
                    current = current.get(key, [])[idx]
                else:
                    current = current.get(part)
                
                # 如果路径中断了，返回False
                if current is None:
                    logger.debug(f"JSON路径 {path} 中的部分 {part} 不存在")
                    return False
            
            # 比较最终值
            result = str(current) == str(expected_value)
            logger.debug(f"JSON检查: 路径={path}, 实际值={current}, 预期值={expected_value}, 结果={result}")
            return result
            
        except (KeyError, IndexError, AttributeError, TypeError) as e:
            logger.warning(f"JSON检查失败: {str(e)}")
            return False
    
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
        json_check = endpoint.get("json_check")
        
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
            
            # 检查返回内容（字符串匹配）
            content_ok = True
            if expected_content and expected_content not in response.text:
                content_ok = False
            
            # 检查JSON结构（如果配置了）
            json_ok = True
            if json_check and status_ok:
                try:
                    json_data = response.json()
                    json_ok = self._check_json_path(
                        json_data, 
                        json_check["path"], 
                        json_check["expected_value"]
                    )
                except json.JSONDecodeError:
                    logger.warning(f"服务 {name} 返回的不是有效的JSON数据")
                    json_ok = False
            
            # 最终检查结果
            check_ok = status_ok and content_ok and json_ok
            
            if check_ok:
                return True, f"服务正常 ({response.status_code}, {response_time:.2f}s)"
            else:
                fail_reason = []
                if not status_ok:
                    fail_reason.append(f"状态码 {response.status_code} (预期 {expected_status})")
                if not content_ok:
                    fail_reason.append("返回内容不符合预期")
                if not json_ok and json_check:
                    fail_reason.append(f"JSON字段检查失败: {json_check['path']}")
                
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
            url = endpoint.get("url", "未知URL")
            method = endpoint.get("method", "GET")
            
            logger.info(f"检查服务: {name} ({method} {url})")
            
            # 执行实际检查
            is_ok, details = self.check_service(endpoint)
            
            # 记录详细日志
            logger.info(f"服务 {name} 检查结果: is_ok={is_ok}, details={details}")
            
            # 获取历史状态
            previous_status = self.status_history.get(name, {}).get("is_ok")
            
            # 检测状态变化并发送通知
            if previous_status is not None:
                if previous_status != is_ok:
                    status_change = "恢复正常" if is_ok else "变为异常"
                    logger.info(f"检测到服务 {name} 状态变化: {status_change}")
                    
                    # 构建通知消息
                    message = f"服务 {name} ({method} {url}) {status_change}\n详情: {details}"
                    subject = f"服务{'已恢复' if is_ok else '异常'}: {name}"
                    level = "info" if is_ok else "error"
                    
                    # 发送通知
                    notifier.send_notification(subject, message, level)
            elif not is_ok:
                # 首次检查就发现异常，也发送通知
                logger.info(f"首次检查发现服务 {name} 异常")
                message = f"服务 {name} ({method} {url}) 异常\n详情: {details}"
                subject = f"服务异常: {name}"
                notifier.send_notification(subject, message, "error")
            
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

    def get_status_summary(self):
        """获取所有服务的状态摘要"""
        if not self.status_history:
            return "无服务检查记录"
        
        summary = []
        for name, status in self.status_history.items():
            if "is_ok" not in status:
                continue  # 跳过不完整的状态记录
                
            state = "正常" if status["is_ok"] else "异常"
            if "last_check" in status and status["last_check"]:
                try:
                    last_check = status["last_check"].strftime("%Y-%m-%d %H:%M:%S")
                except:
                    last_check = "未知时间"
            else:
                last_check = "未知时间"
                
            details = status.get("details", "")
            summary_line = f"{name}: {state} (上次检查: {last_check})"
            if details and not status["is_ok"]:
                summary_line += f", 详情: {details}"
                
            summary.append(summary_line)
        
        return "\n".join(summary)

# 创建服务检查实例
service_checker = ServiceChecker() 