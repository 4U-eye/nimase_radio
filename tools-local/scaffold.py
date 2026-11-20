#!/usr/bin/env python3
"""nimase ラジオ:  compact な下書き JSON を正式な台本ベース JSON に展開する。

使い方:
  python3 scaffold.py <draft.json> <out-base.json>

下書きの形（エージェントが書く最小形）:
{
  "date": "YYYY-MM-DD",            // 省略時はファイル名や今日から推定しない。必須
  "title": "…",
  "highlight": 0,                  // 省略時は 0
  "opening": [line, ...],          // 4文
  "news": [
    {"label": "…", "url": "https://news.web.nhk/…",
     "image": "https://… または null", "description": "…",
     "points": ["…", …], "details": ["…", …],
     "lines": [line, …]}           // 7〜10文
  ],
  "closing": [line, …]             // 4文
}
line は文字列（say と show を同じにする）か {"say": "…", "show": "…"}。

展開時に link{url,title,site,description,image,icon} を自動で組み立て、
検証結果（本数・say総文字数・推定秒数・警告）を標準出力に表示する。
推定秒数は COEIROINK:リリンちゃん の実測 約5.55文字/秒 で計算する。
"""
import json
import sys

CHARS_PER_SEC = 5.55
TARGET_MIN, TARGET_MAX = 4800, 5000
FORBIDDEN = "二間瀬"  # 本名の漢字は台本・公開物に入れない


def expand_line(line):
    if isinstance(line, str):
        return {"say": line, "show": line}
    return {"say": line["say"], "show": line.get("show", line["say"])}


def main():
    draft_path, out_path = sys.argv[1], sys.argv[2]
    with open(draft_path, encoding="utf-8") as f:
        d = json.load(f)

    warnings = []
    news = []
    for i, n in enumerate(d["news"], 1):
        lines = [expand_line(x) for x in n["lines"]]
        if not (4 <= len(lines) <= 12):
            warnings.append(f"news[{i}] lines が {len(lines)} 文（目安7〜10）")
        news.append({
            "label": n["label"],
            "points": n.get("points", []),
            "details": n.get("details", []),
            "lines": lines,
            "url": n["url"],
            "link": {
                "url": n["url"],
                "title": n.get("link_title", n["label"]),
                "site": "news.web.nhk",
                "description": n.get("description", ""),
                "image": n.get("image"),
                "icon": None,
            },
        })

    ep = {
        "format": "monoradio/news-1",
        "date": d["date"],
        "lang": "ja",
        "title": d["title"],
        "opening": [expand_line(x) for x in d["opening"]],
        "news": news,
        "closing": [expand_line(x) for x in d["closing"]],
        "highlight": d.get("highlight", 0),
    }

    blob = json.dumps(ep, ensure_ascii=False)
    if FORBIDDEN in blob:
        warnings.append("禁止文字列（本名の漢字）が含まれています")
    if len(news) != 15:
        warnings.append(f"news が {len(news)} 本（15本が原則）")
    for i, n in enumerate(news, 1):
        if not n["url"].startswith("http"):
            warnings.append(f"news[{i}] url が不正: {n['url']}")

    total_say = sum(len(x["say"]) for x in ep["opening"])
    total_say += sum(len(x["say"]) for n in news for x in n["lines"])
    total_say += sum(len(x["say"]) for x in ep["closing"])
    est = total_say / CHARS_PER_SEC
    if not (TARGET_MIN <= total_say <= TARGET_MAX):
        warnings.append(
            f"say 総文字数 {total_say}（目安 {TARGET_MIN}〜{TARGET_MAX}）")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ep, f, ensure_ascii=False, indent=1)

    print(f"BASE_OK items={len(news)} say_chars={total_say} "
          f"est_seconds={est:.0f} -> {out_path}")
    for w in warnings:
        print(f"WARN: {w}")


if __name__ == "__main__":
    main()
