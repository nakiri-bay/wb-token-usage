# WorkBuddy 积分消耗统计

> 仓库名：`wb-token-usage` · License: MIT · 平台：Windows

一个 Windows 桌面悬浮挂件：人物头顶的气泡实时显示 **今日用量** 与 **累计用量**。
打开它就会自动同步一次官方数据，之后每 13~17 分钟静默同步一次；关掉它，同步也一起停。
点气泡上的 ↻ 可以随时手动刷新。

```
      ╭──────────────────────────╮
      │  今日用量：219.55  ↻      │   ← 气泡（实时刷新）
      │     累计用量：602.44      │
      ╰────────────▼─────────────╯
                ( ˶‾᷄ ⁻̫ ‾᷅˵ )        ← 透明底人物贴图，可拖动
```

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 透明无边框窗口 | 用 Windows `-transparentcolor` 抠掉键色，只有角色和气泡可见，无白底方框 |
| 置顶 + 可拖拽 | 始终在最前，按住人物拖到任意位置 |
| 聊天气泡 | 显示 `今日用量` / `累计用量` |
| ↻ 一键刷新 | 后台线程跑同步，不弹黑窗、不卡界面 |
| 打开即同步 | 启动桌宠时立刻同步一次，无需再单独启动守护进程 |
| 定时同步 | 之后每 **15 分钟 ± 2 分钟** 随机静默同步一次（避免访问过于规律） |
| 退出即停止 | 退出桌宠时同步线程与浏览器进程一并结束，不留后台残留 |
| 双重数据源 | 官方同步值优先，本地估算值（`points_log.jsonl`）兜底 |
| 单实例保护 | 重复双击只会有一个桌宠，第二次会提示“已在运行” |

## 📁 目录结构

```
wb-token-usage/
├── src/                          # 源码
│   ├── deskpet.py                #   主程序：GUI + 同步生命周期（推荐的入口）
│   ├── sync_usage.py             #   官方用量同步（浏览器自动化，可独立调用）
│   ├── auto_sync.py              #   独立同步守护（可选，见下文“两种运行模式”）
│   └── log_points.py             #   本地积分记账（写 points_log.jsonl）
├── scripts/                      # 启动器（双击即用）
│   ├── 静默启动统计.vbs           #   ★ 启动桌宠（无窗口），同步随之开始
│   ├── 启动统计.bat               #   同上，但保留控制台，便于调试
│   ├── 同步用量.vbs / .bat        #   手动立刻同步一次
│   ├── auto_sync.vbs             #   启动“独立同步守护”（不常开桌宠时用）
│   └── 停止自动同步.bat           #   结束独立同步守护
├── assets/
│   └── pet_image.png             #   人物贴图（透明键色预合成，无 alpha）
├── tools/                        # 图像素材工具（只在换角色时需要）
│   ├── make_cutout.py            #   从“纯色/浅色背景”原图抠图生成贴图
│   └── gen_to_pet.py             #   从 AI 生成的“棋盘格假透明”图生成贴图
├── docs/
│   ├── 桌宠功能调研.md            #   同类开源桌宠项目的功能对比
│   └── 发布到GitHub-计划.md
├── config.json                   # 配置（刷新间隔、积分单价等）
├── requirements.txt
├── LICENSE
└── README.md
```

**源码与数据分离**：`src/` 里只有代码；所有运行期数据（配置、用量、日志、浏览器 profile）
都落在**项目根目录**，且已在 `.gitignore` 中排除 —— 这样整个文件夹随便移动都不会丢数据，
也不会误把登录态推到 GitHub。

运行后额外生成（全部已忽略）：

| 文件 | 说明 |
|------|------|
| `official_daily.json` | 官方同步到的每日积分 `{日期: 积分}` |
| `points_log.jsonl` | 本地记账流水（每行一条 JSON） |
| `sync_log.txt` | 同步日志（桌宠内嵌同步也写这里） |
| `auto_sync_log.txt` | 独立守护模式的日志 |
| `edge_sync_profile/` | 浏览器持久化 profile（含登录 Cookie，**切勿提交**） |
| `last_full_snapshot.txt` | 上一次抓取的页面快照（排查用） |

## 🔄 同步是怎么工作的

```
 desktop 浏览器?  不是。
 deskpet.py ──── 后台同步线程 ──── sync_usage.sync_once()
    │                                  │
    │                                  ├─ 拉起 agent-browser（自带 Chromium）
    │                                  │   + 独立 profile（内含已登录 Cookie）
    │                                  ├─ 打开 WorkBuddy 用量页 → 勾选“今天”
    │                                  ├─ 逐页快照 → 解析“积分消耗”列求和（按请求哈希去重）
    │                                  └─ 写入 official_daily.json
    │
    └─ 每 1.5s 读 official_daily.json + points_log.jsonl → 重绘气泡
```

