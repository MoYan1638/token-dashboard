# -*- coding: utf-8 -*-
"""生成 Token 看板的宣传图（纯 PIL 代码绘制）。

产出：
  social-preview.png   1280×640  社交预览图（GitHub Social Preview / 文章头图）
  promo-banner.png     1200×630  通用横幅
"""

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 品牌色（与看板配色一致）----
PLUM = (122, 59, 87)
PLUM_D = (74, 34, 52)
PLUM_L = (158, 88, 118)
CORAL = (255, 107, 129)
CORAL_L = (255, 179, 192)
WHITE = (255, 255, 255)
INK = (29, 33, 41)
T2 = (92, 100, 112)
SLATE = (185, 195, 212)
SLATE_D = (141, 153, 173)

# ---- 字体 ----
F_BD = r"C:\Windows\Fonts\msyhbd.ttc"
F_RG = r"C:\Windows\Fonts\msyh.ttc"
F_MONO = r"C:\Windows\Fonts\consola.ttf"
F_EN_BD = r"C:\Windows\Fonts\segoeuib.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def fnum(size):
    """数字用等宽粗体，但**必须**能画中文单位（亿/万）。

    Segoe UI 不含中日韩字形，直接画「3.16 亿」会出豆腐块，
    所以数值统一走雅黑粗体，避免混排缺字。
    """
    return ImageFont.truetype(F_BD, size)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def vgrad(size, top, bottom):
    """竖向渐变。"""
    w, h = size
    img = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.point((0, y), lerp(top, bottom, y / max(1, h - 1)))
    return img.resize((w, h), Image.BILINEAR)


def dgrad(size, c1, c2):
    """斜向渐变（左上 → 右下）。

    逐像素计算，避免用线条拼接时在画布对角线上留下可见接缝。
    为控制开销，先生成小图再放大——渐变本身平滑，放大后无损失。
    """
    w, h = size
    sw, sh = max(2, w // 8), max(2, h // 8)
    small = Image.new("RGB", (sw, sh))
    px = small.load()
    for y in range(sh):
        for x in range(sw):
            t = (x / max(1, sw - 1) * 0.5 + y / max(1, sh - 1) * 0.5)
            px[x, y] = lerp(c1, c2, t)
    return small.resize((w, h), Image.BICUBIC)


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1],
                                        radius=radius, fill=255)
    return m


def paste_rounded(canvas, img, xy, radius):
    m = rounded_mask(img.size, radius)
    canvas.paste(img, xy, m)


def heart(draw, cx, cy, w, h, fill, steps=200):
    """四条三次贝塞尔闭合心形（与 logo 同一套控制点逻辑）。"""
    left, right = cx - w / 2.0, cx + w / 2.0
    top, bottom = cy - h / 2.0, cy + h / 2.0
    tip = (cx, bottom)
    cleft = (cx - w * 0.255, top + h * 0.135)
    cright = (cx + w * 0.255, top + h * 0.135)
    notch = (cx, top + h * 0.335)
    lside = (left, cy - h * 0.030)
    rside = (right, cy - h * 0.030)

    def bez(p0, p1, p2, p3, n):
        out = []
        for i in range(n + 1):
            t = i / float(n)
            u = 1 - t
            x = (u**3 * p0[0] + 3 * u * u * t * p1[0]
                 + 3 * u * t * t * p2[0] + t**3 * p3[0])
            y = (u**3 * p0[1] + 3 * u * u * t * p1[1]
                 + 3 * u * t * t * p2[1] + t**3 * p3[1])
            out.append((x, y))
        return out

    n = steps // 4
    pts = []
    pts += bez(notch, (cx - w * 0.09, top + h * 0.150), cleft, lside, n)
    pts += bez(lside, (left, cy + h * 0.130), (cx - w * 0.250, bottom),
               tip, n)
    pts += bez(tip, (cx + w * 0.250, bottom), (right, cy + h * 0.130),
               rside, n)
    pts += bez(rside, cright, (cx + w * 0.09, top + h * 0.150), notch, n)
    draw.polygon(pts, fill=fill)


