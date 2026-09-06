# QQ 群活跃度自动发送

自动给多个 QQ 群每天发送 2~3 条随机寒暄消息，维持群活跃度，防止因"低活跃"被踢。支持 **Windows** 和 **安卓（Termux）** 双平台。

> ⚠️ 仅供个人学习使用。任何第三方自动化均违反 QQ 用户协议，存在账号风控风险，请自行评估。建议先用小号试跑 1~2 周。

## 工作原理

```
┌─────────────┐   HTTP (127.0.0.1:3000)   ┌──────────────────┐
│  send.py    │ ──────── 发送消息 ────────▶│  QQ 挂机端        │
│  定时+随机   │                            │ NapCat / Lagrange │
└─────────────┘                            └──────────────────┘
```

- **send.py**：核心脚本，跨平台，纯 Python 标准库（无需 pip 安装）
  - 群顺序随机、文案随机抽取、每群 2~3 条
  - 消息间隔 20~60 秒、群间隔 30~90 秒，模拟真人节奏
  - `--loop` 模式：每天 9~11 点随机挑时间自动发送
- **QQ 挂机端**（登录你的 QQ 号，暴露本地 API）
  - Windows：[NapCat](https://github.com/NapNeko/NapCatQQ)（基于官方客户端内核，风险较低）
  - 安卓：[Lagrange.OneBot](https://github.com/LagrangeDev/Lagrange.OneBot)（Termux 免 root 运行）

## 文件说明

| 文件 | 说明 |
|---|---|
| `send.py` | 发送脚本（两平台通用） |
| `groups.txt` | 群号列表，每行一个 |
| `messages.txt` | 文案库，每行一条，随机抽取 |
| `windows/send.bat` | Windows 启动器，双击运行 |
| `android/start.sh` | 安卓一键启动（挂机端 + 每日循环） |
| `android/stop.sh` | 安卓一键停止 |
| `android/boot.sh` | 安卓开机自启（配合 Termux:Boot） |

## 下载

```bash
# 方式一：git 克隆（私有仓库需输入 GitHub 账号 + Personal Access Token）
git clone https://github.com/kkxxdbx/qq-active.git

# 方式二：网页下载 zip
# 仓库页面 → 绿色 Code 按钮 → Download ZIP → 解压
```

## Windows 使用

1. 安装 [Python](https://www.python.org/downloads/)（勾选 Add to PATH）
2. 下载并运行 NapCat，扫码登录小号，WebUI（`127.0.0.1:6099`）中开启 HTTP 服务器，端口 `3000`
3. 编辑 `groups.txt` 填入群号
4. 测试：`windows\send.bat --test`；完整一轮：`windows\send.bat`
5. 每日自动（管理员 PowerShell）：

```powershell
$action  = New-ScheduledTaskAction -Execute "python" -Argument '"C:\qq-active\send.py" --loop'
$trigger = New-ScheduledTaskTrigger -Daily -At "09:30"
$trigger.RandomDelay = "PT1H"
Register-ScheduledTask -TaskName "QQ群活跃" -Action $action -Trigger $trigger
```

## 安卓使用（建议旧手机插电常开）

1. F-Droid 安装 Termux 和 Termux:Boot（不要用 Play 商店版）
2. `pkg update -y && pkg install python -y && termux-setup-storage`
3. 本项目放到 `~/qq-active/`，下载 Lagrange.OneBot（linux-arm64）至同目录并 `chmod +x`
4. 首次运行 `./Lagrange.OneBot`，编辑 `config.json` 开启 HTTP（端口 3000），再运行扫码登录
5. 启动：`bash android/start.sh`；停止：`bash android/stop.sh`
6. 保活：系统设置中给 Termux 关闭电池优化；`cp android/boot.sh ~/.termux/boot/` 实现开机自启

## 维护建议

- 每月往 `messages.txt` 补充几条新文案，内容越杂越安全
- 小号试跑 1~2 周无异常后再换大号
- 想调整发送条数/间隔，改 `send.py` 顶部配置区
