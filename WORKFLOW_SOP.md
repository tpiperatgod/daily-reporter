# X-News-Digest 业务流程 SOP

## 文档说明

**目标受众:** AI 模型
**文档用途:** 理解和执行完整的推文采集、摘要生成、通知推送业务流程
**最后更新:** 2026-03-08

## 系统概述

X-News-Digest 是一个自动化的 Twitter/X 新闻摘要系统,通过以下三个核心任务完成完整的业务流程:

1. **数据采集** (`collect_user_topics`): 从 Twitter/X 采集用户订阅话题的最新推文
2. **摘要生成** (`generate_user_digest`): 使用 AI 大模型生成结构化摘要报告
3. **通知推送** (`notify_user_digest`): 通过飞书/邮件将摘要发送给用户

### 核心架构

```
用户配置 → Celery Beat 定时调度
    ↓
Task 1: collect_user_topics (数据采集)
    ├─ Twitter API 增量获取推文
    ├─ 语义去重 (Embedding)
    └─ 存储到数据库
    ↓
Task 2: generate_user_digest (摘要生成)
    ├─ 查询时间窗口内的推文
    ├─ LLM Chat API 生成结构化摘要
    └─ 保存 JSON + Markdown 格式
    ↓
Task 3: notify_user_digest (通知推送)
    ├─ 飞书 Webhook (富文本卡片)
    └─ 邮件 SMTP (HTML 格式)
```

### 关键实体

| 实体 | 说明 | 关键字段 |
|------|------|----------|
| User | 用户账户 | email, topics (JSONB), enable_feishu, enable_email |
| Topic | 订阅话题 | name, query, last_tweet_id, is_enabled |
| Item | 推文数据 | source_id, text, author, embedding_hash, metrics |
| UserDigest | 用户摘要 | summary_json, rendered_content, time_window |
| Delivery | 推送记录 | channel, status, retry_count, error_msg |

### 数据流转

```
Twitter API → RawItem → Item (去重) → UserDigest (LLM) → Delivery (通知)
```

---

## Task 1: 数据采集流程

### 触发方式

- **手动触发:** 用户通过 API 调用 `POST /users/{user_id}/trigger`
- **自动触发:** Celery Beat 根据用户配置的 cron 表达式定时执行

### 业务目标

从 Twitter/X 平台采集用户关注的所有话题的最新推文,并进行去重处理后存入数据库。

### 执行流程

#### 1. 加载用户配置

- 系统根据用户 ID 查找用户信息
- 获取用户订阅的话题列表(存储在 `user.topics` JSONB 字段中)
- 如果用户没有配置话题,流程结束

#### 2. 计算时间窗口

- 根据参数(如"过去24小时")计算需要采集的时间范围
- 时区按照系统配置的 `CRON_TIMEZONE` 进行计算(默认为 Asia/Shanghai)
- 将配置时区的时间转换为 UTC 时间用于数据查询

**时间窗口选项:**
- `4h`: 过去 4 小时
- `12h`: 过去 12 小时
- `24h`: 过去 24 小时(默认)
- `1d`: 过去 1 天(等同于 24h)

#### 3. 逐个话题采集数据

对每个启用的话题执行以下操作:

##### 3.1 构建 Twitter API 查询参数

- 从话题的 `query` 字段提取用户名
- 支持三种格式:
  - `@karpathy` → 提取 `karpathy`
  - `karpathy` → 直接使用 `karpathy`
  - `from:karpathy` → 提取 `karpathy`
- 构建 Twitter 高级搜索查询字符串: `from:{username}`
- 如果话题记录了 `last_tweet_id`,则在查询中添加 `since_id:{last_tweet_id}` 实现增量采集
- **查询示例:** `from:karpathy since_id:1234567890`

##### 3.2 调用 twitterapi.io Advanced Search API

**API 端点:**
```
GET https://api.twitterapi.io/twitter/tweet/advanced_search
```

**请求头:**
```http
X-API-Key: {your_api_key}
Accept: application/json
```

**查询参数:**
- `query`: Twitter 高级搜索查询字符串(如 "from:karpathy since_id:1234567890")
- `queryType`: 固定值 "Latest"(按时间倒序返回最新推文)
- `cursor`: 分页游标(首次请求不传,后续请求使用上一页返回的 `next_cursor`)

