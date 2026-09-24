#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统计助手 · WorkBuddy 积分消耗统计
- 形象：透明底人物贴图（assets/pet_image.png，由 tools/make_cutout.py 生成）
- 头顶聊天框：今日用量 / 累计用量，每 1.5s 自动刷新（官方值优先，其次本地估算）
- “今日用量”右侧 ↻ 图标：点击立刻跑一次官方同步（后台线程，约 30-40s，不卡界面）
- 拖动人物移动窗口；右键菜单：立即同步 / 打开官方用量页 / 退出

同步生命周期（本文件自带，无需再单独启动守护进程）：
  启动即同步一次  ->  之后每 15±2 分钟自动同步  ->  退出时终止同步线程与浏览器进程
  即“打开统计助手 = 打开同步”，关掉统计助手 = 关掉同步，不留后台残留。
"""
import os
import sys
import json
import socket
import datetime
import threading
import webbrowser
import tkinter as tk
from tkinter import font as tkfont, Menu
from collections import defaultdict

USAGE_URL = "https://www.workbuddy.cn/profile/plans-usage"

HERE = os.path.dirname(os.path.abspath(__file__))       # <项目根>/src
ROOT = os.path.dirname(HERE)                            # <项目根>
if HERE not in sys.path:
    sys.path.insert(0, HERE)                            # 保证能 import sync_usage
CONFIG_PATH = os.path.join(ROOT, "config.json")
LOG_PATH = os.path.join(ROOT, "points_log.jsonl")
OFFICIAL_PATH = os.path.join(ROOT, "official_daily.json")
SYNC_LOG = os.path.join(ROOT, "sync_log.txt")
IMG_PET = os.path.join(ROOT, "assets", "pet_image.png")

# 单实例端口：已有一个统计助手在跑时，第二个实例直接退出（避免两个同步循环抢浏览器 profile）
SINGLE_INSTANCE_PORT = 47653

# 同步日志的写入锁（主线程 refresh 与同步线程会并发追加）
_LOG_LOCK = threading.Lock()

# sync_usage 必须放在 sys.path 补好之后再导入。允许失败：即便同步模块不可用，
# 统计助手也能照常显示本地已有数据，不至于整个打不开。
try:
    import sync_usage
    next_wait = sync_usage.next_wait
    _SYNC_IMPORT_ERR = ""
except Exception as _e:
    sync_usage = None
    next_wait = lambda: 900        # 兜底：模块不可用时同步循环空转
    _SYNC_IMPORT_ERR = "%r" % (_e,)

# ---- 版式常量（与设计稿一致）----
WIN_W = 240
BUB_W, BUB_H = 210, 76          # 聊天气泡
MARGIN_TOP, GAP = 10, 18        # 顶部留白 / 气泡与人物间距（保证小尾巴完整）
ACCENT = "#E05A6D"              # 气泡描边/图标
T1_COLOR = "#C2185B"            # 今日用量文字
T2_COLOR = "#5D4037"            # 累计用量文字
MAGIC = "#241812"               # 透明键色（与 make_cutout.py 选定的 KEY 一致，原图中不存在此色）
BG = "#FFFFFF"                  # 气泡填充色
ICON_R = 7                      # 刷新图标半径
ICON_GAP = 7                    # 文字与图标间距

DEFAULT_CONFIG = {
    "points_per_reply": 8,
    "points_per_tool_call": 3,
    "refresh_ms": 1500,
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def load_entries():
    entries = []
    if not os.path.exists(LOG_PATH):
        return entries
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return entries


def aggregate(entries):
    daily = defaultdict(int)
    total = 0
    for e in entries:
        try:
            p = int(e.get("points", 0))
        except Exception:
            p = 0
        daily[e.get("date", "")] += p
        total += p
    return daily, total


def load_official():
    """官方同步得到的每日真实积分 {date: points}。"""
    if not os.path.exists(OFFICIAL_PATH):
        return {}
    try:
        with open(OFFICIAL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): float(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def rounded_rect_pts(x1, y1, x2, y2, r):
    """tkinter smooth 多边形用的圆角矩形顶点。"""
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


class DeskPet:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.root.title("WorkBuddy 积分消耗统计")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.configure(bg=MAGIC)
        # Windows 专属：把 MAGIC 色整体抠成透明 -> 只有气泡和人物可见，无白色窗口底
        try:
            self.root.attributes("-transparentcolor", MAGIC)
        except Exception:
            pass  # 非 Windows 或不支持时退化为 MAGIC 色底（视觉近似透明）

        # ---- 人物贴图（由 make_cutout.py 生成：已预合成到键色，无 alpha）----
        self._photo = None
        img_h = 140
        if os.path.exists(IMG_PET):
            self._photo = tk.PhotoImage(file=IMG_PET)
            img_h = self._photo.height()
        self.img_h = img_h

        # ---- 画布：气泡 + 小尾巴 + 人物 ----
        self.H = MARGIN_TOP + BUB_H + GAP + img_h + 8
        self.root.geometry(f"{WIN_W}x{self.H}+"
                           f"{self.root.winfo_screenwidth() - WIN_W - 20}+"
                           f"{self.root.winfo_screenheight() - self.H - 20}")
        self.cv = tk.Canvas(root, width=WIN_W, height=self.H, bg=MAGIC, highlightthickness=0)
        self.cv.pack()

        self.f1 = tkfont.Font(family="Microsoft YaHei", size=12, weight="bold")
        self.f2 = tkfont.Font(family="Microsoft YaHei", size=10)

        self.ty = MARGIN_TOP + BUB_H           # 气泡底部 y（小尾巴起点）
        self._draw_static()                    # 气泡/尾巴/人物（一次）
        self._last_vals = None                 # 缓存，值变化才重绘文字（防闪烁）

        # ---- 同步状态（后台同步线程写、refresh 读；仅作标志位，GIL 下读写安全）----
        self._sync_busy = False
        self._sync_stop = threading.Event()   # 置位后同步线程退出
        self._sync_wake = threading.Event()   # 手动点击时提前唤醒等待

        # ---- 拖动 / 菜单 ----
        self._offset = (0, 0)
        self.cv.bind("<ButtonPress-1>", self.start_move)
        self.cv.bind("<B1-Motion>", self.do_move)
        self.cv.bind("<Button-3>", self.show_menu)
        self.cv.tag_bind("ri", "<Button-1>", self.manual_refresh)   # 刷新图标
        # 悬停时显示手型光标，提示可点击
        self.cv.tag_bind("ri", "<Enter>", lambda e: self.cv.config(cursor="hand2"))
        self.cv.tag_bind("ri", "<Leave>", lambda e: self.cv.config(cursor=""))
        self.menu = Menu(root, tearoff=0)
        self.menu.add_command(label="立即同步用量", command=self.manual_refresh)
        self.menu.add_command(label="打开官方用量页", command=self.open_usage)
        self.menu.add_separator()
        self.menu.add_command(label="退出统计（同时停止同步）", command=self.quit)

        self.refresh()
        self.root.after(int(cfg.get("refresh_ms", 1500)), self.refresh)

        # 同步生命周期随统计助手：启动即同步一次 -> 定时同步 -> 退出时一并结束
        threading.Thread(target=self._sync_loop, daemon=True,
                         name="sync-loop").start()

    # ---------- 静态绘制 ----------
    def _draw_static(self):
        cv = self.cv
        bx = (WIN_W - BUB_W) // 2
        by = MARGIN_TOP
        ty = self.ty
        tx = WIN_W // 2
        # 气泡（圆角矩形）
        cv.create_polygon(rounded_rect_pts(bx, by, bx + BUB_W, by + BUB_H, 16),
                          smooth=True, fill="#FFFFFF", outline=ACCENT, width=2)
        # 小尾巴：白填充盖住气泡底边交界，再画两条描边线
        cv.create_polygon(tx - 11, ty - 3, tx + 11, ty - 3, tx, ty + 11,
                          fill="#FFFFFF", outline="")
        cv.create_line(tx - 11, ty - 3, tx, ty + 11, fill=ACCENT, width=2)
        cv.create_line(tx + 11, ty - 3, tx, ty + 11, fill=ACCENT, width=2)
        # 人物
        if self._photo is not None:
            cv.create_image(WIN_W // 2, ty + GAP, image=self._photo, anchor="n")

    # ---------- 动态文字（值变化才重绘，防闪烁）----------
    def _draw_texts(self, today_val, total, syncing):
        cv = self.cv
        cv.delete("dyn")
        by = MARGIN_TOP
        t1 = f"今日用量：{today_val:.2f}"
        t2 = f"累计用量：{total:.2f}"
        # 第一行：文字 + 刷新图标 整体居中
        w1 = self.f1.measure(t1)
        status = " 同步中…" if syncing else ""
        ws = self.f2.measure(status) if status else 0
        group_w = w1 + ICON_GAP + ICON_R * 2 + ws
        gx = (WIN_W - group_w) / 2
        y1 = by + 25
        cv.create_text(gx, y1, text=t1, font=self.f1, fill=T1_COLOR,
                       anchor="w", tags="dyn")
        # 刷新图标：圆弧 + 箭头（同步中变灰）
        icol = "#CCCCCC" if syncing else ACCENT
        cx = gx + w1 + ICON_GAP + ICON_R
        cy = y1
        # 命中区域：比图标略大的不可见圆。#FFFFFE 与白色气泡肉眼无差、且不是透明键色，
        # 因此既隐形又能接收点击（细弧线自身的命中区太窄，之前"点了没反应"就是它）。
        cv.create_oval(cx - ICON_R - 5, cy - ICON_R - 5, cx + ICON_R + 5, cy + ICON_R + 5,
                       fill="#FFFFFE", outline="", tags=("dyn", "ri"))
        cv.create_arc(cx - ICON_R, cy - ICON_R, cx + ICON_R, cy + ICON_R,
                      start=300, extent=270, style="arc",
                      outline=icol, width=3, tags=("dyn", "ri"))
        import math
        ang = math.radians(210)
        ax, ay = cx + ICON_R * math.cos(ang), cy + ICON_R * math.sin(ang)
        cv.create_polygon(ax - 3, ay - 4, ax + 5, ay - 1, ax - 1, ay + 5,
                          fill=icol, outline="", tags=("dyn", "ri"))
        if status:
            cv.create_text(gx + w1 + ICON_GAP + ICON_R * 2 + 4, y1,
                           text=status.strip(), font=self.f2, fill="#999999",
                           anchor="w", tags="dyn")
        # 第二行
        w2 = self.f2.measure(t2)
        cv.create_text((WIN_W - w2) / 2, by + 52, text=t2, font=self.f2,
                       fill=T2_COLOR, anchor="w", tags="dyn")

    # ---------- 数据刷新 ----------
    def refresh(self):
        try:
            daily_est, _ = aggregate(load_entries())
            official = load_official()
            today = datetime.date.today().isoformat()
            merged = dict(daily_est)
            for d, v in official.items():
                merged[d] = v
            today_val = float(merged.get(today, 0))
            total = float(sum(merged.values()))

            vals = (round(today_val, 2), round(total, 2), self._sync_busy)
            if vals != self._last_vals:
                self._last_vals = vals
                self._draw_texts(today_val, total, self._sync_busy)
        except Exception:
            pass
        self.root.after(int(self.cfg.get("refresh_ms", 1500)), self.refresh)

    # ---------- 同步：启动一次 + 定时 + 退出即停 ----------
    def _log(self, msg):
        """写同步日志。主线程与同步线程都会写，加锁避免并发追加丢行。"""
        try:
            with _LOG_LOCK:
                with open(SYNC_LOG, "a", encoding="utf-8") as f:
                    f.write("[%s] %s\n" % (
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))
        except Exception:
            pass

    def _sync_loop(self):
        """后台同步线程：先立刻同步一次，之后每 15±2 分钟一次。

        手动点 ↻ 只是把等待提前唤醒（_sync_wake），同步本身始终由本线程串行执行，
        因此不会出现两次同步同时操作同一个浏览器 profile 的情况。
        """
        self._log("[循环] 同步线程启动（pid=%d），立即同步一次" % os.getpid())
        reason = "自动"
        while not self._sync_stop.is_set():
            self._do_sync(reason)
            if self._sync_stop.is_set():
                break
            wait = next_wait()
            self._log("[循环] 下次同步等待 %d 秒（约 %.1f 分钟）" % (wait, wait / 60.0))
            woken = self._sync_wake.wait(timeout=wait)
            self._sync_wake.clear()
            if self._sync_stop.is_set():
                break
            reason = "手动" if woken else "自动"
        self._log("[循环] 同步线程退出")

    def _do_sync(self, reason="自动"):
        if sync_usage is None:
            return
        self._sync_busy = True
        self._last_vals = None          # 强制重绘出“同步中…”
        try:
            ok, msg = sync_usage.sync_once()
        except Exception as e:
            ok, msg = False, "同步异常：%r" % (e,)
        self._sync_busy = False
        self._last_vals = None          # 同步完再强制重绘一次（显示最新数值）
        self._log("[%s] %s %s" % (reason, "OK  " if ok else "FAIL", msg))

    def manual_refresh(self, event=None):
        """点击 ↻ / 右键“立即同步”：唤醒同步线程立刻再跑一次（不新开线程）。"""
        if self._sync_busy:
            return
        self._sync_wake.set()

    # ---------- 交互 ----------
    def start_move(self, e):
        self._offset = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def do_move(self, e):
        self.root.geometry(f"+{e.x_root - self._offset[0]}+{e.y_root - self._offset[1]}")

    def show_menu(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    def open_usage(self):
        try:
            webbrowser.open(USAGE_URL, new=2)
        except Exception:
            pass

    def quit(self):
        # 退出时一并结束同步：先通知线程停止，再强行收掉进行中的浏览器进程，
        # 否则 node.exe 是独立进程、主线程退出后它不会自己消失。
        try:
            self._sync_stop.set()
            self._sync_wake.set()
            if sync_usage is not None:
                sync_usage.cancel()
        except Exception:
            pass
        self.root.destroy()


def acquire_single_instance():
    """抢占本地回环端口，实现“同时只允许一个统计助手”。

    比 PID 文件更可靠：进程无论怎么退出（含强杀），socket 都会被系统回收。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        s.listen(1)
        return s
    except OSError:
        try:
            s.close()
        except Exception:
            pass
        return None


