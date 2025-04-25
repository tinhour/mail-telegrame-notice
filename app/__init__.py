"""
消息通知和服务监控系统

该系统提供以下功能：
1. 通知服务：通过邮件和Telegram发送通知
2. 服务监控：定时检查指定服务的可用性
3. 系统资源监控：监控CPU、内存和磁盘使用情况
"""

from flask import Flask
from app.routes.config_routes import config_bp
from app.routes import web_bp

__version__ = "0.1.0"

def create_app():
    app = Flask(__name__)
    
    # 注册蓝图
    app.register_blueprint(config_bp)
    app.register_blueprint(web_bp)
    
    return app 