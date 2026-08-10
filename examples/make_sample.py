#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_sample.py — 生成一个自创、无版权问题的示例 PDF，用于演示 pdf2md。

内容全部为作者原创（示例性质），包含：
  - 中文正文（演示 CJK 文本提取与清洗）
  - 章节 / 小节标题（演示 H1/H2/H3 标题层级，来自 PDF 书签 + 正文）
  - 等宽字体的代码块（演示代码识别与围栏）
  - 矢量绘图流程图（演示 pdf2md 的核心能力：把矢量图渲染成图片）

运行：
    python make_sample.py
会在同目录生成 sample.pdf。随后用 `python ../pdf2md.py sample.pdf`
即可得到 sample/（含 sample.pdf 副本、sample.md、images/）。

注意：本脚本需要系统中文字体（Windows 默认有 simhei.ttf）。其他平台可把
CJK_FONT 改成任意可用的中文字体路径，例如 macOS 的
/Library/Fonts/STHeiti Light.ttc 或 Linux 的 /usr/share/fonts/.../NotoSansCJK-Regular.ttc。
"""

import os
import fitz  # PyMuPDF

# 系统中文字体路径（按需修改）
CJK_FONT = r"C:\Windows\Fonts\simhei.ttf"
CJK_NAME = "cjk"      # 任意名字，配合 fontfile 使用
MONO_NAME = "courier" # 等宽字体，用于代码块（被 pdf2md 识别为代码）

W, H = 595, 842  # A4

doc = fitz.open()
doc.set_metadata({
    "title": "PDF2MD 示例文档",
    "author": "stevenlii",
    "subject": "pdf2md 工具演示样例（自创、无版权问题）",
})


def txt(page, x, y, s, size, cjk=True):
    """写一行文字：中文用 CJK 字体，代码用等宽字体。返回 y。"""
    if cjk:
        page.insert_text((x, y), s, fontname=CJK_NAME, fontfile=CJK_FONT,
                         fontsize=size)
    else:
        page.insert_text((x, y), s, fontname=MONO_NAME, fontsize=size)
    return y


def para(page, text, x, y, size=11, leading=18, max_chars=34):
    """简单的按字符数折行写入中文段落，返回下一行的 y。"""
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= max_chars:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    for ln in lines:
        txt(page, x, y, ln, size, cjk=True)
        y += leading
    return y


def code_block(page, lines, x, y, size=10, leading=15):
    """写入一段等宽字体代码（确保被识别为代码块）。"""
    for ln in lines:
        txt(page, x, y, ln, size, cjk=False)
        y += leading
    return y


def draw_flow(page, top):
    """画一个矢量流程图：两个方框 + 箭头 + 圆，演示矢量图提取。"""
    # 方框 1：输入
    r1 = fitz.Rect(70, top, 250, top + 55)
    page.draw_rect(r1, color=(0.2, 0.2, 0.2), fill=(0.85, 0.9, 0.95), width=1.5)
    page.insert_textbox(r1, "输入 PDF", fontname=CJK_NAME, fontfile=CJK_FONT,
                        fontsize=13, align=fitz.TEXT_ALIGN_CENTER)
    # 箭头
    page.draw_line((250, top + 27), (335, top + 27), color=(0.1, 0.1, 0.1), width=2)
    page.draw_line((335, top + 27), (325, top + 22), color=(0.1, 0.1, 0.1), width=2)
    page.draw_line((335, top + 27), (325, top + 32), color=(0.1, 0.1, 0.1), width=2)
    # 方框 2：输出
    r2 = fitz.Rect(345, top, 525, top + 55)
    page.draw_rect(r2, color=(0.2, 0.2, 0.2), fill=(0.9, 0.95, 0.85), width=1.5)
    page.insert_textbox(r2, "输出 Markdown", fontname=CJK_NAME, fontfile=CJK_FONT,
                        fontsize=13, align=fitz.TEXT_ALIGN_CENTER)
    # 向下箭头到圆
    page.draw_line((435, top + 55), (435, top + 95), color=(0.1, 0.1, 0.1), width=2)
    page.draw_line((435, top + 95), (430, top + 85), color=(0.1, 0.1, 0.1), width=2)
    page.draw_line((435, top + 95), (440, top + 85), color=(0.1, 0.1, 0.1), width=2)
    # 圆：图片
    c = fitz.Point(435, top + 130)
    page.draw_circle(c, 38, color=(0.2, 0.2, 0.2), fill=(0.97, 0.9, 0.8), width=1.5)
    page.insert_textbox(fitz.Rect(c.x - 35, c.y - 10, c.x + 35, c.y + 10),
                        "图片", fontname=CJK_NAME, fontfile=CJK_FONT,
                        fontsize=12, align=fitz.TEXT_ALIGN_CENTER)


# ---------- 第 1 页：封面 + 第1章 ----------
p1 = doc.new_page(width=W, height=H)
txt(p1, 60, 90, "PDF2MD 示例文档", 28, cjk=True)
txt(p1, 60, 125, "—— pdf2md 工具演示样例（自创内容，无版权问题）", 12, cjk=True)
txt(p1, 60, 760, "第1章 入门示例", 20, cjk=True)
y = para(p1, "pdf2md 是一个把 PDF 图书转换成单篇 Markdown 文档的工具，"
             "并把书中的所有插图抽取到 images/ 文件夹。本章介绍它的基本用途。",
         60, 200, size=12, leading=20)
txt(p1, 60, y + 20, "1.1 这是什么", 16, cjk=True)
y = para(p1, "它读取 PDF 的目录结构，自动划分章节，并把矢量绘图渲染为图片。"
             "对于等宽字体排版的代码，它会识别为代码块并加围栏。",
         60, y + 45, size=12, leading=20)
y = code_block(p1, [
    "# example.py  -- a tiny demo",
    "def greet(name):",
    "    return f\"Hello, {name}!\"",
    "",
    "if __name__ == '__main__':",
    "    print(greet('pdf2md'))",
], 60, y + 30)
txt(p1, 60, y + 20, "1.2 工作流程", 16, cjk=True)
y = para(p1, "下图展示了从输入 PDF 到输出 Markdown 的处理流程。",
         60, y + 45, size=12, leading=20)
draw_flow(p1, y + 25)

# ---------- 第 2 页：矢量图放大演示 ----------
p2 = doc.new_page(width=W, height=H)
txt(p2, 60, 80, "图：PDF2MD 处理流程（矢量绘图示例）", 13, cjk=True)
draw_flow(p2, 140)
para(p2, "上面的流程图由矢量路径（矩形、直线、圆）构成，而不是位图。"
          "pdf2md 会把它们聚类后渲染为一张 PNG，写进 images/ 并插入 Markdown。",
     60, 360, size=12, leading=20)

# ---------- 第 3 页：第2章 ----------
p3 = doc.new_page(width=W, height=H)
txt(p3, 60, 90, "第2章 矢量图与代码", 20, cjk=True)
y = para(p3, "本章进一步演示矢量图提取与代码块识别两个核心能力。",
         60, 150, size=12, leading=20)
txt(p3, 60, y + 20, "2.1 矢量图提取", 16, cjk=True)
y = para(p3, "很多技术书用矢量图形讲解概念。pdf2md 会保留这些图形，"
             "而不是把它们当作文字丢弃。",
         60, y + 45, size=12, leading=20)
draw_flow(p3, y + 30)
txt(p3, 60, y + 240, "2.2 代码块识别", 16, cjk=True)
y = code_block(p3, [
    "# tokenizer demo",
    "tokens = 'PDF to Markdown'.split()",
    "for t in tokens:",
    "    print(len(t), t)",
], 60, y + 265)

# 书签 / 目录（pdf2md 据此划分章节）
doc.set_toc([
    [1, "第1章 入门示例", 1],
    [1, "第2章 矢量图与代码", 3],
])

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample.pdf")
doc.save(out)
doc.close()
print("生成示例 PDF:", out)
