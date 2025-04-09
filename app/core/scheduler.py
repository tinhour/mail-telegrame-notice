import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from app.config.settings import CONFIG
from app.services.service_check import service_checker
from app.services.system_monitor import system_monitor
from app.services.notifier import notifier

logger = logging.getLogger(__name__)

class TaskScheduler:
    """任务调度器，负责定时执行系统监控和服务检查任务"""
    
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
        self.system_monitoring_interval = CONFIG["system_monitoring"]["interval_minutes"]
        self.jobs = []
        self.endpoint_jobs = {}  # 存储端点检查任务 {endpoint_name: job}
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            # 添加服务检查任务
            if CONFIG["service_checks"]["enabled"]:
                self._add_service_check_jobs()
            
            # 添加系统监控任务
            if CONFIG["system_monitoring"]["enabled"]:
                self._add_system_monitoring_job()
            
            # 启动调度器
            self.scheduler.start()
            logger.info("任务调度器已启动")
            
            # 发送启动通知
            self._send_startup_notification()
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("任务调度器已停止")
    
    def _add_service_check_jobs(self):
        """添加服务检查任务，为每个端点创建单独的任务"""
        # 清理旧任务
        for job_id in list(self.endpoint_jobs.keys()):
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            del self.endpoint_jobs[job_id]
        
        # 为每个端点创建检查任务
        for endpoint in service_checker.endpoints:
            self._add_endpoint_check_job(endpoint)
    
    def _add_endpoint_check_job(self, endpoint):
        """为单个端点添加检查任务"""
        name = endpoint["name"]
        interval = service_checker.get_endpoint_interval(endpoint)
        
        # 创建检查函数，只检查指定的端点
        def check_single_endpoint():
            logger.info(f"执行计划检查: {name} (间隔: {interval}分钟)")
            is_ok, details = service_checker.check_endpoint_by_name(name)
            logger.info(f"计划检查完成: {name}, 结果: {'正常' if is_ok else '异常'} - {details}")
        
        # 添加任务
        job_id = f"service_check_{name}"
        job = self.scheduler.add_job(
            check_single_endpoint,
            IntervalTrigger(minutes=interval),
            id=job_id,
            name=f'服务检查 - {name}',
            replace_existing=True
        )
        
        self.endpoint_jobs[job_id] = job
        self.jobs.append(job)
        logger.info(f"已添加服务检查任务: {name}, 间隔时间: {interval}分钟")
    
    def _add_system_monitoring_job(self):
        """添加系统监控任务"""
        job = self.scheduler.add_job(
            system_monitor.check_system_resources,
            IntervalTrigger(minutes=self.system_monitoring_interval),
            id='system_monitoring',
            name='系统资源监控',
            replace_existing=True
        )
        self.jobs.append(job)
        logger.info(f"已添加系统资源监控任务，间隔时间: {self.system_monitoring_interval}分钟")
    
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
        
        if CONFIG["system_monitoring"]["enabled"]:
            message += "系统资源监控: 已启用\n"
            message += f"监控间隔: {self.system_monitoring_interval} 分钟\n"
            message += f"CPU阈值: {CONFIG['system_monitoring']['thresholds']['cpu_percent']}%\n"
            message += f"内存阈值: {CONFIG['system_monitoring']['thresholds']['memory_percent']}%\n"
            message += f"磁盘阈值: {CONFIG['system_monitoring']['thresholds']['disk_percent']}%\n"
        else:
            message += "系统资源监控: 已禁用\n"
        
        # 发送通知
        notifier.send_notification(subject, message, "info")
    
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
    
    def remove_job(self, job_id):
        """移除指定的任务"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"移除任务失败: {str(e)}")
            return False
    
    def update_endpoint_interval(self, endpoint_name, new_interval):
        """
        更新端点的检查间隔时间
        
        Args:
            endpoint_name: 端点名称
            new_interval: 新的检查间隔时间（分钟）
            
        Returns:
            bool: 是否更新成功
        """
        # 查找端点
        endpoint = None
        for ep in service_checker.endpoints:
            if ep["name"] == endpoint_name:
                endpoint = ep
                break
        
        if not endpoint:
            logger.error(f"找不到端点: {endpoint_name}")
            return False
        
        # 更新端点配置
        endpoint["interval_minutes"] = new_interval
        
        # 更新调度任务
        job_id = f"service_check_{endpoint_name}"
        if job_id in self.endpoint_jobs:
            self.remove_job(job_id)
        
        self._add_endpoint_check_job(endpoint)
        logger.info(f"已更新端点检查间隔: {endpoint_name}, 新间隔: {new_interval}分钟")
        return True
    
    def list_jobs(self):
        """列出所有任务信息"""
        job_list = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "未调度"
            job_list.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run
            })
        return job_list


# 创建调度器实例
task_scheduler = TaskScheduler() 