**响应结构:**
```json
{
  "tweets": [
    {
      "id": "1234567890",
      "text": "推文内容",
      "author": {
        "userName": "karpathy"
      },
      "url": "https://twitter.com/karpathy/status/1234567890",
      "createdAt": "Tue Nov 18 00:56:32 +0000 2025",
      "likeCount": 100,
      "retweetCount": 20,
      "replyCount": 5,
      "quoteCount": 3,
      "viewCount": 1000,
      "entities": {
        "media": [
          {"url": "https://..."}
        ]
      }
    }
  ],
  "has_next_page": true,
  "next_cursor": "DAABCgABGc..."
}
```

##### 3.3 分页处理

- 系统默认最多获取 5 页数据(可通过 `TWITTER_API_MAX_PAGES` 配置)
- 每页约 20 条推文,总计最多 100 条
- 分页逻辑:
  1. 首次请求不传 `cursor` 参数
  2. 检查响应中的 `has_next_page` 字段
  3. 如果为 `true` 且存在 `next_cursor`,则继续请求下一页
  4. 使用 `cursor` 参数传递上一页的 `next_cursor` 值
  5. 当达到最大页数或 `has_next_page` 为 `false` 时停止分页

##### 3.4 数据映射

将 API 返回的推文数据映射为系统内部的 Item 对象:

| 目标字段 | 来源字段 | 说明 |
|---------|---------|------|
| source_id | tweet.id | 推文唯一标识 |
| author | tweet.author.userName | 用户名 |
| text | tweet.text | 推文内容 |
| url | tweet.url | 推文链接 |
| created_at | tweet.createdAt | 发布时间(RFC 2822 格式) |
| media_urls | tweet.entities.media[].url | 媒体链接列表 |
| metrics | likeCount, retweetCount, etc. | 互动数据 |

**时间戳解析:**
- Twitter API 返回 RFC 2822 格式: `Tue Nov 18 00:56:32 +0000 2025`
- 系统使用 Python 的 `email.utils.parsedate_to_datetime()` 解析
- 转换为 UTC 时区的 datetime 对象

##### 3.5 错误处理

| 错误类型 | HTTP 状态码 | 处理方式 |
|---------|------------|---------|
| 认证失败 | 401/403 | 抛出 ValueError,任务失败 |
| 速率限制 | 429 | 记录警告,抛出异常,触发重试 |
| 其他错误 | 4xx/5xx | 记录错误详情,抛出异常 |

- 如果某个话题采集失败,记录错误但继续处理其他话题
- 话题级别的错误隔离保证部分失败不影响整体流程

#### 4. 数据去重处理

##### 4.1 批量生成语义特征

- 收集所有推文的文本内容到列表
- 调用 LLM Embedding API 批量生成语义向量
- 对每个向量计算 SHA-256 哈希值作为 `embedding_hash`
- 批量处理避免了逐条调用 API 的性能问题

**Embedding 配置:**
- 提供商: 通过 `LLM_EMBEDDING_PROVIDER` 配置(openai 或 ollama)
- OpenAI 兼容: 使用 `OPENAI_EMBEDDING_BASE_URL` 和 `OPENAI_EMBEDDING_API_KEY`
- Ollama: 使用本地 Ollama 服务

##### 4.2 两层去重检查

**第一层 - 全局去重 (source_id):**
- 批量查询数据库中是否存在相同的 `source_id`
- 使用 `SELECT source_id FROM items WHERE source_id IN (...)`
- 同一条推文在整个系统中只存储一次
- 去重范围: 全局(跨所有话题)

**第二层 - 话题内语义去重 (embedding_hash):**
- 批量查询当前话题下是否存在相同的 `embedding_hash`
- 使用 `SELECT embedding_hash FROM items WHERE topic_id = ? AND embedding_hash IN (...)`
- 内容相似的推文在同一话题下只保留一条
- 去重范围: 话题级别(不同话题可以有相似内容)

##### 4.3 批内去重

- 在当前批次内检查是否有重复的 `source_id`
- 使用 Python set 进行内存去重
- 避免同一批次中的重复数据被插入

**去重优先级:**
1. 批内去重(内存检查)
2. 全局 source_id 去重(数据库查询)
3. 话题内 embedding_hash 去重(数据库查询)

#### 5. 保存新数据

