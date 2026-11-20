#!/usr/bin/env python3
"""nimase ラジオ: 届け出用の見出し一覧を episodes/<date>.json から組み立てる。

使い方: python3 episode_summary.py YYYY-MM-DD
冒頭行と15本の見出し（NHK記事リンク付き）と長さを出す。
視聴用URLは固定なので呼び出し側で付ける。
"""
import json
import os
import sys

STATION_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    date = sys.argv[1]
    with open(os.path.join(STATION_DIR, "episodes", f"{date}.json"),
              encoding="utf-8") as f:
        ep = json.load(f)
    print(f"nimase ラジオ {date}")
    for n in ep["news"]:
        print(f"- [{n['label']}]({n['url']})")
    secs = ep.get("seconds", 0)
    print(f"SECONDS={secs} （約{int(secs // 60)}分{int(round(secs % 60))}秒）")


if __name__ == "__main__":
    main()
