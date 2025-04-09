import logging
import psutil
import platform
import os
from datetime import datetime

from app.config.settings import CONFIG
from app.services.notifier import notifier

logger = logging.getLogger(__name__)

class SystemMonitor:
    """系统资源监控器，监控CPU、内存和磁盘使用情况"""
    
    def __init__(self):
        self.config = CONFIG["system_monitoring"]
        self.thresholds = self.config["thresholds"]
        self.last_notification_time = {}  # 上次通知时间记录
        self.notification_cooldown = 1800  # 通知冷却时间（秒）
    
    def get_system_info(self):
        """获取系统基本信息"""
        return {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
    
    def get_cpu_usage(self):
        """获取CPU使用率"""
        cpu_percent = psutil.cpu_percent(interval=1)
        is_overload = cpu_percent >= self.thresholds["cpu_percent"]
        return {
            "percent": cpu_percent,
            "count": psutil.cpu_count(),
            "is_overload": is_overload
        }
    
    def get_memory_usage(self):
        """获取内存使用情况"""
        memory = psutil.virtual_memory()
        is_overload = memory.percent >= self.thresholds["memory_percent"]
        return {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "is_overload": is_overload
        }
    
    def get_disk_usage(self):
        """获取磁盘使用情况"""
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                is_overload = usage.percent >= self.thresholds["disk_percent"]
                partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                    "is_overload": is_overload
                })
            except PermissionError:
                # 某些分区可能无法访问
                continue
        return partitions
    
    def format_bytes(self, bytes_value):
        """将字节数格式化为可读形式"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def check_system_resources(self):
        """检查系统资源使用情况"""
        if not self.config["enabled"]:
            logger.info("系统资源监控功能已禁用")
            return
        
        logger.info("开始检查系统资源使用情况...")
        now = datetime.now()
        
        # 检查CPU使用率
        cpu_info = self.get_cpu_usage()
        if cpu_info["is_overload"]:
            self._notify_overload(
                "CPU", 
                cpu_info["percent"], 
                self.thresholds["cpu_percent"],
                now
            )
        
        # 检查内存使用率
        memory_info = self.get_memory_usage()
        if memory_info["is_overload"]:
            self._notify_overload(
                "内存", 
                memory_info["percent"], 
                self.thresholds["memory_percent"],
                now
            )
        
        # 检查磁盘使用率
        disk_info = self.get_disk_usage()
        for partition in disk_info:
            if partition["is_overload"]:
                self._notify_overload(
                    f"磁盘 ({partition['mountpoint']})", 
                    partition["percent"], 
                    self.thresholds["disk_percent"],
                    now
                )
        
        logger.info("系统资源检查完成")
    
    def _notify_overload(self, resource_type, current_value, threshold, now):
        """
        发送资源超载通知
        
        Args:
            resource_type: 资源类型名称
            current_value: 当前值
            threshold: 阈值
            now: 当前时间
        """
        # 检查通知冷却时间
        last_time = self.last_notification_time.get(resource_type)
        if last_time and (now - last_time).total_seconds() < self.notification_cooldown:
            logger.info(f"{resource_type}使用率超标，但在冷却期内，不发送通知")
            return
        
        # 更新最后通知时间
        self.last_notification_time[resource_type] = now
        
        # 获取系统信息
        sys_info = self.get_system_info()
        hostname = sys_info["hostname"]
        
        # 构建通知消息
        subject = f"系统资源警告: {resource_type}使用率超标"
        message = (
            f"主机: {hostname}\n"
            f"资源: {resource_type}\n"
            f"当前值: {current_value:.1f}%\n"
            f"阈值: {threshold:.1f}%\n"
            f"时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # 发送通知
        notifier.send_notification(subject, message, "warning")
        logger.warning(f"{resource_type}使用率超标: {current_value:.1f}% (阈值: {threshold:.1f}%)")
    
    def get_system_status(self):
        """获取完整的系统状态报告"""
        sys_info = self.get_system_info()
        cpu_info = self.get_cpu_usage()
        memory_info = self.get_memory_usage()
        disk_info = self.get_disk_usage()
        
        status = []
        
        # 系统信息
        status.append(f"主机名: {sys_info['hostname']}")
        status.append(f"系统: {sys_info['os']}")
        status.append("")
        
        # CPU信息
        status.append(f"CPU使用率: {cpu_info['percent']:.1f}% (阈值: {self.thresholds['cpu_percent']:.1f}%)")
        status.append(f"CPU核心数: {cpu_info['count']}")
        status.append("")
        
        # 内存信息
        status.append(f"内存使用率: {memory_info['percent']:.1f}% (阈值: {self.thresholds['memory_percent']:.1f}%)")
        status.append(f"总内存: {self.format_bytes(memory_info['total'])}")
        status.append(f"可用内存: {self.format_bytes(memory_info['available'])}")
        status.append("")
        
        # 磁盘信息
        status.append("磁盘使用情况:")
        for partition in disk_info:
            status.append(f"  {partition['mountpoint']} ({partition['device']}): {partition['percent']:.1f}% 已用 "
                          f"({self.format_bytes(partition['used'])}/{self.format_bytes(partition['total'])})")
        
        return "\n".join(status)


# 创建系统监控实例
system_monitor = SystemMonitor() 