- 将去重后的新推文批量插入数据库
- 使用 `session.add_all(new_items)` 批量插入
- 更新每个话题的 `last_tweet_id` 为本次采集到的最大推文 ID
- 推文 ID 是数字字符串,系统会比较数值大小找出最大值
- `last_tweet_id` 将在下次采集时作为 `since_id` 参数使用

**last_tweet_id 更新逻辑:**
```python
max_tweet_id = None
for raw_item in raw_items:
    current_id = int(raw_item.source_id)
    if max_tweet_id is None or current_id > max_tweet_id:
        max_tweet_id = current_id

topic.last_tweet_id = str(max_tweet_id)
```

#### 6. 触发下一步流程

- 查询时间窗口内所有已处理话题的推文
- 使用 SQL 查询: `WHERE topic_id IN (...) AND created_at >= ? AND created_at <= ?`
- 按推文发布时间倒序排列,限制最多 1000 条
- 如果有数据,自动触发摘要生成流程 (`generate_user_digest`)
- 传递参数:
  - `user_id`: 用户 ID
  - `topic_ids`: 话题 ID 列表
  - `topic_names`: 话题 ID 到名称的映射字典
  - `window_start`: 时间窗口起始时间(ISO 格式)
  - `window_end`: 时间窗口结束时间(ISO 格式)
- 如果没有数据,流程结束

### 关键优化点

1. **增量采集机制**
   - 使用 `since_id` 参数只获取新推文
   - 减少 90% 以上的 API 调用
   - 降低 API 成本和响应时间

2. **批量处理**
   - 语义特征生成采用批量 API 调用
   - 数据库查询使用 `IN` 子句批量检查
   - 避免 N+1 查询问题

3. **话题隔离**
   - 单个话题失败不影响其他话题的采集
   - 错误记录到日志但不中断流程

4. **分页控制**
   - 限制最大页数防止单次采集时间过长
   - 平衡数据完整性和系统响应速度

---

## Task 2: 摘要生成流程

### 触发方式

- **自动触发:** 由数据采集流程在发现新数据后自动触发
- **手动触发:** 用户可以通过 API 手动触发历史数据的摘要生成

### 业务目标

将用户所有话题在时间窗口内采集到的推文,通过 AI 大模型生成一份结构化的个性化摘要报告。

### 执行流程

#### 1. 参数验证

接收上游传递的参数并进行严格验证:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| user_id | UUID string | 是 | 用户唯一标识 |
| topic_ids | List[UUID string] | 是 | 话题 ID 列表 |
| topic_names | Dict[UUID string, string] | 是 | 话题 ID 到名称的映射 |
| window_start | ISO datetime string | 是 | 时间窗口起始时间 |
| window_end | ISO datetime string | 是 | 时间窗口结束时间 |

**验证规则:**
- 所有参数不能为空或 None
- UUID 字符串必须符合 UUID 格式
- ISO 时间字符串必须可解析为 datetime 对象
- 如果参数缺失或格式错误,直接返回错误(不重试)

**错误语义:**
- 参数验证错误属于确定性错误,不应重试
- 返回错误字典包含 `_deterministic: true` 标记

#### 2. 查询时间窗口内的推文数据

- 根据话题 ID 列表和时间窗口查询数据库
- SQL 查询条件:
  ```sql
  SELECT * FROM items
  WHERE topic_id IN (...)
    AND created_at >= ?
    AND created_at <= ?
  ORDER BY created_at DESC
  ```
- 如果没有查询到数据,流程结束(返回成功状态)

#### 3. 准备 LLM 输入数据

将每条推文转换为结构化格式:

```python
{
    "id": "uuid",
    "text": "推文内容",
    "author": "用户名",
    "url": "https://twitter.com/...",
    "created_at": "2025-11-18T00:56:32Z",
    "metrics": {
        "likes": 100,
        "retweets": 20,
        "replies": 5,
        "quotes": 3,
        "views": 1000
    },
    "topic_name": "话题名称"
}
```

#### 4. 调用 LLM Chat API 生成摘要

##### API 配置

- **Base URL:** 从 `LLM_CHAT_BASE_URL` 配置读取
- **Model:** 从 `LLM_CHAT_MODEL` 配置读取
- **API Key:** 从 `LLM_CHAT_API_KEY` 配置读取
- **超时时间:** 300 秒
- **支持的提供商:** DeepSeek、OpenAI、GLM 等兼容 OpenAI API 格式的服务

