**简体中文** | [English](README.en.md)

# twx

`twx` 是一个面向 harness agent 和自动化工作流的 JSON-first Twitter/X CLI。它封装了
[twitterapi.io](https://twitterapi.io) 的只读接口，并把结果以稳定、机器可读的 JSON 输出到 stdout。

这个项目刻意保持简单：

- 没有数据库
- 没有 Web 服务
- 没有任务队列
- 没有交互式提示
- 没有只适合人看的富文本输出

如果你需要一个能被 agent 快速安装、稳定调用、方便重定向和解析的 CLI，`twx` 的目标就是这个场景。

## 快速开始

前置要求：

- Python 3.10+
- 一个 [twitterapi.io](https://twitterapi.io) API Key

安装：

```bash
git clone https://github.com/tpiperatgod/twx.git
cd twx

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

配置环境变量并试跑：

```bash
export TWITTER_API_KEY=your_twitterapi_io_key

twx user --username karpathy --limit 10
twx search --query "AI agents" --mode top --limit 5
twx trending --ranking engagement --limit 20
```

更完整的安装、环境变量和示例见 [Quickstart](docs/quickstart.md)。

## 为什么适合 Harness Agent

- 成功输出始终是单个 JSON 对象，写到 stdout。
- 失败输出是结构化 JSON，写到 stderr。
- exit code 稳定，便于自动化判断和重试。
- Tweet 会被规整到统一 schema，减少上游字段波动带来的解析成本。
- `--raw` 可在调试或迁移时带回原始上游 payload。

输出契约细节见 [Contracts](docs/contracts.md)。

## 文档导航

- [Documentation Index](docs/README.md)
- [Quickstart](docs/quickstart.md)
- [Commands](docs/commands.md)
- [Contracts](docs/contracts.md)
- [Limitations](docs/limitations.md)
- [Development](docs/development.md)

## 一眼看懂

- `twx user`：抓取某个账号的时间线
- `twx search`：按关键词搜索推文
- `twx trending`：返回当前“trending”搜索结果，可按互动量重排

命令示例和参数说明见 [Commands](docs/commands.md)。

## Claude Code Skill

仓库内置了一个 Claude Code skill：[`.claude/skills/twitter-daily-report/`](.claude/skills/twitter-daily-report/SKILL.md)，把 `twx` 包装成自动化的每日 Tech Twitter 日报流程。

在 Claude Code 里说「今日日报」/「技术推特日报」/「today's report」就会触发完整流水线：

1. 并行调用 `twx user` 抓取一批预设的 Tech Twitter 账号。
2. 用 `♥ + 2×🔁 + 3×💬` 打分,挑出头条。
3. 渲染成 Markdown 报告,输出到 `docs/reports/daily-YYYY-MM-DD.md`。

账号清单写在 `scripts/fetch_tweets.sh`(`ACCOUNTS`)和 `scripts/analyze.py`(`ROLES`、`DISPLAY_NAMES`),要自定义就改这两处。个人 watchlist 放在 `watchlists/` 下,默认 gitignore。

## License

MIT
