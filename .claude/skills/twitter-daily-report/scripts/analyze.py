#!/usr/bin/env python3
"""
Analyze fetched twx JSON dumps and emit a structured analysis JSON.

Input:  directory of <username>.json files produced by twx user.
Output: a single JSON document on stdout containing:
  - headlines: top N tweets across all accounts, deduped by account
  - by_role:   ordered role -> list of accounts with their tweets
  - stats:     overview metrics (active accounts, totals, max-likes tweet,
               keywords, zh/en ratio)
  - navigation: role -> (total_accounts, active_accounts)

The script does no natural-language rewriting — it only collects and ranks
raw data so the model can focus on writing headlines, summaries, and
background notes.

Usage:
  analyze.py <raw_dir> [--top N] > analysis.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Role order and account membership must match docs/tech-twitter-accounts.md.
# Accounts appearing in multiple roles are listed in each — the "primary"
# role shown in headlines is resolved via ACCOUNT_PRIMARY_ROLE below.
ROLES: list[tuple[str, str, list[str]]] = [
    ("tech_educator", "🎓", [
        "karpathy", "AndrewYNg", "sentdex", "rasbt",
        "dotey", "lijigang_com", "ruanyf",
    ]),
    ("ai_researcher", "🔬", [
        "ylecun", "goodfellow_ian", "karpathy",
        "soumithchintala", "indigo11", "karminski3",
    ]),
    ("thought_leader", "🧠", [
        "AndrewYNg", "esabraha", "kaifulee",
    ]),
    ("builder", "🏗️", [
        "levelsio", "karpathy", "aborroni",
        "op7418", "AlchainHust", "bourneliu66",
    ]),
    ("tech_newscaster", "📡", [
        "_akhaliq", "aabrazny", "IntuitMachine",
        "WaytoAGI", "Gorden_Sun", "shao__meng",
    ]),
    ("practitioner", "🔧", [
        "vista8", "oran_ge", "xicilion", "lifesinger",
    ]),
]

# When an account spans multiple roles, pick the most "content-defining" one
# for headline display. Order of ROLES above determines precedence unless
# overridden here.
ACCOUNT_PRIMARY_ROLE = {
    "karpathy": "tech_educator",
    "AndrewYNg": "tech_educator",
}

# Display names, pulled from docs/tech-twitter-accounts.md. Used in the
# per-role section header "@username — Display Name".
DISPLAY_NAMES = {
    "karpathy": "Andrej Karpathy",
    "AndrewYNg": "Andrew Ng",
    "sentdex": "Harrison Kinsley",
    "rasbt": "Sebastian Raschka",
    "dotey": "宝玉",
    "lijigang_com": "李继刚",
    "ruanyf": "阮一峰",
    "ylecun": "Yann LeCun",
    "goodfellow_ian": "Ian Goodfellow",
    "soumithchintala": "Soumith Chintala",
    "indigo11": "indigo / 芦义",
    "karminski3": "牙医",
    "esabraha": "Elon Scheckner",
    "kaifulee": "李开复",
    "levelsio": "Pieter Levels",
    "aborroni": "Alex Borroni",
    "op7418": "歸藏",
    "AlchainHust": "AI进化论-花生",
    "bourneliu66": "刘小排r",
    "_akhaliq": "A k h a l i q",
    "aabrazny": "Abrazny",
    "IntuitMachine": "IntuitMachine",
    "WaytoAGI": "WaytoAGI",
    "Gorden_Sun": "Gorden Sun",
    "shao__meng": "shao__meng",
    "vista8": "向阳乔木",
    "oran_ge": "Orange AI",
    "xicilion": "响马",
    "lifesinger": "玉伯 / Frank Wang",
}

# Stopwords for keyword extraction. Intentionally small — favor signal over
# exhaustiveness. The model can always re-rank if the picks look wrong.
STOPWORDS_EN = {
    "the", "a", "an", "and", "or", "but", "if", "then", "is", "are", "was",
    "were", "be", "been", "being", "to", "of", "in", "on", "for", "with",
    "at", "by", "from", "as", "it", "its", "this", "that", "these", "those",
    "i", "you", "he", "she", "we", "they", "my", "your", "our", "their",
    "have", "has", "had", "do", "does", "did", "will", "would", "can",
    "could", "should", "may", "might", "must", "not", "no", "yes", "so",
    "just", "only", "very", "more", "most", "some", "any", "all", "one",
    "two", "new", "like", "about", "get", "also", "via", "rt", "amp",
}

STOPWORDS_ZH = {
    "的", "了", "是", "我", "你", "他", "她", "它", "们", "这", "那", "就",
    "都", "也", "在", "和", "与", "或", "但", "而", "如", "把", "被", "让",
    "从", "到", "给", "对", "为", "以", "用", "会", "要", "有", "没", "不",
    "个", "上", "下", "里", "中", "出", "去", "过", "来", "说", "看", "做",
    "一个", "一些", "这个", "那个", "可以", "可能", "需要", "如果", "因为",
    "所以", "但是", "不过", "然后", "还是", "已经", "现在", "今天", "什么",
    "怎么", "为什么", "这样", "那样", "非常", "特别", "比较", "更", "最",
    "很", "太", "和", "跟",
}


def extract_tweets_from_response(doc: dict) -> list[dict]:
    """Tweets live at response.data.tweets OR response.data (list) OR response.tweets."""
    if not doc.get("ok"):
        return []
    data = doc.get("data")
    if isinstance(data, dict):
        if isinstance(data.get("tweets"), list):
            return data["tweets"]
    if isinstance(data, list):
        return data
    if isinstance(doc.get("tweets"), list):
        return doc["tweets"]
    return []


def get_metrics(t: dict) -> dict[str, int]:
    """twx normalize_tweet exposes metrics under .metrics with snake_case keys."""
    m = t.get("metrics") or {}
    return {
        "like_count": int(m.get("like_count") or t.get("likeCount") or 0),
        "retweet_count": int(m.get("retweet_count") or t.get("retweetCount") or 0),
        "reply_count": int(m.get("reply_count") or t.get("replyCount") or 0),
    }


def score_tweet(m: dict[str, int]) -> int:
    return m["like_count"] + 2 * m["retweet_count"] + 3 * m["reply_count"]


URL_RE = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"@\w+")
HASHTAG_RE = re.compile(r"#(\w+)")
EN_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}")
CJK_RE = re.compile(r"[一-鿿]")


def is_mostly_chinese(text: str) -> bool:
    cjk = len(CJK_RE.findall(text))
    total_letters = cjk + len(EN_WORD_RE.findall(text))
    return total_letters > 0 and cjk / total_letters > 0.3


def extract_keywords(texts: list[str], top_k: int = 5) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for t in texts:
        cleaned = URL_RE.sub(" ", t)
        cleaned = MENTION_RE.sub(" ", cleaned)
        # keep hashtag body, drop "#"
        cleaned = HASHTAG_RE.sub(r"\1", cleaned)
        # English tokens
        for w in EN_WORD_RE.findall(cleaned):
            wl = w.lower()
            if wl in STOPWORDS_EN or len(wl) < 3:
                continue
            counter[wl] += 1
        # Chinese: naive 2-gram — good enough for frequency signal.
        cjk_only = "".join(CJK_RE.findall(cleaned))
        for i in range(len(cjk_only) - 1):
            bigram = cjk_only[i : i + 2]
            if bigram in STOPWORDS_ZH:
                continue
            if any(ch in STOPWORDS_ZH for ch in bigram):
                continue
            counter[bigram] += 1
    return counter.most_common(top_k)


def primary_role(username: str) -> str:
    if username in ACCOUNT_PRIMARY_ROLE:
        return ACCOUNT_PRIMARY_ROLE[username]
    for role, _emoji, accts in ROLES:
        if username in accts:
            return role
    return "unknown"


def normalize_tweet(t: dict, username: str) -> dict[str, Any]:
    metrics = get_metrics(t)
    tweet_id = t.get("id") or t.get("tweet_id") or ""
    text = t.get("text") or ""
    return {
        "tweet_id": str(tweet_id),
        "text": text,
        "account": username,
        "role": primary_role(username),
        "created_at": t.get("created_at") or t.get("createdAt") or "",
        "likes": metrics["like_count"],
        "retweets": metrics["retweet_count"],
        "replies": metrics["reply_count"],
        "score": score_tweet(metrics),
        "is_retweet": bool(t.get("is_retweet") or t.get("isRetweet")),
        "url": f"https://x.com/{username}/status/{tweet_id}" if tweet_id else "",
    }


def pick_headlines(all_tweets: list[dict], top_n: int = 5) -> list[dict]:
    """Rank by score, dedup by account, prefer originals over RTs."""
    sorted_tweets = sorted(
        all_tweets,
        key=lambda t: (t["score"], not t["is_retweet"]),
        reverse=True,
    )
    picked: list[dict] = []
    seen_accounts: set[str] = set()
    for t in sorted_tweets:
        if t["account"] in seen_accounts:
            continue
        # Skip RTs unless they have outsized engagement.
        if t["is_retweet"] and t["score"] < 50:
            continue
        picked.append(t)
        seen_accounts.add(t["account"])
        if len(picked) >= top_n:
            break
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir", help="Directory containing <username>.json files")
    ap.add_argument("--top", type=int, default=5, help="Max headlines (default 5)")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    if not raw_dir.is_dir():
        print(f"error: {raw_dir} is not a directory", file=sys.stderr)
        return 1

    # Unique accounts (cross-role dedup).
    all_accounts: list[str] = []
    seen: set[str] = set()
    for _role, _emoji, accts in ROLES:
        for a in accts:
            if a not in seen:
                seen.add(a)
                all_accounts.append(a)

    per_account_tweets: dict[str, list[dict]] = {}
    for acct in all_accounts:
        path = raw_dir / f"{acct}.json"
        tweets: list[dict] = []
        if path.exists():
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
                raw = extract_tweets_from_response(doc)
                tweets = [normalize_tweet(t, acct) for t in raw]
            except Exception as e:
                print(f"warn: failed to parse {path}: {e}", file=sys.stderr)
        per_account_tweets[acct] = tweets

    # Flat list for headlines and stats.
    flat = [t for ts in per_account_tweets.values() for t in ts]

    # Language ratio.
    zh_count = sum(1 for t in flat if is_mostly_chinese(t["text"]))
    en_count = len(flat) - zh_count

    # Max-likes tweet.
    max_likes = max(flat, key=lambda t: t["likes"], default=None)

    # Keywords.
    keywords = [kw for kw, _c in extract_keywords([t["text"] for t in flat], top_k=5)]

    # by_role — preserve original role lists (with duplicates across roles),
    # but the same tweet will appear under each role the account belongs to.
    by_role: list[dict] = []
    for role, emoji, accts in ROLES:
        role_entry = {"role": role, "emoji": emoji, "accounts": []}
        for a in accts:
            role_entry["accounts"].append({
                "account": a,
                "display_name": DISPLAY_NAMES.get(a, a),
                "tweets": per_account_tweets.get(a, []),
            })
        by_role.append(role_entry)

    # Navigation counts (as listed, including cross-role duplicates).
    navigation: list[dict] = []
    for role, _emoji, accts in ROLES:
        active = sum(1 for a in accts if per_account_tweets.get(a))
        navigation.append({
            "role": role,
            "count": len(accts),
            "active": active,
        })

    headlines = pick_headlines(flat, top_n=args.top)

    active_accounts = sum(1 for ts in per_account_tweets.values() if ts)

    result = {
        "stats": {
            "total_accounts": len(all_accounts),
            "active_accounts": active_accounts,
            "total_tweets": len(flat),
            "max_likes_tweet": max_likes,
            "keywords": keywords,
            "zh_count": zh_count,
            "en_count": en_count,
        },
        "headlines": headlines,
        "by_role": by_role,
        "navigation": navigation,
    }

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
