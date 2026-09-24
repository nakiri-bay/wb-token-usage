# wb-token-usage — 发布计划

> ⚠️ **历史存档**：本文是**最初一轮**的发布计划（当时仓库还是扁平目录、同步靠独立守护进程）。
> 之后又做了两件事，最终形态请以 [README](../README.md) 为准：
> 1. **目录重构**：源码 → `src/`、启动器 → `scripts/`、贴图 → `assets/`、图像工具 → `tools/`、文档 → `docs/`；
> 2. **同步生命周期并入桌宠**：打开桌宠 = 启动同步（先同步一次，之后每 15±2 分钟），
>    退出桌宠 = 同步进程一并结束；`auto_sync.py` 降级为可选的"独立守护模式"。

> 仓库名：**wb-token-usage**
> 目标：把"WorkBuddy 用量桌宠"整理成可公开的 GitHub 仓库。
> 现状：`D:\桌宠` 目前**不是** git 仓库，目录里混有大量开发临时文件、浏览器登录 profile（668MB）和真实用量数据。

---

## 一、文件清单（按处理方式分类）

### ✅ 保留并提交（功能必需）
| 文件 | 作用 |
|------|------|
| `deskpet.py` | 桌宠主程序（GUI、气泡、刷新图标、拖拽、右键菜单） |
| `sync_usage.py` | 官方用量同步（浏览器自动化 + 解析） |
| `auto_sync.py` | 自动同步守护进程（15±2 分钟随机） |
| `log_points.py` | 本地积分记账（写 points_log.jsonl） |
| `config.json` | 配置（宠物名/颜色/刷新间隔/积分单价） |
| `pet_image.png` | 宠物贴图（25KB，运行时必需） |
| `静默启动统计.vbs` | 无窗口启动桌宠 |
| `auto_sync.vbs` | 启动自动同步守护 |
| `同步用量.vbs` / `同步用量.bat` | 手动同步一次 |
| `停止自动同步.bat` | 结束守护进程 |
| `启动统计.bat` | 带控制台启动（调试用） |

### ✅ 已完成的脱敏（本轮）
| 文件 | 原问题 | 处理结果 |
|------|--------|----------|
| `sync_usage.py` | 硬编码手机号作登录判断 | **已删除**，改为检测"套餐与用量"/"个人版" |
| `sync_usage.py` | `NODE`/`WS` 写死 `C:\Users\<用户名>\...` | **已改为** `_find_node()` / `_find_cli()`：环境变量 → PATH → 常见目录自动探测 |
| `sync_usage.py` | 注释里写死 `D:\桌宠\edge_sync_profile` | **已改为**"脚本同目录下的 edge_sync_profile" |
| `*.vbs`（3 个） | 写死 `C:\Users\<用户名>\...\pythonw.exe` | **已改为** `ResolvePythonW()`：扫描 `%LOCALAPPDATA%\Programs\Python\Python3*`，回退 PATH |
| `*.bat`（2 个） | 同上 | **已改为** `%LOCALAPPDATA%` + `Python3*` 扫描 + 回退 `pythonw` |
| `make_cutout.py` | 写死 `C:\Users\<用户名>\.workbuddy\clipboard-images\...` | **已改为** 命令行参数，缺省 `gen/input.png` |
| `gen_to_pet.py` | 写死 `D:\桌宠\gen\...` | **已改为** 命令行参数，缺省 `gen/input.png` |

### 🚫 排除（加入 .gitignore，不上传）
| 文件/目录 | 原因 |
|-----------|------|
| `edge_sync_profile/`（93M）、`edge_profile_sync/`（668M）、`browser_profile/`（32M） | 含已登录 Cookie，**隐私 + 体积** |
| `official_daily.json` | 真实用量数据 |
| `points_log.jsonl` | 真实记账流水 |
| `sync_log.txt`、`auto_sync_log.txt`、`auto_sync.pid` | 运行日志 |
| `last_full_snapshot.txt`（91KB） | 用量页快照，含账号信息（且每次同步会重新生成，故靠 .gitignore 拦截） |
| 所有 `_*.txt`、`open*.txt`、`edge_open*.txt`、`page.png` | 开发过程临时产物 |
| `__pycache__/`、`.workbuddy/` | 缓存 / 本地记忆 |
| `pet_cutout.png`、`*_preview.png`、`gen/` | 图像处理中间产物 |
| `Nakiri.png`（4.3MB） | 人物原图，体积大且可能涉版权，按需决定 |

### ❓ 可选（建议放 `tools/` 或按需提交）
| 文件 | 说明 |
|------|------|
| `make_cutout.py`、`gen_to_pet.py`、`gen/` | 展示"贴图怎么做的"，非运行必需 |
| `桌宠功能调研.md` | 调研笔记，可选 |

---

## 二、执行步骤

### 阶段 1：本地清理与脱敏 ✅（已完成）
1. ~~删除/移走开发临时文件~~ → 待做：把 `_*.txt`、`open*.txt`、`edge_open*.txt`、`page.png` 移入 `_trash/`。
2. ✅ `sync_usage.py`：删手机号、路径参数化。
3. ✅ `*.vbs` / `*.bat`：去掉用户名，改为自动定位 pythonw。
4. ✅ `make_cutout.py` / `gen_to_pet.py`：输入路径改为命令行参数。

### 阶段 2：补齐仓库基础文件
- [x] `.gitignore`（已生成，覆盖上述排除项）
- [x] `README.md`（已生成）
- [x] `requirements.txt`（已生成）
- [ ] `LICENSE`（如 MIT）—— 待定

### 阶段 3：初始化 Git 并首次提交
```bash
cd /d/桌宠
git init
git add README.md .gitignore requirements.txt deskpet.py sync_usage.py auto_sync.py log_points.py config.json pet_image.png
git add "静默启动统计.vbs" auto_sync.vbs "同步用量.vbs" "同步用量.bat" "停止自动同步.bat" "启动统计.bat"
git commit -m "feat: WorkBuddy 用量桌宠首个版本"
```

### 阶段 4：创建远程仓库并推送
```bash
# 方式 A（gh CLI，推荐）
gh repo create wb-token-usage --public --source=. --remote=origin --push

# 方式 B（网页建仓后）
git remote add origin https://github.com/<用户名>/wb-token-usage.git
git branch -M main
git push -u origin main
```

### 阶段 5：发布前自检（关键！）
```bash
# 1) 确认敏感文件未入库（应无输出）
git ls-files | grep -Ei "profile|official_daily|points_log|snapshot|\.log$|Nakiri|\.pid$"
# 2) 仓库体积应 < 2MB
git count-objects -vH
# 3) 人工复查：源码/文档中不含手机号、真实用户名、Cookie
```

---

## 三、待你决定的事项
1. ✅ 仓库名：**wb-token-usage**
2. **公开 / 私有**：含浏览器自动化 + 产品用量逻辑，建议**先私有**，稳定后再转公开。
3. **是否提交人物原图 `Nakiri.png` 和图像处理脚本**（涉及版权/体积）。
4. **License**：是否用 MIT。

> 阶段 1、2 已完成；确认后即可执行阶段 3，推送阶段会再和你确认。
