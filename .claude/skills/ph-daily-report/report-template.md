# Product Hunt Daily Scout - {YYYY-MM-DD}

> 数据来源：`phx launches` + `phx product`  
> 输出语言：产品名、tagline、topics、makers 和原始链接保留英文；判断与分析用中文。  
> 筛选原则：rank / votes / comments 是注意力信号，不是最终入选理由。

---

## 今日判断

{用 3-5 句话总结当天 Product Hunt launch 的主线。不要罗列产品名，要提炼趋势、同质化问题、新机会或值得警惕的信号。}

---

## 深度精选

### 1. {product_name} - {tagline}

- Product Hunt: [{product_name}]({product_hunt_url})
- Website: [{website_domain_or_name}]({website_url})
- PH 信号：rank #{ranking} / {votes_count} votes / {comments_count} comments
- Topics: {topics}
- Makers: {makers}

**一句话判断**

{一句话说明为什么这个产品值得目标读者看。不要写"排名高"。}

**产品做什么**

{基于 Product Hunt tagline / description / links 说明产品功能。不要脑补。}

**为什么值得看**

{2-4 句。说明对 AI practitioners、developers、independent builders 或 startup operators 的价值。}

**市场/机会信号**

{说明它暴露的用户需求、定位方式、分发机会、市场 wedge 或同类产品趋势。无法从 PH 数据支持时标为推断。}

**风险与边界**

{说明信息不足、同质化、证据弱、website 缺失、目标用户过窄等边界。}

---

### 2. {product_name} - {tagline}

- Product Hunt: [{product_name}]({product_hunt_url})
- Website: [{website_domain_or_name}]({website_url})
- PH 信号：rank #{ranking} / {votes_count} votes / {comments_count} comments
- Topics: {topics}
- Makers: {makers}

**一句话判断**

{one_line_judgment}

**产品做什么**

{what_it_does}

**为什么值得看**

{why_it_matters}

**市场/机会信号**

{market_signal}

**风险与边界**

{caveat}

---

### 3. {product_name} - {tagline}

- Product Hunt: [{product_name}]({product_hunt_url})
- Website: [{website_domain_or_name}]({website_url})
- PH 信号：rank #{ranking} / {votes_count} votes / {comments_count} comments
- Topics: {topics}
- Makers: {makers}

**一句话判断**

{one_line_judgment}

**产品做什么**

{what_it_does}

**为什么值得看**

{why_it_matters}

**市场/机会信号**

{market_signal}

**风险与边界**

{caveat}

---

## 今日榜单速览

| Rank | Product | Tagline | PH Signal | Topics | 备注 |
|---:|---|---|---:|---|---|
| #{ranking} | [{product_name}]({product_hunt_url}) | {tagline} | {votes_count} votes / {comments_count} comments | {topics} | {one_line_note} |

---

## 被拒绝的热门产品

| Product | PH Signal | 拒选原因 |
|---|---:|---|
| [{product_name}]({product_hunt_url}) | rank #{ranking} / {votes_count} votes / {comments_count} comments | {reason} |

---

## 数据概览

| 指标 | 数值 |
|---|---:|
| Launch pool | {launch_count} |
| Detail fetched | {detail_count} |
| Detail errors | {detail_error_count} |
| Final picks | {included_count} |
| Rejected hot products | {rejected_count} |
| Top topics | {top_topics} |
| Highest votes | {highest_votes_product} |
| Most comments | {most_comments_product} |

---

## 方法说明

- `phx launches` 提供当天 Product Hunt ranked launch pool。
- skill 先对 launch pool 做浅筛，再用 `phx product` 拉取部分产品详情。
- AI 负责判断产品价值、创业信号、同质化风险和报告写作。
- 所有 Product Hunt 原始字段保持可追溯；无法从 PH 数据支持的判断应删除或标为推断。

---

*本报告由 `phx` 数据驱动生成。*
