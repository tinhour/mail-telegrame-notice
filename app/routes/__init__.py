# 将routes目录标记为Python包

from app.routes.config_routes import config_bp
from app.routes.web_routes import web_bp

__all__ = ['config_bp', 'web_bp'] 