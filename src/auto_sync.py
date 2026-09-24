#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""auto_sync.py —— 每 15±2 分钟静默同步一次 WorkBuddy 官方积分（后台常驻，无窗口）。

说明：桌宠（deskpet.py）已内嵌同样的同步循环，默认随桌宠一起启动/退出。
      本脚本是**独立守护模式**，供不想常驻桌宠窗口的用户单独使用；
      两者不要同时跑（会争抢同一个浏览器 profile），二选一即可。

- 由 scripts/auto_sync.vbs 以 pythonw 启动（双击即可，无窗口）。
- 同步节奏复用 sync_usage.INTERVAL / JITTER（基准 900s ±120s，即 13~17 分钟随机）。
- 自身 PID 写入 <项目根>/auto_sync.pid，停止请用「停止自动同步.bat」。
- 每次同步结果与下次等待时长记录到 <项目根>/auto_sync_log.txt。
"""
import os
import sys
import time
import datetime
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))   # <项目根>/src
ROOT = os.path.dirname(HERE)                        # <项目根>
sys.path.insert(0, HERE)
import sync_usage  # 复用同步逻辑

PID_PATH = os.path.join(ROOT, "auto_sync.pid")
LOG_PATH = os.path.join(ROOT, "auto_sync_log.txt")
INTERVAL = sync_usage.INTERVAL   # 基准间隔：15 分钟
JITTER = sync_usage.JITTER       # 随机抖动：±2 分钟


def log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))


def next_wait():
    """下一次同步的等待秒数：15 分钟 ± 2 分钟随机。"""
    return sync_usage.next_wait()


def _pid_alive(pid):
    """Windows 下判断某 PID 是否仍在运行。

    坑：中文 Windows 的 tasklist 输出是 GBK 编码，若直接 text=True（按 UTF-8 解码）
    会抛 UnicodeDecodeError；异常被吞掉后本函数永远返回 False，
    于是 already_running() 永远为 False，单实例保护形同虚设。故这里按字节取回再 GBK 解码。
    """
    try:
        r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        out = r.stdout.decode("gbk", "replace")
        return ("%d" % pid) in out
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
