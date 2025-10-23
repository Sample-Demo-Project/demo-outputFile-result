#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_folder_gallery.py
--------------------------
把指定資料夾（預設 ./uploads）中的所有檔案，做成 docs/index.html 靜態頁面，
並將檔案複製到 docs/files/ 以利 GitHub Pages 直接提供預覽與下載。

不需第三方套件（僅用標準庫）。
支援預覽：
- 圖片：png/jpg/jpeg/gif/svg/webp
- PDF：<iframe> 內嵌（瀏覽器支援）
- CSV：前 30 列（純 HTML 表格）
- JSON：pretty-print（前 ~200KB）
- TXT/LOG/MD：前 200 行
- 其他：顯示檔名與下載按鈕

可用環境變數覆寫來源資料夾：GALLERY_SRC
"""
from __future__ import annotations
import os, csv, json, mimetypes, shutil, html
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
SRC_DIR = Path(os.environ.get("GALLERY_SRC", "uploads"))  # 學生只要把檔案放這裡
DOCS = ROOT / "docs"
FILES = DOCS / "files"
ASSETS = DOCS / "site_assets"

def ensure_dirs():
    DOCS.mkdir(parents=True, exist_ok=True)
    FILES.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

def write_css():
    (ASSETS / "styles.css").write_text("""\