def notify_already_running():
    """已有一个统计助手时的轻提示：无边框小条，2.6 秒自动消失（不打断操作）。"""
    try:
        r = tk.Tk()
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.configure(bg=ACCENT)
        tk.Label(r, text="  统计助手已经在运行啦，看看屏幕右下角 :)  ",
                 bg=ACCENT, fg="white",
                 font=("Microsoft YaHei", 10)).pack(padx=8, pady=6)
        w, h = 320, 38
        r.geometry("%dx%d+%d+%d" % (w, h,
                                    r.winfo_screenwidth() - w - 20,
                                    r.winfo_screenheight() - h - 150))
        r.after(2600, r.destroy)
        r.mainloop()
    except Exception:
        pass


def main():
    guard = acquire_single_instance()
    if guard is None:
        notify_already_running()
        return
    cfg = load_config()
    root = tk.Tk()
    pet = DeskPet(root, cfg)

    # pythonw 没有控制台，任何异常都会静默消失；统一落到 sync_log.txt 便于排查。
    def _on_tk_error(exc, val, tb):
        import traceback
        pet._log("[异常] Tk 回调出错：%s: %s" % (getattr(exc, "__name__", exc), val))
        pet._log(traceback.format_exc())
    root.report_callback_exception = _on_tk_error

    if _SYNC_IMPORT_ERR:
        pet._log("[启动] 同步模块导入失败：%s" % _SYNC_IMPORT_ERR)
    pet._log("[启动] 统计助手启动完成（pid=%d），窗口 %dx%d" % (os.getpid(), WIN_W, pet.H))
    try:
        root.mainloop()
    except Exception as e:
        import traceback
        pet._log("[致命] 主循环异常退出：%r" % (e,))
        pet._log(traceback.format_exc())
        raise
    finally:
        pet._log("[退出] 统计助手进程结束（pid=%d）" % os.getpid())
    del pet, guard          # 显式释放：guard 关闭即让出单实例端口


if __name__ == "__main__":
    main()
