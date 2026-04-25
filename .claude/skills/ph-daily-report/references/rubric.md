# Product Hunt Daily Report Rubric

Use this reference after `fetch_launches.sh` produces the launch pool and again after `fetch_details.sh` enriches selected products.

The report serves three reader needs at once:

- AI / developer tools / independent builder usefulness.
- Product Hunt attention and launch momentum.
- Startup and market-opportunity scouting.

Votes, comments, and rank are attention signals. They are never final inclusion reasons by themselves.

## Shallow Screen

Input: `data.launches` from `/tmp/phx_launches.json`.

Select `10-15` slugs for detail fetch. The goal is coverage for final judgment, not final recommendation.

Use this JSON shape while screening:

```json
{
  "selected_for_detail": [
    {
      "slug": "product-slug",
      "name": "Product Name",
      "provisional_reason": "Why this deserves detail fetch before final judgment",
      "signals": ["rank_1", "devtools_topic", "clear_tagline"]
    }
  ],
  "held_for_top_list_only": [
    {
      "slug": "other-product",
      "reason": "Visible but unlikely to need detail fetch"
    }
  ]
}
```

Prioritize:

- Clear developer, AI, infrastructure, automation, design, productivity, or founder workflow relevance.
- Strong rank/votes/comments combined with a clear problem statement.
- Products whose tagline or topics suggest a new market wedge.
- A few wildcards when the category is unusual and could reveal an emerging use case.

Avoid selecting only by rank. Include lower-ranked products when their tagline, topics, or audience fit looks stronger than hotter but generic launches.

## Final Selection Dimensions

After details are fetched, judge each enriched product on:

| Dimension | What to look for |
|---|---|
| `developer_value` | Could it change a developer workflow, toolchain, automation pattern, or technical choice? |
| `startup_signal` | Does it reveal a new market, underserved niche, positioning opportunity, distribution tactic, or buyer pain? |
| `product_clarity` | Are tagline, description, website, media, links, topics, and makers enough to understand what it does? |
| `novelty` | Is there a meaningful difference from common wrappers, dashboards, AI chat surfaces, or generic SaaS? |
| `evidence_strength` | Do Product Hunt metadata and available links support the claim? |
| `audience_fit` | Is it useful for AI practitioners, developers, independent builders, startup operators, or technical product readers? |

## Demerits

Reject or downgrade products with:

- Vague tagline or description.
- Generic AI wrapper with no visible differentiation.
- High rank but little product clarity.
- Consumer novelty with limited relevance to the target reader.
- Claims that require external facts not present in Product Hunt data.
- Broken or missing website/product links when the website is needed to understand the product.
- Product Hunt metadata that is too thin to support a meaningful judgment.

## Final Output Guidance

Pick `3-5` deep selections. Prefer `3` strong entries over padding to `5`.

Optimize for mix:

- 1-2 AI / developer workflow products.
- 1 startup or market signal.
- 1 productivity, design, data, infrastructure, or independent-builder wildcard.

Always record `3-5` rejected high-attention products. Good rejected reasons look like:

- "热度高，但 Product Hunt 信息只显示通用 AI 包装，差异点不足。"
- "定位清楚但读者相关性弱，更适合榜单速览。"
- "评论和票数不错，但缺少 website/media/detail 支撑，无法形成可靠判断。"

## Evidence Rules

- Product names, taglines, topics, makers, and links stay in English.
- Analysis and judgment are written in Chinese.
- Do not invent competitors, funding, users, pricing, maker backgrounds, or traction.
- If a statement is inferred from Product Hunt metadata, label it as inference.
- If the website link exists but was not opened, do not claim website-only facts.
- Treat votes, comments, and rank as "PH signals", not proof of product quality.
