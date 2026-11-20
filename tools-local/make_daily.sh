#!/bin/bash
# nimase ラジオ: エンジン起動 → 音声作成 → エンジン停止 を1回でやる。
#
# 使い方: make_daily.sh <base-episode.json>
# 成功時は make_episode_coeiro.py の結果 JSON と SECONDS=<秒> を出す。
# エンジンが起動できなければ ENGINE_FAIL（終了コード3）。
# その場合だけ従来の make_episode.py（Muse 音声）へフォールバックすること。
set -u
cd "$(dirname "$0")/.." || exit 1

BASE="${1:?usage: make_daily.sh <base-episode.json>}"

if ! bash tools-local/engine.sh start; then
  echo "ENGINE_FAIL"
  exit 3
fi

OUT=$(python3 tools-local/make_episode_coeiro.py "$BASE" 2>&1)
RC=$?
bash tools-local/engine.sh stop >/dev/null 2>&1

echo "$OUT" | tail -5
if [ $RC -ne 0 ]; then
  echo "MAKE_FAIL rc=$RC"
  exit $RC
fi
EP_SECONDS=$(echo "$OUT" | grep -o '"seconds": *[0-9.]*' | tail -1 | grep -o '[0-9.]*')
echo "SECONDS=${EP_SECONDS:-unknown}"