##### 请求格式

**端点:**
```
POST {LLM_CHAT_BASE_URL}/chat/completions
```

**请求头:**
```http
Content-Type: application/json
Authorization: Bearer {LLM_CHAT_API_KEY}
```

**请求体:**
```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业的内容分析助手,擅长从大量社交媒体内容中提取关键信息并生成结构化摘要。"
    },
    {
      "role": "user",
      "content": "请分析以下推文并生成摘要:\n\n[推文数据JSON数组]\n\n时间范围: 2025-11-17 00:00:00 到 2025-11-18 00:00:00"
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "digest_result",
      "schema": {
        "type": "object",
        "properties": {
          "headline": {
            "type": "string",
            "description": "一句话总结本次摘要的核心内容"
          },
          "highlights": {
            "type": "array",
            "description": "重点内容列表,按重要性排序",
            "items": {
              "type": "object",
              "properties": {
                "title": {"type": "string", "description": "重点标题"},
                "summary": {"type": "string", "description": "2-3句话的详细说明"},
                "representative_urls": {
                  "type": "array",
                  "description": "代表性推文链接",
                  "items": {"type": "string"}
                },
                "score": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 10,
                  "description": "重要性评分(1-10)"
                }
              },
              "required": ["title", "summary", "representative_urls", "score"]
            }
          },
          "themes": {
            "type": "array",
            "description": "识别出的主要主题标签",
            "items": {"type": "string"}
          },
          "sentiment": {
            "type": "string",
            "enum": ["positive", "neutral", "negative", "mixed"],
            "description": "整体情感倾向"
          },
          "stats": {
            "type": "object",
            "description": "统计数据",
            "properties": {
              "total_posts_analyzed": {"type": "integer"},
              "unique_authors": {"type": "integer"},
              "total_engagement": {"type": "number"},
              "avg_engagement_per_post": {"type": "number"}
            },
            "required": ["total_posts_analyzed", "unique_authors", "total_engagement", "avg_engagement_per_post"]
          }
        },
        "required": ["headline", "highlights", "themes", "sentiment", "stats"]
      }
    }
  },
  "max_tokens": 4000
}
```

##### 响应结构

**成功响应:**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "{\"headline\":\"...\",\"highlights\":[...],\"themes\":[...],\"sentiment\":\"...\",\"stats\":{...}}"
      },
      "finish_reason": "stop"
    }
  ]
}
```

**LLM 返回的摘要结构说明:**

| 字段 | 类型 | 说明 |
|------|------|------|
| headline | string | 总体标题,一句话概括本次摘要 |
| highlights | array | 重点内容列表,每个包含 title, summary, representative_urls, score |
| themes | array | 识别出的主要主题标签列表 |
| sentiment | enum | 整体情感倾向: positive/neutral/negative/mixed |
| stats | object | 统计数据: 推文总数、独立作者数、总互动量、平均互动量 |

**JSON Schema 约束的作用:**
- 强制 LLM 返回符合预定义结构的 JSON 数据
- 避免自由文本格式导致的解析错误
- 确保所有必需字段都存在
- 验证数据类型和取值范围

#### 5. 渲染 Markdown 格式内容

将 LLM 返回的结构化数据转换为易读的 Markdown 格式:

**Markdown 模板结构:**
```markdown
# 📰 User Digest

**时间范围:** 2025-11-17 00:00:00 - 2025-11-18 00:00:00

## 📌 总览

{headline}

**情感倾向:** {sentiment}  
**主题标签:** {themes}

---

## 🔥 重点内容

### 1. {highlight.title} (评分: {highlight.score}/10)

{highlight.summary}

**相关推文:**
- {representative_url_1}
- {representative_url_2}

---

## 📊 统计数据

