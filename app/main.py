#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import argparse
import time
import importlib
from flask import Flask, jsonify, request

# 导入配置和核心模块
from app.config.settings import CONFIG, load_config
# 有条件地导入数据库模块
try:
    from app.core.db import init_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logging.warning("数据库模块不可用，将只从配置文件读取配置")

from app.core.scheduler import task_scheduler
from app.services.notifier import notifier
from app.services.service_check import service_checker
from app.services.system_monitor import system_monitor

# 配置日志
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok"}), 200

@app.route('/api/status', methods=['GET'])
def status():
    """获取系统状态信息"""
    # 获取服务检查状态
    service_status = service_checker.get_status_summary()
    
    # 获取系统资源状态
    system_status = system_monitor.get_system_status()
    
    # 获取调度器任务
    scheduler_jobs = task_scheduler.list_jobs()
    
    return jsonify({
        "status": "运行中",
        "version": "0.1.0",
        "services": service_status,
        "system": system_status,
        "scheduled_jobs": scheduler_jobs
    })

@app.route('/api/endpoints', methods=['GET', 'POST'])
def manage_endpoints():
    """管理服务检查端点"""
    if request.method == 'GET':
        # 返回当前的端点列表
        return jsonify(service_checker.endpoints)
    elif request.method == 'POST':
        # 添加新端点
        data = request.json
        if not data:
            return jsonify({"error": "请提供有效的端点配置"}), 400
            
        required_fields = ['name', 'url']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"缺少必要字段: {', '.join(missing_fields)}"}), 400
        
        # 添加端点
        service_checker.add_endpoint(
            name=data['name'],
            url=data['url'],
            expected_status=data.get('expected_status', 200),
            expected_content=data.get('expected_content'),
            headers=data.get('headers'),
            method=data.get('method', 'GET'),
            body=data.get('body'),
            interval_minutes=data.get('interval_minutes'),
            json_check=data.get('json_check')
        )
        
        # 如果调度器已启动，为新端点添加任务
        if task_scheduler.scheduler.running:
            for endpoint in service_checker.endpoints:
                if endpoint["name"] == data['name']:
                    task_scheduler._add_endpoint_check_job(endpoint)
                    break
        
        return jsonify({"status": "success", "message": f"已添加端点: {data['name']}"}), 201

@app.route('/api/endpoints/<endpoint_name>/interval', methods=['PUT'])
def update_endpoint_interval(endpoint_name):
    """更新端点的检查间隔时间"""
    data = request.json
    if not data or 'interval_minutes' not in data:
        return jsonify({"error": "请提供有效的间隔时间"}), 400
    
    try:
        interval = int(data['interval_minutes'])
        if interval <= 0:
            return jsonify({"error": "间隔时间必须大于0"}), 400
    except ValueError:
        return jsonify({"error": "间隔时间必须是整数"}), 400
    
    success = task_scheduler.update_endpoint_interval(endpoint_name, interval)
    
    if success:
        return jsonify({
            "status": "success", 
            "message": f"已更新端点检查间隔: {endpoint_name}, 新间隔: {interval}分钟"
        })
    else:
        return jsonify({"error": f"找不到端点: {endpoint_name}"}), 404

@app.route('/api/notify', methods=['POST'])
def send_notification():
    """发送测试通知"""
    data = request.json
    if not data:
        return jsonify({"error": "请提供通知内容"}), 400
        
    subject = data.get('subject', '测试通知')
    message = data.get('message', '这是一条测试通知消息')
    level = data.get('level', 'info')
    
    success = notifier.send_notification(subject, message, level)
    
    if success:
        return jsonify({"status": "success", "message": "通知已发送"}), 200
    else:
        return jsonify({"error": "通知发送失败"}), 500

def setup_services():
    """初始化所有服务"""
    try:
        global CONFIG
        # 初始化数据库（如果可用）
        db_monitoring_enabled = False
        if DB_AVAILABLE:
            try:
                init_db()
                logger.info("数据库初始化完成")
                db_monitoring_enabled = True
            except Exception as e:
                logger.error(f"数据库初始化失败: {str(e)}")
                logger.warning("将使用配置文件代替数据库")
                # 重新加载配置（跳过数据库）
                CONFIG = load_config(skip_db_settings=True)
        else:
            logger.info("数据库模块不可用，跳过数据库初始化")
            # 确保从环境变量和配置文件重新加载配置（跳过数据库）
            try:
                CONFIG = load_config(skip_db_settings=True)
                logger.info("从环境变量和配置文件加载配置完成")
            except Exception as e:
                logger.error(f"从配置文件加载配置失败: {str(e)}")
        
        # 加载服务端点配置
        if "endpoints" in CONFIG["service_checks"]:
            for endpoint in CONFIG["service_checks"]["endpoints"]:
                service_checker.add_endpoint(
                    name=endpoint["name"],
                    url=endpoint["url"],
                    expected_status=endpoint.get("expected_status", 200),
                    expected_content=endpoint.get("expected_content"),
                    headers=endpoint.get("headers"),
                    method=endpoint.get("method", "GET"),
                    body=endpoint.get("body"),
                    interval_minutes=endpoint.get("interval_minutes"),
                    json_check=endpoint.get("json_check")
                )
        
        # 启动调度器
        task_scheduler.start(db_monitoring_enabled=db_monitoring_enabled)
        
        logger.info("所有服务初始化完成")
        return True
    except Exception as e:
        logger.error(f"服务初始化失败: {str(e)}")
        return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='消息通知和服务监控系统')
    parser.add_argument('--host', default='0.0.0.0', help='监听主机地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='开启调试模式')
    parser.add_argument('--config', help='配置文件路径')
    
    return parser.parse_args()

def main():
    """主程序入口点"""
    args = parse_args()
    
    # 设置配置文件路径
    if args.config:
        os.environ["CONFIG_FILE"] = args.config
    
    # 初始化服务
    if not setup_services():
        sys.exit(1)
    
    # 启动Web服务
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main() 