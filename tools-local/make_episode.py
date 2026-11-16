#!/usr/bin/env python3
"""nimase ラジオ: 台本ベースJSON → 音声・タイミング付き台本・その日のHTML を作る。

使い方:
  python3 make_episode.py <base-episode.json>

base JSON は episodes/2026-11-09.json から seconds / lines_timed / segments /
made_at を除いた形（format, date, lang, title, opening, news[], closing, highlight）。
出力:
  episodes/<date>.json   (タイミング付き台本)
  audio/<date>.mp3       (1本の音声)
  episodes.json          (一覧の先頭に追加)
  daily/<date>.html      (スマホで開ける、その日だけの単体HTML。音声は埋め込み)
最後に結果を JSON で1行 print する。
"""
import base64
import datetime
import html
import json
import os
import subprocess
import sys

STATION_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = "avocado_v2:vd2_r82_rep5k_2026_v068_28k_g5k"  # Meticulous Pen (F, Japanese)
LEAD = 0.6
GAP_IN = 0.25
GAP_PART = 0.5
JST = datetime.timezone(datetime.timedelta(hours=9))
WEEKDAYS = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]


def dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, text=True)
    return float(json.loads(out.stdout)["format"]["duration"])


def silence(path, secs, work):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", str(secs), "-c:a", "libmp3lame", "-b:a", "128k", path], check=True)