- **分析推文数:** {total_posts_analyzed}
- **独立作者数:** {unique_authors}
- **总互动量:** {total_engagement}
- **平均互动量:** {avg_engagement_per_post}
```

这个 Markdown 内容将用于邮件通知的正文。

#### 6. 保存摘要记录

创建 UserDigest 数据库记录:

**字段说明:**
- `user_id`: 关联的用户 UUID
- `topic_ids`: 包含的话题 ID 列表(JSONB 数组)
- `time_window_start`: 时间窗口起始时间(UTC)
- `time_window_end`: 时间窗口结束时间(UTC)
- `summary_json`: LLM 返回的完整 JSON 结构(JSONB 字段)
- `rendered_content`: 渲染后的 Markdown 内容(TEXT 字段)
- `created_at`: 记录创建时间(自动生成)

**数据库操作:**
1. 创建 UserDigest 对象
2. 调用 `session.add(user_digest)`
3. 调用 `session.flush()` 获取自动生成的摘要 ID
4. 提交事务 `session.commit()`

#### 7. 触发下一步流程

- 自动触发通知推送流程 (`notify_user_digest`)
- 传递摘要 ID 作为唯一参数
- 使用 Celery 的 `.delay()` 方法异步调用

### 错误处理和重试

**确定性错误(不重试):**
- 参数验证失败(缺失、格式错误)
- UUID 格式错误
- ISO 时间字符串解析失败
- 返回错误字典,标记 `_deterministic: true`

**瞬时性错误(可重试):**
- LLM API 调用失败
- 数据库连接超时
- 网络请求失败
- 最多重试 1 次,重试间隔 30 秒

**重试逻辑:**
```python
if self.request.retries < self.max_retries:
    countdown = 30  # 30 seconds
    raise self.retry(exc=e, countdown=countdown)
```

### 关键技术点

1. **JSON Schema 约束**
   - 使用 `response_format` 参数强制 LLM 返回结构化数据
   - 避免自由文本格式导致的解析错误
   - 确保数据完整性和一致性

2. **多提供商支持**
   - 支持 DeepSeek、OpenAI、GLM 等兼容 OpenAI API 的服务
   - 通过配置切换不同的 LLM 提供商
   - 统一的 API 调用接口

3. **双格式存储**
   - JSON 格式用于 API 响应和数据分析
   - Markdown 格式用于邮件通知和人类阅读
   - 避免重复渲染,提高性能

4. **错误语义区分**
   - 确定性错误直接返回,不浪费重试资源
   - 瞬时性错误自动重试,提高成功率

---

## Task 3: 通知推送流程

### 触发方式

- **自动触发:** 由摘要生成流程自动触发
- **手动触发:** 用户可以通过 API 手动触发已生成摘要的重新推送

### 业务目标

将生成的摘要通过用户配置的通知渠道(飞书、邮件)发送给用户,并记录推送状态。

### 执行流程

#### 1. 加载摘要和用户信息

- 根据摘要 ID 查询 UserDigest 记录
- 使用 SQLAlchemy 的 `selectinload` 预加载关联的用户信息
- SQL 查询: `SELECT * FROM user_digests WHERE id = ? JOIN users ...`
- 如果摘要不存在,返回错误

#### 2. 确定通知渠道

根据用户配置的开关决定使用哪些渠道:

**飞书通知条件:**
- `user.enable_feishu = true`
- `user.feishu_webhook_url` 不为空

**邮件通知条件:**
- `user.enable_email = true`
- `user.email` 不为空

**渠道列表构建:**
```python
channels = []
if user.enable_feishu and user.feishu_webhook_url:
    channels.append("feishu")
if user.enable_email and user.email:
    channels.append("email")
```

如果没有启用任何渠道,流程结束(返回成功状态)。

#### 3. 幂等性检查(防止重复推送)

**目的:** 防止任务重试时产生重复推送

**实现机制:**
- 查询数据库是否已存在相同的推送记录
- 查询条件: `user_digest_id = ? AND user_id = ? AND channel = ?`
- 如果存在,复用该记录而不是创建新记录
- 如果不存在,创建新的 Delivery 记录

**SQL 查询:**
```sql
SELECT * FROM deliveries
WHERE user_digest_id = ?
  AND user_id = ?
  AND channel = ?
```

#### 4. 逐个渠道发送通知

对每个启用的渠道执行以下操作:

##### 4.1 飞书 Webhook 推送

**API 端点:**
```
POST {user.feishu_webhook_url}
```

**请求头:**
```http
Content-Type: application/json
```

**签名验证(如果配置了 webhook_secret):**

1. 生成时间戳(当前时间的秒级 Unix 时间戳)
2. 拼接字符串: `{timestamp}\n{webhook_secret}`
3. 使用 HMAC-SHA256 算法计算签名
4. Base64 编码签名结果

**Python 实现:**
```python
import hmac
import hashlib
import base64
import time

