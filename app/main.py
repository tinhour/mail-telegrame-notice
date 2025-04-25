#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import argparse
import time
import importlib
from flask import Flask, jsonify, request, render_template

# 导入配置和核心模块
from app.config.settings import CONFIG, load_config
from app.core.scheduler import task_scheduler
from app.services.notifier import notifier
from app.services.service_check import service_checker

# 导入应用工厂函数
from app import create_app

# 配置日志
logger = logging.getLogger(__name__)

# 创建Flask应用
app = create_app()

@app.route('/config/')
def config_new_direct():
    return render_template('config.html')

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok"}), 200

@app.route('/api/status', methods=['GET'])
def status():
    """获取系统状态信息"""
    try:
        # 获取服务检查状态
        service_status = service_checker.get_status_summary()
        
        # 获取调度器任务
        try:
            scheduler_jobs = task_scheduler.list_jobs()
        except Exception as e:
            logger.error(f"获取调度任务列表失败: {str(e)}")
            scheduler_jobs = []
        
        # 确保返回的数据可以被JSON序列化
        return jsonify({
            "status": "运行中",
            "version": "0.1.0",
            "services": service_status,
            "scheduled_jobs": scheduler_jobs
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"状态API出错: {str(e)}\n{error_trace}")
        return jsonify({
            "status": "错误",
            "error": f"获取状态信息失败: {str(e)}",
            "version": "0.1.0"
        }), 500

@app.route('/api/endpoints', methods=['GET', 'POST'])
def manage_endpoints():
    """管理服务检查端点"""
    if request.method == 'GET':
        # 返回所有端点
        endpoints = []
        for i, endpoint in enumerate(service_checker.endpoints):
            # 创建端点的可序列化副本
            endpoint_copy = dict(endpoint)
            # 添加ID字段，使用端点名称作为ID
            endpoint_copy['id'] = endpoint.get('name', str(i))
            # 排除不可序列化的字段
            if 'json_check' in endpoint_copy and isinstance(endpoint_copy['json_check'], dict):
                endpoint_copy['json_check'] = dict(endpoint_copy['json_check'])
            endpoints.append(endpoint_copy)
            
        # 直接返回端点数组，而不是包裹在对象中
        return jsonify(endpoints)
    
    # 添加新端点
    data = request.json
    if not data or 'name' not in data or 'url' not in data:
        return jsonify({"error": "请提供端点名称和URL"}), 400
    
    # 检查是否已存在同名端点
    for endpoint in service_checker.endpoints:
        if endpoint["name"] == data['name']:
            return jsonify({"error": f"端点已存在: {data['name']}"}), 409
    
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

@app.route('/api/endpoints/<endpoint_name>', methods=['GET', 'PUT', 'DELETE'])
def endpoint_operations(endpoint_name):
    """对单个端点进行操作"""
    # 查找指定的端点
    target_endpoint = None
    for endpoint in service_checker.endpoints:
        if endpoint["name"] == endpoint_name:
            target_endpoint = endpoint
            break
    
    # GET方法：获取端点详情
    if request.method == 'GET':
        if target_endpoint:
            # 创建可序列化的副本
            endpoint_copy = dict(target_endpoint)
            # 添加ID字段
            endpoint_copy['id'] = endpoint_name
            # 处理不可序列化的字段
            if 'json_check' in endpoint_copy and isinstance(endpoint_copy['json_check'], dict):
                endpoint_copy['json_check'] = dict(endpoint_copy['json_check'])
            
            return jsonify(endpoint_copy)
        else:
            return jsonify({"status": "error", "message": f"找不到端点: {endpoint_name}"}), 404
    
    # PUT方法：更新端点
    elif request.method == 'PUT':
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "请提供必要的端点信息"}), 400
        
        if target_endpoint:
            # 更新端点配置
            for key, value in data.items():
                if key in ['name', 'id']: # 名称作为标识符不能更改
                    continue
                target_endpoint[key] = value
            
            # 如果调度器已启动，更新任务
            if task_scheduler.scheduler.running:
                task_scheduler.update_endpoint_job(endpoint_name, target_endpoint)
            
            return jsonify({"status": "success", "message": f"已更新端点: {endpoint_name}"})
        else:
            return jsonify({"error": f"找不到端点: {endpoint_name}"}), 404
    
    # DELETE方法：删除端点
    elif request.method == 'DELETE':
        if target_endpoint:
            # 删除端点任务
            if task_scheduler.scheduler.running:
                task_scheduler.remove_endpoint_job(endpoint_name)
            
            # 从列表中删除端点
            service_checker.endpoints.remove(target_endpoint)
            
            return jsonify({"status": "success", "message": f"已删除端点: {endpoint_name}"})
        else:
            return jsonify({"error": f"找不到端点: {endpoint_name}"}), 404

def setup_services():
    """初始化所有服务"""
    try:
        global CONFIG
        
        logger.info("数据库功能和系统资源监控已禁用")
        # 确保从环境变量和配置文件加载配置
        try:
            CONFIG = load_config()
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
        task_scheduler.start()
        
        logger.info("所有服务初始化完成")
        return True
    except Exception as e:
        logger.error(f"服务初始化失败: {str(e)}")
        return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='消息通知和服务监控系统')
    parser.add_argument('--host', default='0.0.0.0', help='监听主机地址')
    parser.add_argument('--port', type=int, default=3003, help='监听端口')
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