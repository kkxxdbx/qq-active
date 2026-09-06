#!/data/data/com.termux/files/usr/bin/sh
# 一键停止所有相关进程
pkill -f Lagrange.OneBot
pkill -f "send.py"
command -v termux-wake-unlock >/dev/null && termux-wake-unlock
echo "已全部停止"