timestamp = str(int(time.time()))
string_to_sign = f"{timestamp}\n{webhook_secret}"
hmac_code = hmac.new(
    webhook_secret.encode("utf-8"),
    string_to_sign.encode("utf-8"),
    digestmod=hashlib.sha256
).digest()
sign = base64.b64encode(hmac_code).decode("utf-8")
```

**请求体(富文本卡片格式):**
```json
{
  "timestamp": "1700000000",
  "sign": "xxx",
  "msg_type": "interactive",
  "card": {
    "header": {
      "title": {
        "tag": "plain_text",
        "content": "📰 User Digest"
      },
      "template": "blue"
    },
    "elements": [
      {
        "tag": "div",
        "text": {
          "tag": "lark_md",
          "content": "**{headline}**"
        }
      },
      {
        "tag": "hr"
      },
      {
        "tag": "div",
        "text": {
          "tag": "lark_md",
          "content": "🔥 **重点内容**\n\n{highlights_formatted}"
        }
      },
      {
        "tag": "div",
        "text": {
          "tag": "lark_md",
          "content": "🏷️ **主题**: {themes_joined}"
        }
      },
      {
        "tag": "div",
        "text": {
          "tag": "lark_md",
          "content": "📊 **统计**: 分析了 {total_posts} 条推文,来自 {unique_authors} 位作者"
        }
      },
      {
        "tag": "note",
        "elements": [
          {
            "tag": "plain_text",
            "content": "时间范围: {window_start} - {window_end}"
          }
        ]
      }
    ]
  }
}
```

**飞书卡片元素说明:**

| 元素类型 | tag | 用途 |
|---------|-----|------|
| 标题 | header | 卡片顶部标题,支持颜色模板 |
| 文本块 | div + lark_md | 支持 Markdown 格式的文本内容 |
| 分隔线 | hr | 视觉分隔 |
| 备注 | note | 次要信息,灰色小字 |

**飞书 Webhook 响应:**
```json
{
  "code": 0,
  "msg": "success"
}
```

**错误处理:**
- 如果 `code` 不为 0,视为发送失败
- 记录错误信息到 Delivery 记录的 `error_msg` 字段
- 常见错误码:
  - `9499`: 签名验证失败
  - `19021`: Webhook URL 无效
  - `19024`: 消息格式错误

##### 4.2 邮件推送

**SMTP 配置:**

| 配置项 | 环境变量 | 说明 |
|--------|---------|------|
| 服务器地址 | EMAIL_HOST | 如 smtp.gmail.com |
| 端口 | EMAIL_PORT | 通常为 587(STARTTLS) |
| 发件人 | EMAIL_FROM | 发件人邮箱地址 |
| 用户名 | EMAIL_USERNAME | SMTP 认证用户名 |
| 密码 | EMAIL_PASSWORD | SMTP 认证密码 |
| 加密方式 | - | STARTTLS(端口 587) |

**邮件内容:**
- **收件人:** `user.email`
- **主题:** `Digest: User Digest`
- **正文格式:** HTML(将 Markdown 转换为 HTML)
- **正文内容:** 使用摘要的 `rendered_content` 字段

**Markdown 转 HTML:**
- 使用 Python 的 `markdown` 库
- 支持表格、代码块、链接等扩展语法
- 添加 CSS 样式美化显示

**邮件 HTML 模板:**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
    }
    h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    h2 { color: #34495e; margin-top: 30px; }
    h3 { color: #7f8c8d; }
    a { color: #3498db; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .highlight {
      background-color: #ecf0f1;
      padding: 15px;
      margin: 15px 0;
      border-left: 4px solid #3498db;
      border-radius: 4px;
    }
    .stats {
      background-color: #f8f9fa;
      padding: 15px;
      border-radius: 4px;
      margin-top: 20px;
    }
    code {
      background-color: #f4f4f4;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Courier New', monospace;
    }
  </style>
</head>
<body>
  {Markdown转HTML的内容}
</body>
</html>
```

**日志模式(开发环境):**
- 如果 `EMAIL_LOG_ONLY = True`,不实际发送邮件
- 只将邮件内容记录到日志中
- 用于开发和测试环境,避免误发邮件

**SMTP 发送流程:**
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

