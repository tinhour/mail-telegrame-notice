import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import time

from app.config.settings import CONFIG
from app.services.service_check import service_checker
from app.services.notifier import notifier

logger = logging.getLogger(__name__)

class TaskScheduler:
    """任务调度器，负责定时执行服务检查任务"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(
            executors={
                'default': ThreadPoolExecutor(20)
            },
            job_defaults={
                'coalesce': False,
                'max_instances': 3
            }
        )
        self.service_check_interval = CONFIG["service_checks"]["interval_minutes"]
        self.jobs = []
        self.endpoint_jobs = {}  # 存储端点检查任务 {endpoint_name: job}
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            # 添加服务检查任务
            if CONFIG["service_checks"]["enabled"]:
                self._add_service_check_jobs()
            
            # 启动调度器
            self.scheduler.start()
            logger.info("任务调度器已启动")
            
            # 发送启动通知
            self._send_startup_notification()
    
    def _add_service_check_jobs(self):
        """添加服务检查任务"""
        # 清理现有任务
        for job_id in list(self.endpoint_jobs.keys()):
            job = self.endpoint_jobs.pop(job_id)
            if job in self.jobs:
                self.jobs.remove(job)
        
        # 为每个端点创建单独的任务
        for endpoint in service_checker.endpoints:
            self._add_endpoint_check_job(endpoint)
        
        logger.info(f"已添加 {len(service_checker.endpoints)} 个服务检查任务")
    
    def _add_endpoint_check_job(self, endpoint):
        """为单个端点添加检查任务"""
        endpoint_name = endpoint["name"]
        interval = service_checker.get_endpoint_interval(endpoint)
        
        # 创建指定端点检查的闭包函数
        def check_endpoint_wrapper():
            logger.info(f"执行端点检查: {endpoint_name}")
            try:
                for ep in service_checker.endpoints:
                    if ep["name"] == endpoint_name:
                        is_ok, details = service_checker.check_service(ep)
                        return
                logger.warning(f"找不到端点 {endpoint_name} 的配置")
            except Exception as e:
                logger.error(f"端点检查异常: {str(e)}")
        
        # 添加到调度器
        job_id = f"service_check_{endpoint_name}"
        job = self.scheduler.add_job(
            check_endpoint_wrapper,
            IntervalTrigger(minutes=interval),
            id=job_id,
            name=f"服务检查: {endpoint_name}",
            replace_existing=True
        )
        
        # 记录任务信息
        self.jobs.append(job)
        self.endpoint_jobs[endpoint_name] = job
        logger.info(f"已添加端点检查任务: {endpoint_name}, 间隔时间: {interval}分钟")
    
    def _send_startup_notification(self):
        """发送启动通知"""
        subject = "监控服务已启动"
        message = "监控和通知服务已成功启动，开始执行定时监控任务。\n\n"
        
        if CONFIG["service_checks"]["enabled"]:
            endpoints_count = len(service_checker.endpoints)
            message += f"服务检查: 已启用 ({endpoints_count} 个端点)\n"
            
            # 列出所有端点及其检查间隔
            if endpoints_count > 0:
                message += "检查端点列表:\n"
                for endpoint in service_checker.endpoints:
                    interval = service_checker.get_endpoint_interval(endpoint)
                    message += f"- {endpoint['name']}: 每 {interval} 分钟检查一次\n"
            
            message += "\n"
        else:
            message += "服务检查: 已禁用\n\n"
        
        message += "系统资源监控: 已禁用\n\n"
        message += "数据库连接监控: 已禁用\n"
        
        # 发送通知
        notifier.send_notification(subject, message, "info")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("任务调度器已停止")
    
    def add_scheduled_task(self, func, minutes, job_id, job_name):
        """添加自定义定时任务"""
        job = self.scheduler.add_job(
            func,
            IntervalTrigger(minutes=minutes),
            id=job_id,
            name=job_name,
            replace_existing=True
        )
        self.jobs.append(job)
        logger.info(f"已添加自定义任务: {job_name}，间隔时间: {minutes}分钟")
        return job
    
    def update_endpoint_interval(self, endpoint_name, interval_minutes):
        """
        更新端点检查间隔时间
        
        Args:
            endpoint_name: 端点名称
            interval_minutes: 新的间隔时间（分钟）
            
        Returns:
            bool: 是否更新成功
        """
        found = False
        
        # 更新服务检查器中的端点配置
        for endpoint in service_checker.endpoints:
            if endpoint["name"] == endpoint_name:
                endpoint["interval_minutes"] = interval_minutes
                found = True
                break
        
        # 如果找到了端点，更新调度任务
        if found and endpoint_name in self.endpoint_jobs:
            # 先删除旧任务
            old_job = self.endpoint_jobs[endpoint_name]
            if old_job in self.jobs:
                self.jobs.remove(old_job)
            self.scheduler.remove_job(old_job.id)
            
            # 为该端点重新添加新间隔的任务
            for endpoint in service_checker.endpoints:
                if endpoint["name"] == endpoint_name:
                    self._add_endpoint_check_job(endpoint)
                    break
                    
            logger.info(f"已更新端点检查间隔: {endpoint_name}, 新间隔: {interval_minutes}分钟")
            return True
        
        logger.warning(f"找不到端点: {endpoint_name}，无法更新间隔")
        return False
    
    def list_jobs(self):
        """获取当前的调度任务列表"""
        job_list = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else '未调度'
            job_list.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run
            })
        return job_list
    
    def update_endpoint_job(self, endpoint_name, updated_endpoint):
        """
        更新端点任务配置
        
        Args:
            endpoint_name: 端点名称
            updated_endpoint: 更新后的端点配置
            
        Returns:
            bool: 是否更新成功
        """
        # 如果调度器没有运行，直接返回成功
        if not self.scheduler.running:
            logger.info(f"调度器未运行，无需更新端点任务: {endpoint_name}")
            return True
            
        # 如果存在旧任务，先移除
        if endpoint_name in self.endpoint_jobs:
            old_job = self.endpoint_jobs[endpoint_name]
            if old_job in self.jobs:
                self.jobs.remove(old_job)
            self.scheduler.remove_job(old_job.id)
            logger.info(f"已移除旧的端点任务: {endpoint_name}")
        
        # 添加新的任务
        try:
            self._add_endpoint_check_job(updated_endpoint)
            logger.info(f"已更新端点任务: {endpoint_name}")
            return True
        except Exception as e:
            logger.error(f"更新端点任务失败: {endpoint_name}, 错误: {str(e)}")
            return False
    
    def remove_endpoint_job(self, endpoint_name):
        """
        移除端点任务
        
        Args:
            endpoint_name: 端点名称
            
        Returns:
            bool: 是否移除成功
        """
        # 如果调度器没有运行，直接返回成功
        if not self.scheduler.running:
            logger.info(f"调度器未运行，无需移除端点任务: {endpoint_name}")
            return True
            
        # 如果存在任务，移除它
        if endpoint_name in self.endpoint_jobs:
            try:
                old_job = self.endpoint_jobs[endpoint_name]
                if old_job in self.jobs:
                    self.jobs.remove(old_job)
                self.scheduler.remove_job(old_job.id)
                del self.endpoint_jobs[endpoint_name]
                logger.info(f"已移除端点任务: {endpoint_name}")
                return True
            except Exception as e:
                logger.error(f"移除端点任务失败: {endpoint_name}, 错误: {str(e)}")
                return False
        else:
            logger.warning(f"找不到端点任务: {endpoint_name}")
            return False


# 创建任务调度器实例
task_scheduler = TaskScheduler() 