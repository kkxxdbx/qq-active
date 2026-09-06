#!/data/data/com.termux/files/usr/bin/sh
# QQ 群活跃 · 安卓一键安装（Termux）
# 用法（仓库公开时）:
#   bash <(curl -fsSL https://raw.githubusercontent.com/kkxxdbx/qq-active/main/android/install.sh)
# 仓库私有时，先手动克隆再运行:
#   git clone https://github.com/kkxxdbx/qq-active.git ~/qq-active && bash ~/qq-active/android/install.sh
set -e
REPO_URL="${REPO_URL:-https://github.com/kkxxdbx/qq-active.git}"
DIR="$HOME/qq-active"

echo "==> [1/5] 安装基础软件..."
pkg update -y && pkg install -y python git wget unzip curl

echo "==> [2/5] 获取项目代码..."
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only || echo "更新失败，使用本地已有代码"
else
  git clone --depth 1 "$REPO_URL" "$DIR"
fi
cd "$DIR"

echo "==> [3/5] 下载 Lagrange.OneBot (linux-arm64)..."
if [ ! -x ./Lagrange.OneBot ]; then
  URL=$(curl -fsSL https://api.github.com/repos/LagrangeDev/Lagrange.OneBot/releases/latest \
        | grep -o '"browser_download_url": *"[^"]*linux-arm64[^"]*"' | head -1 | cut -d'"' -f4)
  if [ -z "$URL" ]; then
    echo "未找到下载地址，请到 LagrangeDev/Lagrange.OneBot 的 Releases 手动下载 linux-arm64 版"
    exit 1
  fi
  wget -q -O lagrange.zip "$URL"
  unzip -o -q lagrange.zip
  rm -f lagrange.zip
  chmod +x Lagrange.OneBot
fi

echo "==> [4/5] 配置 HTTP 接口 (127.0.0.1:3000)..."
# 首次运行让 Lagrange 生成默认配置
[ -f appsettings.json ] || [ -f config.json ] || timeout 8 ./Lagrange.OneBot >/dev/null 2>&1 || true
python - <<'EOF'
import json, os
for name in ("appsettings.json", "config.json"):
    if not os.path.exists(name):
        continue
    with open(name, encoding="utf-8") as f:
        cfg = json.load(f)
    imps = cfg.setdefault("implementations", [])
    for imp in imps:
        if imp.get("type") in ("forward_http", "http", "HttpPost"):
            imp.update({"type": "forward_http", "host": "127.0.0.1", "port": 3000})
            break
    else:
        imps.append({"type": "forward_http", "host": "127.0.0.1", "port": 3000})
    with open(name, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"已配置 {name}: HTTP 127.0.0.1:3000")
    break
else:
    print("未找到配置文件，请按 README 手动配置 HTTP 3000")
EOF

echo "==> [5/5] 保活与开机自启..."
command -v termux-wake-lock >/dev/null && termux-wake-lock && echo "CPU 唤醒锁已开启"
if command -v su >/dev/null 2>&1; then
  if su -c 'dumpsys deviceidle whitelist +com.termux' >/dev/null 2>&1; then
    echo "root: 已将 Termux 加入系统休眠白名单"
  else
    echo "root: 白名单设置失败，请手动到设置里关闭 Termux 电池优化"
  fi
else
  echo "无 root: 请到系统设置 → 应用 → Termux → 电池 → 不受限"
fi
if [ -d "$HOME/.termux/boot" ]; then
  cp -f android/boot.sh "$HOME/.termux/boot/qq-active.sh"
  echo "开机自启已配置（需已安装 Termux:Boot 应用）"
fi

echo
echo "安装完成！接下来两步："
echo "  1. 填群号:      nano ~/qq-active/groups.txt   （每行一个群号）"
echo "  2. 启动并登录:  bash ~/qq-active/android/start.sh  （首次会显示二维码，用小号扫）"
