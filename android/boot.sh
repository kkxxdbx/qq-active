#!/data/data/com.termux/files/usr/bin/sh
# 开机自启脚本：复制到 ~/.termux/boot/ 目录（需先安装 Termux:Boot 应用）
# cp android/boot.sh ~/.termux/boot/qq-active.sh
termux-wake-lock
sleep 15
bash ~/qq-active/android/start.sh >> ~/qq-active/boot-run.log 2>&1 &
