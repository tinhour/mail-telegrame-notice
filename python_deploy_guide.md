# Python部署脚本使用指南

## 前提条件

1. 本地环境已安装Python 3.6+
2. 生产服务器运行 Debian GNU/Linux 12 (Bookworm)
3. 确保服务器上的SSH服务已启用，且允许root用户登录

## 部署步骤

### 1. 安装依赖

在使用部署脚本前，需要先安装必要的Python依赖：

```
pip install -r deploy_requirements.txt
```

### 2. 配置环境变量

确保您的`.env`文件包含以下配置：

```ini
# 部署配置
DEPLOY_ENABLED=true
DEPLOY_SCRIPT_PATH=/opt/deploy/notify/
DEPLOY_SERVER_IP=38.145.218.208  # 您的生产服务器IP
DEPLOY_SERVER_PORT=22            # SSH端口
DEPLOY_SERVER_USER=root          # 登录用户
DEPLOY_SERVER_PASSWORD=您的密码   # 登录密码
```

### 3. 执行部署脚本

直接运行Python脚本：

```
python deploy.py
```

脚本将执行以下操作：
- 读取`.env`文件中的配置信息
- 创建临时工作目录
- 将必要的文件复制到临时目录
- 创建归档文件
- 通过SSH连接到服务器
- 上传归档文件
- 在服务器上执行部署操作
- 清理临时文件

## 故障排除

### 编码问题

如果遇到以下错误：
```
错误：部署失败: 'utf-8' codec can't decode byte 0xXX in position 0: invalid continuation byte
```

这是由于字符编码不兼容导致的，最新版本的脚本已处理此问题。如果仍然出现：

1. 确保使用最新版本的deploy.py
2. 检查服务器是否返回了非UTF-8编码的输出
3. 如果问题仍然存在，可以尝试手动修改脚本，在相关代码处添加`errors='replace'`参数

### 连接问题

如果遇到SSH连接问题：

1. 确认IP地址和端口是否正确
2. 确认用户名和密码是否正确
3. 检查服务器防火墙设置是否允许SSH连接

### Windows特有问题

在Windows环境中可能遇到的特殊问题：

1. **行结束符问题**：Windows使用CRLF(\r\n)作为行结束符，而Linux使用LF(\n)。最新脚本会自动处理这个问题。

2. **控制台颜色问题**：如果控制台不显示彩色输出，可以在PowerShell中运行以下命令启用ANSI颜色：
   ```powershell
   $Host.UI.RawUI.ForegroundColor = "Gray"
   ```

3. **中文显示问题**：如果控制台显示中文为乱码，请确保PowerShell或命令提示符设置为UTF-8编码：
   ```powershell
   chcp 65001
   ```

### 权限问题

如果遇到权限相关错误：

1. 确保使用的是root用户或具有足够权限的用户
2. 检查服务器上目标目录的权限

### 依赖问题

如果脚本运行时报告缺少模块：

1. 确保已正确安装所有依赖：`pip install -r deploy_requirements.txt`
2. 如果使用虚拟环境，确保已激活正确的环境

如果遇到依赖冲突错误（如python-telegram-bot和apscheduler版本冲突）：

1. 已修复版本的requirements.txt文件已将apscheduler版本设置为3.6.3，兼容python-telegram-bot的要求
2. 如果仍有冲突，可以手动安装：
   ```
   pip install python-telegram-bot==13.14
   pip install -r requirements.txt --no-deps
   pip install psycopg2-binary pyyaml schedule requests psutil flask prometheus-client SQLAlchemy python-dotenv
   ```
3. 部署脚本现在包含自动处理依赖冲突的逻辑

### 服务器问题

如果服务器端部署失败：

1. 确保服务器上有足够的磁盘空间
2. 查看服务器日志获取更多信息：`journalctl -xeu evm-tracker`
3. 可以在服务器上手动执行`remote_deploy.sh`脚本，观察具体哪一步出现问题