- **一条 batch 命令**内完成 打开 / 勾选 / 翻页 / 快照：浏览器自动化 daemon 在单次调用期间
  持续存活，分条调用会因 daemon 不跨进程常驻而失败。
- 每次同步前先 `agent-browser close` 清掉残留守护，否则会打印
  `--profile, --args ignored: daemon already running` 并拿到残缺快照。
- 同步跑在后台线程且**串行**：手动点 ↻ 只是提前唤醒等待，不会和定时任务抢同一个 profile。

## ⚙️ 两种运行模式（二选一）

| 模式 | 入口 | 适合 |
|------|------|------|
| **随桌宠（默认，推荐）** | `scripts/静默启动统计.vbs` | 想要桌面挂件，且希望同步随挂件开关 |
| **独立守护** | `scripts/auto_sync.vbs` | 不想常驻窗口，只要后台默默记录 |

> 两种模式**不要同时跑**：它们会争抢同一个浏览器 profile，导致快照残缺、同步失败。
> 桌宠自带单实例保护，独立守护用 `auto_sync.pid` 做单实例保护。

## 🔧 运行环境

- Windows 10 / 11
- Python 3.8+，**必须包含 `tkinter`**（python.org 官方安装默认自带）
- Node.js + [`agent-browser`](https://www.npmjs.com/package/agent-browser)
  —— **仅“同步官方用量”需要**；只要界面不要同步的话可以不装

启动器会自动在 `%LOCALAPPDATA%\Programs\Python\Python3*` 下寻找带 tkinter 的 `pythonw.exe`，
找不到则回退到 PATH 里的 `pythonw`，无需手动改路径。
若 node / agent-browser 在非标准位置，可设环境变量 `WB_NODE_EXE`、`WB_AGENT_BROWSER_JS`。

## 🚀 快速开始

```bash
git clone https://github.com/nakiri-bay/wb-token-usage.git
cd wb-token-usage
pip install -r requirements.txt     # 仅图像工具需要；主程序只用标准库
npm i -g agent-browser              # 仅“同步官方用量”需要
```

首次使用同步功能前，需要在 `edge_sync_profile` 里**登录一次** WorkBuddy：
双击 `scripts/同步用量.bat`（有控制台、能看到提示）跑一次，按提示在弹出的浏览器里登录。
Cookie 会持久化，之后无需重复登录。

## ▶️ 使用

1. **启动**：双击 `scripts/静默启动统计.vbs` —— 桌宠出现，同时自动同步一次。
   想看日志就用 `scripts/启动统计.bat`。
2. **手动同步**：点气泡上的 ↻，或右键人物 → 立即同步用量。
3. **退出**：右键人物 → 退出统计（同步线程与浏览器进程一并结束）。
4. **开机自启**（可选）：把 `scripts/静默启动统计.vbs` 的快捷方式放进
   `shell:startup`（Win+R 输入即可打开启动文件夹）。

## ⚙️ 配置（`config.json`）

| 字段 | 说明 |
|------|------|
| `refresh_ms` | 界面刷新间隔（毫秒），默认 `1500` |
| `points_per_reply` | 本地估算：每次助手回复折算积分 |
| `points_per_tool_call` | 本地估算：每次工具调用折算积分 |
| `pet_name` | 角色名字 |
| `pet_color` / `bg_color` | 主题色（供扩展使用） |

同步节奏常量在 `src/sync_usage.py` 顶部的 `INTERVAL` / `JITTER`（默认 900±120 秒），
桌宠内嵌同步与独立守护共用这一处，改一次即可。

## ❓ 常见问题

**气泡一直显示估算值，同步没生效？**
看 `sync_log.txt`。若出现 `--profile, --args ignored: daemon already running`，
说明有残留的浏览器守护进程——现代码每次同步前会先 `agent-browser close`，正常不应再出现。

**提示页面未登录？**
`edge_sync_profile/` 里的登录态失效了。删掉该目录，用 `scripts/同步用量.bat` 重新登录一次。

**双击没反应？**
用 `scripts/启动统计.bat` 启动能看到报错信息（`静默启动统计.vbs` 没有窗口）。

## 🔒 隐私说明

本仓库**不包含**任何登录态、Cookie、手机号或真实用量数据：

- 浏览器 profile（`edge_sync_profile/` 等）已在 `.gitignore` 中排除；
- `official_daily.json`、`points_log.jsonl`、各类日志、页面快照均已排除；
- 启动器里的路径全部用 `%LOCALAPPDATA%`、`%~dp0` 动态解析，不含用户名；
- 同步脚本只读取你本机已登录的用量页面，不向任何第三方发送数据。

## 📄 License

[MIT](LICENSE) © 2026 nakiri-bay
