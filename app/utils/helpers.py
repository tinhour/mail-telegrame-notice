import os
import time
import yaml
import socket
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def save_yaml_config(config_data, file_path):
    """
    将配置数据保存为YAML文件
    
    Args:
        config_data: 要保存的配置数据
        file_path: 保存路径
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"配置已保存到: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        return False

def format_time_delta(seconds):
    """
    将秒数格式化为可读的时间差
    
    Args:
        seconds: 秒数
    """
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{seconds // 60}分钟 {seconds % 60}秒"
    elif seconds < 86400:
        return f"{seconds // 3600}小时 {(seconds % 3600) // 60}分钟"
    else:
        return f"{seconds // 86400}天 {(seconds % 86400) // 3600}小时"

def is_port_open(host, port, timeout=2):
    """
    检查指定主机的端口是否开放
    
    Args:
        host: 主机名或IP地址
        port: 端口号
        timeout: 超时时间（秒）
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"检查端口时出错: {str(e)}")
        return False

def retry_function(func, max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
    """
    重试函数，自动在失败时重试
    
    Args:
        func: 要重试的函数
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间的倍增因子
        exceptions: 捕获的异常类型
        
    Returns:
        函数的返回值或引发最后一次异常
    """
    retries = 0
    current_delay = delay
    
    while retries < max_retries:
        try:
            return func()
        except exceptions as e:
            retries += 1
            if retries >= max_retries:
                logger.error(f"重试失败，达到最大重试次数: {max_retries}")
                raise e
            
            logger.warning(f"操作失败，将在 {current_delay}秒 后重试 ({retries}/{max_retries})")
            time.sleep(current_delay)
            current_delay *= backoff

def parse_size_string(size_str):
    """
    解析大小字符串，如 '5MB', '1.5GB'
    
    Args:
        size_str: 大小字符串
        
    Returns:
        字节数
    """
    size_str = size_str.strip().upper()
    if not size_str:
        return 0
    
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024
    }
    
    # 查找单位
    unit = 'B'
    for suffix in units.keys():
        if size_str.endswith(suffix):
            unit = suffix
            size_str = size_str[:-len(suffix)].strip()
            break
    
    try:
        size_value = float(size_str)
        return int(size_value * units[unit])
    except ValueError:
        logger.error(f"无法解析大小字符串: {size_str}")
        return 0

def generate_date_range(start_date, end_date=None, days=None):
    """
    生成日期范围
    
    Args:
        start_date: 开始日期（datetime对象或字符串'YYYY-MM-DD'）
        end_date: 结束日期（datetime对象或字符串'YYYY-MM-DD'）
        days: 如果提供，则忽略end_date，生成start_date后days天的日期
        
    Returns:
        日期列表
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    
    if end_date is None and days is not None:
        end_date = start_date + timedelta(days=days)
    elif isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    date_list = []
    current_date = start_date
    
    while current_date <= end_date:
        date_list.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    return date_list 