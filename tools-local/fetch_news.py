#!/usr/bin/env python3
"""nimase ラジオ: NHK RSS から、その朝のニュース候補をまとめて取得する。

使い方:
  python3 fetch_news.py [--date YYYY-MM-DD]

NHK のカテゴリ別 RSS (www3.nhk.or.jp/rss/news/cat*.xml) を読み、
重複を除いた候補一覧を標準出力にコンパクトに表示する。
全文 JSON は work/candidates-<date>.json に保存する（scaffold.py が使う）。

記事本文は news.web.nhk がスクリプトアクセスを 403 で拒むため取得しない。
事実確認は従来どおり browser.open で各記事を開いて行うこと。
このスクリプトの役割は「トップ/新着ページを巡回して候補を拾う」手間の削減。
"""
import datetime
import email.utils
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

STATION_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = datetime.timezone(datetime.timedelta(hours=9))

CATEGORIES = [
    ("cat0", "総合"),
    ("cat1", "社会"),
    ("cat2", "科学・文化"),
    ("cat3", "政治"),
    ("cat4", "ビジネス"),
    ("cat5", "国際"),
    ("cat6", "スポーツ"),
    ("cat7", "暮らし"),
]
RSS_URL = "https://www3.nhk.or.jp/rss/news/{cat}.xml"
UA = {"User-Agent": "Mozilla/5.0 (nimase-radio fetch_news)"}


def fetch_rss(cat):
    req = urllib.request.Request(RSS_URL.format(cat=cat), headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def parse_items(xml_bytes, cat_name):
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if not title or not link:
            continue
        dt = None
        if pub:
            try:
                dt = email.utils.parsedate_to_datetime(pub)
            except (TypeError, ValueError):
                dt = None
        items.append({
            "title": title,
            "url": link,
            "description": desc,
            "category": cat_name,
            "pubdate": dt.isoformat() if dt else None,
            "_dt": dt,
        })
    return items


def main():
    date = datetime.datetime.now(JST).date().isoformat()
    if "--date" in sys.argv:
        date = sys.argv[sys.argv.index("--date") + 1]

    seen = set()
    all_items = []
    errors = []
    for cat, name in CATEGORIES:
        try:
            items = parse_items(fetch_rss(cat), name)
        except Exception as e:  # noqa: BLE001 - 1カテゴリ失敗でも続行する
            errors.append(f"{name}: {e}")
            continue
        for it in items:
            if it["url"] in seen:
                continue
            seen.add(it["url"])
            all_items.append(it)

    all_items.sort(key=lambda x: (x["_dt"] is not None, x["_dt"]),
                   reverse=True)
    newest = next((it["_dt"] for it in all_items if it["_dt"]), None)
    for it in all_items:
        del it["_dt"]

    out_path = os.path.join(STATION_DIR, "work", f"candidates-{date}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"date": date, "items": all_items}, f,
                  ensure_ascii=False, indent=1)

    # 鮮度ガード: 最新記事が36時間より古ければ、そのフィードは
    # その朝の候補として使えない（古いスナップショットの可能性がある）。
    now = datetime.datetime.now(JST)
    if newest is not None:
        age_h = (now - newest.astimezone(JST)).total_seconds() / 3600
        if age_h > 36:
            print(f"STALE_FEED newest={newest.isoformat()} "
                  f"age_hours={age_h:.0f}")
            print("RSS が古いため候補として使わないこと。"
                  "従来どおりブラウザでトップ/新着から収集すること。")
            sys.exit(4)

    print(f"# NHKニュース候補 {date} 全{len(all_items)}件 -> {out_path}")
    for i, it in enumerate(all_items, 1):
        t = ""
        if it["pubdate"]:
            t = datetime.datetime.fromisoformat(it["pubdate"]).strftime("%H:%M")
        desc = it["description"].replace("\n", " ")
        if len(desc) > 110:
            desc = desc[:110] + "…"
        print(f"{i}. [{it['category']}] {it['title']} | {t}")
        print(f"    {it['url']}")
        if desc:
            print(f"    {desc}")
    for e in errors:
        print(f"! RSS取得失敗 {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
