# pdf-to-markdown（中文说明）

将一个 PDF 书籍转换为**单个 Markdown 文档**，并附带一个 `images/` 图片文件夹。
设计思路参考 [`epub2md`](https://github.com/stevenlii/epub2md)。

本工具针对**图文并茂的技术书**做了优化——尤其是中文书——因为这类书里大部分
插图是**矢量绘制**，需要渲染成图片，而不是简单地抽取内嵌位图。

---

## 功能特性

- **生成一个合并的 `.md` 文件**，标题层级清晰：
  - `#` —— 书名（取自 PDF 元数据）
  - `##` —— 章节（取自 PDF 的目录 / outline）
  - `###` / `####` —— 带编号的小节（`1.1`、`1.1.1` …）
- **矢量插图渲染**：用 PyMuPDF 的 `get_drawings()` 把矢量图渲染成 PNG。
- **内嵌位图抽取**（CMYK → RGB 修正，保证预览正常）。
- **代码块识别**：通过等宽字体判断，并加 ` ```python ` 围栏；
  连中文的 `#` 注释（否则会被误判成标题）也能识别为代码。
- **中文空格清理**；自动过滤页眉/页脚和页码。
- **跳过微小装饰图标**。
- **把原文 PDF 拷贝**进输出文件夹，形成自包含归档。

## 环境要求

- Python **3.8+**
- [`pymupdf`](https://pymupdf.readthedocs.io/)（内置 MuPDF，macOS / Windows
  无需额外系统库；在 Linux / CentOS 无头环境也能直接跑）

这是**唯一**的第三方依赖。

## 安装

### 隔离的虚拟环境（推荐）

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### macOS

```bash
brew install python              # 若还没有 Python 3.8+
python3 -m venv .venv && source .venv/bin/activate
pip install pymupdf
```

### Windows

```powershell
# 从 python.org 安装 Python，或执行：  winget install Python.Python.3.12
python -m venv .venv
.venv\Scripts\activate
pip install pymupdf
```

### CentOS / RHEL

```bash
sudo yum install python3 python3-pip      # 或：sudo dnf install ...
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install pymupdf
```

> 提示：在共用服务器上不想建虚拟环境，可改用用户级安装：
> `pip install --user pymupdf`，然后直接 `python3 pdf2md.py …`。

## 用法

```bash
python pdf2md.py path/to/book.pdf
# 也可显式指定输出文件夹：
python pdf2md.py book.pdf -o output_dir
```

如果省略 PDF 参数，脚本会使用当前目录下**唯一**的那个 `.pdf`（方便快速运行）。

## 输出结构

以 `book.pdf` 为例，脚本会创建一个以 `book` 命名的文件夹，内含：

```
book/
├── book.pdf          # 原文 PDF（已拷贝）
├── book.md           # 转换后的 Markdown
└── images/           # 抽取的图片（image_0001.png …）
```

- `book.md` 中图片引用为 `images/image_0001.png` —— 用 **Obsidian**
  或任意 Markdown 查看器打开即可。
- PDF 目录里的章节会变成 `##` 标题；带编号的小节变成 `###` / `####`。
- 代码块都加了围栏。

## 说明 / 可调项

- **章节识别**依赖 PDF 自带的目录（outline）。没有目录的书不会被拆成
  `##` 章节——但标题仍会按字号大小被识别出来。
- 标题/字号相关的启发式规则，以及页脚过滤列表（`pdf2md.py` 里的
  `FOOTER_SUB`）都是"尽力而为"。若有页脚漏过，把该书重复的页脚字符串加进
  `FOOTER_SUB` 即可。
- 插图默认按 **150 DPI** 渲染；需要更高清可在 `extract_page()` 里改 `dpi`。
- 大本书是单线程转换，通常 400 页以内一分钟跑完。

## 致谢

输出结构参考 [`epub2md`](https://github.com/stevenlii/epub2md)。矢量插图渲染
方案针对"图解"类技术书。

## 许可证

MIT —— 如需可添加 `LICENSE` 文件。
