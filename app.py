# -*- coding: utf-8 -*-
"""
QQ 群活跃 —— Windows 安装向导 + 主控台
双击运行：图形界面，左侧组件清单，右侧安装/执行，全部完成后进入主界面
命令行：qq-active.exe --daily （计划任务调用：随机延迟后发送一轮并退出）
"""
import json
import os
import queue
import random
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

# 打包成 exe 后，配置文件放在 exe 同目录
if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).parent
else:
    BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

# --windowed 打包后无控制台，stdout 可能为 None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import send  # 复用发送逻辑

import tkinter as tk
from tkinter import ttk, messagebox

NAPCAT_DIR = BASE / "napcat"
TASK_NAME = "QQ群活跃"
LOG_FILE = BASE / "send.log"
QQ_URL = "https://im.qq.com/pcqq/index.shtml"
NAPCAT_API = "https://api.github.com/repos/NapNeko/NapCatQQ/releases/latest"

DEFAULT_GROUPS = "# 群号列表，每行一个\n"
DEFAULT_MESSAGES = (
    "# 文案库，每行一条，发送时随机抽取\n"
    "早上好呀，都起了吗\n大家中午吃的啥\n下午好，摸鱼时间到\n今天天气不错啊\n"
    "晚上好，都吃了吗\n周末愉快各位\n最近有啥好看的电影没\n这天气忽冷忽热的，注意加衣服\n"
    "刚下班，累瘫\n有打游戏的老哥吗\n今天啥日子，群里这么安静\n路过冒个泡，证明我还活着\n"
    "祝大家天天开心\n周五啦，坚持一下就放假了\n周一综合症，谁懂\n群里有人抢到演唱会票吗\n"
    "今日份的签到来了\n"
)


def ensure_default_files():
    if not send.GROUPS_FILE.exists():
        send.GROUPS_FILE.write_text(DEFAULT_GROUPS, encoding="utf-8")
    if not send.MESSAGES_FILE.exists():
        send.MESSAGES_FILE.write_text(DEFAULT_MESSAGES, encoding="utf-8")


# ---------- 检测与安装动作（在线程里跑，log 为回调） ----------

def http_ok():
    try:
        with urllib.request.urlopen(send.API + "/get_version_info", timeout=3) as r:
            return json.loads(r.read().decode("utf-8")).get("retcode") == 0
    except Exception:
        return False


def qq_installed():
    candidates = [os.path.expandvars(p) for p in (
        r"%PROGRAMFILES%\Tencent\QQNT\QQ.exe",
        r"%PROGRAMFILES(X86)%\Tencent\QQNT\QQ.exe",
        r"%LOCALAPPDATA%\Programs\Tencent\QQNT\QQ.exe",
    )]
    return any(os.path.exists(p) for p in candidates)


def find_boot_bat():
    for name in ("NapCatWinBootMain.bat", "BootMain.bat", "Launcher.bat", "launcher.bat"):
        p = NAPCAT_DIR / name
        if p.exists():
            return p
    bats = sorted(NAPCAT_DIR.glob("*.bat"))
    return bats[0] if bats else None


def act_qq(log):
    log("已打开 QQ 官网下载页，安装完成后回到本程序点【重新检测】")
    webbrowser.open(QQ_URL)
    return False  # 需要用户手动装完再检测