msg = MIMEMultipart("alternative")
msg["Subject"] = subject
msg["From"] = EMAIL_FROM
msg["To"] = to_email

html_part = MIMEText(html_content, "html")
msg.attach(html_part)

with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
    server.starttls()
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    server.send_message(msg)
```

#### 5. 更新推送记录状态

对每个渠道的推送结果进行状态更新:

**成功情况:**
- 设置 `delivery.status = "success"`
- 记录发送时间 `delivery.sent_at = datetime.now(UTC)`
- 记录日志包含: 渠道、用户 ID、摘要 ID、推送记录 ID

**日志示例:**
```
INFO: Sent feishu notification to user@example.com
  channel=feishu user_id=xxx user_digest_id=yyy delivery_id=zzz
```

**失败情况:**
- 设置 `delivery.status = "failed"`
- 记录错误信息到 `delivery.error_msg`
- 增加重试计数 `delivery.retry_count += 1`
- 记录错误日志包含: 渠道、用户 ID、摘要 ID、错误详情

**错误日志示例:**
```
ERROR: Failed to send email notification to user@example.com: SMTP authentication failed
  channel=email user_id=xxx user_digest_id=yyy
```

#### 6. 提交数据库事务

- 保存所有推送记录的状态更新
- 使用 `session.commit()` 提交事务
- 返回推送结果统计

**返回结果:**
```json
{
  "status": "success",
  "user_digest_id": "uuid",
  "channels": ["feishu", "email"],
  "successful": 2,
  "failed": 0
}
```

### 错误处理和重试

**单渠道失败处理:**
- 单个渠道失败不影响其他渠道的推送
- 每个渠道的错误独立记录
- 部分成功也视为任务成功

**任务级别重试:**
- 如果所有渠道都失败,任务会重试
- 最多重试 2 次
- 重试间隔:
  - 第 1 次重试: 60 秒后
  - 第 2 次重试: 120 秒后

**重试逻辑:**
```python
if self.request.retries < self.max_retries:
    countdown = 60 * (self.request.retries + 1)
    raise self.retry(exc=e, countdown=countdown)
