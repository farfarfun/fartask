#!/usr/bin/env bash
# fartask NiceGUI 网页看板的统一生命周期管理入口。
#
# 用法：
#   scripts/setup.sh install-dev        构建并安装当前源码
#   scripts/setup.sh install-prod [版本] 从包索引安装正式包
#   scripts/setup.sh publish            发布正式包
#   scripts/setup.sh run                前台运行
#   scripts/setup.sh start              后台运行
#   scripts/setup.sh stop|restart|status
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
RUN_DIR="$ROOT/.run"
PORT=8080

log() { echo "[fartask] $*"; }

pid_file() { echo "$RUN_DIR/fartask.pid"; }
log_file() { echo "$RUN_DIR/fartask.log"; }
cmd_file() { echo "$RUN_DIR/fartask.cmd"; }

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
  local pid="$1"
  is_alive "$pid" || return 1
  local actual cf
  actual=$(proc_cmdline "$pid")
  [ -n "$actual" ] || return 1
  cf=$(cmd_file)
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
  rm -f "$(pid_file)" "$(cmd_file)"
}

ensure_installed_package() {
  if ! command -v fartask >/dev/null 2>&1; then
    echo "[fartask] 错误：当前环境未安装 fartask；请先执行 install-dev 或 install-prod" >&2
    exit 1
  fi
}

installed_version() {
  python3 -c 'from importlib.metadata import version; print(version("fartask"))' 2>/dev/null || echo "未安装"
}

# 本服务的启动命令（数组），start 与 run 共用，同时作为进程身份指纹
service_command() {
  SERVICE_CMD=(fartask --port "$PORT")
}

cmd_run() {
  ensure_installed_package
  service_command
  log "前台运行（版本 $(installed_version)，端口 $PORT）"
  exec "${SERVICE_CMD[@]}"
}

cmd_start() {
  ensure_installed_package
  mkdir -p "$RUN_DIR"
  local pf lf pid
  pf=$(pid_file)
  lf=$(log_file)
  if [ -f "$pf" ]; then
    pid=$(cat "$pf")
    if is_our_service "$pid"; then
      echo "[fartask] 已在运行（PID $pid），拒绝重复启动" >&2
      exit 1
    fi
    if is_alive "$pid"; then
      log "PID $pid 仍存活但不是本服务（PID 已被复用），按陈旧 PID 文件处理"
    else
      log "发现陈旧 PID 文件（$pid 已不存在），清理后继续"
    fi
    clear_runtime_files
  fi
  service_command
  log "后台启动（版本 $(installed_version)，端口 $PORT），日志：$lf"
  nohup "${SERVICE_CMD[@]}" >>"$lf" 2>&1 &
  pid=$!
  echo "$pid" > "$pf"
  sleep 0.1
  if ! is_alive "$pid" || [ -z "$(proc_cmdline "$pid")" ]; then
    clear_runtime_files
    echo "[fartask] 启动失败，详见 $lf" >&2
    exit 1
  fi
  proc_cmdline "$pid" > "$(cmd_file)"
  log "已启动，PID $pid"
}

cmd_stop() {
  local pf
  pf=$(pid_file)
  if [ ! -f "$pf" ]; then
    log "未在运行（无 PID 文件）"
    return 0
  fi
  local pid
  pid=$(cat "$pf")
  if is_our_service "$pid"; then
    kill "$pid"
    log "已停止（PID $pid）"
  elif is_alive "$pid"; then
    log "PID $pid 仍存活但不是本服务（PID 已被复用），不发送终止信号，仅清理运行时文件"
  else
    log "PID 文件陈旧（$pid 已不存在）"
  fi
  clear_runtime_files
}

cmd_restart() {
  cmd_stop
  cmd_start
}

cmd_status() {
  local pf pid version
  pf=$(pid_file)
  version=$(installed_version)
  if [ -f "$pf" ]; then
    pid=$(cat "$pf")
    if is_our_service "$pid"; then
      log "运行中（版本 $version，PID $pid，端口 $PORT）"
    elif is_alive "$pid"; then
      log "未运行（版本 $version，PID $pid 已被其他进程复用，PID 文件陈旧）"
    else
      log "未运行（版本 $version，陈旧 PID 文件 $pid）"
    fi
  else
    log "未运行（版本 $version）"
  fi
}

require_funbuild() {
  command -v funbuild >/dev/null 2>&1 || {
    echo "[fartask] 错误：需要先安装 funbuild" >&2
    exit 1
  }
}

action="${1:-}"
case "$action" in
  run|start|stop|restart)
    [ "$#" -eq 1 ] || { echo "usage: $0 $action" >&2; exit 1; }
    "cmd_$action"
    ;;
  status)
    [ "$#" -eq 1 ] || { echo "usage: $0 status" >&2; exit 1; }
    cmd_status
    ;;
  install-dev)
    [ "$#" -eq 1 ] || { echo "usage: $0 $action" >&2; exit 1; }
    require_funbuild
    (cd "$ROOT" && funbuild install)
    ;;
  publish)
    [ "$#" -eq 1 ] || { echo "usage: $0 $action" >&2; exit 1; }
    require_funbuild
    (cd "$ROOT" && funbuild build)
    ;;
  install-prod)
    [ "$#" -le 2 ] || { echo "usage: $0 install-prod [version]" >&2; exit 1; }
    python3 -m pip install "fartask${2:+==$2}"
    ;;
  *)
    echo "usage: $0 {install-dev|publish|run|start|stop|restart|status} | $0 install-prod [version]" >&2
    exit 1
    ;;
esac
