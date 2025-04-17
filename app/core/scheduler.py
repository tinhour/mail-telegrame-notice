import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import time

from app.config.settings import CONFIG, DB_AVAILABLE
from app.services.service_check import service_checker
from app.services.system_monitor import system_monitor
from app.services.notifier import notifier

# 有条件地导入数据库监控模块
if DB_AVAILABLE:
    try:
        from app.services.db_monitor import db_monitor
        DB_MONITOR_AVAILABLE = True
    except ImportError:
        DB_MONITOR_AVAILABLE = False
        logging.warning("无法导入数据库监控模块")
else:
    DB_MONITOR_AVAILABLE = False
    logging.warning("数据库模块不可用，跳过导入数据库监控模块")

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
        self.db_monitoring_interval = 5  # 数据库监控间隔（分钟）
        self.jobs = []
        self.endpoint_jobs = {}  # 存储端点检查任务 {endpoint_name: job}
    
    def start(self, db_monitoring_enabled=True):
        """
        启动调度器
        
        Args:
            db_monitoring_enabled: 是否启用数据库监控，默认为True
        """
        if not self.scheduler.running:
            # 添加服务检查任务
            if CONFIG["service_checks"]["enabled"]:
                self._add_service_check_jobs()
            
            # 添加系统监控任务
            if CONFIG["system_monitoring"]["enabled"]:
                self._add_system_monitoring_job()
                
            # 添加数据库监控任务（如果启用）
            if db_monitoring_enabled and DB_MONITOR_AVAILABLE:
                self._add_db_monitoring_job()
            else:
                logger.info("数据库监控已禁用")
            
            # 启动调度器
            self.scheduler.start()
            logger.info("任务调度器已启动")
            
            # 发送启动通知
            self._send_startup_notification(db_monitoring_enabled and DB_MONITOR_AVAILABLE)
    
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

        # 创建通知状态字典，用于跟踪该端点的通知状态
        notification_status = {
            "last_status": None,  # 上次通知时的状态
            "notified": False,    # 是否已经发送过通知
            "last_notification_time": 0  # 上次通知时间戳
        }
        
        # 创建检查函数，只检查指定的端点
        def check_single_endpoint():
            logger.info(f"执行计划检查: {name} (间隔: {interval}分钟)")
            is_ok, details = service_checker.check_endpoint_by_name(name)
            logger.info(f"计划检查完成: {name}, 结果: {'正常' if is_ok else '异常'} - {details}")
            
            # 当前时间戳
            current_time = time.time()
            # 通知重发间隔（小时）
            notification_resend_hours = 3
            # 转换为秒
            notification_resend_interval = notification_resend_hours * 60 * 60
            
            # 决定是否需要发送通知
            should_notify = False
            
            # 初始状态判断
            if notification_status["last_status"] is None:
                # 首次检查：如果异常则发送通知
                should_notify = not is_ok
                notification_status["last_status"] = is_ok
            elif notification_status["last_status"] != is_ok:
                # 状态变化：始终发送通知
                should_notify = True
                notification_status["last_status"] = is_ok
                # 重置通知标志
                notification_status["notified"] = False
                notification_status["last_notification_time"] = current_time
            elif not is_ok:
                # 持续异常状态：检查是否已经过了重发间隔
                time_since_last = current_time - notification_status["last_notification_time"]
                logger.debug(f"服务 {name} 持续异常状态，距上次通知已过 {time_since_last/3600:.2f} 小时")
                
                if time_since_last >= notification_resend_interval:
                    # 已经过了重发间隔，重新发送通知
                    should_notify = True
                    notification_status["last_notification_time"] = current_time
                    logger.info(f"服务 {name} 仍然异常，触发定期重发通知")
            
            # 如果需要发送通知
            if should_notify:
                # 从端点中获取方法和URL信息
                endpoint_info = None
                for ep in service_checker.endpoints:
                    if ep["name"] == name:
                        endpoint_info = ep
                        break
                
                # 构建通知消息
                if endpoint_info:
                    method = endpoint_info.get("method", "GET")
                    url = endpoint_info.get("url", "未知URL")
                    if notification_status["last_status"] is not None and notification_status["last_status"] == is_ok and not is_ok:
                        # 持续异常状态
                        message = f"服务 {name} ({method} {url}) 持续异常\n详情: {details}"
                        subject = f"服务持续异常: {name}"
                    elif is_ok:
                        # 恢复正常
                        message = f"服务 {name} ({method} {url}) 已恢复正常\n详情: {details}"
                        subject = f"服务已恢复: {name}"
                    else:
                        # 变为异常
                        message = f"服务 {name} ({method} {url}) 变为异常\n详情: {details}"
                        subject = f"服务异常: {name}"
                else:
                    if notification_status["last_status"] is not None and notification_status["last_status"] == is_ok and not is_ok:
                        # 持续异常状态
                        message = f"服务 {name} 持续异常\n详情: {details}"
                        subject = f"服务持续异常: {name}"
                    elif is_ok:
                        # 恢复正常
                        message = f"服务 {name} 已恢复正常\n详情: {details}"
                        subject = f"服务已恢复: {name}"
                    else:
                        # 变为异常
                        message = f"服务 {name} 变为异常\n详情: {details}"
                        subject = f"服务异常: {name}"
                
                # 设置通知级别
                level = "info" if is_ok else "error"
                
                # 记录日志
                if not is_ok:
                    logger.warning(f"服务检查异常: {name}")
                else:
                    logger.info(f"服务已恢复正常: {name}")
                
                # 发送通知
                success = notifier.send_notification(subject, message, level)
                
                if success:
                    # 更新通知状态
                    notification_status["notified"] = True
                    logger.info(f"已发送{subject}")
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
    
    def _add_db_monitoring_job(self):
        """添加数据库监控任务"""
        if not DB_MONITOR_AVAILABLE:
            logger.warning("数据库监控模块不可用，无法添加数据库监控任务")
            return
            
        job = self.scheduler.add_job(
            db_monitor.check_connection,
            IntervalTrigger(minutes=self.db_monitoring_interval),
            id='db_monitoring',
            name='数据库连接监控',
            replace_existing=True
        )
        self.jobs.append(job)
        logger.info(f"已添加数据库连接监控任务，间隔时间: {self.db_monitoring_interval}分钟")
    
    def _send_startup_notification(self, db_monitoring_enabled=True):
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
            message += f"磁盘阈值: {CONFIG['system_monitoring']['thresholds']['disk_percent']}%\n\n"
        else:
            message += "系统资源监控: 已禁用\n\n"
            
        if db_monitoring_enabled and DB_MONITOR_AVAILABLE:
            message += "数据库连接监控: 已启用\n"
            message += f"监控间隔: {self.db_monitoring_interval} 分钟\n"
        else:
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
    
    def update_db_monitoring_interval(self, new_interval):
        """
        更新数据库监控间隔时间
        
        Args:
            new_interval: 新的检查间隔时间（分钟）
            
        Returns:
            bool: 是否更新成功
        """
        if not DB_MONITOR_AVAILABLE:
            logger.warning("数据库监控模块不可用，无法更新监控间隔")
            return False
            
        if new_interval <= 0:
            logger.error(f"无效的检查间隔: {new_interval}")
            return False
            
        self.db_monitoring_interval = new_interval
        
        # 更新调度任务
        self.remove_job('db_monitoring')
        self._add_db_monitoring_job()
        
        logger.info(f"已更新数据库监控间隔时间: {new_interval}分钟")
        return True
    
    def remove_job(self, job_id):
        """移除指定的任务"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"移除任务失败: {str(e)}")
            return False
    
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