import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, List, Union
import uuid

class ConfigManager:
    """配置文件管理器，负责从文件中读取和写入配置"""
    
    def __init__(self, config_dir: str = "./config"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件存储目录
        """
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 默认配置
        self.default_config = {
            "general": {
                "app_name": "EVM追踪服务",
                "logging_level": "info",
                "check_interval": 60
            },
            "notifications": {
                "email": {
                    "enabled": False,
                    "smtp_server": "",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "sender": "",
                    "recipients": [],
                    "use_tls": True
                },
                "webhook": {
                    "enabled": False,
                    "url": "",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "template": '{"text": "服务 {{endpoint.name}} 状态: {{status}}", "details": {"url": "{{endpoint.url}}", "message": "{{message}}"}}'
                },
                "telegram": {
                    "enabled": False,
                    "token": "",
                    "chat_ids": []
                },
                "notify_on_status": "error",
                "format": "text"
            }
        }
        
        # 加载配置文件
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        从文件加载配置，如果文件不存在则尝试从YAML加载，如果都没有则使用默认配置
        
        Returns:
            Dict: 配置字典
        """
        config_file = os.path.join(self.config_dir, "config.json")
        yaml_file = os.path.join(self.config_dir, "config.yaml")
        
        # 1. 尝试加载JSON配置
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.logger.info(f"从 {config_file} 加载配置")
                    return config
            except Exception as e:
                self.logger.error(f"加载JSON配置文件时出错: {e}")
        
        # 2. 尝试加载YAML配置
        if os.path.exists(yaml_file):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.logger.info(f"从 {yaml_file} 加载配置")
                    # 保存为JSON格式
                    self.save_config(config)
                    return config
            except Exception as e:
                self.logger.error(f"加载YAML配置文件时出错: {e}")
        
        # 3. 使用默认配置
        self.logger.info("使用默认配置")
        self.save_config(self.default_config)
        return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置字典
            
        Returns:
            bool: 保存是否成功
        """
        config_file = os.path.join(self.config_dir, "config.json")
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            self.logger.info(f"配置已保存到 {config_file}")
            # 重新加载配置到内存
            self.config = self.load_config()
            return True
        except Exception as e:
            self.logger.error(f"保存配置文件时出错: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            Dict: 当前配置字典
        """
        return self.config
    
    def update_config(self, config_dict: Dict[str, Any]) -> bool:
        """
        更新配置
        
        Args:
            config_dict: 要更新的配置字典
            
        Returns:
            bool: 更新是否成功
        """
        # 合并配置
        self.config.update(config_dict)
        return self.save_config(self.config)
    
    def update_section(self, section: str, config_dict: Dict[str, Any]) -> bool:
        """
        更新指定部分的配置
        
        Args:
            section: 配置部分（例如: 'general', 'notification', 'smtp', 'webhook', 'advanced'）
            config_dict: 要更新的配置字典
            
        Returns:
            bool: 更新是否成功
        """
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
        
        # 处理嵌套配置部分
        if '.' in actual_section:
            parts = actual_section.split('.')
            current = self.config
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = config_dict
        else:
            # 直接更新配置部分
            self.config[actual_section] = config_dict
        
        return self.save_config(self.config)
    
    def reset_config(self) -> bool:
        """
        重置配置为默认值
        
        Returns:
            bool: 重置是否成功
        """
        return self.save_config(self.default_config.copy())
    
    def load_endpoints(self) -> Dict[str, Any]:
        """
        加载端点配置
        
        Returns:
            Dict: 包含endpoints列表的字典
        """
        # 首先检查config.json中是否有端点配置
        if 'service_checks' in self.config and 'endpoints' in self.config['service_checks']:
            endpoints = self.config['service_checks']['endpoints']
            self.logger.info(f"从config.json加载了{len(endpoints)}个端点配置")
            return {"endpoints": endpoints}
        
        # 如果config.json中没有，尝试从根目录的config.yaml加载
        root_yaml = os.path.join(os.getcwd(), "config.yaml")
        if os.path.exists(root_yaml):
            try:
                with open(root_yaml, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f)
                    
                if (yaml_config and 'service_checks' in yaml_config and 
                    'endpoints' in yaml_config['service_checks']):
                    endpoints = yaml_config['service_checks']['endpoints']
                    # 同步到当前配置
                    if 'service_checks' not in self.config:
                        self.config['service_checks'] = {}
                    self.config['service_checks']['endpoints'] = endpoints
                    self.save_config(self.config)
                    
                    self.logger.info(f"从根目录config.yaml加载了{len(endpoints)}个端点配置")
                    return {"endpoints": endpoints}
            except Exception as e:
                self.logger.error(f"从根目录config.yaml加载端点配置失败: {e}")
        
        # 如果没有找到任何端点配置
        self.logger.info("未找到端点配置，返回空列表")
        return {"endpoints": []}
    
    def save_endpoints(self, endpoints_data: Dict[str, List[Dict[str, Any]]]) -> bool:
        """
        保存端点配置到config.json
        
        Args:
            endpoints_data: 包含endpoints列表的字典
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保config中有service_checks部分
            if 'service_checks' not in self.config:
                self.config['service_checks'] = {}
            
            # 更新endpoints部分
            if 'endpoints' in endpoints_data:
                self.config['service_checks']['endpoints'] = endpoints_data['endpoints']
            
            # 保存整个配置
            return self.save_config(self.config)
        except Exception as e:
            self.logger.error(f"保存端点配置时出错: {e}")
            return False
    
    def add_endpoint(self, endpoint: Dict[str, Any]) -> bool:
        """
        添加端点
        
        Args:
            endpoint: 端点配置
            
        Returns:
            bool: 添加是否成功
        """
        endpoints_data = self.load_endpoints()
        endpoints = endpoints_data.get('endpoints', [])
        
        # 检查是否已存在相同名称的端点
        for existing in endpoints:
            if existing.get('name') == endpoint.get('name'):
                self.logger.warning(f"已存在相同名称的端点: {endpoint.get('name')}")
                return False
        
        # 确保端点有id字段，如果没有则使用name作为id
        if 'id' not in endpoint or endpoint['id'] is None:
            endpoint['id'] = endpoint.get('name')
        
        # 添加端点
        endpoints.append(endpoint)
        return self.save_endpoints({"endpoints": endpoints})
    
    def update_endpoint(self, endpoint_name: str, endpoint: Dict[str, Any]) -> bool:
        """
        更新端点
        
        Args:
            endpoint_name: 端点名称或ID
            endpoint: 端点配置
            
        Returns:
            bool: 更新是否成功
        """
        endpoints_data = self.load_endpoints()
        endpoints = endpoints_data.get('endpoints', [])
        
        # 确保端点有id字段，如果没有则使用name作为id
        if 'id' not in endpoint or endpoint['id'] is None:
            endpoint['id'] = endpoint.get('name')
        
        # 查找并更新端点（同时支持通过名称和ID查找）
        for i, existing in enumerate(endpoints):
            if (existing.get('name') == endpoint_name or 
                existing.get('id') == endpoint_name):
                endpoints[i] = endpoint
                return self.save_endpoints({"endpoints": endpoints})
        
        self.logger.warning(f"未找到名称为{endpoint_name}的端点")
        return False
    
    def delete_endpoint(self, endpoint_name: str) -> bool:
        """
        删除端点
        
        Args:
            endpoint_name: 端点名称
            
        Returns:
            bool: 删除是否成功
        """
        endpoints_data = self.load_endpoints()
        endpoints = endpoints_data.get('endpoints', [])
        
        # 过滤掉要删除的端点
        new_endpoints = [ep for ep in endpoints if ep.get('name') != endpoint_name]
        
        if len(new_endpoints) < len(endpoints):
            return self.save_endpoints({"endpoints": new_endpoints})
        else:
            self.logger.warning(f"未找到名称为{endpoint_name}的端点")
            return False
    
    def save_endpoint_history(self, endpoint_id: str, history_entry: Dict[str, Any]) -> bool:
        """
        保存端点历史记录
        
        Args:
            endpoint_id: 端点ID
            history_entry: 历史记录条目
            
        Returns:
            bool: 保存是否成功
        """
        history_dir = os.path.join(self.config_dir, "history")
        os.makedirs(history_dir, exist_ok=True)
        
        history_file = os.path.join(history_dir, f"{endpoint_id}.json")
        
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = []
            
            # 添加新记录
            history.append(history_entry)
            
            # 限制历史记录数量
            max_records = self.config.get('max_history_records', 100)
            if len(history) > max_records:
                history = history[-max_records:]
            
            # 保存历史记录
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
            
            return True
        except Exception as e:
            self.logger.error(f"保存端点历史记录时出错: {e}")
            return False
    
    def get_endpoint_history(self, endpoint_id: str) -> List[Dict[str, Any]]:
        """
        获取端点历史记录
        
        Args:
            endpoint_id: 端点ID
            
        Returns:
            List: 历史记录列表
        """
        history_file = os.path.join(self.config_dir, "history", f"{endpoint_id}.json")
        
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"加载端点历史记录时出错: {e}")
                return []
        else:
            return []
    
    def import_config_from_yaml(self, yaml_file: str) -> bool:
        """
        从YAML文件导入配置
        
        Args:
            yaml_file: YAML文件路径
            
        Returns:
            bool: 导入是否成功
        """
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict):
                self.logger.error(f"YAML文件格式错误: {yaml_file}")
                return False
            
            return self.save_config(config)
        except Exception as e:
            self.logger.error(f"从YAML导入配置时出错: {e}")
            return False
    
    def export_config_to_yaml(self, yaml_file: str) -> bool:
        """
        导出配置到YAML文件
        
        Args:
            yaml_file: YAML文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(yaml_file), exist_ok=True)
            
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            self.logger.info(f"配置已成功导出到YAML: {yaml_file}")
            return True
        except Exception as e:
            self.logger.error(f"导出配置到YAML时出错: {e}")
            return False

    def get_general_config(self) -> Dict[str, Any]:
        """获取常规设置配置"""
        return self.config.get('general', self.default_config['general'])

    def get_notifications_config(self) -> Dict[str, Any]:
        """获取通知设置配置"""
        return self.config.get('notifications', self.default_config['notifications'])

    def get_email_config(self) -> Dict[str, Any]:
        """获取邮件通知配置"""
        return self.config.get('notifications', {}).get('email', self.default_config['notifications']['email'])

    def get_webhook_config(self) -> Dict[str, Any]:
        """获取Webhook配置"""
        return self.config.get('notifications', {}).get('webhook', self.default_config['notifications']['webhook'])

    def get_telegram_config(self) -> Dict[str, Any]:
        """获取Telegram配置"""
        return self.config.get('notifications', {}).get('telegram', self.default_config['notifications']['telegram'])

# 创建配置管理器实例
config_manager = ConfigManager()
