#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WorkBuddy 积分记账脚本（由 WorkBuddy 自动调用，也可手动调用）。
每次调用向 points_log.jsonl 追加一笔记录。

用法示例：
  python log_points.py --task "搭建桌宠 v1" --replies 1 --tools 6
  python log_points.py --task "手动校正" --points 120 --auto false
"""
import argparse
import json
import os
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))       # <项目根>/src
ROOT = os.path.dirname(BASE)                            # <项目根>
CONFIG_PATH = os.path.join(ROOT, "config.json")
LOG_PATH = os.path.join(ROOT, "points_log.jsonl")

DEFAULT_CONFIG = {
    "points_per_reply": 8,
    "points_per_tool_call": 3,
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


def main():
    parser = argparse.ArgumentParser(description="WorkBuddy 积分记账")
    parser.add_argument("--task", default="", help="本次任务描述")
    parser.add_argument("--replies", type=int, default=0, help="本次助手回复轮数")
    parser.add_argument("--tools", type=int, default=0, help="本次工具调用次数")
    parser.add_argument("--points", type=int, default=None, help="直接指定积分（覆盖估算）")
    parser.add_argument("--auto", default="true", help="true=WorkBuddy自动记账 / false=手动")
    args = parser.parse_args()

    cfg = load_config()
    ppr = int(cfg.get("points_per_reply", DEFAULT_CONFIG["points_per_reply"]))
    ppt = int(cfg.get("points_per_tool_call", DEFAULT_CONFIG["points_per_tool_call"]))

    if args.points is not None:
        points = args.points
    else:
        points = args.replies * ppr + args.tools * ppt

    now = datetime.datetime.now()
    record = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "points": int(points),
        "task": args.task,
        "auto": str(args.auto).lower() == "true",
    }

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    src = "自动" if record["auto"] else "手动"
    print(f"[记账 {src}] +{points} 积分 | 任务: {args.task or '(未命名)'} | 已写入 {LOG_PATH}")


if __name__ == "__main__":
    main()
