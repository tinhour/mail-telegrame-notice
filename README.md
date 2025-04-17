# 消息通知和服务监控系统

这是一个使用Python开发的消息通知和服务监控系统，它能够监控服务状态和系统资源，并通过邮件或Telegram发送通知。

## 功能特点

- **多渠道通知**：支持通过邮件和Telegram发送通知消息
- **服务状态监控**：定时检查指定的API或网站服务状态
- **系统资源监控**：监控CPU、内存和磁盘使用情况，超过阈值时发送警报
- **Web API接口**：提供Web API用于查看状态和手动触发通知
- **灵活配置**：支持通过YAML配置文件或环境变量配置系统
- **可扩展**：模块化设计，易于扩展新功能

## 系统要求

- Python 3.6+
- PostgreSQL 数据库
- 依赖的Python库（见requirements.txt）

## 安装步骤

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/evm-tracker-notice.git
cd evm-tracker-notice
```

2. 创建虚拟环境并安装依赖：

```bash
python -m venv venv
source venv/bin/activate  # 在Windows上使用 venv\Scripts\activate
pip install -r requirements.txt
```

3. 配置环境：

```bash
cp .env.example .env
# 编辑.env文件设置你的配置

cp config.yaml.example config.yaml
# 编辑config.yaml文件设置更多配置
```

## 使用方法

### 启动服务

```bash
# 2. 激活虚拟环境
# - macOS/Linux:
source venv/bin/activate
# windows
.\venv\Scripts\Activate.ps1
#运行程序
python -m app.main
#退出环境
	deactivate
```

或者指定配置文件路径：

```bash
python -m app.main --config=/path/to/config.yaml
```

### 访问Web界面

启动服务后，可以访问以下API端点：

- 健康检查：`http://localhost:3003/health`
- 系统状态：`http://localhost:3003/api/status`
- 管理端点：`http://localhost:3003/api/endpoints`
- 发送通知：`http://localhost:3003/api/notify`

### 添加服务监控端点

通过API添加监控端点：

```bash
curl -X POST http://localhost:5000/api/endpoints \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的服务",
    "url": "https://myservice.com/health",
    "expected_status": 200
  }'
```

或者直接编辑配置文件中的`endpoints`部分。

### 发送测试通知

```bash
curl -X POST http://localhost:5000/api/notify \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "测试通知",
    "message": "这是一条测试消息",
    "level": "info"
  }'
```

## 配置说明

### 主要配置选项

- **数据库设置**：PostgreSQL连接信息
- **通知设置**：邮件和Telegram通知配置
- **服务检查**：监控端点和检查间隔
- **系统监控**：资源阈值和监控间隔

详细配置见`.env.example`和`config.yaml.example`文件。

## 作为系统服务运行

### Systemd (Linux)

创建服务文件 `/etc/systemd/system/evm-tracker-notice.service`：

```
[Unit]
Description=EVM Tracker Notice Service
After=network.target postgresql.service

[Service]
User=yourusername
WorkingDirectory=/path/to/evm-tracker-notice
ExecStart=/path/to/evm-tracker-notice/venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl enable evm-tracker-notice
sudo systemctl start evm-tracker-notice
```

## 项目结构

```
evm-tracker-notice/
├── app/
│   ├── config/          # 配置相关模块
│   ├── core/            # 核心功能模块
│   ├── services/        # 服务模块
│   ├── utils/           # 工具函数
│   └── main.py          # 主程序入口
├── tests/               # 测试代码
├── config.yaml          # 配置文件
├── .env                 # 环境变量文件
├── requirements.txt     # 依赖列表
└── README.md            # 项目说明
```

## 贡献指南

欢迎提交问题报告和代码贡献！请确保遵循以下步骤：

1. Fork仓库并创建一个新的分支
2. 编写并测试你的代码
3. 提交拉取请求

## 许可证

本项目采用MIT许可证 - 详见LICENSE文件 