def build_html(ep, mp3_path):
    date = ep["date"]
    d = datetime.date.fromisoformat(date)
    date_jp = f"{d.year}年{d.month}月{d.day}日（{WEEKDAYS[d.weekday()]}）"
    b64 = base64.b64encode(open(mp3_path, "rb").read()).decode()
    mins = int(ep["seconds"] // 60)
    secs = int(round(ep["seconds"] % 60))
    length = f"約{mins}分{secs}秒"

    def esc(s):
        return html.escape(s or "")

    cards = []
    for n in ep["news"]:
        link = n.get("link") or {}
        img = ""
        if link.get("image"):
            img = f'<img src="{esc(link["image"])}" alt="" loading="lazy" referrerpolicy="no-referrer">'
        points = "".join(f"<li>{esc(p)}</li>" for p in n.get("points", []))
        details = "".join(
            f"<p>{esc(x)}</p>" for x in (n.get("details") or []) if x)
        src = n.get("url") or link.get("url") or ""
        cards.append(f"""
    <article class="card">
      {img}
      <h2>{esc(n.get("label"))}</h2>
      <ul>{points}</ul>
      {details}
      <p class="src"><a href="{esc(src)}">出典：{esc(link.get("title") or src)}（{esc(link.get("site") or "")}）</a></p>
    </article>""")

    script_lines = []
    for l in ep["opening"]:
        script_lines.append(l["show"])
    for n in ep["news"]:
        for l in n["lines"]:
            script_lines.append(l["show"])
    for l in ep["closing"]:
        script_lines.append(l["show"])
    script_html = "".join(f"<p>{esc(s)}</p>" for s in script_lines)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>nimase ラジオ {date_jp}</title>
<style>
  body {{ margin:0; background:#07080c; color:#f2f3f5; font-family: system-ui, "Hiragino Kaku Gothic ProN", sans-serif; }}
  main {{ max-width: 640px; margin: 0 auto; padding: 20px 16px 48px; }}
  header .name {{ color:#ffd028; font-weight:700; letter-spacing:.08em; font-size:13px; }}
  h1 {{ font-size: 22px; margin: 6px 0 2px; line-height:1.4; }}
  .date {{ color:#9aa3b2; font-size: 14px; margin-bottom: 16px; }}
  audio {{ width: 100%; margin: 8px 0 20px; }}
  .card {{ background:#10131c; border:1px solid #232838; border-radius:14px; padding:16px; margin:0 0 14px; }}
  .card img {{ width:100%; border-radius:10px; margin-bottom:10px; }}
  .card h2 {{ font-size:17px; margin:0 0 8px; }}
  .card ul {{ margin:0 0 8px; padding-left:20px; }}
  .card p {{ color:#c9cedb; font-size:14px; line-height:1.7; }}
  .card .src a {{ color:#3fe0dc; font-size:13px; }}
  .script {{ margin-top:28px; }}
  .script h2 {{ font-size:16px; color:#ffd028; }}
  .script p {{ font-size:14px; line-height:1.8; color:#dfe3ec; margin:0 0 6px; }}
  footer {{ color:#6b7386; font-size:12px; margin-top:32px; }}
</style>
</head>
<body>
<main>
  <header>
    <div class="name">nimase ラジオ</div>
    <h1>{esc(ep["title"])}</h1>
    <div class="date">{date_jp} ・ {length}</div>
    <audio controls preload="metadata" src="data:audio/mpeg;base64,{b64}"></audio>
  </header>
  {''.join(cards)}
  <section class="script">
    <h2>台本</h2>
    {script_html}
  </section>
  <footer>nimase ラジオ ／ 声：Muse の音声合成 ／ 出典は各カードのリンク先（NHKニュース）</footer>
</main>
</body>
</html>
"""


def main():
    base_path = sys.argv[1]
    ep = json.load(open(base_path, encoding="utf-8"))
    date = ep["date"]
    work = os.path.join(STATION_DIR, "work", date)
    os.makedirs(work + "/lines", exist_ok=True)
    os.makedirs(work + "/sil", exist_ok=True)

    flat = []
    for l in ep["opening"]:
        flat.append({"part": 0, "kind": "opening", "index": None, "say": l["say"], "show": l["show"]})
    for n, item in enumerate(ep["news"]):
        for l in item["lines"]:
            flat.append({"part": n + 1, "kind": "news", "index": n, "say": l["say"], "show": l["show"]})
    for l in ep["closing"]:
        flat.append({"part": len(ep["news"]) + 1, "kind": "closing", "index": None, "say": l["say"], "show": l["show"]})

    for i, l in enumerate(flat):
        import hashlib
        h = hashlib.md5(l["say"].encode("utf-8")).hexdigest()[:8]
        p = f"{work}/lines/{i:02d}-{h}.mp3"
        if not (os.path.exists(p) and os.path.getsize(p) > 1000):
            r = subprocess.run(
                ["/opt/hatch/bin/tts", "speak", "--voice", VOICE, "--language", "ja",
                 "--output", p, "--text-stdin"],
                input=l["say"], capture_output=True, text=True)
            if r.returncode != 0:
                print(json.dumps({"ok": False, "error": f"TTS failed at line {i}", "detail": (r.stdout + r.stderr)[-400:]}, ensure_ascii=False))
                sys.exit(1)
        l["file"] = p
        l["dur"] = dur(p)

    seq = []
    lead_p = f"{work}/sil/lead.mp3"
    silence(lead_p, LEAD, work)
    seq.append(lead_p)
    t = LEAD
    timed = []
    segments = []
    cur_key = None
    seg_start = None
    prev_end = None
    for i, l in enumerate(flat):
        key = (l["kind"], l["index"])
        if i > 0:
            gap = GAP_IN if key == cur_key else GAP_PART
            gp = f"{work}/sil/gap_{gap}.mp3"
            if not os.path.exists(gp):
                silence(gp, gap, work)
            seq.append(gp)
            t += gap
        if key != cur_key:
            if cur_key is not None:
                segments.append({"kind": cur_key[0], "index": cur_key[1],
                                 "start": round(seg_start, 3), "end": round(prev_end, 3)})
            cur_key = key
            seg_start = t
        start = t
        end = t + l["dur"]
        timed.append({"start": round(start, 3), "end": round(end, 3), "show": l["show"], "part": l["part"]})
        seq.append(l["file"])
        t = end
        prev_end = end
    segments.append({"kind": cur_key[0], "index": cur_key[1],
                     "start": round(seg_start, 3), "end": round(prev_end, 3)})
    total = prev_end

    mp3_out = os.path.join(STATION_DIR, "audio", f"{date}.mp3")
    inputs = []
    filt = []
    for j, p in enumerate(seq):
        inputs += ["-i", p]
        filt.append(f"[{j}:a]")
    filterstr = "".join(filt) + f"concat=n={len(seq)}:v=0:a=1[a]"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error"] + inputs +
                       ["-filter_complex", filterstr, "-map", "[a]",
                        "-c:a", "libmp3lame", "-b:a", "128k", mp3_out],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(json.dumps({"ok": False, "error": "ffmpeg failed", "detail": r.stderr[-400:]}, ensure_ascii=False))
        sys.exit(1)

    ep["seconds"] = round(total, 2)
    ep["lines_timed"] = timed
    ep["segments"] = segments
    ep["made_at"] = datetime.datetime.now(JST).isoformat(timespec="seconds")
    ep_json = os.path.join(STATION_DIR, "episodes", f"{date}.json")
    with open(ep_json, "w", encoding="utf-8") as f:
        json.dump(ep, f, ensure_ascii=False, indent=1)

    eps_path = os.path.join(STATION_DIR, "episodes.json")
    eps = json.load(open(eps_path, encoding="utf-8"))
    eps = [e for e in eps if e.get("date") != date]
    eps.insert(0, {"date": date, "title": ep["title"], "seconds": ep["seconds"]})
    eps.sort(key=lambda e: e["date"], reverse=True)
    with open(eps_path, "w", encoding="utf-8") as f:
        json.dump(eps, f, ensure_ascii=False, indent=1)

    html_out = os.path.join(STATION_DIR, "daily", f"{date}.html")
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(build_html(ep, mp3_out))

    print(json.dumps({"ok": True, "date": date, "title": ep["title"], "seconds": ep["seconds"],
                      "audio": mp3_out, "episode_json": ep_json, "html": html_out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
