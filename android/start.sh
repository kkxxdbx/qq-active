#!/data/data/com.termux/files/usr/bin/sh
# Termux 一键启动：Lagrange（后台挂机）+ 每日定时发送循环（前台）
# 用法: bash android/start.sh
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1

# 防止手机休眠杀后台（还需在系统设置里给 Termux 关闭电池优化）
command -v termux-wake-lock >/dev/null && termux-wake-lock

if [ ! -x ./Lagrange.OneBot ]; then
    echo "未找到 Lagrange.OneBot，请先按部署说明下载并解压到本目录"
    exit 1
fi

if ! pgrep -f Lagrange.OneBot >/dev/null; then
    nohup ./Lagrange.OneBot > lagrange.log 2>&1 &
    echo "Lagrange 已后台启动（日志: lagrange.log）"
else
    echo "Lagrange 已在运行"
fi

echo "启动每日发送循环..."
exec python send.py --loop
