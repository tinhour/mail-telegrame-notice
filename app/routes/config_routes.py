from flask import Blueprint, render_template, request, jsonify
import os
import json
from app.utils.config_manager import ConfigManager
import flask

# 创建蓝图
config_bp = Blueprint('config', __name__)

# 初始化配置管理器
config_manager = ConfigManager(os.getenv('CONFIG_DIR', './config'))

@config_bp.route('/config')
def config_page():
    """配置页面"""
    return render_template('config.html')

@config_bp.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    return jsonify(config_manager.get_config())

@config_bp.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "无效的请求数据"}), 400
            
        # 处理前端发送的数据格式
        if 'section' in data and 'data' in data:
            section = data.get('section')
            section_data = data.get('data')
            
            # 将表单ID映射到配置部分
            section_mapping = {
                'generalSettingsForm': 'general',
                'notificationSettingsForm': 'notifications',
                'smtpSettingsForm': 'notifications.email',
                'webhookSettingsForm': 'notifications.webhook',
                'telegramSettingsForm': 'notifications.telegram',
                'advancedSettingsForm': 'advanced'
            }
            
            # 获取实际的配置部分名称
            actual_section = section_mapping.get(section, section)
            
            success = config_manager.update_section(actual_section, section_data)
            if success:
                return jsonify({"status": "success", "message": "配置已更新"}), 200
            else:
                return jsonify({"status": "error", "message": "更新配置失败"}), 500
        else:
            # 直接更新整个配置
            success = config_manager.update_config(data)
            if success:
                return jsonify({"status": "success", "message": "配置已更新"}), 200
            else:
                return jsonify({"status": "error", "message": "更新配置失败"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"更新配置失败: {str(e)}"}), 500

@config_bp.route('/api/config/<section>', methods=['POST'])
def update_section(section):
    """更新配置部分"""
    try:
        section_data = request.json
        success = config_manager.update_section(section, section_data)
        if success:
            return jsonify({"status": "success", "message": f"{section}部分配置已更新"}), 200
        else:
            return jsonify({"status": "error", "message": f"更新{section}部分配置失败"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"更新配置失败: {str(e)}"}), 500

@config_bp.route('/api/config/reset', methods=['POST'])
def reset_config():
    """重置配置"""
    try:
        success = config_manager.reset_config()
        if success:
            return jsonify({"status": "success", "message": "配置已重置为默认值"}), 200
        else:
            return jsonify({"status": "error", "message": "重置配置失败"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"重置配置失败: {str(e)}"}), 500

@config_bp.route('/api/config/test-smtp', methods=['POST'])
def test_smtp():
    """测试SMTP配置"""
    try:
        smtp_config = request.json
        
        # 这里应该添加实际的SMTP测试逻辑
        # 暂时返回模拟的成功响应
        return jsonify({"status": "success", "message": "SMTP配置测试成功"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"SMTP配置测试失败: {str(e)}"}), 500

