# HN 高价值内容报告 — {YYYY-MM-DD}

> 数据来源：`hnx top` / `hnx best` / `hnx new` 候选池 + `hnx thread` 评论树  
> 目标读者：{target_reader}  
> 筛选原则：只收录能帮助读者做技术、产品、架构或行业判断的讨论；`score` 和 `comment_count` 只作为注意力信号，不作为入选理由。

---

## 今日判断

{用 3-5 句话总结当天 HN 高价值讨论的主线。不要罗列标题，要提炼趋势、冲突或共同问题。}

示例写法：

- 今天的高价值讨论集中在 {theme_1} 和 {theme_2}。
- 多个 thread 的共同分歧是 {core_tension}。
- 对读者最有用的判断是 {practical_judgment}。

---

## 快速导航

| # | 主题 | 类型 | 为什么值得读 | HN |
|---:|---|---|---|---|
| 1 | {short_topic} | {value_type} | {one_line_value} | [讨论]({hn_url}) |
| 2 | {short_topic} | {value_type} | {one_line_value} | [讨论]({hn_url}) |
| 3 | {short_topic} | {value_type} | {one_line_value} | [讨论]({hn_url}) |

---

## 精选条目

### 1. {headline}

- 类型：{firsthand_experience | tool | industry_shift | research | incident | ask_hn | show_hn | other}
- 原文：[{source_title_or_domain}]({source_url})
- HN 讨论：[item?id={story_id}]({hn_url})
- HN 信号：{score} points / {comment_count} comments

**为什么值得读**

{一句话说明这条内容的决策价值。不要写“因为分数高”或“评论多”，要说明它能改变什么判断。}

**核心洞察**

{2-4 句，综合 story 和评论区。先写结论，再写原因。避免复述标题。}

**争论脉络**

- 观点 A：{主要支持观点或原文主张。}
- 观点 B / 反驳：{评论区中最强的反例、边界条件或替代解释。}
- 更稳妥的结论：{在证据约束下可以相信什么，不能过度推出什么。}

**实操启发**

{读者可以如何应用到技术选型、架构设计、产品判断、团队流程、学习路线或风险识别。}

**证据**

- [{comment_author}]({comment_hn_url})：{该评论提供的一手经验、反例、替代方案、上下文或数据点。}
- [{comment_author}]({comment_hn_url})：{该评论提供的一手经验、反例、替代方案、上下文或数据点。}
- [{comment_author}]({comment_hn_url})：{可选，只有确实增加信息时保留。}

**注意边界**

{这条结论在哪些条件下可能不成立；哪些信息仍然缺失；哪些判断只是推测。}

---

### 2. {headline}

- 类型：{value_type}
- 原文：[{source_title_or_domain}]({source_url})
- HN 讨论：[item?id={story_id}]({hn_url})
- HN 信号：{score} points / {comment_count} comments

**为什么值得读**

{one_sentence_decision_value}

**核心洞察**

{summary}

**争论脉络**

- 观点 A：{claim}
- 观点 B / 反驳：{counterpoint}
- 更稳妥的结论：{balanced_conclusion}

**实操启发**

{practical_takeaway}

**证据**

- [{comment_author}]({comment_hn_url})：{evidence_summary}
- [{comment_author}]({comment_hn_url})：{evidence_summary}

**注意边界**

{caveat}

---

### 3. {headline}

- 类型：{value_type}
- 原文：[{source_title_or_domain}]({source_url})
- HN 讨论：[item?id={story_id}]({hn_url})
- HN 信号：{score} points / {comment_count} comments

**为什么值得读**

{one_sentence_decision_value}

**核心洞察**

{summary}

**争论脉络**

- 观点 A：{claim}
- 观点 B / 反驳：{counterpoint}
- 更稳妥的结论：{balanced_conclusion}

**实操启发**

{practical_takeaway}

**证据**

- [{comment_author}]({comment_hn_url})：{evidence_summary}
- [{comment_author}]({comment_hn_url})：{evidence_summary}

**注意边界**

{caveat}

---

## 被拒绝的热门内容

> 这部分用于校准判断边界：热门但没有进入精选，不代表不重要，而是本次没有足够的 HN 讨论增量或决策价值。

| Story | HN 信号 | 拒选原因 |
|---|---:|---|
| [{title}]({hn_url}) | {score} / {comment_count} | {reason} |
| [{title}]({hn_url}) | {score} / {comment_count} | {reason} |
| [{title}]({hn_url}) | {score} / {comment_count} | {reason} |

---

## 数据概览

| 指标 | 数值 |
|---|---:|
| 候选 stories | {pool_story_count} |
| 初筛候选 | {candidate_count} |
| 抓取 threads | {thread_count} |
| 最终入选 | {included_count} |
| 拒选记录 | {rejected_count} |
| 主要类型 | {top_value_types} |

---

## 方法说明

- `hnx` 只负责拉取和归一化 HN 数据，输出稳定 JSON。
- AI 负责语义识别、过滤、争论脉络提取和报告写作。
- 每条入选内容必须能追溯到 story 或 comment 链接。
- 不把 `score`、`comment_count` 或标题关键词当作最终入选理由。
- 无法从 story/comment 支撑的判断，应删除或明确标注为推测。

---

*本报告由 `hnx` 数据驱动生成。*
