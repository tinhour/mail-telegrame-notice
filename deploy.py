#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import shutil
import tarfile
import time
import paramiko
from dotenv import load_dotenv
from pathlib import Path
from io import StringIO

# 远程部署脚本内容
REMOTE_DEPLOY_SCRIPT = """#!/bin/bash
set -e

# 设置工作目录
DEPLOY_DIR="/opt/deploy/notify"
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR

echo "正在安装系统依赖..."
apt-get update
apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib

echo "正在设置Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

echo "正在安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

echo "正在创建服务文件..."
cat > /etc/systemd/system/evm-tracker.service << 'EOF'
[Unit]
Description=EVM Tracker Notification Service
After=network.target

[Service]
User=root
WorkingDirectory=/opt/deploy/notify
ExecStart=/opt/deploy/notify/venv/bin/python -m app
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "正在重新加载systemd..."
systemctl daemon-reload

echo "正在启动服务..."
systemctl enable evm-tracker
systemctl restart evm-tracker

echo "部署完成!"
"""

def print_colored(text, color='green'):
    """打印彩色文本"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'reset': '\033[0m'
    }
    print(f"{colors.get(color, colors['green'])}{text}{colors['reset']}")

def read_env_vars():
    """读取环境变量"""
    print_colored("读取环境变量...", "blue")
    
    # 检查.env文件是否存在
    if not os.path.exists('.env'):
        print_colored("错误：.env 文件不存在", "red")
        sys.exit(1)
    
    # 加载环境变量
    load_dotenv()
    
    # 读取部署所需的环境变量
    deploy_server_ip = os.getenv('DEPLOY_SERVER_IP')
    deploy_server_port = os.getenv('DEPLOY_SERVER_PORT')
    deploy_server_user = os.getenv('DEPLOY_SERVER_USER')
    deploy_server_password = os.getenv('DEPLOY_SERVER_PASSWORD')
    deploy_script_path = os.getenv('DEPLOY_SCRIPT_PATH', '/opt/deploy/notify/')
    
    # 检查必要的环境变量
    if not all([deploy_server_ip, deploy_server_port, deploy_server_user, deploy_server_password]):
        print_colored("错误：缺少部署所需的环境变量", "red")
        print("请在.env文件中配置以下变量：")
        print("DEPLOY_SERVER_IP - 服务器IP地址")
        print("DEPLOY_SERVER_PORT - SSH端口")
        print("DEPLOY_SERVER_USER - 用户名")
        print("DEPLOY_SERVER_PASSWORD - 密码")
        sys.exit(1)
    
    return {
        'ip': deploy_server_ip,
        'port': int(deploy_server_port),
        'user': deploy_server_user,
        'password': deploy_server_password,
        'path': deploy_script_path
    }

def prepare_files(temp_dir):
    """准备部署所需的文件"""
    print_colored("准备部署文件...", "blue")
    
    # 复制必要的文件到临时目录
    try:
        # 复制app目录
        if os.path.exists('app'):
            shutil.copytree('app', os.path.join(temp_dir, 'app'))
        else:
            print_colored("警告：app目录不存在", "yellow")
        
        # 复制config.yaml
        if os.path.exists('config.yaml'):
            shutil.copy('config.yaml', temp_dir)
        else:
            print_colored("警告：config.yaml文件不存在", "yellow")
        
        # 复制requirements.txt
        if os.path.exists('requirements.txt'):
            shutil.copy('requirements.txt', temp_dir)
        else:
            print_colored("警告：requirements.txt文件不存在", "yellow")
        
        # 复制.env文件
        shutil.copy('.env', temp_dir)
        
        # 创建远程部署脚本
        with open(os.path.join(temp_dir, 'remote_deploy.sh'), 'w', newline='\n') as f:
            f.write(REMOTE_DEPLOY_SCRIPT)
        
    except Exception as e:
        print_colored(f"错误：准备文件失败: {str(e)}", "red")
        sys.exit(1)

def create_archive(temp_dir, archive_name):
    """创建归档文件"""
    print_colored("创建归档文件...", "blue")
    
    try:
        with tarfile.open(archive_name, "w:gz") as tar:
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                tar.add(item_path, arcname=item)
        return True
    except Exception as e:
        print_colored(f"错误：创建归档文件失败: {str(e)}", "red")
        return False

def deploy_to_server(server_info, archive_name):
    """部署到服务器"""
    print_colored("连接到服务器...", "blue")
    
    # 创建SSH客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # 连接到服务器
        ssh.connect(
            hostname=server_info['ip'],
            port=server_info['port'],
            username=server_info['user'],
            password=server_info['password'],
            timeout=30
        )
        print_colored("已连接到服务器", "green")
        
        # 创建SFTP客户端
        sftp = ssh.open_sftp()
        
        # 上传归档文件
        print_colored("上传文件到服务器...", "blue")
        remote_archive_path = "/tmp/evm-tracker-notice.tar.gz"
        sftp.put(archive_name, remote_archive_path)
        
        # 在服务器上执行部署
        print_colored("在服务器上执行部署...", "blue")
        
        commands = [
            f"mkdir -p {server_info['path']}",
            f"tar -xzf {remote_archive_path} -C {server_info['path']}",
            f"chmod +x {server_info['path']}/remote_deploy.sh",
            f"cd {server_info['path']} && ./remote_deploy.sh"
        ]
        
        for cmd in commands:
            print(f"执行: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            # 实时输出命令执行结果
            while True:
                line = stdout.readline()
                if not line:
                    break
                print(line.strip())
            
            # 检查命令是否执行成功
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error_output = stderr.read().decode('utf-8')
                print_colored(f"错误：命令执行失败 (退出码 {exit_status})", "red")
                print(error_output)
                return False
        
        # 清理远程临时文件
        ssh.exec_command(f"rm {remote_archive_path}")
        
        print_colored("部署完成！", "green")
        return True
        
    except Exception as e:
        print_colored(f"错误：部署失败: {str(e)}", "red")
        return False
    finally:
        ssh.close()

def main():
    """主函数"""
    print_colored("开始部署 EVM 跟踪器通知系统...", "green")
    
    # 读取环境变量
    server_info = read_env_vars()
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    archive_name = "evm-tracker-notice.tar.gz"
    
    try:
        # 准备文件
        prepare_files(temp_dir)
        
        # 创建归档文件
        if not create_archive(temp_dir, archive_name):
            sys.exit(1)
        
        # 部署到服务器
        if not deploy_to_server(server_info, archive_name):
            sys.exit(1)
        
        print_colored("部署过程成功完成！", "green")
        
    except KeyboardInterrupt:
        print_colored("\n部署被用户中断", "yellow")
        sys.exit(1)
    except Exception as e:
        print_colored(f"发生错误: {str(e)}", "red")
        sys.exit(1)
    finally:
        # 清理临时文件
        print_colored("清理临时文件...", "blue")
        try:
            shutil.rmtree(temp_dir)
            if os.path.exists(archive_name):
                os.remove(archive_name)
        except Exception as e:
            print_colored(f"警告：清理临时文件失败: {str(e)}", "yellow")

if __name__ == "__main__":
    main() 