#!/bin/bash
# nimase ラジオ: その日の回を GitHub に保存し、公開サイトへ反映する。
#
# 使い方: publish_daily.sh YYYY-MM-DD
# 手順（従来の手作業をそのままスクリプト化したもの）:
#   a. ローカル局リポジトリにその日のファイルをコミットし local origin へ push
#      （publish.sh はコミット済み内容から gh-pages を作るため必須）
#   b. tools/publish.sh で gh-pages を再構築
#   c. 作業用クローン経由で GitHub main へ push、gh-pages を force push
#   d. raw と公開サイトの episodes.json にその日が入ったか確認
# 最後に PUBLISH_RESULT=... と episode_summary の出力を表示する。
# 音声MP3と画像PNGは main に入れない。
set -u
DATE="${1:?usage: publish_daily.sh YYYY-MM-DD}"
ST="$HOME/workspace/nimase-radio"
CLONE="$HOME/workspace/nimase-radio-gh"
SHARE_FONT=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc
FAIL=""

step() { echo "== $1"; }

step "local commit"
git -C "$ST" add "episodes/${DATE}.json" episodes.json "daily/${DATE}.html" || FAIL="$FAIL local-add"
if git -C "$ST" diff --cached --quiet; then
  echo "local: no changes"
else
  git -C "$ST" commit -m "nimase ラジオ ${DATE} の回を追加" >/dev/null || FAIL="$FAIL local-commit"
fi
git -C "$ST" push origin main >/dev/null 2>&1 || FAIL="$FAIL local-push"

step "publish.sh"
# publish.sh は局リポジトリの中で実行する必要がある（git rev-parse を使用するため）
(cd "$ST" && SHARE_FONT=$SHARE_FONT bash "$ST/tools/publish.sh") >/tmp/publish-daily.log 2>&1 \
  || { FAIL="$FAIL publish.sh"; tail -5 /tmp/publish-daily.log; }

step "github main"
git -C "$CLONE" fetch origin >/dev/null 2>&1 || FAIL="$FAIL clone-fetch"
git -C "$CLONE" checkout main >/dev/null 2>&1
git -C "$CLONE" reset --hard origin/main >/dev/null 2>&1 || FAIL="$FAIL clone-reset"
cp "$ST/episodes/${DATE}.json" "$CLONE/episodes/${DATE}.json"
cp "$ST/episodes.json" "$CLONE/episodes.json"
cp "$ST/daily/${DATE}.html" "$CLONE/daily/${DATE}.html"
cp "$ST/work/${DATE}-base.json" "$CLONE/work/${DATE}-base.json"
git -C "$CLONE" add -A
if git -C "$CLONE" diff --cached --quiet; then
  echo "github main: no changes"
else
  git -C "$CLONE" commit -m "nimase ラジオ ${DATE} の回を追加" >/dev/null || FAIL="$FAIL main-commit"
  git -C "$CLONE" push origin main >/dev/null 2>&1 || FAIL="$FAIL main-push"
fi

step "github gh-pages"
git -C "$CLONE" fetch local gh-pages >/dev/null 2>&1 || FAIL="$FAIL pages-fetch"
git -C "$CLONE" push --force origin FETCH_HEAD:refs/heads/gh-pages >/dev/null 2>&1 \
  || FAIL="$FAIL pages-push"

step "verify"
RAW=$(curl -s -m 15 "https://raw.githubusercontent.com/4U-eye/nimase_radio/main/episodes.json")
SITE=$(curl -s -m 15 "https://4u-eye.github.io/nimase_radio/episodes.json")
case "$RAW" in *"$DATE"*) echo "RAW_OK";; *) echo "RAW_MISSING"; FAIL="$FAIL raw";; esac
case "$SITE" in *"$DATE"*) echo "SITE_OK";; *) echo "SITE_PENDING";; esac

if [ -n "$FAIL" ]; then
  echo "PUBLISH_RESULT=FAIL steps:${FAIL}"
else
  echo "PUBLISH_RESULT=OK"
fi
python3 "$ST/tools-local/episode_summary.py" "$DATE"