def act_napcat(log):
    NAPCAT_DIR.mkdir(exist_ok=True)
    log("正在获取 NapCat 最新版本...")
    req = urllib.request.Request(NAPCAT_API, headers={"User-Agent": "qq-active-installer"})
    with urllib.request.urlopen(req, timeout=30) as r:
        rel = json.loads(r.read().decode("utf-8"))
    asset = next((a for a in rel["assets"]
                  if a["name"].startswith("NapCat.Shell") and a["name"].endswith(".zip")), None)
    if not asset:
        log("未找到 NapCat.Shell 资源，请到 GitHub Releases 手动下载")
        return False
    log(f"下载 {asset['name']} ...")
    zip_path = BASE / "napcat.zip"
    urllib.request.urlretrieve(asset["browser_download_url"], zip_path)
    log("解压中...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(NAPCAT_DIR)
    zip_path.unlink()
    log(f"NapCat 已安装到 {NAPCAT_DIR}")
    return True


def act_login(log):
    bat = find_boot_bat()
    if not bat:
        log("未找到 NapCat 启动脚本，请先完成上一步")
        return False
    log(f"启动 {bat.name} ...")
    subprocess.Popen(["cmd", "/c", str(bat)], cwd=str(NAPCAT_DIR))
    log("1) 在弹出的 NapCat 窗口中完成 QQ 登录（小号）")
    log("2) 稍后自动打开 WebUI → 网络配置 → 新建 HTTP 服务器，端口 3000")
    webbrowser.open("http://127.0.0.1:6099/webui")
    for i in range(100):  # 最长等 5 分钟
        time.sleep(3)
        if http_ok():
            log("OneBot HTTP 接口已连通")
            return True
        if i % 10 == 9:
            log("等待接口开通...（请确认已在 WebUI 开启 HTTP 3000）")
    log("超时：完成登录和配置后，点【重新检测】")
    return False


def task_exists():
    try:
        r = subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME],
                           capture_output=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False


def act_task(log):
    if getattr(sys, "frozen", False):
        target = f'"{sys.executable}" --daily'
    else:
        target = f'python "{BASE / "app.py"}" --daily'
    r = subprocess.run(
        ["schtasks", "/Create", "/F", "/TN", TASK_NAME,
         "/TR", target, "/SC", "DAILY", "/ST", "09:30"],
        capture_output=True, text=True, timeout=15)
    out = (r.stdout or "") + (r.stderr or "")
    if out.strip():
        log(out.strip())
    if r.returncode == 0:
        log("计划任务已注册：每天 9:30 触发，程序内随机延迟 0~60 分钟发送")
        return True
    log("注册失败：请右键以管理员身份运行本程序再试")
    return False


# ---------- 组件定义 ----------

COMPONENTS = [
    {"key": "qq", "name": "QQ 桌面客户端",
     "desc": "NapCat 需要官方 QQ 客户端作为运行基础。\n检测不到时会打开官网，安装后点【重新检测】。",
     "check": qq_installed, "act": act_qq, "threaded": True},
    {"key": "napcat", "name": "NapCat（QQ 挂机端）",
     "desc": "从 GitHub 自动下载最新 NapCat.Shell 并解压到 napcat 目录。",
     "check": lambda: find_boot_bat() is not None, "act": act_napcat, "threaded": True},
    {"key": "login", "name": "登录与接口开通",
     "desc": "启动 NapCat，你扫码登录小号，并在 WebUI 里开启 HTTP 3000。\n程序会自动轮询直到接口连通。",
     "check": http_ok, "act": act_login, "threaded": True},
    {"key": "config", "name": "群号与文案配置",
     "desc": "填写要发消息的群号（每行一个），文案库可先用默认。",
     "check": lambda: bool(send.load_lines(send.GROUPS_FILE))
                      and bool(send.load_lines(send.MESSAGES_FILE)),
     "act": None, "threaded": False},  # act 由界面直接打开编辑器
    {"key": "task", "name": "每日定时任务",
     "desc": "注册 Windows 计划任务：每天 9:30 触发，随机延迟 0~60 分钟后自动发送一轮。",
     "check": task_exists, "act": act_task, "threaded": True},
]


# ---------- GUI ----------

