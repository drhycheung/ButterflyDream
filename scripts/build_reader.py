#!/usr/bin/env python3
"""Generate a static novel reader (index.html) from numbered Markdown chapters.

Usage:
    python3 scripts/build_reader.py [src_dir] \
        [--title 书名] [--subtitle 副标题] [--out index.html] [--prefix 前缀]

Conventions:
    - Chapters are files named `[0-9][0-9]-*.md` in src_dir.
    - Chapter 00 is rendered as "楔子：…", the highest-numbered chapter as
      "尾声：…", everything else as "第N章：…".
    - localStorage keys are namespaced by --prefix so multiple readers on the
      same domain do not share reading position / theme / font size.

Example:
    python3 scripts/build_reader.py . --title 黄海1894 --subtitle "架空历史 · 短篇"
"""
import re
import html
import json
import argparse
from pathlib import Path


def volume_label(path, root):
    """Derive the volume label from a chapter file's parent folder name.

    Volume folders carry a sortable numeric prefix, e.g. “01-卷一·蜃楼”;
    the prefix is stripped and the label becomes “卷一 · 蜃楼”. Chapters
    living directly in the source directory (楔子、尾声) have no label.
    """
    parent = path.parent.name
    if not parent or parent == root.name:
        return None
    name = re.sub(r"^\d+\s*[-_.]?\s*", "", parent)
    return re.sub(r"\s*·\s*", " · ", name)


def md_to_html(text):
    lines = text.strip().split("\n")
    paras = []
    buf = []
    end_re = re.compile(r"^\*\*——\s*(.+?)\s*——\*\*$")
    for ln in lines:
        s = ln.rstrip()
        if not s:
            if buf:
                paras.append("".join(buf))
                buf = []
            continue
        m_end = end_re.match(s)
        if m_end:  # 卷末/全书完结标记：独立居中显示
            if buf:
                paras.append("".join(buf))
                buf = []
            paras.append('<div class="end-mark">%s</div>' % html.escape(m_end.group(1)))
            continue
        if re.match(r"^#{1,6}\s", s):
            continue
        if re.fullmatch(r"(?:-{3,}|\*{3,}|_{3,})\s*", s):
            if buf:
                paras.append("".join(buf))
                buf = []
            paras.append("<hr>")
            continue
        buf.append(html.escape(s))
    if buf:
        paras.append("".join(buf))
    body = []
    for p in paras:
        if p == "<hr>" or p.startswith('<div class="end-mark">'):
            body.append(p)
        else:
            body.append(f"<p>{p}</p>")
    return "\n".join(body)


def chapter_meta(files):
    """Return (display_title, is_last_chapter) per file, sorted numerically."""
    nums = []
    for f in files:
        m = re.match(r"^([0-9][0-9])-", f.stem)
        nums.append(int(m.group(1)) if m else None)
    highest = max((n for n in nums if n is not None), default=None)
    out = []
    for f, n in zip(files, nums):
        name = re.sub(r"^[0-9][0-9]-", "", f.stem)
        if n == 0:
            title = "楔子：" + re.sub(r"^楔子[\s·:：]*", "", name)
        elif "尾声" in name:
            title = "尾声：" + name
        else:
            title = "第" + str(n) + "章：" + name
        out.append((title, n == highest))
    return out


def build(src_dir, title, subtitle, out_path, prefix):
    folder = Path(src_dir)
    files = sorted(folder.rglob("[0-9][0-9]-*.md"), key=lambda p: p.name)
    metas = chapter_meta(files)

    chapters = []
    for f, (title_text, _) in zip(files, metas):
        text = f.read_text(encoding="utf-8")
        chapters.append({"title": title_text, "html": md_to_html(text), "vol": volume_label(f, folder)})

    data_json = json.dumps(chapters, ensure_ascii=False)

    template = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ · 阅读器</title>
