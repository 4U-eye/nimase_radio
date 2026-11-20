#!/bin/bash
# nimase ラジオ: COEIROINK エンジンの起動・停止・状態確認。
# エンジンは常駐させず、回を作る時だけ起動する（2026-11-20 ユーザー方針）。
# このVMでは /etc が再起動で初期化されるため、ユニットが無ければ
# ~/workspace/coeiroink/systemd/ の控えから再配置する。enable はしない。
#
# 使い方: engine.sh start|stop|status
#   start : 応答があれば何もしない。無ければ service→直接起動の順に試す。
#           成功で ENGINE_OK、失敗で ENGINE_FAIL（終了コード3）。
#   stop  : service 停止＋直接起動プロセス終了。ENGINE_STOPPED を出す。
#   status: 応答があれば話者名、無ければ ENGINE_DOWN。

UNIT_SRC="$HOME/workspace/coeiroink/systemd/coeiroink-engine.service"
UNIT_DST="/etc/systemd/system/coeiroink-engine.service"
ENGINE_BIN="$HOME/workspace/coeiroink/app/COEIROINK_LINUX_CPU_v.2025.4.1/engine/engine"
API="http://127.0.0.1:50032/v1/speakers"

responding() {
  curl -s -m 5 "$API" >/dev/null 2>&1
}

wait_response() {
  for _ in $(seq 1 30); do
    if responding; then return 0; fi
    sleep 2
  done
  return 1
}

case "${1:-}" in
  status)
    if responding; then
      curl -s -m 5 "$API" | python3 -c \
        'import json,sys; print("ENGINE_UP:", ", ".join(s["speakerName"] for s in json.load(sys.stdin)))'
    else
      echo "ENGINE_DOWN"
    fi
    ;;
  start)
    if responding; then
      echo "ENGINE_OK (already running)"
      exit 0
    fi
    if [ -f "$UNIT_DST" ]; then
      systemctl start coeiroink-engine 2>/dev/null
    elif [ -f "$UNIT_SRC" ]; then
      cp "$UNIT_SRC" "$UNIT_DST" 2>/dev/null
      systemctl daemon-reload 2>/dev/null
      systemctl start coeiroink-engine 2>/dev/null
    fi
    if wait_response; then
      echo "ENGINE_OK (service)"
      exit 0
    fi
    # 直接起動にフォールバック
    nohup "$ENGINE_BIN" >/tmp/coeiroink-engine.log 2>&1 &
    if wait_response; then
      echo "ENGINE_OK (direct)"
      exit 0
    fi
    echo "ENGINE_FAIL"
    exit 3
    ;;
  stop)
    systemctl stop coeiroink-engine 2>/dev/null
    pkill -f "COEIROINK_LINUX_CPU.*engine/engine" 2>/dev/null
    sleep 1
    if responding; then
      echo "ENGINE_STILL_UP"
      exit 1
    fi
    echo "ENGINE_STOPPED"
    ;;
  *)
    echo "usage: engine.sh start|stop|status" >&2
    exit 2
    ;;
esac
