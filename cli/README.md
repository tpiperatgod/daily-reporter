# xndctl - X News Digest CLI Tool

X News Digest 的命令行管理工具，提供用户、Topic、订阅的完整管理功能。

## 安装

```bash
cd cli/
pip install -e .
```

**要求**：
- Python 3.10+
- 后端 API 服务运行中

## 快速开始

### 1. 初始化配置

首次运行会自动提示配置：

```bash
xndctl config
```

或手动初始化：

```bash
xndctl init
```

### 2. 创建用户

```bash
# 交互模式（推荐）
xndctl user create -p

# 标志模式
xndctl user create --name "John Doe" --email "john@example.com"
```

### 3. 创建 Topic

```bash
# 交互模式（带 cron 验证）
xndctl topic create -p

# 标志模式
xndctl topic create --name "AI News" --query "artificial intelligence" --cron "0 8 * * *"
```

### 4. 创建订阅

```bash
# 交互模式（必需）
xndctl sub create -p
```

### 5. 触发采集

```bash
xndctl trigger -p
```

### 6. 发送通知

```bash
xndctl notify -p
```

## 全局选项

| 选项 | 说明 |
|------|------|
| `-v, --verbose` | 显示详细错误信息和堆栈跟踪 |
| `-o, --output` | 输出格式：`table`（默认）、`json`、`yaml` |

## 命令参考

### user - 用户管理

#### 创建用户

```bash
# 交互模式
xndctl user create -p

# 标志模式
xndctl user create --name "John Doe" --email "john@example.com" \
  --feishu-webhook-url "https://..." \
  --feishu-webhook-secret "secret"
```

#### 列出用户

```bash
xndctl user ls
xndctl user ls --limit 50 --offset 0
xndctl user ls --output json
```

#### 获取用户详情

```bash
xndctl user get --id <uuid>
xndctl user get --name "John Doe"
xndctl user get --email "john@example.com"
```

#### 更新用户

```bash
# 交互模式
xndctl user update --name "John Doe" -p

# 标志模式
xndctl user update --name "John Doe" --new-email "newemail@example.com"
```

#### 删除用户

```bash
xndctl user delete --name "John Doe"
xndctl user delete --id <uuid> -y  # 跳过确认
```

### topic - Topic 管理

#### 创建 Topic

```bash
# 交互模式（带 cron 验证）
xndctl topic create -p

# 标志模式
xndctl topic create --name "AI News" --query "artificial intelligence" --cron "0 8 * * *"
```

**Cron 表达式格式**：`minute hour day month weekday`

示例：
- `0 8 * * *` - 每天 8:00
- `0 */6 * * *` - 每 6 小时
- `0 9 * * 1` - 每周一 9:00

#### 列出 Topics

```bash
xndctl topic ls
xndctl topic ls --limit 50 --offset 0
```

#### 获取 Topic 详情

```bash
xndctl topic get --name "AI News"
xndctl topic get --id <uuid>
```

#### 更新 Topic

```bash
# 交互模式
xndctl topic update --name "AI News" -p

# 标志模式
xndctl topic update --name "AI News" --new-name "AI & ML News" --cron "0 9 * * *"
xndctl topic update --name "AI News" --enable
xndctl topic update --name "AI News" --disable
```

#### 删除 Topic

```bash
xndctl topic delete --name "AI News"
xndctl topic delete --id <uuid> -y  # 跳过确认
```

### sub - 订阅管理

#### 创建订阅

```bash
# 交互模式（必需）
xndctl sub create -p
```

此命令会：
1. 显示可用用户列表
2. 显示可用 Topic 列表
3. 提示选择通知渠道（飞书、邮件）
4. 确认后创建

#### 列出订阅

```bash
xndctl sub ls
xndctl sub ls --user-id <uuid>
xndctl sub ls --topic-id <uuid>
```

#### 获取订阅详情

```bash
xndctl sub get --id <uuid>
```

#### 删除订阅

```bash
xndctl sub delete --id <uuid>
xndctl sub delete --id <uuid> -y  # 跳过确认
```

### trigger - 触发采集

```bash
xndctl trigger -p
```

此命令会：
1. 显示可用用户列表
2. 显示用户的订阅和 Topics
3. 触发用户级聚合采集
4. 显示任务 ID 和 Topic 数量

**触发流程**：
- 收集用户所有订阅 Topic 的数据
- 生成单一聚合摘要
- 通过配置的渠道发送通知

### notify - 发送通知

```bash
xndctl notify -p
```

此命令会：
1. 显示最近的摘要列表
2. 显示所选摘要的 Topic 订阅
3. 发送通知到选择的订阅
4. 显示发送统计（成功/失败数量）

### config - 配置管理

#### 查看配置

```bash
xndctl config
```

#### 重新初始化

```bash
xndctl init
```

配置存储在 `~/.xndctl/config.yaml`：

```yaml
api:
  base_url: "http://localhost:8000"
  timeout: 30
  verify_ssl: true

output:
  default_format: "table"
  color: true

logging:
  level: "INFO"
```

## 输出格式

### Table（默认）

人类可读的表格格式，带分页元数据：

```bash
xndctl user ls
```

### JSON

机器可读的 JSON 格式：

```bash
xndctl user ls --output json
xndctl user ls -o json
```

### YAML

人类可读的 YAML 格式：

```bash
xndctl topic ls --output yaml
```

## 错误处理

### 默认模式

简洁的错误消息：

```bash
xndctl user delete --name "NonExistent"
# Error: User with name 'NonExistent' not found
```

### 详细模式

详细的错误信息和堆栈跟踪：

```bash
xndctl user ls --verbose
xndctl user ls -v
```

## 完整工作流示例

```bash
# 1. 创建用户
xndctl user create -p
# Name: John Doe
# Email: john@example.com

# 2. 创建 Topic
xndctl topic create -p
# Name: AI News
# Query: artificial intelligence
# Cron: 0 8 * * *

# 3. 创建订阅
xndctl sub create -p
# Select user: 1 (John Doe)
# Select topic: 1 (AI News)
# Enable Feishu: Yes
# Enable Email: Yes

# 4. 触发采集
xndctl trigger -p
# Select user: 1 (John Doe)

# 5. 发送通知（采集完成后）
xndctl notify -p
# Select digest: 1
# Select subscription: 1
```

## 故障排查

### 无法连接到 API

```bash
# 检查配置中的 API URL
xndctl config

# 更新 API URL
xndctl init
```

### 无效的 cron 表达式

使用格式：`minute hour day month weekday`

有效示例：
- `0 8 * * *`（每天 8 AM）
- `*/30 * * * *`（每 30 分钟）
- `0 0 * * 0`（每周日午夜）

测试工具：https://crontab.guru

### 权限错误

确保后端 API 正在运行且可访问：

```bash
curl http://localhost:8000/health
```

## 项目结构

```
cli/
├── xndctl/
│   ├── cli.py              # 主 CLI 入口
│   ├── config.py           # 配置管理
│   ├── client.py           # API 客户端
│   ├── schemas.py          # Pydantic 模型
│   ├── utils.py            # 显示和错误处理
│   ├── commands/           # 命令实现
│   │   ├── user.py
│   │   ├── topic.py
│   │   ├── subscription.py
│   │   ├── trigger.py
│   │   └── notify.py
│   └── prompts/            # 交互式提示
│       ├── user.py
│       ├── topic.py
│       └── subscription.py
├── tests/
├── setup.py
└── README.md
```

## 许可证

MIT License