```

**幂等性保证:**
- 重试时复用已存在的 Delivery 记录
- 避免重复推送给用户
- 通过数据库唯一性约束实现

### 关键技术点

1. **飞书 Webhook 签名验证**
   - 使用 HMAC-SHA256 算法确保消息来源可信
   - 防止 Webhook URL 被恶意调用
   - 时间戳防止重放攻击

2. **飞书富文本卡片**
   - 使用交互式卡片提供更好的视觉体验
   - 支持 Markdown 格式的文本内容
   - 支持多种元素类型(标题、文本、分隔线、备注等)

3. **邮件日志模式**
   - 开发环境不实际发送邮件
   - 避免误发邮件给真实用户
   - 便于调试和测试

4. **推送记录追踪**
   - 每次推送都创建 Delivery 记录
   - 记录状态、重试次数、错误信息
   - 便于排查问题和统计分析

5. **幂等性设计**
   - 防止重试导致的重复通知
   - 通过数据库查询复用已存在的记录
   - 提高系统可靠性

---

## 附录

### 环境变量配置清单

#### Twitter API 配置
- `X_PROVIDER`: "TWITTER_API" 或 "MOCK"
- `TWITTER_API_KEY`: twitterapi.io API Key
- `TWITTER_API_BASE_URL`: https://api.twitterapi.io
- `TWITTER_API_TIMEOUT_SECONDS`: 30
- `TWITTER_API_MAX_PAGES`: 5

#### LLM Chat API 配置
- `LLM_CHAT_BASE_URL`: Chat API 基础 URL
- `LLM_CHAT_MODEL`: 模型名称(如 deepseek-chat)
- `LLM_CHAT_API_KEY`: Chat API Key
- `LLM_MAX_TOKENS`: 4000

#### LLM Embedding API 配置
- `LLM_EMBEDDING_PROVIDER`: "openai" 或 "ollama"
- `OPENAI_EMBEDDING_BASE_URL`: Embedding API 基础 URL
- `OPENAI_EMBEDDING_MODEL`: 模型名称(如 embedding-3)
- `OPENAI_EMBEDDING_API_KEY`: Embedding API Key
- `LLM_EMBEDDING_RETRY_MAX_ATTEMPTS`: 5
- `LLM_EMBEDDING_RETRY_INITIAL_BACKOFF`: 1.0

#### 邮件配置
- `EMAIL_HOST`: SMTP 服务器地址
- `EMAIL_PORT`: SMTP 端口(587)
- `EMAIL_FROM`: 发件人邮箱
- `EMAIL_USERNAME`: SMTP 用户名
- `EMAIL_PASSWORD`: SMTP 密码
- `EMAIL_LOG_ONLY`: True(开发) / False(生产)

#### 时区配置
- `CRON_TIMEZONE`: Asia/Shanghai(或其他 IANA 时区名称)

### 数据库表结构

#### users 表
- `id`: UUID, 主键
- `name`: VARCHAR(255), 可空
- `email`: VARCHAR(255), 唯一, 非空
- `feishu_webhook_url`: TEXT, 可空
- `feishu_webhook_secret`: VARCHAR(255), 可空
- `topics`: JSONB, 非空, 默认 []
- `enable_feishu`: BOOLEAN, 非空, 默认 true
- `enable_email`: BOOLEAN, 非空, 默认 true
- `created_at`: TIMESTAMP WITH TIME ZONE

#### topics 表
- `id`: UUID, 主键
- `name`: VARCHAR(255), 非空
- `query`: TEXT, 非空
- `is_enabled`: BOOLEAN, 非空, 默认 true
- `last_tweet_id`: VARCHAR(255), 可空, 索引
- `last_item_created_at`: TIMESTAMP WITH TIME ZONE, 可空
- `created_at`: TIMESTAMP WITH TIME ZONE

#### items 表
- `id`: UUID, 主键
- `topic_id`: UUID, 外键 → topics.id, 非空
- `source_id`: VARCHAR(255), 唯一, 非空, 索引
- `author`: VARCHAR(255), 可空
- `text`: TEXT, 可空
- `url`: TEXT, 可空
- `created_at`: TIMESTAMP WITH TIME ZONE, 非空
- `collected_at`: TIMESTAMP WITH TIME ZONE, 默认 now()
- `media_urls`: JSONB, 可空
- `metrics`: JSONB, 可空
- `embedding_hash`: VARCHAR(64), 可空, 索引

#### user_digests 表
- `id`: UUID, 主键
- `user_id`: UUID, 外键 → users.id, 非空
- `topic_ids`: JSONB, 非空
- `time_window_start`: TIMESTAMP WITH TIME ZONE, 非空
- `time_window_end`: TIMESTAMP WITH TIME ZONE, 非空
- `summary_json`: JSONB, 非空
- `rendered_content`: TEXT, 非空
- `created_at`: TIMESTAMP WITH TIME ZONE, 默认 now()

#### deliveries 表
- `id`: UUID, 主键
- `user_digest_id`: UUID, 外键 → user_digests.id, 可空
- `user_id`: UUID, 外键 → users.id, 非空
- `channel`: VARCHAR(50), 非空
- `status`: VARCHAR(50), 非空, 默认 "pending"
- `retry_count`: INTEGER, 非空, 默认 0
- `error_msg`: TEXT, 可空
- `sent_at`: TIMESTAMP WITH TIME ZONE, 可空
- `created_at`: TIMESTAMP WITH TIME ZONE, 默认 now()

### 常见问题排查

#### 1. Twitter API 认证失败
- 检查 `TWITTER_API_KEY` 是否正确
- 确认 API Key 是否已激活
- 查看 twitterapi.io 账户余额

#### 2. 推文采集为空
- 检查话题的 `query` 字段格式是否正确
- 确认用户名是否存在
- 查看 `last_tweet_id` 是否过新(导致没有新推文)

#### 3. LLM 摘要生成失败
- 检查 `LLM_CHAT_API_KEY` 是否正确
- 确认 API 余额是否充足
- 查看 LLM 服务是否正常

#### 4. 飞书通知发送失败
- 检查 `feishu_webhook_url` 是否正确
- 确认 Webhook 签名是否配置正确
- 查看飞书机器人是否被禁用

#### 5. 邮件发送失败
- 检查 SMTP 配置是否正确
- 确认 `EMAIL_PASSWORD` 是否为应用专用密码
- 查看邮箱是否开启了 SMTP 服务

---

**文档版本:** 1.0  
**最后更新:** 2026-03-08  
**维护者:** X-News-Digest Team