class QueueWriter:
    def __init__(self, q):
        self.q = q

    def write(self, s):
        if s.strip():
            self.q.put(s)

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        root.title("QQ 群活跃 · 安装向导")
        root.geometry("860x560")
        self.q = queue.Queue()
        self.sending = False
        self.sel = 0
        self.status = {c["key"]: None for c in COMPONENTS}  # None=未检测
        ensure_default_files()

        self.installer_frame = ttk.Frame(root, padding=10)
        self.main_frame = ttk.Frame(root, padding=10)
        self._build_installer()
        self._build_main()
        self.show_installer()
        root.after(200, self._poll_log)

    # ----- 安装页 -----
    def _build_installer(self):
        f = self.installer_frame
        left = ttk.Frame(f)
        left.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(left, text="安装清单", font=("", 11, "bold")).pack(anchor="w", pady=(0, 6))
        self.comp_list = tk.Listbox(left, width=24, height=len(COMPONENTS),
                                    activestyle="dotbox", exportselection=False)
        for c in COMPONENTS:
            self.comp_list.insert("end", f"⬜ {c['name']}")
        self.comp_list.pack(fill="y")
        self.comp_list.bind("<<ListboxSelect>>", lambda e: self._on_select())

        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True)
        self.desc_var = tk.StringVar()
        ttk.Label(right, textvariable=self.desc_var, justify="left", wraplength=520).pack(anchor="w", pady=(0, 8))
        btns = ttk.Frame(right)
        btns.pack(anchor="w", pady=(0, 8))
        self.btn_act = ttk.Button(btns, text="安装 / 执行", command=self._do_act)
        self.btn_act.pack(side="left", padx=(0, 6))
        self.btn_check = ttk.Button(btns, text="重新检测", command=self._do_check)
        self.btn_check.pack(side="left", padx=(0, 6))
        self.btn_all = ttk.Button(btns, text="一键全部安装", command=self._do_all)
        self.btn_all.pack(side="left")
        self.btn_next = ttk.Button(right, text="全部完成，进入主界面 →", command=self.show_main, state="disabled")
        self.btn_next.pack(anchor="w", pady=(6, 8))
        self.log_text = tk.Text(right, height=14, state="disabled", wrap="none")
        self.log_text.pack(fill="both", expand=True)

    def show_installer(self):
        self.main_frame.pack_forget()
        self.installer_frame.pack(fill="both", expand=True)
        self._refresh()

    def _on_select(self):
        sel = self.comp_list.curselection()
        if sel:
            self.sel = sel[0]
            self._refresh()

    def _refresh(self):
        self.comp_list.delete(0, "end")
        for i, c in enumerate(COMPONENTS):
            mark = {None: "⬜", False: "❌", True: "✅"}[self.status[c["key"]]]
            self.comp_list.insert("end", f"{mark} {c['name']}")
            if i == self.sel:
                self.comp_list.selection_set(i)
        self.desc_var.set(COMPONENTS[self.sel]["desc"])
        if all(self.status[c["key"]] for c in COMPONENTS):
            self.btn_next.config(state="normal")

    def log(self, msg):
        self.q.put(msg if msg.endswith("\n") else msg + "\n")

    def _poll_log(self):
        try:
            while True:
                self.log_text.config(state="normal")
                self.log_text.insert("end", self.q.get_nowait())
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(200, self._poll_log)

    def _do_check(self):
        c = COMPONENTS[self.sel]
        self.status[c["key"]] = bool(c["check"]())
        self._refresh()

    def _do_act(self):
        c = COMPONENTS[self.sel]
        if c["key"] == "config":
            self._open_editor()
            self.status["config"] = bool(c["check"]())
            self._refresh()
            return
        self._run_act(c)

    def _run_act(self, c):
        self.btn_act.config(state="disabled")
        self.btn_all.config(state="disabled")

        def worker():
            try:
                ok = c["act"](self.log)
            except Exception as e:
                self.log(f"出错: {e}")
                ok = False
            self.status[c["key"]] = bool(ok)
            self.root.after(0, self._refresh)
            self.root.after(0, lambda: (self.btn_act.config(state="normal"),
                                        self.btn_all.config(state="normal")))
        threading.Thread(target=worker, daemon=True).start()

    def _do_all(self):
        def worker():
            for c in COMPONENTS:
                self.log(f"===== {c['name']} =====")
                if c["check"]():
                    self.status[c["key"]] = True
                    self.root.after(0, self._refresh)
                    self.log("已就绪，跳过")
                    continue
                if c["key"] == "config":
                    self.root.after(0, self._open_editor_blocking_next)
                    return  # 编辑器需要主线程交互，装完前几项后再继续
                try:
                    ok = c["act"](self.log)
                except Exception as e:
                    self.log(f"出错: {e}")
                    ok = False
                self.status[c["key"]] = bool(ok)
                self.root.after(0, self._refresh)
                if not ok and c["key"] == "qq":
                    self.log("请先安装 QQ，再点【一键全部安装】继续")
                    return
            self.log("===== 全部完成，可进入主界面 =====")
        threading.Thread(target=worker, daemon=True).start()

    def _open_editor_blocking_next(self):
        self._open_editor()
        self.status["config"] = bool(COMPONENTS[3]["check"]())
        self._refresh()
        self.log("配置已保存。若其他项均 ✅，可进入主界面；否则继续【一键全部安装】")
        self.btn_act.config(state="normal")
        self.btn_all.config(state="normal")

    def _open_editor(self):
        win = tk.Toplevel(self.root)
        win.title("群号与文案配置")
        win.geometry("640x520")
        ttk.Label(win, text="群号（每行一个）").pack(anchor="w", padx=10, pady=(10, 0))
        g = tk.Text(win, height=10)
        g.pack(fill="both", expand=True, padx=10)
        g.insert("1.0", send.GROUPS_FILE.read_text(encoding="utf-8"))
        ttk.Label(win, text="文案库（每行一条，随机抽取）").pack(anchor="w", padx=10, pady=(8, 0))
        m = tk.Text(win, height=12)
        m.pack(fill="both", expand=True, padx=10)
        m.insert("1.0", send.MESSAGES_FILE.read_text(encoding="utf-8"))

        def save():
            send.GROUPS_FILE.write_text(g.get("1.0", "end"), encoding="utf-8")
            send.MESSAGES_FILE.write_text(m.get("1.0", "end"), encoding="utf-8")
            messagebox.showinfo("保存", "已保存", parent=win)
            win.destroy()
        ttk.Button(win, text="保存", command=save).pack(pady=8)
        win.grab_set()

    # ----- 主界面 -----
    def _build_main(self):
        f = self.main_frame
        ttk.Label(f, text="QQ 群活跃 · 主控台", font=("", 13, "bold")).pack(anchor="w", pady=(0, 4))
        self.main_info = tk.StringVar(value=(
            "一切就绪。每天 9:30 计划任务自动触发，随机延迟 0~60 分钟后发送一轮。\n"
            "发送时会从文案库随机抽取，每个群 2~3 条，群间隔 30~90 秒。"))
        ttk.Label(f, textvariable=self.main_info, justify="left").pack(anchor="w", pady=(0, 10))
        btns = ttk.Frame(f)
        btns.pack(anchor="w", pady=(0, 10))
        ttk.Button(btns, text="立即发送一轮", command=lambda: self._send(test=False)).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="测试发送一条", command=lambda: self._send(test=True)).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="编辑群号与文案", command=self._open_editor).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="返回安装页", command=self.show_installer).pack(side="left")
        self.main_log = tk.Text(f, height=16, state="disabled", wrap="none")
        self.main_log.pack(fill="both", expand=True)

    def show_main(self):
        self.installer_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.log_text = self.main_log  # 日志切到主界面

    def _send(self, test=False):
        if self.sending:
            self.log("已有发送任务在进行中")
            return
        groups = send.load_lines(send.GROUPS_FILE)
        messages = send.load_lines(send.MESSAGES_FILE)
        if not groups or not messages:
            self.log("groups.txt / messages.txt 为空")
            return

        def worker():
            self.sending = True
            old = sys.stdout
            sys.stdout = QueueWriter(self.q)
            try:
                if test:
                    send.send_group_msg(groups[0], random.choice(messages))
                    self.log("测试发送完成，去群里看看")
                else:
                    send.run_once(groups, messages)
            except Exception as e:
                self.log(f"发送出错: {e}")
            finally:
                sys.stdout = old
                self.sending = False
        threading.Thread(target=worker, daemon=True).start()


def run_daily_console():
    """计划任务调用：日志写文件，随机延迟后发一轮"""
    with open(LOG_FILE, "a", encoding="utf-8", buffering=1) as lf:
        class Tee:
            def write(self, s):
                lf.write(s)

            def flush(self):
                lf.flush()
        sys.stdout = sys.stderr = Tee()
        print(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} 计划任务触发 =====")
        ensure_default_files()
        groups = send.load_lines(send.GROUPS_FILE)
        messages = send.load_lines(send.MESSAGES_FILE)
        if not groups or not messages:
            print("配置为空，跳过本次发送")
            return
        delay = random.randint(0, 3600)
        print(f"随机延迟 {delay // 60} 分 {delay % 60} 秒后发送")
        time.sleep(delay)
        send.run_once(groups, messages)


def main():
    if "--daily" in sys.argv:
        run_daily_console()
        return
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