<style>
:root {
  --bg: #f6f2e9;
  --panel: #ede5d3;
  --text: #2b2620;
  --muted: #8a7f6c;
  --accent: #8a3b2f;
  --border: #d8cdb6;
}
.dark {
  --bg: #1d1a15;
  --panel: #262219;
  --text: #d8cfb8;
  --muted: #8d8167;
  --accent: #c96a54;
  --border: #3a3428;
}
* { box-sizing: border-box; }
body {
  margin: 0; font-family: "Songti SC", "STSong", "SimSun", serif;
  background: var(--bg); color: var(--text); transition: background .3s, color .3s;
}
#app { display: flex; height: 100vh; }
aside {
  width: 280px; flex-shrink: 0; background: var(--panel); border-right: 1px solid var(--border);
  overflow-y: auto; padding: 16px 8px;
}
aside h1 { font-size: 18px; margin: 4px 8px 12px; }
aside h1 small { display:block; font-size: 12px; color: var(--muted); font-weight: normal; margin-top: 4px; }
.toc a {
  display: block; padding: 7px 12px; margin: 2px 4px; border-radius: 6px;
  color: var(--text); text-decoration: none; font-size: 14px; cursor: pointer;
}
.toc a:hover { background: var(--border); }
.toc a.active { background: var(--accent); color: #fff; }
.toc-vol {
  margin: 14px 12px 4px; padding-bottom: 5px; border-bottom: 1px solid var(--border);
  font-size: 12px; letter-spacing: .15em; color: var(--muted);
}
.toc-vol:first-child { margin-top: 2px; }
main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.toolbar {
  display: flex; align-items: center; gap: 8px; padding: 10px 16px;
  background: var(--panel); border-bottom: 1px solid var(--border); flex-wrap: wrap;
}
.toolbar button {
  background: transparent; color: var(--text); border: 1px solid var(--border);
  border-radius: 6px; padding: 5px 10px; font-size: 13px; cursor: pointer;
}
.toolbar button:hover { background: var(--border); }
.toolbar .spacer { flex: 1; }
#progress { font-size: 12px; color: var(--muted); }
article { flex: 1; overflow-y: auto; padding: 40px 60px 80px; max-width: 760px; margin: 0 auto; width: 100%; }
article hr { border: none; margin: 2.4em auto; width: 140px; height: 1px; background: var(--border); }
.end-mark { text-align: center; margin-top: 3em; letter-spacing: .35em; text-indent: .35em; color: var(--muted); }
.vol-tag {
  text-align: center; font-size: 13px; letter-spacing: .35em; text-indent: .35em;
  color: var(--muted); margin: 0 0 10px;
}
article h2 {
  font-size: 26px; text-align: center; margin: 0 0 36px; color: var(--accent);
  padding-bottom: 16px; border-bottom: 1px solid var(--border);
}
article p { line-height: 2.0; font-size: 18px; margin: 0 0 22px; text-align: justify; }
#nav {
  display: flex; justify-content: space-between; padding: 20px 60px 40px; max-width: 760px; margin: 0 auto; width: 100%;
}
#nav button {
  background: var(--accent); color: #fff; border: none; border-radius: 8px;
  padding: 10px 22px; font-size: 15px; cursor: pointer;
}
#nav button:disabled { opacity: .35; cursor: default; }
.mobile-toc { display: none; }
@media (max-width: 720px) {
  aside { display: none; position: fixed; z-index: 10; width: 100%; height: 100%; }
  aside.open { display: block; }
  .mobile-toc { display: block; }
  article { padding: 24px 22px 60px; }
  article p { font-size: 17px; }
  #nav { padding: 16px 22px 32px; }
  .toolbar { padding: 8px 10px; }
}
</style>
</head>
<body>
<div id="app">
  <aside id="sidebar">
    <h1>__TITLE__<small>__SUBTITLE__</small></h1>
    <nav class="toc" id="toc"></nav>
  </aside>
  <main>
    <div class="toolbar">
      <button class="mobile-toc" id="btnToc">目录</button>
      <span class="spacer"></span>
      <button id="btnFontDown">A−</button>
      <button id="btnFontUp">A+</button>
      <button id="btnTheme">🌓 明暗</button>
      <span id="progress"></span>
    </div>
    <article id="article"></article>
    <div id="nav">
      <button id="btnPrev">← 上一章</button>
      <button id="btnNext">下一章 →</button>
    </div>
  </main>
</div>
<script>
const CHAPTERS = __DATA__;
let idx = 0;
const fontSizeKey = '__PREFIX___font';
const themeKey = '__PREFIX___theme';
const posKey = '__PREFIX___pos';

const article = document.getElementById('article');
const progress = document.getElementById('progress');

