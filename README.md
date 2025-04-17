# 服务监控与通知系统

一个强大的服务状态监控和通知系统，可以实时监控API服务的健康状态，检测系统资源使用情况，并通过多种渠道发送通知。

## 🔍 功能特点

- **多渠道通知**
  - 邮件通知：支持SMTP邮件服务，包括SSL/TLS加密
  - Telegram通知：通过Telegram Bot API发送即时消息
  - 通知级别：支持信息(info)、警告(warning)、错误(error)不同级别的通知

- **服务监控**
  - HTTP(S)服务健康检查：支持GET/POST请求方法
  - 灵活的检查条件：状态码验证、内容匹配、JSON结构检查
  - 自定义检查间隔：每个服务可设置不同的检查频率
  - 智能通知策略：状态变化和持续异常时发送通知

- **系统资源监控**
  - CPU使用率监控
  - 内存使用情况监控
  - 磁盘空间监控
  - 可自定义阈值设置

- **易用的Web API**
  - RESTful接口设计
  - 服务状态查询
  - 动态添加和管理监控端点
  - 手动发送测试通知

- **灵活配置**
  - YAML配置文件支持
  - 环境变量配置支持
  - 数据库存储配置（可选）

## 🛠️ 安装指南

### 系统要求

- Python 3.6+
- 可选：PostgreSQL数据库（用于存储配置）

### 步骤一：克隆代码库

```bash
git clone <repository-url>
cd evm-tracker-notice
```

### 步骤二：创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤三：配置系统

```bash
# 复制配置示例文件
cp .env.example .env
cp config.yaml.example config.yaml

# 编辑配置文件
# 根据需要修改 .env 和 config.yaml 文件
```

## 📝 配置说明

### 关键配置项

#### 通知配置

- **邮件通知**
  ```yaml
  notifications:
    email:
      enabled: true
      smtp_server: smtp.example.com
      smtp_port: 465  # 使用SSL时通常为465，使用TLS时通常为587
      username: your_username
      password: your_password
      sender: sender@example.com
      recipients:
        - recipient1@example.com
        - recipient2@example.com
  ```

- **Telegram通知**
  ```yaml
  notifications:
    telegram:
      enabled: true
      token: your_bot_token
      chat_ids:
        - your_chat_id_1
        - your_chat_id_2
  ```

#### 服务监控配置

```yaml
service_checks:
  enabled: true
  interval_minutes: 5  # 默认检查间隔
  endpoints:
    - name: "示例服务"
      url: "https://example.com/health"
      expected_status: 200
      method: "GET"
      interval_minutes: 2  # 可单独设置检查间隔
    - name: "API服务"
      url: "https://api.example.com/v1/status"
      expected_status: 200
      method: "POST"
      body: {"check": "full"}
      headers:
        Authorization: "Bearer token123"
      json_check:
        path: "data.status"
        expected_value: "healthy"
```

#### 系统资源监控配置

```yaml
system_monitoring:
  enabled: true
  interval_minutes: 5
  thresholds:
    cpu_percent: 80
    memory_percent: 85
    disk_percent: 90
```

## 🚀 使用方法

### 启动服务

```bash
# 使用默认配置启动
python -m app.main

# 指定主机和端口
python -m app.main --host 127.0.0.1 --port 5000

# 指定配置文件路径
python -m app.main --config /path/to/custom/config.yaml

# 开启调试模式
python -m app.main --debug
```

### API接口文档

#### 1. 健康检查

- **URL**: `/health`
- **方法**: `GET`
- **描述**: 简单的健康检查，确认服务是否正常运行
- **返回示例**:
  ```json
  {
    "status": "ok"
  }
  ```

#### 2. 系统状态查询

- **URL**: `/api/status`
- **方法**: `GET`
- **描述**: 获取系统运行状态，包括服务检查状态、系统资源使用情况、计划任务列表
- **返回示例**:
  ```json
  {
    "status": "运行中",
    "version": "0.1.0",
    "services": "示例服务: 正常 (上次检查: 2023-04-17 13:45:02)\nAPI服务: 异常 (上次检查: 2023-04-17 13:45:10), 详情: 服务异常: 状态码 500 (预期 200)",
    "system": {
      "cpu_percent": "25.5%",
      "memory_percent": "60.2%",
      "memory_used": "4.8 GB",
      "memory_total": "8.0 GB",
      "disk_percent": "75.0%",
      "disk_used": "120.5 GB",
      "disk_total": "250.0 GB",
      "last_update": "2023-04-17 13:45:15"
    },
    "scheduled_jobs": [
      {
        "id": "service_check_示例服务",
        "name": "服务检查 - 示例服务",
        "next_run": "2023-04-17 13:47:02"
      },
      {
        "id": "service_check_API服务",
        "name": "服务检查 - API服务",
        "next_run": "2023-04-17 13:50:10"
      },
      {
        "id": "system_monitoring",
        "name": "系统资源监控",
        "next_run": "2023-04-17 13:50:15"
      }
    ]
  }
  ```