:root { --fg:#111; --bg:#fff; --muted:#666; --accent:#0b63f6; --line:#e5e5e5; }
* { box-sizing:border-box; }
html, body { margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans TC",Arial,sans-serif; background:var(--bg); color:var(--fg); }
header { position:sticky; top:0; background:#fff; border-bottom:1px solid var(--line); padding:12px 16px; }
h1 { margin:0; font-size:20px; }
main { max-width:1100px; margin:20px auto; padding:0 16px 48px; }
.note { color:var(--muted); font-size:12px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; }
.card { border:1px solid var(--line); border-radius:10px; padding:12px; background:#fff; overflow:hidden; display:flex; flex-direction:column; gap:8px; }
.meta { font-size:13px; color:#333; line-height:1.4; }
.meta b { display:inline-block; min-width:82px; color:#000; }
.btn { display:inline-block; padding:7px 10px; border:1px solid var(--accent); color:var(--accent); border-radius:6px; text-decoration:none; }
.table-wrap { overflow:auto; border:1px solid var(--line); border-radius:8px; }
table { border-collapse:collapse; width:100%; font-size:13px; }
thead { background:#fafafa; }
th,td { border-bottom:1px solid var(--line); padding:6px 8px; white-space:nowrap; text-align:left; }
pre.code { background:#0d1117; color:#c9d1d9; padding:12px; border-radius:8px; overflow:auto; font-size:12px; }
.pdf-wrap { border:1px solid var(--line); border-radius:8px; overflow:hidden; }
.pdf-wrap iframe { width:100%; height:420px; border:0; }
.badge { display:inline-block; font-size:11px; padding:2px 6px; border-radius:999px; background:#f3f3f3; border:1px solid var(--line); }
""", encoding="utf-8")

def esc(s: str) -> str:
    return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
             .replace('"',"&quot;").replace("'","&#39;"))

def preview_for(path: Path, rel_href: str) -> str:
    ext = path.suffix.lower().lstrip(".")
    if ext in {"png","jpg","jpeg","gif","svg","webp"}:
        return f'<img src="{rel_href}" alt="{esc(path.name)}" style="max-width:100%;height:auto;border:1px solid #eee;border-radius:6px;" loading="lazy"/>'
    if ext == "pdf":
        return f'<div class="pdf-wrap"><iframe src="{rel_href}" title="pdf"></iframe><div class="note">若無法預覽，請點下載。</div></div>'
    if ext == "csv":
        rows, header = [], []
        try:
            with path.open("r", encoding="utf-8") as f:
                rd = csv.reader(f); header = next(rd, []) or []
                for i, r in enumerate(rd):
                    if i>=30: break
                    rows.append(r)
        except Exception:
            try:
                with path.open("r", encoding="utf-8-sig") as f:
                    rd = csv.reader(f); header = next(rd, []) or []
                    for i, r in enumerate(rd):
                        if i>=30: break
                        rows.append(r)
            except Exception as e:
                return f'<p class="note">CSV 讀取失敗：{esc(str(e))}</p>'
        thead = "".join(f"<th>{esc(h)}</th>" for h in header)
        trs = []
        for r in rows:
            tds = "".join(f"<td>{esc(c)}</td>" for c in r)
            trs.append(f"<tr>{tds}</tr>")
        return f'<div class="table-wrap"><table><thead><tr>{thead}</tr></thead><tbody>{"".join(trs)}</tbody></table><p class="note">僅顯示前 {len(rows)} 列。</p></div>'
    if ext == "json":
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
            data = json.loads(raw)
            pretty = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            pretty = path.read_text(encoding="utf-8", errors="replace")[:200_000]
        return f'<pre class="code">{esc(pretty)}</pre>'
    if ext in {"txt","log","md"}:
        txt = path.read_text(encoding="utf-8", errors="replace").splitlines()[:200]
        return f'<pre class="code">{esc("\\n".join(txt))}</pre>'
    return '<p class="note">此檔案型別未提供預覽。</p>'

def human_size(n: int) -> str:
    units = ["B","KB","MB","GB","TB"]
    x = float(n)
    for u in units:
        if x < 1024 or u == units[-1]:
            return f"{x:.1f}{u}"
        x /= 1024

def main():
    ensure_dirs()
    write_css()

    if not SRC_DIR.exists():
        # 建立空頁提示
        (DOCS / "index.html").write_text(
            f"<!doctype html><meta charset='utf-8'><link rel='stylesheet' href='./site_assets/styles.css'>"
            f"<body><main><h1>資料夾不存在</h1><p class='note'>找不到來源資料夾：<code>{esc(str(SRC_DIR))}</code></p></main></body>",
            encoding="utf-8"
        )
        print(f"Source folder not found: {SRC_DIR}")
        return

    # 收集來源檔案（遞迴）
    src_files = [p for p in SRC_DIR.rglob("*") if p.is_file()]
    cards = []
    for src in sorted(src_files):
        dst = FILES / src.name
        # 避免名稱衝突
        i = 1
        while dst.exists():
            dst = FILES / f"{src.stem}_{i}{src.suffix}"
            i += 1
        dst.write_bytes(src.read_bytes())
        rel = f"./files/{dst.name}"
        size = human_size(dst.stat().st_size)
        mime, _ = mimetypes.guess_type(dst.name)
        kind = mime or "application/octet-stream"
        prev = preview_for(dst, rel)
        cards.append(f"""
<article class="card">
  <div class="meta">
    <div><span class="badge">{esc(dst.suffix.lstrip('.').lower() or 'file')}</span></div>
    <div><b>檔名</b>{esc(dst.name)}</div>
    <div><b>大小</b>{size}</div>
    <div><b>MIME</b>{esc(kind)}</div>
  </div>
  {prev}
  <div><a class="btn" href="{rel}" download>下載</a></div>
</article>
""")

    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    html_page = f"""<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>資料夾內容總覽</title>
<link rel="stylesheet" href="./site_assets/styles.css"/>
<body>
<header><h1>資料夾內容總覽</h1></header>
<main>
  <p class="note">來源資料夾：<code>{esc(str(SRC_DIR))}</code>；更新時間：{updated}</p>
  <section class="grid">
    {''.join(cards) if cards else "<p class='note'>資料夾目前沒有檔案。</p>"}
  </section>
</main>
</body>
</html>"""
    (DOCS / "index.html").write_text(html_page, encoding="utf-8")
    print(f"[OK] Wrote docs/index.html from {SRC_DIR}")

if __name__ == "__main__":
    mimetypes.init()
    main()
