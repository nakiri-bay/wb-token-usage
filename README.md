# WorkBuddy 积分消耗统计

> 仓库：`wb-token-usage`

一个 Windows 桌面悬浮挂件：人物头顶气泡实时显示 **今日用量** 与 **累计用量**。
点一下气泡上的 ↻ 图标即可在后台拉取 WorkBuddy 官方数据，另有一个静默守护进程每
13~17 分钟自动同步一次，让你随时知道今天“烧”了多少积分。

> 仅支持 Windows（依赖 `-transparentcolor` 透明窗口与 `pythonw` 无窗口运行）。

## ✨ 功能

- **透明无边框窗口 + 置顶**：人物贴图没有白底、没有方框，只有角色和气泡。
- **聊天气泡**：显示 `今日用量：xx` / `累计用量：xx`。
- **↻ 一键刷新**：点图标在后台线程跑同步，不弹黑窗、不卡界面，完成后自动收尾。
- **可拖拽**：按住人物拖到任意位置。
- **右键菜单**：手动刷新 / 打开官方用量页 / 退出。
- **自动同步**：后台守护进程每 15 分钟 ±2 分钟随机静默同步一次。
- **双重数据源**：官方同步值优先，本地估算值（`points_log.jsonl`）兜底。

## 📁 目录结构

```
wb-token-usage/
├─ deskpet.py            # 主程序（GUI）
├─ sync_usage.py         # 官方用量同步（浏览器自动化）
├─ auto_sync.py          # 自动同步守护进程（后台常驻）
├─ log_points.py         # 本地积分记账（写入 points_log.jsonl）
├─ config.json           # 配置（角色名、颜色、刷新间隔、积分单价）
├─ pet_image.png         # 人物贴图（透明键色预合成）
├─ requirements.txt
├─ 静默启动统计.vbs       # 双击启动（无窗口）
├─ auto_sync.vbs         # 双击启动自动同步守护
├─ 同步用量.vbs / .bat    # 手动同步一次
├─ 停止自动同步.bat       # 结束自动同步守护
└─ 启动统计.bat           # 带控制台启动（调试用）
```

运行后会额外生成（已在 `.gitignore` 中排除）：

| 文件 | 说明 |
|------|------|
| `official_daily.json` | 官方同步到的每日积分（`{日期: 积分}`） |
| `points_log.jsonl` | 本地记账流水（每行一条 JSON） |
| `sync_log.txt` / `auto_sync_log.txt` | 同步日志 |
| `edge_sync_profile/` | 浏览器持久化 profile（含登录 Cookie，**勿提交**） |

## 🔧 运行环境

- Windows 10 / 11
- Python 3.8+，**必须包含 `tkinter`**（官方 python.org 安装默认自带）
- Node.js + [`agent-browser`](https://www.npmjs.com/package/agent-browser)（**仅“同步官方用量”功能需要**，纯界面运行不需要）

> 启动器（`.vbs` / `.bat`）会自动在 `%LOCALAPPDATA%\Programs\Python\Python3*` 下寻找可用的
> `pythonw.exe`，找不到时回退到 PATH 里的 `pythonw`，无需手动改路径。
> 若你的 node / agent-browser 在非标准位置，可设置环境变量 `WB_NODE_EXE`、
> `WB_AGENT_BROWSER_JS` 指向对应文件。

## 🚀 安装

```bash
git clone https://github.com/nakiri-bay/wb-token-usage.git
cd wb-token-usage
pip install -r requirements.txt
```

`requirements.txt` 中的依赖仅用于图像处理脚本（`make_cutout.py` / `gen_to_pet.py`）。
主程序与同步脚本只用 Python 标准库。

## ▶️ 使用

1. **启动**：双击 `静默启动统计.vbs`（无窗口）。调试时可用 `启动统计.bat` 看输出。
2. **启动自动同步**：双击 `auto_sync.vbs`。日志见 `auto_sync_log.txt`。
3. **手动同步一次**：双击 `同步用量.vbs`。
4. **停止自动同步**：双击 `停止自动同步.bat`。
5. **退出**：右键人物 → 退出统计。

> 首次使用“同步官方用量”前，需要在 `edge_sync_profile` 对应的浏览器 profile 里
> 登录一次 WorkBuddy，之后 Cookie 会持久化，无需重复登录。

## ⚙️ 配置（`config.json`）

| 字段 | 说明 |
|------|------|
| `refresh_ms` | 界面刷新间隔（毫秒），默认 1500 |
| `points_per_reply` | 本地估算：每次助手回复折算积分 |
| `points_per_tool_call` | 本地估算：每次工具调用折算积分 |
| `pet_name` | 角色名字 |
| `pet_color` / `bg_color` | 主题色（供扩展使用） |

## 🔒 隐私说明

本仓库**不包含**任何登录态、Cookie、手机号或真实用量数据：

- 浏览器 profile（`edge_sync_profile/` 等）已在 `.gitignore` 中排除；
- `official_daily.json`、`points_log.jsonl`、各类日志均已排除；
- 同步脚本只读取你本机已登录的用量页面，不向任何第三方发送数据。

## 📄 License

MIT（见 [LICENSE](LICENSE)）。