#### 3. 获取监控端点列表

- **URL**: `/api/endpoints`
- **方法**: `GET`
- **描述**: 获取当前配置的所有监控端点
- **返回示例**:
  ```json
  [
    {
      "name": "示例服务",
      "url": "https://example.com/health",
      "expected_status": 200,
      "method": "GET",
      "interval_minutes": 2,
      "headers": {},
      "body": null,
      "expected_content": null,
      "json_check": null
    },
    {
      "name": "API服务",
      "url": "https://api.example.com/v1/status",
      "expected_status": 200,
      "method": "POST",
      "interval_minutes": 5,
      "headers": {
        "Authorization": "Bearer token123"
      },
      "body": {"check": "full"},
      "expected_content": null,
      "json_check": {
        "path": "data.status",
        "expected_value": "healthy"
      }
    }
  ]
  ```

#### 4. 添加监控端点

- **URL**: `/api/endpoints`
- **方法**: `POST`
- **描述**: 动态添加新的监控端点
- **请求体示例**:
  ```json
  {
    "name": "新服务",
    "url": "https://newservice.com/status",
    "expected_status": 200,
    "method": "GET",
    "interval_minutes": 3,
    "headers": {
      "User-Agent": "ServiceMonitor/1.0"
    },
    "json_check": {
      "path": "status",
      "expected_value": "ok"
    }
  }
  ```
- **返回示例**:
  ```json
  {
    "status": "success",
    "message": "已添加端点: 新服务"
  }
  ```

#### 5. 更新端点检查间隔

- **URL**: `/api/endpoints/<endpoint_name>/interval`
- **方法**: `PUT`
- **描述**: 更新指定端点的检查间隔时间
- **请求体示例**:
  ```json
  {
    "interval_minutes": 10
  }
  ```
- **返回示例**:
  ```json
  {
    "status": "success",
    "message": "已更新端点检查间隔: 示例服务, 新间隔: 10分钟"
  }
  ```

#### 6. 发送测试通知

- **URL**: `/api/notify`
- **方法**: `POST`
- **描述**: 手动发送测试通知
- **请求体示例**:
  ```json
  {
    "subject": "测试通知",
    "message": "这是一条测试通知消息",
    "level": "info"  # 可选值: info, warning, error
  }
  ```
- **返回示例**:
  ```json
  {
    "status": "success",
    "message": "通知已发送"
  }
  ```

## 🌐 部署指南

### Docker部署

1. 创建Dockerfile:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3003

CMD ["python", "-m", "app.main"]
```

2. 构建和运行容器:

```bash
docker build -t service-monitor .
docker run -p 3003:3003 -v $(pwd)/config.yaml:/app/config.yaml service-monitor
```

### 系统服务部署 (Linux)

1. 创建systemd服务文件 `/etc/systemd/system/service-monitor.service`:

```ini
[Unit]
Description=Service Monitor and Notification System
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/evm-tracker-notice
ExecStart=/path/to/evm-tracker-notice/venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. 启用和启动服务:

```bash
sudo systemctl daemon-reload
sudo systemctl enable service-monitor
sudo systemctl start service-monitor
```

3. 查看服务状态:

```bash
sudo systemctl status service-monitor
```

### 日志管理

服务默认将日志输出到控制台和`app.log`文件。您可以使用logrotate等工具进行日志轮转，避免日志文件过大。

示例logrotate配置:

```
/path/to/evm-tracker-notice/app.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 yourusername yourusername
}
```

## 📁 项目结构

```
evm-tracker-notice/
├── app/
│   ├── config/          # 配置相关模块
│   │   └── settings.py  # 配置加载和管理
│   ├── core/            # 核心功能模块
│   │   ├── db.py        # 数据库连接
│   │   └── scheduler.py # 任务调度器
│   ├── services/        # 服务模块
│   │   ├── notifier.py  # 通知服务
│   │   ├── service_check.py  # 服务检查
│   │   └── system_monitor.py # 系统资源监控
│   ├── utils/           # 工具函数
│   └── main.py          # 主程序和API接口
├── tests/               # 测试代码
├── config.yaml          # 配置文件
├── .env                 # 环境变量文件
├── requirements.txt     # 依赖列表
└── README.md            # 项目说明
```

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！请按以下步骤:

1. Fork仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交Pull Request

## 📄 许可证

本项目采用MIT许可证。详情请参见[LICENSE](LICENSE)文件。

## 📧 联系方式

如有任何问题或建议，请通过以下方式联系:

- 项目维护者: [维护者姓名](mailto:维护者邮箱)
- 项目仓库: [GitHub仓库地址](项目GitHub地址)

---

感谢使用服务监控与通知系统！希望它能为您的服务可靠性保障提供帮助。 