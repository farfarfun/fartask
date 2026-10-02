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
cmd_file() { echo "$RUN_DIR/fartask-$1.cmd"; }

is_alive() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

proc_cmdline() {
  local pid="$1"
  local raw=""
  if [ -r "/proc/$pid/cmdline" ]; then
    raw=$(tr '\0' ' ' < "/proc/$pid/cmdline")
  else
    raw=$(ps -p "$pid" -o args= 2>/dev/null || true)
  fi
  # 去掉尾部空白（/proc 的 cmdline 以 NUL 结尾，转换后会多一个空格）
  echo "${raw%"${raw##*[![:space:]]}"}"
}

# PID 存活只能证明"有进程"，不能证明"是本服务"：PID 会被系统回收复用。
# 用启动时落盘的命令行指纹核对进程身份，不匹配就按陈旧 PID 处理，不发信号。
is_our_service() {
  local pid="$1" env="$2"
  is_alive "$pid" || return 1
  local actual cf
  actual=$(proc_cmdline "$pid")
  [ -n "$actual" ] || return 1
  cf=$(cmd_file "$env")
  if [ -f "$cf" ]; then
    [ "$actual" = "$(cat "$cf")" ]
    return
  fi
  # 没有指纹文件（如历史遗留的 PID 文件）时，退化为校验这确实是看板进程
  case "$actual" in
    *"-m fartask"*) return 0 ;;
    *) return 1 ;;
  esac
}

clear_runtime_files() {
  local env="$1"
  rm -f "$(pid_file "$env")" "$(cmd_file "$env")"
}

# prod 只能跑已安装的正式包，绝不回退到源码/本地构建产物。
ensure_installed_package() {
  local env="$1"
  local package_info
  if ! package_info=$(python3 - <<'PY'
import importlib.metadata as metadata
import importlib.util
import os

try:
    spec = importlib.util.find_spec("fartask")
    dist = metadata.distribution("fartask")
except metadata.PackageNotFoundError:
    raise SystemExit(1)
if spec is None or spec.origin is None:
    raise SystemExit(1)
print(os.path.dirname(spec.origin))
print("direct-url" if dist.read_text("direct_url.json") else "published")
PY
  ); then
    echo "[fartask] 错误：当前环境未安装 fartask（dev 用 'uv sync'），无法以 $env 模式启动" >&2
    exit 1
  fi
  local pkg_dir install_source
  pkg_dir=$(sed -n '1p' <<<"$package_info")
  install_source=$(sed -n '2p' <<<"$package_info")
  if [ "$env" = "prod" ] && { [[ "$pkg_dir" == "$ROOT"/* ]] || [ "$install_source" = "direct-url" ]; }; then
    echo "[fartask] 错误：prod 模式只允许从包索引安装的 fartask 正式包，拒绝源码/本地构建产物" >&2
    echo "[fartask] fartask 尚未发布到 PyPI：当前请用 'scripts/setup.sh start dev'" >&2
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

# 本服务的启动命令（数组），start 与 run 共用，同时作为进程身份指纹
service_command() {
  local env="$1"
  SERVICE_CMD=(python3 -m fartask --port "$(port_for "$env")")
}

cmd_run() {
  local env="$1"
  ensure_installed_package "$env"
  local port
  port=$(port_for "$env")
  service_command "$env"
  log "前台运行（$env，端口 $port）"
  exec "${SERVICE_CMD[@]}"
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
    if is_our_service "$pid" "$env"; then
      echo "[fartask] $env 已在运行（PID $pid），拒绝重复启动" >&2
      exit 1
    fi
    if is_alive "$pid"; then
      log "PID $pid 仍存活但不是本服务（PID 已被复用），按陈旧 PID 文件处理"
    else
      log "发现陈旧 PID 文件（$pid 已不存在），清理后继续"
    fi
    clear_runtime_files "$env"
  fi
  local port
  port=$(port_for "$env")
  service_command "$env"
  log "后台启动（$env，端口 $port），日志：$lf"
  nohup "${SERVICE_CMD[@]}" >>"$lf" 2>&1 &
  pid=$!
  echo "$pid" > "$pf"
  echo "${SERVICE_CMD[*]}" > "$(cmd_file "$env")"
  log "已启动，PID $pid"
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
  if is_our_service "$pid" "$env"; then
    kill "$pid"
    log "已停止 $env（PID $pid）"
  elif is_alive "$pid"; then
    log "PID $pid 仍存活但不是本服务（PID 已被复用），不发送终止信号，仅清理运行时文件"
  else
    log "$env PID 文件陈旧（$pid 已不存在）"
  fi
  clear_runtime_files "$env"
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
      if is_our_service "$pid" "$env"; then
        log "$env: 运行中（PID $pid，端口 $(port_for "$env")）"
      elif is_alive "$pid"; then
        log "$env: 未运行（PID $pid 已被其他进程复用，PID 文件陈旧）"
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
