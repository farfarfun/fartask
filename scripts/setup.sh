#!/usr/bin/env bash
# fartask NiceGUI 网页看板的统一生命周期管理入口。
#
# 用法：
#   scripts/setup.sh run     dev|prod   前台运行
#   scripts/setup.sh start   dev|prod   后台运行
#   scripts/setup.sh stop    dev|prod
#   scripts/setup.sh restart dev|prod
#   scripts/setup.sh status
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
RUN_DIR="$ROOT/.run"
PORT_DEV=8080
PORT_PROD=8080

log() { echo "[fartask] $*"; }

pid_file() { echo "$RUN_DIR/fartask-$1.pid"; }
log_file() { echo "$RUN_DIR/fartask-$1.log"; }

is_alive() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

# prod 只能跑已安装的正式包，绝不回退到源码/本地构建产物。
ensure_installed_package() {
  local env="$1"
  local pkg_dir
  if ! pkg_dir=$(python3 -c "import fartask, os; print(os.path.dirname(fartask.__file__))" 2>/dev/null); then
    echo "[fartask] 错误：未安装 fartask（pip install fartask），无法以 $env 模式启动" >&2
    exit 1
  fi
  if [ "$env" = "prod" ] && [[ "$pkg_dir" == "$ROOT"/* ]]; then
    echo "[fartask] 错误：prod 模式检测到 fartask 是从源码目录($ROOT)以可编辑方式安装的，拒绝启动" >&2
    echo "[fartask] 请先 'pip install fartask'（正式发布包）后再以 prod 模式运行" >&2
    exit 1
  fi
}

port_for() {
  case "$1" in
    dev) echo "$PORT_DEV" ;;
    prod) echo "$PORT_PROD" ;;
  esac
}

require_env() {
  case "${1:-}" in
    dev|prod) ;;
    *)
      echo "[fartask] 错误：需要指定环境 dev 或 prod" >&2
      exit 1
      ;;
  esac
}

cmd_run() {
  local env="$1"
  ensure_installed_package "$env"
  local port
  port=$(port_for "$env")
  log "前台运行（$env，端口 $port）"
  exec python3 -m fartask
}

cmd_start() {
  local env="$1"
  ensure_installed_package "$env"
  mkdir -p "$RUN_DIR"
  local pf lf pid
  pf=$(pid_file "$env")
  lf=$(log_file "$env")
  if [ -f "$pf" ]; then
    pid=$(cat "$pf")
    if is_alive "$pid"; then
      echo "[fartask] $env 已在运行（PID $pid），拒绝重复启动" >&2
      exit 1
    fi
    log "发现陈旧 PID 文件（$pid 已不存在），清理后继续"
    rm -f "$pf"
  fi
  local port
  port=$(port_for "$env")
  log "后台启动（$env，端口 $port），日志：$lf"
  nohup python3 -m fartask >>"$lf" 2>&1 &
  echo $! > "$pf"
  log "已启动，PID $(cat "$pf")"
}

cmd_stop() {
  local env="$1"
  local pf
  pf=$(pid_file "$env")
  if [ ! -f "$pf" ]; then
    log "$env 未在运行（无 PID 文件）"
    return 0
  fi
  local pid
  pid=$(cat "$pf")
  if is_alive "$pid"; then
    kill "$pid"
    log "已停止 $env（PID $pid）"
  else
    log "$env PID 文件陈旧（$pid 已不存在）"
  fi
  rm -f "$pf"
}

cmd_restart() {
  local env="$1"
  cmd_stop "$env"
  cmd_start "$env"
}

cmd_status() {
  local any=0
  for env in dev prod; do
    local pf pid
    pf=$(pid_file "$env")
    if [ -f "$pf" ]; then
      pid=$(cat "$pf")
      if is_alive "$pid"; then
        log "$env: 运行中（PID $pid，端口 $(port_for "$env")）"
      else
        log "$env: 未运行（陈旧 PID 文件 $pid）"
      fi
    else
      log "$env: 未运行"
    fi
    any=1
  done
  [ "$any" = 1 ]
}

action="${1:-}"
case "$action" in
  run|start|stop|restart)
    require_env "${2:-}"
    "cmd_$action" "$2"
    ;;
  status)
    cmd_status
    ;;
  *)
    echo "usage: $0 {run|start|stop|restart} {dev|prod} | $0 status" >&2
    exit 1
    ;;
esac
