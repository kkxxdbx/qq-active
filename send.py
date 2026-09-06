# -*- coding: utf-8 -*-
"""
QQ 群活跃度自动发送脚本（Windows / Android 通用）
- 从 groups.txt 读取群号，messages.txt 读取文案库
- 每个群随机发 2~3 条消息，消息间隔 20~60 秒，群间隔 30~90 秒
- 全部使用标准库，无需 pip 安装

用法:
    python send.py           # 立即发送一轮（全部群）
    python send.py --test    # 测试：只给第一个群发 1 条
    python send.py --loop    # 常驻模式：每天在 LOOP_WINDOW 时间段内随机发一轮
    python send.py --daily   # 单日模式：随机延迟 0~60 分钟后发一轮并退出（配合计划任务/cron）
"""
import json
import random
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ========== 配置区 ==========
API = "http://127.0.0.1:3000"          # OneBot HTTP API 地址（NapCat / Lagrange 都监听这里）
# 打包成 exe 后，配置文件放在 exe 同目录，而不是临时解压目录
if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).parent
else:
    BASE = Path(__file__).parent
GROUPS_FILE = BASE / "groups.txt"
MESSAGES_FILE = BASE / "messages.txt"
MIN_MSG_PER_GROUP = 2                   # 每群最少发几条
MAX_MSG_PER_GROUP = 3                   # 每群最多发几条
MSG_INTERVAL = (20, 60)                 # 同一群内两条消息间隔（秒）
GROUP_INTERVAL = (30, 90)               # 群与群之间的间隔（秒）
LOOP_WINDOW = (9, 11)                   # --loop 模式：每天在这个小时区间内随机挑时间发送
# ===========================


def load_lines(path):
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def send_group_msg(group_id, text):
    payload = json.dumps({
        "group_id": int(group_id),
        "message": text,
    }).encode("utf-8")
    req = urllib.request.Request(
        API + "/send_group_msg",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("retcode") == 0:
        print(f"[OK] 群 {group_id}: {text}")
    else:
        print(f"[FAIL] 群 {group_id}: {result}")


def run_once(groups, messages):
    # 打乱群顺序，每次发送顺序不同，更像真人
    random.shuffle(groups)
    total = len(groups)
    for i, group_id in enumerate(groups, 1):
        count = random.randint(MIN_MSG_PER_GROUP, MAX_MSG_PER_GROUP)
        picked = random.sample(messages, min(count, len(messages)))
        print(f"--- 群 {group_id}（{i}/{total}）发 {len(picked)} 条 ---")
        for j, msg in enumerate(picked):
            send_group_msg(group_id, msg)
            if j < len(picked) - 1:
                wait = random.randint(*MSG_INTERVAL)
                print(f"    等待 {wait} 秒...")
                time.sleep(wait)
        if i < total:
            wait = random.randint(*GROUP_INTERVAL)
            print(f"切换下一个群前等待 {wait} 秒...")
            time.sleep(wait)
    print("本轮发送完成")


def next_run_time():
    """计算下一次发送时间：每天 LOOP_WINDOW 区间内随机挑一个"""
    now = datetime.now()
    run_at = now.replace(
        hour=random.randint(LOOP_WINDOW[0], LOOP_WINDOW[1] - 1),
        minute=random.randint(0, 59),
        second=0,
        microsecond=0,
    )
    if run_at <= now:
        run_at += timedelta(days=1)
    return run_at


def main():
    groups = load_lines(GROUPS_FILE)
    messages = load_lines(MESSAGES_FILE)
    if not groups:
        print("groups.txt 为空，请先填入群号")
        sys.exit(1)
    if not messages:
        print("messages.txt 为空，请先填入文案")
        sys.exit(1)

    if "--test" in sys.argv:
        send_group_msg(groups[0], random.choice(messages))
        print("测试完成，去群里看看是否收到")
        return

    if "--daily" in sys.argv:
        # 计划任务/cron 每天调用一次：随机延迟后发一轮就退出，避免多实例
        delay = random.randint(0, 3600)
        print(f"单日模式：随机延迟 {delay // 60} 分 {delay % 60} 秒后发送")
        time.sleep(delay)
        run_once(groups, messages)
        return

    if "--loop" in sys.argv:
        print("进入每日循环模式（Ctrl+C 退出）")
        try:
            while True:
                run_at = next_run_time()
                print(f"下次发送时间: {run_at:%Y-%m-%d %H:%M}")
                time.sleep(max(1, (run_at - datetime.now()).total_seconds()))
                try:
                    run_once(groups, messages)
                except Exception as e:
                    print(f"本轮发送出错，明天继续: {e}")
        except KeyboardInterrupt:
            print("已退出循环模式")
        return

    run_once(groups, messages)


if __name__ == "__main__":
    main()