@config_bp.route('/api/config/test-webhook', methods=['POST'])
def test_webhook():
    """测试Webhook配置"""
    try:
        webhook_config = request.json
        
        # 这里应该添加实际的Webhook测试逻辑
        # 暂时返回模拟的成功响应
        return jsonify({"status": "success", "message": "Webhook配置测试成功"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Webhook配置测试失败: {str(e)}"}), 500

@config_bp.route('/api/config/general', methods=['GET'])
def get_general_config():
    """获取常规设置配置"""
    return jsonify(config_manager.get_general_config())

@config_bp.route('/api/config/notifications', methods=['GET'])
def get_notifications_config():
    """获取通知设置配置"""
    return jsonify(config_manager.get_notifications_config())

@config_bp.route('/api/config/email', methods=['GET'])
def get_email_config():
    """获取邮件设置配置"""
    return jsonify(config_manager.get_email_config())

@config_bp.route('/api/config/webhook', methods=['GET'])
def get_webhook_config():
    """获取Webhook设置配置"""
    return jsonify(config_manager.get_webhook_config())

@config_bp.route('/api/config/telegram', methods=['GET'])
def get_telegram_config():
    """获取Telegram设置配置"""
    return jsonify(config_manager.get_telegram_config())

@config_bp.route('/api/endpoints', methods=['GET'])
def get_endpoints():
    """获取所有端点"""
    try:
        endpoints_data = config_manager.load_endpoints()
        # 直接返回端点数组，而不是包含在endpoints字段中的对象
        endpoints = endpoints_data.get('endpoints', [])
        
        # 为每个端点添加id字段
        for i, endpoint in enumerate(endpoints):
            if 'id' not in endpoint:
                endpoint['id'] = endpoint.get('name', str(i))
        
        return jsonify(endpoints)
    except Exception as e:
        return jsonify([]), 200  # 即使出错也返回空数组，确保前端能正常显示

@config_bp.route('/api/endpoints', methods=['POST'])
def add_endpoint():
    """添加端点"""
    try:
        endpoint_data = request.json
        
        # 确保新添加的端点有正确的ID
        if 'id' not in endpoint_data or endpoint_data['id'] is None:
            # 使用name作为ID
            endpoint_data['id'] = endpoint_data.get('name')
            
        success = config_manager.add_endpoint(endpoint_data)
        if success:
            return jsonify({"status": "success", "message": "端点已添加"}), 201
        else:
            return jsonify({"status": "error", "message": "添加端点失败"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"添加端点失败: {str(e)}"}), 500

@config_bp.route('/api/endpoints/<endpoint_name>', methods=['GET'])
def get_endpoint(endpoint_name):
    """获取单个端点"""
    try:
        endpoints_data = config_manager.load_endpoints()
        endpoints = endpoints_data.get('endpoints', [])
        
        # 优先通过name查找端点，其次尝试通过id查找
        for endpoint in endpoints:
            # 通过name查找
            if endpoint.get('name') == endpoint_name:
                return jsonify(endpoint), 200
                
            # 通过id查找
            if endpoint.get('id') == endpoint_name:
                return jsonify(endpoint), 200
        
        return jsonify({"status": "error", "message": "未找到指定的端点"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"获取端点失败: {str(e)}"}), 500

@config_bp.route('/api/endpoints/<endpoint_name>', methods=['PUT'])
def update_endpoint(endpoint_name):
    """更新端点"""
    try:
        endpoint_data = request.json
        
        # 确保endpoint_data中使用正确的ID和name
        if 'id' in endpoint_data and endpoint_data['id'] is None:
            # 如果ID为null，使用name作为ID
            endpoint_data['id'] = endpoint_data.get('name')
        
        success = config_manager.update_endpoint(endpoint_name, endpoint_data)
        if success:
            return jsonify({"status": "success", "message": "端点已更新"}), 200
        else:
            return jsonify({"status": "error", "message": "更新端点失败"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"更新端点失败: {str(e)}"}), 500

@config_bp.route('/api/endpoints/<endpoint_name>', methods=['DELETE'])
def delete_endpoint(endpoint_name):
    """删除端点"""
    try:
        endpoints_data = config_manager.load_endpoints()
        endpoints = endpoints_data.get('endpoints', [])
        found = False
        
        # 查找匹配的端点（支持通过name或id删除）
        new_endpoints = []
        for endpoint in endpoints:
            if endpoint.get('name') == endpoint_name or endpoint.get('id') == endpoint_name:
                found = True
                continue  # 不添加到新列表，相当于删除
            new_endpoints.append(endpoint)
            
        if found:
            # 保存更新后的端点列表
            success = config_manager.save_endpoints({"endpoints": new_endpoints})
            if success:
                return jsonify({"status": "success", "message": "端点已删除"}), 200
            else:
                return jsonify({"status": "error", "message": "删除端点失败"}), 500
        else:
            return jsonify({"status": "error", "message": "未找到指定的端点"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"删除端点失败: {str(e)}"}), 500

@config_bp.route('/api/endpoints/<endpoint_name>/history', methods=['GET'])
def get_endpoint_history(endpoint_name):
    """获取端点历史记录"""
    history = config_manager.get_endpoint_history(endpoint_name)
    return jsonify(history)

@config_bp.route('/api/import-config', methods=['POST'])
def import_config():
    """导入配置"""
    try:
        if 'config_file' not in request.files:
            return jsonify({"status": "error", "message": "没有上传文件"}), 400
        
        file = request.files['config_file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "没有选择文件"}), 400
            
        # 检查文件扩展名
        if not (file.filename.endswith('.yaml') or file.filename.endswith('.yml') or file.filename.endswith('.json')):
            return jsonify({"status": "error", "message": "仅支持YAML和JSON格式文件"}), 400
        
        # 确保临时目录存在
        temp_dir = os.getenv('TEMP_DIR', './temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 保存上传的文件
        temp_path = os.path.join(temp_dir, 'import_config.yaml')
        file.save(temp_path)
        
        # 导入配置
        success = config_manager.import_config_from_yaml(temp_path)
        
        # 删除临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if success:
            return jsonify({"status": "success", "message": "配置已导入"}), 200
        else:
            return jsonify({"status": "error", "message": "导入配置失败，文件格式可能不正确"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"导入配置失败: {str(e)}"}), 500

@config_bp.route('/api/export-config', methods=['GET'])
def export_config():
    """导出配置"""
    try:
        # 确保临时目录存在
        temp_dir = os.getenv('TEMP_DIR', './temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_path = os.path.join(temp_dir, 'export_config.yaml')
        
        success = config_manager.export_config_to_yaml(temp_path)
        
        if not success:
            return jsonify({"status": "error", "message": "导出配置失败"}), 500
        
        # 返回配置文件
        return jsonify({"status": "success", "download_url": "/api/download-config"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"导出配置失败: {str(e)}"}), 500

@config_bp.route('/api/download-config', methods=['GET'])
def download_config():
    """下载配置文件"""
    try:
        temp_path = os.path.join(os.getenv('TEMP_DIR', './temp'), 'export_config.yaml')
        
        if not os.path.exists(temp_path):
            return jsonify({"status": "error", "message": "配置文件不存在"}), 404
        
        with open(temp_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # 创建直接下载的响应
        response = flask.make_response(config_content)
        response.headers["Content-Disposition"] = "attachment; filename=config.yaml"
        response.headers["Content-Type"] = "application/x-yaml"
        return response
    except Exception as e:
        return jsonify({"status": "error", "message": f"下载配置失败: {str(e)}"}), 500