def bar_chart_icon(draw, x, y, w, h, color, lw, heights):
    """画一个迷你柱状图图标（与看板标题图标同一形态）。"""
    baseline = y + h
    draw.line([(x, baseline), (x + w, baseline)], fill=color, width=lw)
    n = len(heights)
    gap = w / float(n)
    for i, bh in enumerate(heights):
        bx = x + gap * (i + 0.5)
        draw.line([(bx, baseline), (bx, baseline - bh)], fill=color, width=lw)


def make_social(w=1280, h=640):
    img = Image.new("RGB", (w, h), PLUM_D)
    # 背景：梅子紫斜向渐变
    img.paste(dgrad((w, h), PLUM_L, PLUM_D), (0, 0))

    # 柔光层：画在比画布更大的画布上再居中裁回，
    # 否则模糊到边缘时椭圆会被画布边界切断，留下生硬的斜线。
    from PIL import ImageFilter
    m = 260                      # 外扩余量
    gw, gh = w + m * 2, h + m * 2
    glow = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([m + w - 620, m - 400, m + w + 300, m + 520],
               fill=CORAL + (64,))
    gd.ellipse([m + w - 300, m + 20, m + w + 460, m + 820],
               fill=WHITE + (28,))
    gd.ellipse([m - 480, m + h - 400, m + 560, m + h + 360],
               fill=PLUM_D + (165,))
    glow = glow.filter(ImageFilter.GaussianBlur(96))
    glow = glow.crop((m, m, m + w, m + h))   # 裁回原尺寸，边缘已柔化
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")

    pad = 84

    # ---- 左栏可用宽度：给右侧卡片留出空间，标题绝不越界 ----
    card_w = 452
    left_w = w - card_w - pad * 2 - 56   # 左栏内容最大宽度

    # ---- 图标 ----
    ib = 84
    ix, iy = pad, 112
    plate = Image.new("RGB", (ib, ib), WHITE)
    paste_rounded(img, plate, (ix, iy), 22)
    d = ImageDraw.Draw(img, "RGBA")
    bar_chart_icon(d, ix + 24, iy + 28, ib - 48, ib - 52,
                   PLUM, 6, [17, 32, 22, 42, 28])

    # ---- 标题（Token 用英文粗体，中文用雅黑，整体限制在左栏内）----
    title_size = 72
    f_title_zh = font(F_BD, title_size)
    f_title_en = font(F_EN_BD, title_size - 4)
    tx = ix + ib + 24
    d.text((tx, iy + 2), "Token", font=f_title_en, fill=WHITE)
    tw = d.textlength("Token", font=f_title_en)
    d.text((tx + tw + 18, iy + 6), "消耗看板", font=f_title_zh, fill=CORAL_L)

    # ---- 副标题 ----
    f_sub = font(F_RG, 29)
    d.text((pad, iy + ib + 30), "各 AI Agent 通用的本地用量分析工具",
           font=f_sub, fill=(255, 255, 255, 234))

    # ---- 卖点标签：按左栏宽度自动换行，不侵入右侧卡片 ----
    f_tag = font(F_BD, 23)
    tags = ["零依赖", "纯离线", "12 种日志来源", "实时刷新", "暗色模式",
            "跨平台"]
    cx, cy = pad, iy + ib + 100
    chip_h = 44
    for t in tags:
        tw_ = d.textlength(t, font=f_tag)
        bw = tw_ + 36
        if cx + bw > pad + left_w:
            cx, cy = pad, cy + chip_h + 12
        chip = Image.new("RGBA", (int(bw), chip_h), (0, 0, 0, 0))
        ImageDraw.Draw(chip).rounded_rectangle(
            [0, 0, int(bw) - 1, chip_h - 1], radius=chip_h // 2,
            fill=(255, 255, 255, 40), outline=CORAL_L + (150,), width=2)
        img.paste(chip, (int(cx), int(cy)), chip)
        d = ImageDraw.Draw(img, "RGBA")
        d.text((cx + 18, cy + 9), t, font=f_tag, fill=(255, 255, 255, 242))
        cx += bw + 12

    # ---- 右侧迷你看板卡片 ----
    cw, ch = card_w, 342
    cx0, cy0 = w - cw - pad, 138
    card = Image.new("RGB", (cw, ch), WHITE)
    paste_rounded(img, card, (cx0, cy0), 20)
    d = ImageDraw.Draw(img, "RGBA")

    # 卡片内顶部：两个标题占位条
    d.rounded_rectangle([cx0 + 24, cy0 + 24, cx0 + 24 + 122, cy0 + 41],
                        radius=8, fill=(238, 241, 246))
    d.rounded_rectangle([cx0 + 160, cy0 + 26, cx0 + 160 + 62, cy0 + 39],
                        radius=7, fill=(232, 247, 240))

    # KPI 小卡 2×2
    f_kv = fnum(28)
    f_kl = font(F_RG, 16)
    kpis = [("3.16 亿", "输入 Token"), ("98.2%", "缓存命中"),
            ("2,724", "总请求数"), ("¥1,842", "费用估算")]
    gw2 = (cw - 24 * 2 - 13) // 2
    gh2 = 60
    for i, (v, l) in enumerate(kpis):
        r, c = divmod(i, 2)
        kx = cx0 + 24 + c * (gw2 + 13)
        ky = cy0 + 56 + r * (gh2 + 11)
        d.rounded_rectangle([kx, ky, kx + gw2, ky + gh2], radius=12,
                            fill=(250, 251, 253), outline=(228, 232, 239),
                            width=1)
        d.text((kx + 15, ky + 8), v, font=f_kv, fill=PLUM)
        d.text((kx + 15, ky + 40), l, font=f_kl, fill=T2)

    # 迷你柱状图
    bx0, by0 = cx0 + 24, cy0 + 212
    bwid, bhei = cw - 48, 100
    vals = [0.42, 0.58, 0.36, 0.72, 0.50, 0.88, 0.64, 0.78, 0.46, 0.92]
    n = len(vals)
    slot = bwid / float(n)
    bar_w = slot * 0.58
    for i, v in enumerate(vals):
        bh_ = bhei * v
        bxx = bx0 + slot * i + (slot - bar_w) / 2
        d.rounded_rectangle(
            [bxx, by0 + bhei - bh_, bxx + bar_w, by0 + bhei],
            radius=3, fill=SLATE)
        chh = bh_ * 0.62
        d.rounded_rectangle(
            [bxx, by0 + bhei - chh, bxx + bar_w, by0 + bhei],
            radius=3, fill=CORAL)

    # ---- 底栏：细线 + 署名 ----
    d.line([(pad, h - pad - 6), (w - pad, h - pad - 6)],
           fill=(255, 255, 255, 48), width=2)
    f_sign = font(F_BD, 25)
    sign = "by MoYan"
    sw = d.textlength(sign, font=f_sign)
    sy = h - pad + 14
    d.text((w - pad - sw, sy), sign, font=f_sign, fill=(255, 255, 255, 222))
    heart(d, w - pad - sw - 24, sy + 16, 22, 20, CORAL_L)

    return img


if __name__ == "__main__":
    os.makedirs(HERE, exist_ok=True)
    out1 = os.path.join(HERE, "social-preview.png")
    make_social(1280, 640).save(out1, "PNG", optimize=True)
    print("saved", out1, os.path.getsize(out1))

    out2 = os.path.join(HERE, "promo-banner.png")
    make_social(1280, 640).resize((1200, 630), Image.LANCZOS).save(
        out2, "PNG", optimize=True)
    print("saved", out2, os.path.getsize(out2))
