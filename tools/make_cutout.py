#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_cutout.py v3 —— 生成桌宠贴图 pet_image.png（预合成到透明键色上）

做法：
1. 两遍泛洪抠出人物 mask（与之前相同的成熟逻辑）。
2. mask 轻微高斯羽化 -> BILINEAR 缩到 140 宽（得到平滑的抗锯齿 alpha，无硬边）。
3. 原图 LANCZOS 缩到同尺寸。
4. 去白污染并预合成到键色 KEY：
   out = rgb - (1-a)*(255-KEY)   （即 先去白混色，再向 KEY 混合）
   -> 边缘是从人物色到 KEY 的平滑渐变（视觉上像深色描边），窗口端 -transparentcolor
      把 KEY 色抠透明即可，无锯齿、无白边、无黑脏边。
5. KEY 从候选色中选一个【原图中不存在】的颜色，避免人物内部出现透明洞。

用法：python tools/make_cutout.py [输入图路径]
     （缺省输入为 <项目根>/gen/input.png，输出 <项目根>/assets/pet_image.png）
"""
from PIL import Image, ImageFilter
from collections import deque
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))       # <项目根>/tools
ROOT = os.path.dirname(HERE)                            # <项目根>
# 输入图：命令行第一个参数；缺省用 <项目根>/gen/input.png
IMG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "gen", "input.png")
OUT_IMG = os.path.join(ROOT, "assets", "pet_image.png")
# 预览图是调试产物，放 gen/（整个目录都在 .gitignore 里），保持 assets/ 只有成品
OUT_PREVIEW = os.path.join(ROOT, "gen", "pet_image_preview.png")
os.makedirs(os.path.dirname(OUT_IMG), exist_ok=True)
os.makedirs(os.path.dirname(OUT_PREVIEW), exist_ok=True)
W_TARGET = 140

# ---------- 1. 抠 mask（两遍泛洪，同已验证逻辑）----------
src = Image.open(IMG).convert("RGB")
w, h = src.size
px = src.load()

def is_bg(p):
    r, g, b = p
    if (r + g + b) / 3 > 170:          # 近白/浅暖灰
        return True
    if r > 200 and (r - g) > 35 and (r - b) > 25 and g > 130 and b > 130:
        return True                     # 浅粉圆点
    return False

seen = [[False] * w for _ in range(h)]
q = deque()
for x in range(w):
    for y in (0, h - 1):
        if is_bg(px[x, y]) and not seen[y][x]:
            seen[y][x] = True; q.append((x, y))
for y in range(h):
    for x in (0, w - 1):
        if is_bg(px[x, y]) and not seen[y][x]:
            seen[y][x] = True; q.append((x, y))
while q:
    x, y = q.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and is_bg(px[nx, ny]):
            seen[ny][nx] = True; q.append((nx, ny))

# 第二遍：图内孤立小背景口袋
visited = [[False] * w for _ in range(h)]
for sy in range(h):
    for sx in range(w):
        if visited[sy][sx] or seen[sy][sx] or not is_bg(px[sx, sy]):
            continue
        comp = [(sx, sy)]
        visited[sy][sx] = True
        qq = deque([(sx, sy)])
        while qq:
            x, y = qq.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (0 <= nx < w and 0 <= ny < h and not visited[ny][nx]
                        and not seen[ny][nx] and is_bg(px[nx, ny])):
                    visited[ny][nx] = True
                    comp.append((nx, ny))
                    qq.append((nx, ny))
        if len(comp) < 800:
            for x, y in comp:
                seen[y][x] = True

# mask：人物=255 背景=0
mask = Image.new("L", (w, h), 0)
mp = mask.load()
for y in range(h):
    for x in range(w):
        if not seen[y][x]:
            mp[x, y] = 255

# ---------- 2. 选键色：原图中不存在的候选色 ----------
colors = set()
for y in range(h):
    for x in range(w):
        colors.add(px[x, y])
KEY = None
for c in ["#241812", "#1A0F0A", "#010203", "#030104", "#200D06"]:
    t = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    if t not in colors:
        KEY = t
        KEY_HEX = c
        break
assert KEY, "所有候选键色均出现在原图中！"
print("选定键色:", KEY_HEX, KEY)

# ---------- 3. 裁剪 bbox + 缩放 ----------
bbox = mask.getbbox()
mask_c = mask.crop(bbox)
src_c = src.crop(bbox)
tw = W_TARGET
th = round(mask_c.height * tw / mask_c.width)
# 先轻羽化，再 BILINEAR 缩放 -> 平滑抗锯齿 alpha
alpha = mask_c.filter(ImageFilter.GaussianBlur(0.6)).resize((tw, th), Image.BILINEAR)
rgb = src_c.resize((tw, th), Image.LANCZOS)

# ---------- 4. 去白污染 + 预合成到 KEY ----------
ap = alpha.load(); rp = rgb.load()
out = Image.new("RGB", (tw, th), KEY)
op = out.load()
for y in range(th):
    for x in range(tw):
        a = ap[x, y] / 255.0
        if a <= 0.02:
            continue  # 保持纯 KEY（窗口端抠透明）
        r, g, b = rp[x, y]
        op[x, y] = (
            max(0, min(255, round(r - (1 - a) * (255 - KEY[0])))),
            max(0, min(255, round(g - (1 - a) * (255 - KEY[1])))),
            max(0, min(255, round(b - (1 - a) * (255 - KEY[2])))),
        )
out.save(OUT_IMG)
print("saved", OUT_IMG, out.size)

# ---------- 5. 预览图（模拟浅色桌面看边缘效果）----------
prev = Image.new("RGB", (tw + 60, th + 60), "#EEF2F7")
prev.paste(out, (30, 30))
pk = prev.load()
for y in range(prev.height):
    for x in range(prev.width):
        if pk[x, y] == KEY:
            pk[x, y] = (238, 242, 247)
prev.save(OUT_PREVIEW)
print("saved", OUT_PREVIEW, prev.size)
