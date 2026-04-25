# HN Digest Rubric & Schemas

This is the detailed reference for `hn-daily-report`. Read it when you start Step 2 (story screen) or Step 4 (thread analysis). It holds the scoring criteria and the exact JSON shapes you should produce between steps.

## Table of contents

- [Story screen rubric](#story-screen-rubric)
- [Story screen output schema](#story-screen-output-schema)
- [Thread analysis criteria](#thread-analysis-criteria)
- [Thread analysis output schema](#thread-analysis-output-schema)
- [Value types](#value-types)
- [Evidence roles](#evidence-roles)
- [Why not scripts](#why-not-scripts)

---

## Story screen rubric

For each story in the pool, score six dimensions on a 0–5 scale. Do not average them — use them as lenses, and weight by what matters for this particular story.

| Dimension | Question |
|---|---|
| `decision_value` | Would reading this help a reader make a technical, product, or architectural call? |
| `discussion_potential` | Does the comment count / title / topic suggest a real debate or firsthand reports — not just applause or flamewar? |
| `novelty` | Is the information non-obvious? Does it push past what an informed reader already knows? |
| `practitioner_signal` | Likely to attract actual users, maintainers, operators, founders, researchers — people with skin in the game? |
| `transferability` | Can the insight transfer to the reader's own work, or is it a one-off curiosity? |
| `audience_fit` | Does it match the digest's target reader (technical founder / infra engineer / independent dev / tech product judge)? If a theme was specified in Step 0, factor it in — but don't let it override quality. |

### Demerits (demote or reject)

- High attention but no technical / decision content. Pure news.
- Primarily ideology, tribalism, or emotional venting.
- The linked article itself matters but the HN thread adds nothing.
- Title sounds like a tool / project, but the thread has ~no user feedback.
- Off-theme when a theme was specified, unless its second-order impact is unusually large.

### Priority buckets

- `thread_priority: high` — strong on multiple dimensions, likely to reward fetching the full comment tree. Aim for 5–8 of these per run.
- `thread_priority: medium` — worth a quick look with a lighter `--max-depth 3 --max-comments 40` fetch if you have budget.
- `thread_priority: low` — do not fetch the thread. Either reject or keep as background.

### What not to do

- Do not use `score > X` as a filter. High-score news stories with 12 comments are usually rejects. Low-score (40–80 points) stories with a strong firsthand lead comment are often the best content of the day.
- Do not filter by keyword. A title containing "Rust" or "AI" is not more valuable than one that doesn't. Read it semantically.
- Do not reject `ask_hn` / `show_hn` posts by default. Some of the best firsthand content lives there.

---

## Story screen output schema

Produce this between Step 2 and Step 3. You don't have to write it to disk, but keeping it inline in your working notes lets Step 5 produce a clean "rejected" table and "数据概览" row.

```json
{
  "candidates": [
    {
      "id": 123,
      "title": "...",
      "hn_url": "https://news.ycombinator.com/item?id=123",
      "source_url": "...",
      "score": 321,
      "comment_count": 87,
      "value_type": "firsthand_experience",
      "rubric": {
        "decision_value": 4,
        "discussion_potential": 5,
        "novelty": 3,
        "practitioner_signal": 4,
        "transferability": 4,
        "audience_fit": 5
      },
      "why_candidate": "Why it's worth fetching the thread, not just the headline.",
      "risk": "What might make it worthless; what thread evidence would confirm or kill it.",
      "thread_priority": "high"
    }
  ],
  "rejected": [
    {
      "id": 456,
      "title": "...",
      "score": 812,
      "comment_count": 45,
      "reason": "High attention but thread is thin; article self-contained, no practitioner signal."
    }
  ]
}
```

Keep at least 3 entries in `rejected` — they go into the "被拒绝的热门内容" table in the final report and calibrate future runs.

---

## Thread analysis criteria

When reading a thread JSON, your job is **not** to summarize every comment. It is to find the evidence a reader would need to update their prior.

### Prefer threads that have at least one of:

- **Firsthand experience** — commenter says "I built / ran / maintained / migrated / paid for / hit this in prod".
- **High-quality counterpoint** — not mere disagreement, but naming a boundary condition, hidden cost, alternative explanation, or concrete counterexample.
- **Transferable engineering lesson** — something you'd apply in selection, architecture, debugging, org process, or product judgment.
- **Multi-angle perspective** — dev / user / maintainer / founder / regulator / industry participant voices that complement each other.
- **Concrete detail** — numbers, versions, architectures, cost breakdowns, failure modes, constraints, alternatives tried and why.

### Downgrade or reject threads that are:

- Mostly jokes, emotional takes, tribalism, or echoes of the same point.
- Long top comments that pad but add no new verifiable information.
- Cases where only the external article is worth reading; HN adds no insight.
- Impossible to trace back to a specific story / comment without guessing.

### Minimum bar for `verdict: include`

- ≥ 2 independent evidence comments, **or**
- 1 very strong firsthand comment on a story that is itself clearly important, **or**
- Discussion is thin but the topic and source carry clear decision value for the target reader (use sparingly — this is the easiest place to over-select).

If you can't meet one of those, the verdict is `reject`. Write the reason. A report with 3 strong entries and 7 honest rejections is better than 5 padded entries.

---

## Thread analysis output schema

One JSON object per thread, in your working notes (they become the source for Step 5 prose):

```json
{
  "story_id": 123,
  "title": "...",
  "verdict": "include",
  "value_type": "firsthand_experience",
  "thesis": "The single most useful judgment a reader should take from this discussion.",
  "why_now": "Why it matters this week. If it's not time-sensitive, state the long-term value.",
  "target_reader": "Who specifically should read this.",
  "evidence": [
    {
      "comment_id": 124,
      "author": "hn_user",
      "hn_url": "https://news.ycombinator.com/item?id=124",
      "role": "firsthand",
      "paraphrase": "Your paraphrase of what evidence this comment provides.",
      "confidence": "high"
    },
    {
      "comment_id": 131,
      "author": "other_user",
      "hn_url": "https://news.ycombinator.com/item?id=131",
      "role": "counterexample",
      "paraphrase": "...",
      "confidence": "medium"
    }
  ],
  "debate_map": [
    "Position A: ...",
    "Position B / counter: ...",
    "More defensible conclusion: ..."
  ],
  "practical_takeaway": "Concrete judgment or action the reader can apply.",
  "caveats": ["Boundary conditions, risks, unresolved questions."],
  "reject_reason": null
}
```

For `verdict: reject`, set `reject_reason` and you can leave `evidence` / `debate_map` / `practical_takeaway` empty. Keep rejected thread notes — they're useful for the rejected table and for understanding what the screen let through that the threads didn't support.

---

## Value types

Use these as the `value_type` label. They also drive the diversity check in Step 5 (final selection aims for a mix across types, not five of the same flavor).

| Value type | Meaning |
|---|---|
| `firsthand_experience` | Someone actually did / shipped / ran / suffered the thing. |
| `tool` | A specific tool, library, framework, or CLI — with user feedback that helps selection. |
| `industry_shift` | Platform / regulatory / market change that changes what you'd build or how. |
| `research` | A paper, preprint, or result that alters what's believed possible. |
| `incident` | Outage / breach / migration gone wrong with a usable postmortem. |
| `ask_hn` | Question-driven thread where the answers are the value. |
| `show_hn` | Project launch with meaningful user / maintainer feedback (not just applause). |
| `other` | Doesn't fit; use sparingly and explain in `thesis`. |

---

## Evidence roles

Tag each evidence comment with one of these. The mix tells you whether the thread is balanced.

| Role | Meaning |
|---|---|
| `firsthand` | Commenter's own experience with the thing under discussion. |
| `counterexample` | A concrete case that breaks the main claim. |
| `alternative` | A different approach that's worth comparing. |
| `caveat` | A boundary condition or hidden cost the OP missed. |
| `context` | Background that makes the story readable (history, prior art, terminology). |
| `data_point` | Numbers, benchmarks, version details, or other quantifiable evidence. |

A thread with only `context` comments usually isn't strong enough to include. Look for at least one of `firsthand` / `counterexample` / `alternative` / `data_point`.

---

## Why not scripts

The SOP (`docs/hnx/hn-digest-sop.md`) explains the reasoning in detail. The short version:

- Keyword filters are fragile. They miss high-value discussions without the expected terms and admit low-value ones that happen to include them.
- Score thresholds conflate attention with quality. A day's best thread is often well below the day's highest score.
- Truncated-preview summarizers mistake the opening of a long comment for its point.
- Tight coupling of fetch + screen + summarize makes the skill hard to adjust per-run.

`hnx` gives you deterministic fetching with a stable envelope. Everything from that JSON to the final markdown is an AI judgment call. When a run goes wrong, the fix is almost always "read more comments" or "tighten the rubric in your head for this run", not "add a new regex".
