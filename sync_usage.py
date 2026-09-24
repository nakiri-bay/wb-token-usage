#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sync_usage.py —— 通过浏览器自动化把 WorkBuddy 官方「今日积分消耗」同步进桌宠。

机制（已实测可用）：
  - 用 agent-browser（自带 Chromium）+ 独立持久 profile（脚本同目录下的 edge_sync_profile，
    内含已登录的 WorkBuddy Cookie）打开用量页。
  - 全部操作在【一条 batch 命令】内完成：浏览器自动化 daemon 在单次调用期间持续存活，
    因此 open / 勾选“今天” / 翻页 / 快照 状态一致（分条调用会因 daemon 不跨进程常驻而失败）。
  - 勾选“今天”单选 -> 表格仅显示今日记录 -> 逐页快照（scrollintoview+click 翻页） ->
    解析“积分消耗”列求和（按请求哈希去重，避免末页重复计数）。
  - 结果写入 official_daily.json（按日期覆盖），桌宠(deskpet.py)读取后官方值优先于估算值。

运行：双击「同步用量.bat」
"""
import os
import re
import sys
import json
import shutil
import subprocess
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
PROFILE = os.path.join(BASE, "edge_sync_profile")
OFFICIAL_PATH = os.path.join(BASE, "official_daily.json")
SNAP_PATH = os.path.join(BASE, "last_full_snapshot.txt")
USAGE_URL = "https://www.workbuddy.cn/profile/plans-usage"


def _find_node():
    """定位 node：环境变量 WB_NODE_EXE > PATH > 常见托管目录。"""
    env = os.environ.get("WB_NODE_EXE")
    if env and os.path.exists(env):
        return env
    found = shutil.which("node")
    if found:
        return found
    managed = os.path.join(HOME, ".workbuddy", "binaries", "node", "versions")
    if os.path.isdir(managed):
        for d in sorted(os.listdir(managed), reverse=True):
            cand = os.path.join(managed, d, "node.exe")
            if os.path.exists(cand):
                return cand
    return "node"


def _find_cli():
    """定位 agent-browser 的 JS 入口：环境变量 WB_AGENT_BROWSER_JS > 常见安装位置。"""
    env = os.environ.get("WB_AGENT_BROWSER_JS")
    if env and os.path.exists(env):
        return env
    for c in (
        os.path.join(HOME, ".workbuddy", "binaries", "node", "workspace",
                     "node_modules", "agent-browser", "bin", "agent-browser.js"),
        os.path.join(HOME, "AppData", "Roaming", "npm", "node_modules",
                     "agent-browser", "bin", "agent-browser.js"),
    ):
        if os.path.exists(c):
            return c
    return None


NODE = _find_node()
CLI = _find_cli()

# 单次同步最多抓取的页数（每页 10 条）。今日记录约 62 条≈7 页；留足余量即可，避免空转。
PAGES = 9
TODAY = datetime.date.today().isoformat()

TS_RE = re.compile(r'StaticText "(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}"')
STATIC_RE = re.compile(r'^\s*- StaticText "((?:[^"\\]|\\.)*)"')


def build_batch():
    """构造单条 batch 命令的参数列表。"""
    cmds = [
        f"open {USAGE_URL}",
        "wait 6000",
        "snapshot",            # 建立 ref 映射（e25=今天单选）；同时含 7天视图第1页
        "check @e25",          # 勾选“今天”单选（每新加载恒为 e25）
        "wait 3000",
        "snapshot",            # 第 1 页（今日）
    ]
    for _ in range(PAGES - 1):
        cmds += [
            "scrollintoview @e43",   # 下一页按钮在页脚，需先滚动入视口
            "click @e43",
            "wait 2500",
            "snapshot",
        ]
    return cmds


def _reset_daemon():
    """关闭可能残留的 agent-browser 守护进程。

    若已有守护在跑，batch 会打印「--profile, --args ignored: daemon already running」，
    于是沿用旧 profile/session，快照残缺、同步失败（表现为“定时更新没生效”）。
    """
    try:
        subprocess.run([NODE, CLI, "close"], timeout=25,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:
        pass


def run_batch(cmds):
    """运行 batch，并把 node 的 stdout/stderr 重定向到文件（不要用 capture_output=True）。

    原因：agent-browser 会启动一个常驻 daemon，它继承了 stdout 管道，导致
    capture_output=True 的管道永远收不到 EOF、subprocess.run 无限阻塞被 harness 杀掉(SIGTERM)。
    改为重定向到文件后，node 退出时 run() 立即返回。
    """
    if not CLI:
        print("[错误] 未找到 agent-browser，请先安装：npm i -g agent-browser"
              "（或设置环境变量 WB_AGENT_BROWSER_JS 指向 agent-browser.js）。")
        return False
    _reset_daemon()  # 先关掉可能残留的旧守护，避免 --profile/--args 被忽略
    args = [NODE, CLI, "--args", "--no-sandbox",
            "--session", "points-sync", "--profile", PROFILE, "batch"] + cmds
    try:
        with open(SNAP_PATH, "w", encoding="utf-8") as out:
            # CREATE_NO_WINDOW：桌宠是 pythonw(无控制台)，直接拉起 node.exe(控制台程序)
            # 会被 Windows 分配一个可见黑窗；加此标志彻底静默。
            subprocess.run(args, stdout=out, stderr=subprocess.STDOUT, timeout=200,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        print("[超时] batch 执行超时（>200s）。")
        return False
    return True


def parse_today(text):
    """从 batch 输出中解析今日积分消耗总和。

    每行记录：[时间戳][请求块(generic clickable，含哈希)][积分消耗(纯数字)][模型名(拉丁开头)][WorkBuddy]
    规则：一个纯数字 StaticText 是“积分消耗”当且仅当它【下一个】StaticText 以拉丁字母开头且非 WorkBuddy；
         再用该行最近的时间戳判断是否为今日；最后按 (日期,请求哈希) 去重，避免末页重复。
    """
    lines = text.splitlines()
    ts_list = []     # (line_idx, date)
    st_list = []     # (line_idx, value)
    hash_list = []   # (line_idx, hash)  请求哈希（长 hex）
    for i, ln in enumerate(lines):
        m = TS_RE.search(ln)
        if m:
            ts_list.append((i, m.group(1)))
            continue
        s = STATIC_RE.match(ln)
        if s:
            v = s.group(1)
            st_list.append((i, v))
            if re.fullmatch(r"[0-9a-f]{16,}", v):
                hash_list.append((i, v))

    total = 0.0
    count = 0
    seen = set()
    for idx, val in st_list:
        if not re.fullmatch(r"\d+(\.\d+)?", val):
            continue
        # 下一个 StaticText
        nxt = None
        for j in range(len(st_list)):
            if st_list[j][0] > idx:
                nxt = st_list[j][1]
                break
        if nxt is None or nxt.strip() == "WorkBuddy" or not re.match(r"^[A-Za-z]", nxt.strip()):
            continue
        # 日期
        date = None
        for ti, td in ts_list:
            if ti < idx:
                date = td
            else:
                break
        if date != TODAY:
            continue
        # 请求哈希（用于去重）
        h = None
        for hi, hv in hash_list:
            if hi < idx:
                h = hv
            else:
                break
        key = (date, h)
        if key in seen:
            continue
        seen.add(key)
        total += float(val)
        count += 1
    return total, count


def sync_once():
    """执行一次完整同步，返回 (ok: bool, msg: str)。供 CLI 与守护脚本共用。"""
    global TODAY
    TODAY = datetime.date.today().isoformat()  # 每次重算，避免跨午夜后写入旧日期键
    ok = run_batch(build_batch())
    if not ok or not os.path.exists(SNAP_PATH) or os.path.getsize(SNAP_PATH) == 0:
        return False, "[失败] 未获取到任何页面输出，请确认 agent-browser 已安装且 profile 有效。"
    out = open(SNAP_PATH, encoding="utf-8").read()

    if "套餐与用量" not in out and "个人版" not in out:
        return False, "⚠️ 页面似乎未登录（未检测到 WorkBuddy 用量页内容）。"

    total, count = parse_today(out)
    if count == 0:
        return False, "[提示] 今日视图暂无积分消耗记录（可能尚未产生消耗，或页面结构变动）。"

    data = {}
    if os.path.exists(OFFICIAL_PATH):
        try:
            data = json.load(open(OFFICIAL_PATH, encoding="utf-8"))
        except Exception:
            data = {}
    data[TODAY] = round(total, 2)
    with open(OFFICIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True, f"[同步成功] 今日({TODAY})官方积分消耗合计：{total:.2f}（计入 {count} 条记录）"


def main():
    print(f"== 同步官方今日积分（{TODAY}）==")
    print("（浏览器自动化：打开用量页 -> 勾选今天 -> 翻页快照 -> 求和）")
    try:
        ok, msg = sync_once()
    except Exception as e:
        print(f"[异常] {e!r}")
        return
    print(msg)
    if ok:
        print(f"   已写入 official_daily.json，桌宠将在下次刷新（约 1.5s）显示该官方值。")


if __name__ == "__main__":
    import sys as _sys, datetime as _dt
    _logp = os.path.join(BASE, "sync_log.txt")
    class _Tee:
        def __init__(self, f): self.f = f
        def write(self, s):
            try: self.f.write(s); self.f.flush()
            except Exception: pass
        def flush(self): pass
    with open(_logp, "a", encoding="utf-8") as _lf:
        _lf.write("\n=== %s ===\n" % _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        _sys.stdout = _Tee(_lf)
        _sys.stderr = _Tee(_lf)
        try:
            main()
        except Exception as _e:
            print("EXCEPTION: %r" % _e)
