import logging
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config.settings import CONFIG

logger = logging.getLogger(__name__)

# 创建SQLAlchemy基类
Base = declarative_base()

def get_postgres_connection():
    """获取PostgreSQL数据库连接"""
    try:
        db_config = CONFIG["database"]
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            dbname=db_config["dbname"]
        )
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return None

def create_sqlalchemy_engine():
    """创建SQLAlchemy引擎"""
    try:
        db_config = CONFIG["database"]
        db_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        logger.error(f"创建SQLAlchemy引擎失败: {str(e)}")
        raise

# 创建SQLAlchemy引擎和会话
engine = create_sqlalchemy_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """获取数据库会话"""
    session = SessionLocal()
    try:
        return session
    finally:
        session.close()

def init_db():
    """初始化数据库架构"""
    Base.metadata.create_all(bind=engine) 