function render() {
  const ch = CHAPTERS[idx];
  article.innerHTML = (ch.vol ? '<div class="vol-tag">' + ch.vol + '</div>' : '') + '<h2>' + ch.title + '</h2>' + ch.html;
  progress.textContent = (idx + 1) + ' / ' + CHAPTERS.length;
  document.querySelectorAll('#toc a').forEach(a => a.classList.toggle('active', +a.dataset.i === idx));
  document.getElementById('btnPrev').disabled = idx === 0;
  document.getElementById('btnNext').disabled = idx === CHAPTERS.length - 1;
  document.title = ch.title + ' · __TITLE__';
  article.scrollTop = 0;
}

function buildToc() {
  const toc = document.getElementById('toc');
  let lastVol;
  CHAPTERS.forEach((ch, i) => {
    if (ch.vol && ch.vol !== lastVol) {
      const v = document.createElement('div');
      v.className = 'toc-vol';
      v.textContent = ch.vol;
      toc.appendChild(v);
    }
    lastVol = ch.vol || lastVol;
    const a = document.createElement('a');
    a.dataset.i = i;
    a.textContent = ch.title;
    a.addEventListener('click', () => { idx = i; render(); save(); closeMobileToc(); });
    toc.appendChild(a);
  });
}

function save() {
  localStorage.setItem(posKey, idx);
  localStorage.setItem(fontSizeKey, getComputedStyle(article).fontSize);
}
function closeMobileToc(){ document.getElementById('sidebar').classList.remove('open'); }

document.getElementById('btnPrev').onclick = () => { if (idx>0) { idx--; render(); save(); } };
document.getElementById('btnNext').onclick = () => { if (idx<CHAPTERS.length-1) { idx++; render(); save(); } };
document.getElementById('btnToc').onclick = () => document.getElementById('sidebar').classList.toggle('open');

function setFont(d) {
  const cur = parseFloat(getComputedStyle(article).fontSize) || 18;
  const next = Math.min(28, Math.max(13, cur + d));
  article.style.fontSize = next + 'px';
  save();
}
document.getElementById('btnFontUp').onclick = () => setFont(1);
document.getElementById('btnFontDown').onclick = () => setFont(-1);

const btnTheme = document.getElementById('btnTheme');
function applyTheme(dark){ document.body.classList.toggle('dark', dark); btnTheme.textContent = dark ? '☀ 明亮' : '🌓 明暗'; }
btnTheme.onclick = () => { const dark = !document.body.classList.contains('dark'); applyTheme(dark); localStorage.setItem(themeKey, dark ? '1':'0'); };

(function init(){
  buildToc();
  const savedTheme = localStorage.getItem(themeKey) === '1';
  applyTheme(savedTheme);
  const savedFont = localStorage.getItem(fontSizeKey);
  if (savedFont) article.style.fontSize = savedFont;
  const savedPos = parseInt(localStorage.getItem(posKey));
  if (!isNaN(savedPos) && savedPos >= 0 && savedPos < CHAPTERS.length) idx = savedPos;
  render();
})();
</script>
</body>
</html>
"""

    out = (template.replace("__DATA__", data_json)
                  .replace("__TITLE__", title)
                  .replace("__SUBTITLE__", subtitle)
                  .replace("__PREFIX___", prefix + "_"))
    out_path = Path(out_path)
    out_path.write_text(out, encoding="utf-8")
    print(f"OK: {len(chapters)} chapters -> {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate a static novel reader from numbered Markdown chapters.")
    parser.add_argument("src_dir", nargs="?", default=".",
                        help="folder containing [0-9][0-9]-*.md chapters (default: current dir)")
    parser.add_argument("--title", default="小说", help="book title shown in sidebar / tab")
    parser.add_argument("--subtitle", default="", help="small subtitle under the title")
    parser.add_argument("--out", default=None, help="output html path (default: <src_dir>/index.html)")
    parser.add_argument("--prefix", default=None,
                        help="localStorage key prefix (default: derived from title; avoids cross-book state clash)")
    args = parser.parse_args()

    title = args.title
    if args.prefix is None:
        prefix = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", title) or "reader"
    else:
        prefix = args.prefix
    out_path = args.out or (Path(args.src_dir) / "index.html")
    build(args.src_dir, title, args.subtitle, out_path, prefix)


if __name__ == "__main__":
    main()