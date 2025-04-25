import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.utils.config_manager import ConfigManager
import os

logger = logging.getLogger(__name__)

# 创建Blueprint
web_bp = Blueprint('web', __name__, template_folder='templates')

# 初始化配置管理器
config_manager = ConfigManager(os.getenv('CONFIG_DIR', './config'))

@web_bp.route('/')
def index():
    """主页面，重定向到配置页面"""
    return redirect(url_for('web.config_page'))

@web_bp.route('/config')
def config_page():
    """配置页面"""
    return render_template('config.html')

@web_bp.route('/config/new', methods=['GET'])
def config_new():
    """新版配置界面"""
    return render_template('config_new.html')

@web_bp.route('/endpoints')
def endpoints_page():
    """端点管理页面"""
    return render_template('endpoints.html')

# API路由 - 获取配置
@web_bp.route('/api/config/general', methods=['GET'])
def get_general_config():
    """获取常规设置配置"""
    try:
        return jsonify(config_manager.get_general_config())
    except Exception as e:
        logger.error(f"获取常规设置失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@web_bp.route('/api/config/notifications', methods=['GET'])
def get_notifications_config():
    """获取通知设置配置"""
    try:
        return jsonify(config_manager.get_notifications_config())
    except Exception as e:
        logger.error(f"获取通知设置失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@web_bp.route('/api/config/email', methods=['GET'])
def get_email_config():
    """获取邮件通知配置"""
    try:
        return jsonify(config_manager.get_email_config())
    except Exception as e:
        logger.error(f"获取邮件设置失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@web_bp.route('/api/config/webhook', methods=['GET'])
def get_webhook_config():
    """获取Webhook配置"""
    try:
        return jsonify(config_manager.get_webhook_config())
    except Exception as e:
        logger.error(f"获取Webhook设置失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@web_bp.route('/api/config/telegram', methods=['GET'])
def get_telegram_config():
    """获取Telegram通知配置"""
    try:
        config = config_manager.get_config()
        telegram_config = config.get('notifications', {}).get('telegram', {})
        return jsonify({
            'enabled': telegram_config.get('enabled', False),
            'token': telegram_config.get('token', ''),
            'chat_ids': telegram_config.get('chat_ids', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_bp.route('/api/config/service_checks', methods=['GET'])
def get_service_checks_config():
    """获取服务检查配置"""
    return jsonify(config_manager.get_service_checks_config())

@web_bp.route('/api/endpoints', methods=['GET'])
def get_endpoints():
    """获取服务检查端点列表"""
    return jsonify({"endpoints": config_manager.get_endpoints()})

# API路由 - 更新配置
@web_bp.route('/api/config/email', methods=['POST'])
def update_email_config():
    """更新邮件通知配置"""
    data = request.json
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400
    
    # 处理布尔值
    if "enabled" in data:
        data["enabled"] = data["enabled"] in [True, "true", "True", 1]
    
    # 处理端口
    if "smtp_port" in data and isinstance(data["smtp_port"], str):
        try:
            data["smtp_port"] = int(data["smtp_port"])
        except ValueError:
            return jsonify({"error": "SMTP端口必须是整数"}), 400
    
    success = config_manager.update_email_config(data)
    if success:
        # 保存配置
        if config_manager.save_config():
            return jsonify({"status": "success", "message": "邮件通知配置已更新"})
        else:
            return jsonify({"error": "保存配置失败"}), 500
    else:
        return jsonify({"error": "更新邮件配置失败"}), 500

@web_bp.route('/api/config/telegram', methods=['POST'])
def update_telegram_config():
    """更新Telegram通知配置"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        # 处理聊天ID列表
        if 'chat_ids' in data and isinstance(data['chat_ids'], str):
            data['chat_ids'] = [id.strip() for id in data['chat_ids'].split('\n') if id.strip()]

        # 更新配置
        success = config_manager.update_section('telegram', data)
        if success:
            return jsonify({'status': 'success', 'message': 'Telegram配置已更新'})
        else:
            return jsonify({'error': '更新Telegram配置失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_bp.route('/api/config/service_checks', methods=['POST'])
def update_service_checks_config():
    """更新服务检查配置"""
    data = request.json
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400
    
    # 处理布尔值
    if "enabled" in data:
        data["enabled"] = data["enabled"] in [True, "true", "True", 1]
    
    # 处理间隔时间
    if "interval_minutes" in data and isinstance(data["interval_minutes"], str):
        try:
            data["interval_minutes"] = int(data["interval_minutes"])
        except ValueError:
            return jsonify({"error": "检查间隔必须是整数"}), 400
    
    success = config_manager.update_service_checks_config(data)
    if success:
        # 保存配置
        if config_manager.save_config():
            return jsonify({"status": "success", "message": "服务检查配置已更新"})
        else:
            return jsonify({"error": "保存配置失败"}), 500
    else:
        return jsonify({"error": "更新服务检查配置失败"}), 500

@web_bp.route('/api/endpoints', methods=['POST'])
def add_endpoint():
    """添加服务检查端点"""
    data = request.json
    if not data or "name" not in data or "url" not in data:
        return jsonify({"error": "请提供端点名称和URL"}), 400
    
    # 处理预期状态码
    if "expected_status" in data and isinstance(data["expected_status"], str):
        try:
            data["expected_status"] = int(data["expected_status"])
        except ValueError:
            return jsonify({"error": "预期状态码必须是整数"}), 400
    
    # 处理检查间隔
    if "interval_minutes" in data and isinstance(data["interval_minutes"], str):
        try:
            data["interval_minutes"] = int(data["interval_minutes"])
        except ValueError:
            return jsonify({"error": "检查间隔必须是整数"}), 400
    
    success = config_manager.add_endpoint(data)
    if success:
        # 保存配置
        if config_manager.save_config():
            return jsonify({"status": "success", "message": f"端点已添加: {data['name']}"})
        else:
            return jsonify({"error": "保存配置失败"}), 500
    else:
        return jsonify({"error": f"端点已存在: {data['name']}"}), 409

@web_bp.route('/api/endpoints/<endpoint_name>', methods=['PUT'])
def update_endpoint(endpoint_name):
    """更新服务检查端点"""
    data = request.json
    if not data or "name" not in data or "url" not in data:
        return jsonify({"error": "请提供端点名称和URL"}), 400
    
    # 处理预期状态码
    if "expected_status" in data and isinstance(data["expected_status"], str):
        try:
            data["expected_status"] = int(data["expected_status"])
        except ValueError:
            return jsonify({"error": "预期状态码必须是整数"}), 400
    
    # 处理检查间隔
    if "interval_minutes" in data and isinstance(data["interval_minutes"], str):
        try:
            data["interval_minutes"] = int(data["interval_minutes"])
        except ValueError:
            return jsonify({"error": "检查间隔必须是整数"}), 400
    
    success = config_manager.update_endpoint(endpoint_name, data)
    if success:
        # 保存配置
        if config_manager.save_config():
            return jsonify({"status": "success", "message": f"端点已更新: {data['name']}"})
        else:
            return jsonify({"error": "保存配置失败"}), 500
    else:
        return jsonify({"error": f"找不到端点: {endpoint_name}"}), 404

@web_bp.route('/api/endpoints/<endpoint_name>', methods=['DELETE'])
def delete_endpoint(endpoint_name):
    """删除服务检查端点"""
    success = config_manager.delete_endpoint(endpoint_name)
    if success:
        # 保存配置
        if config_manager.save_config():
            return jsonify({"status": "success", "message": f"端点已删除: {endpoint_name}"})
        else:
            return jsonify({"error": "保存配置失败"}), 500
    else:
        return jsonify({"error": f"找不到端点: {endpoint_name}"}), 404

@web_bp.route('/api/notifications/test', methods=['POST'])
def test_notification():
    """发送测试通知"""
    try:
        # 发送测试通知
        subject = "测试通知"
        message = "这是一条来自系统的测试通知，用于验证通知功能是否正常。"
        level = "info"
        
        # 调用通知服务发送通知
        from app.services.notifier import notifier
        success = notifier.send_notification(subject, message, level)
        
        if success:
            return jsonify({"success": True, "message": "测试通知已发送"}), 200
        else:
            return jsonify({"success": False, "message": "发送测试通知失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"发送测试通知时出错: {str(e)}"}), 500 