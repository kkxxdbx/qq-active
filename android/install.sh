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
if [ -x ./Lagrange.OneBot ]; then
  echo "已安装，跳过（重装请删除 Lagrange.OneBot 后重跑）"
else
  # OneBot 仓库已合并：发布物现在挂在 Lagrange.Core 的 nightly 下
  URL=$(curl -fsSL "https://api.github.com/repos/LagrangeDev/Lagrange.Core/releases/tags/nightly" 2>/dev/null \
        | grep -o '"browser_download_url": *"[^"]*linux-arm64[^"]*\.tar\.gz"' | head -1 | cut -d'"' -f4)
  if [ -z "$URL" ]; then
    # API 限流/失败时用固定直链兜底
    URL="https://github.com/LagrangeDev/Lagrange.Core/releases/download/nightly/Lagrange.OneBot_linux-arm64_net9.0_SelfContained.tar.gz"
    echo "GitHub API 不可用，改用固定直链"
  fi
  echo "下载: $URL"
  wget -q -O lagrange.pkg "$URL" || { echo "下载失败，请手动下载后放到 $DIR 并 chmod +x"; exit 1; }
  case "$URL" in
    *.zip)          unzip -o -q lagrange.pkg ;;
    *.tar.gz|*.tgz) tar xzf lagrange.pkg ;;
    *)              tar xzf lagrange.pkg 2>/dev/null || unzip -o -q lagrange.pkg ;;
  esac
  rm -f lagrange.pkg
  # 发布包内是深层嵌套路径（.../publish/Lagrange.OneBot），把主程序挪到根目录
  FOUND=$(find . -type f -name "Lagrange.OneBot" 2>/dev/null | head -1)
  if [ -z "$FOUND" ]; then
    echo "解压后未找到主程序 Lagrange.OneBot"
    exit 1
  fi
  if [ "$FOUND" != "./Lagrange.OneBot" ]; then
    mv "$FOUND" ./Lagrange.OneBot.tmp
    rm -rf ./Lagrange.OneBot        # 解压出的目录树与目标文件名冲突，先删
    mv ./Lagrange.OneBot.tmp ./Lagrange.OneBot
  fi
  chmod +x ./Lagrange.OneBot
fi

echo "==> [4/5] 配置 HTTP 接口 (127.0.0.1:3000)..."
# 首次运行让 Lagrange 生成默认配置
[ -f appsettings.json ] || [ -f config.json ] || timeout 15 ./Lagrange.OneBot >/dev/null 2>&1 || true
python - <<'EOF'
import json, os
for name in ("appsettings.json", "config.json"):
    if not os.path.exists(name):
        continue
    with open(name, encoding="utf-8") as f:
        cfg = json.load(f)
    # 新版配置键为大写 Implementations，兼容旧小写
    key = "Implementations" if "Implementations" in cfg else "implementations"
    imps = cfg.get(key) or []
    replaced = False
    for imp in imps:
        t = imp.get("Type") or imp.get("type") or ""
        if t.lower() in ("forwardhttp", "forward_http", "http"):
            imp.clear()
            imp.update({"Type": "ForwardHttp", "Host": "127.0.0.1", "Port": 3000,
                        "HeartBeatEnable": False, "HeartBeatInterval": 5000, "AccessToken": ""})
            replaced = True
            break
    if not replaced:
        imps.append({"Type": "ForwardHttp", "Host": "127.0.0.1", "Port": 3000,
                     "HeartBeatEnable": False, "HeartBeatInterval": 5000, "AccessToken": ""})
    cfg[key] = imps
    with open(name, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)
    print(f"已配置 {name}: ForwardHttp 127.0.0.1:3000")
    break
else:
    print("未找到配置文件，请按 README 手动配置 ForwardHttp 127.0.0.1:3000")
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
