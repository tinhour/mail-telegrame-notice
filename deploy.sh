#!/bin/bash

# 读取环境变量
if [ -f .env ]; then
    source .env
else
    echo "错误：.env 文件不存在"
    exit 1
fi

# 检查必要的环境变量
if [ -z "$DEPLOY_SERVER_IP" ] || [ -z "$DEPLOY_SERVER_PORT" ] || [ -z "$DEPLOY_SERVER_USER" ] || [ -z "$DEPLOY_SERVER_PASSWORD" ]; then
    echo "错误：缺少部署所需的环境变量"
    exit 1
fi

# 创建临时目录
TEMP_DIR=$(mktemp -d)
ARCHIVE="evm-tracker-notice.tar.gz"

echo "正在准备文件..."
# 复制必要的文件到临时目录
cp -r app config.yaml requirements.txt .env $TEMP_DIR/
# 创建远程部署脚本
cat > $TEMP_DIR/remote_deploy.sh << 'EOL'
#!/bin/bash
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
EOL

# 为远程部署脚本添加执行权限
chmod +x $TEMP_DIR/remote_deploy.sh

# 创建归档文件
echo "正在创建归档文件..."
tar -czf $ARCHIVE -C $TEMP_DIR .

# 将文件上传到服务器
echo "正在上传文件到服务器..."
sshpass -p "$DEPLOY_SERVER_PASSWORD" scp -P $DEPLOY_SERVER_PORT -o StrictHostKeyChecking=no $ARCHIVE $DEPLOY_SERVER_USER@$DEPLOY_SERVER_IP:/tmp/

# 在服务器上执行部署
echo "正在服务器上执行部署..."
sshpass -p "$DEPLOY_SERVER_PASSWORD" ssh -p $DEPLOY_SERVER_PORT -o StrictHostKeyChecking=no $DEPLOY_SERVER_USER@$DEPLOY_SERVER_IP << EOF
mkdir -p $DEPLOY_SCRIPT_PATH
tar -xzf /tmp/$ARCHIVE -C $DEPLOY_SCRIPT_PATH
chmod +x $DEPLOY_SCRIPT_PATH/remote_deploy.sh
cd $DEPLOY_SCRIPT_PATH
./remote_deploy.sh
EOF

# 清理临时文件
echo "正在清理临时文件..."
rm -rf $TEMP_DIR
rm $ARCHIVE

echo "部署成功完成!" 