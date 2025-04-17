# EVM跟踪器通知系统部署指南

## 前提条件

在开始部署之前，请确保满足以下条件：

1. 生产服务器运行 Debian GNU/Linux 12 (Bookworm)
2. 确保服务器上的SSH服务已启用，且允许root用户登录
3. 确保您已将正确的服务器信息配置在`.env`文件中

## 部署方法

根据您的本地环境，您可以选择以下部署方法之一：

### 方法1：使用WSL (Windows Subsystem for Linux)

这是在Windows环境中最简单的部署方法：

1. 安装WSL：
   ```
   wsl --install
   ```

2. 在WSL中安装sshpass：
   ```
   sudo apt-get update
   sudo apt-get install sshpass
   ```

3. 将项目复制到WSL环境中：
   ```
   # 在Windows中
   cd C:\project\evm-tracker-notice
   wsl
   
   # 在WSL中
   mkdir -p ~/evm-tracker-notice
   cp -r /mnt/c/project/evm-tracker-notice/* ~/evm-tracker-notice/
   cd ~/evm-tracker-notice
   chmod +x deploy_linux.sh
   ```

4. 执行部署脚本：
   ```
   ./deploy_linux.sh
   ```

### 方法2：使用Git Bash

如果您已安装Git for Windows，可以使用Git Bash执行部署：

1. 安装sshpass：
   - 下载sshpass for Windows: [MSYS2 packages](https://packages.msys2.org/package/sshpass?repo=msys&variant=x86_64)
   - 将下载的sshpass.exe文件放在Git Bash的bin目录中 (通常位于 `C:\Program Files\Git\usr\bin\`)

2. 修改deploy.sh脚本使其适用于Git Bash：
   - 在Git Bash中，打开deploy.sh
   - 确保脚本中使用了正确的路径格式（可能需要使用Windows路径格式）

3. 在Git Bash中执行脚本：
   ```
   chmod +x deploy.sh
   ./deploy.sh
   ```

### 方法3：使用远程Linux服务器

如果您有访问其他Linux服务器的权限：

1. 将项目文件复制到该服务器
2. 在该服务器上安装sshpass
3. 执行deploy_linux.sh脚本

## 配置说明

确保您的`.env`文件包含以下配置：

```ini
# 部署配置（示例）
DEPLOY_ENABLED=true
DEPLOY_SCRIPT=deploy.sh
DEPLOY_SCRIPT_PATH=/opt/deploy/notify/
DEPLOY_SCRIPT_TIMEOUT=300
DEPLOY_SCRIPT_RETRY=3
DEPLOY_SERVER_IP=38.145.218.208  # 您的生产服务器IP
DEPLOY_SERVER_PORT=22            # SSH端口
DEPLOY_SERVER_USER=root          # 登录用户
DEPLOY_SERVER_PASSWORD=你的密码   # 登录密码
```

## 部署后验证

部署成功后，系统会自动创建并启动服务。您可以通过以下方式验证部署：

1. 检查服务状态：
   ```
   ssh root@服务器IP "systemctl status evm-tracker"
   ```

2. 检查应用程序日志：
   ```
   ssh root@服务器IP "journalctl -u evm-tracker -n 50"
   ```

3. 访问应用健康检查接口（如果配置了对外访问）：
   ```
   curl http://服务器IP:端口/health
   ```

## 故障排除

如果部署过程中遇到问题：

1. **SSH连接失败**：
   - 检查服务器IP地址和端口是否正确
   - 确认服务器上的SSH服务已启动
   - 检查服务器防火墙是否允许SSH连接

2. **部署脚本执行失败**：
   - 检查服务器上是否有足够的磁盘空间
   - 确保服务器上的Python版本 >= 3.8
   - 检查是否有足够的权限创建目录和安装软件包

3. **服务无法启动**：
   - 检查应用日志：`journalctl -u evm-tracker -n 100`
   - 确保配置文件正确
   - 确保所有依赖项已正确安装

如需更多帮助，请联系系统管理员或开发团队。 