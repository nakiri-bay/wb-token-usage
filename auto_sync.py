#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""auto_sync.py —— 每 15±2 分钟静默同步一次 WorkBuddy 官方积分（后台常驻，无窗口）。

- 由 auto_sync.vbs 以 pythonw 启动（双击即可，无窗口）。
- 基准间隔 INTERVAL=900s（15 分钟），每次实际等待在 INTERVAL±JITTER(120s) 内随机，
  即 13~17 分钟不等，避免每次都准时踩点、访问模式过于规律。
- 自身 PID 写入 auto_sync.pid，停止请用「停止自动同步.bat」。
- 每次同步结果与下次等待时长记录到 auto_sync_log.txt。
"""
import os
import sys
import time
import random
import datetime
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import sync_usage  # 复用同步逻辑

PID_PATH = os.path.join(BASE, "auto_sync.pid")
LOG_PATH = os.path.join(BASE, "auto_sync_log.txt")
INTERVAL = 900   # 基准间隔：15 分钟
JITTER = 120     # 随机抖动：±2 分钟


def log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))


def next_wait():
    """下一次同步的等待秒数：15 分钟 ± 2 分钟随机。"""
    return random.randint(INTERVAL - JITTER, INTERVAL + JITTER)


def _pid_alive(pid):
    """Windows 下判断某 PID 是否仍在运行。"""
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return ("%d" % pid) in (out.stdout or "")
    except Exception:
        return False


def already_running():
    """已有守护在跑则不再启动，避免「开机自启」与「手动双击」重复拉起。"""
    try:
        with open(PID_PATH, "r", encoding="utf-8") as f:
            pid = int(f.read().strip())
    except Exception:
        return False
    return pid != os.getpid() and _pid_alive(pid)


if __name__ == "__main__":
    if already_running():
        try:
            old = open(PID_PATH, encoding="utf-8").read().strip()
        except Exception:
            old = "?"
        log("已有守护在运行（pid=%s），本次启动跳过。" % old)
        sys.exit(0)
    with open(PID_PATH, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    log("自动同步启动 pid=%s，基准 %d 秒 ±%d 秒随机" % (os.getpid(), INTERVAL, JITTER))
    try:
        while True:
            try:
                ok, msg = sync_usage.sync_once()
                log(("OK   " if ok else "FAIL ") + msg)
            except Exception as e:
                log("异常: %r" % e)
            wait = next_wait()
            log("下次同步等待 %d 秒（约 %.1f 分钟）" % (wait, wait / 60.0))
            time.sleep(wait)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            os.remove(PID_PATH)
        except Exception:
            pass
        log("自动同步已停止")
