r"""md-table-view — bake Markdown files into standalone HTML pages whose tables are easy to read.

    python mdtableview.py notes.md                 one file   → _html/notes.html next to it
    python mdtableview.py docs/ -o site/ --open    a folder   → same folder structure under site/

Tables get: sticky header row + sticky first column, horizontal scroll, click-to-sort columns,
drag-to-resize columns (remembered per page in the browser), and a quick filter box on long tables.

The .md stays the single source. The HTML is a disposable view: edit the .md, then bake again.
Same input → same output (no timestamps are written).
"""
import argparse
import html
import os
import re
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote, unquote

from markdown_it import MarkdownIt

__version__ = "0.1.0"

MD_EXT = (".md", ".markdown")
SKIP_DIRS = {"node_modules", "__pycache__"}

DARK = "--paper:#0F1513;--paper2:#161E1B;--ink:#E3EAE6;--muted:#9CA7A1;--rule:#2B3531;--accent:#6FB4C9;--hover:rgba(111,180,201,.07)"
LIGHT = "--paper:#FBFBF9;--paper2:#F1F3F0;--ink:#1B2420;--muted:#5F6B65;--rule:#D5DBD7;--accent:#1F7A93;--hover:rgba(31,122,147,.07)"

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{%VARS%;
--sans:'Pretendard','Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',system-ui,sans-serif;--mono:'Cascadia Mono',ui-monospace,Consolas,monospace}
html{background:var(--paper)}
body{margin:0;padding:24px 16px 64px;font-family:var(--sans);color:var(--ink);background:var(--paper);font-size:14px;line-height:1.6}
main{max-width:1180px;margin:0 auto}
body.wide main{max-width:none}
nav{font-family:var(--mono);font-size:11px;letter-spacing:.08em;color:var(--muted);margin-bottom:12px}
h1{font-size:22px;line-height:1.3;margin:0 0 12px}
h2{font-size:17px;margin:32px 0 10px;padding-top:14px;border-top:1px solid var(--rule)}
h3{font-size:15px;margin:22px 0 8px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
img{max-width:100%}
blockquote{margin:10px 0;padding:8px 14px;border-left:3px solid var(--rule);color:var(--muted);background:var(--paper2)}
blockquote p{margin:4px 0}
code{font-family:var(--mono);font-size:12px;background:var(--paper2);padding:1px 5px;border-radius:3px}
pre{background:var(--paper2);padding:12px 14px;border-radius:6px;overflow-x:auto}
pre code{padding:0;background:none}
hr{border:0;border-top:1px solid var(--rule);margin:28px 0}
details{margin:10px 0;padding:6px 12px;border:1px solid var(--rule);border-radius:6px}
summary{cursor:pointer;color:var(--muted)}
.tw{overflow-x:auto;margin:12px 0;border:1px solid var(--rule);border-radius:6px;scrollbar-color:var(--rule) transparent}
body.wide .tw{max-height:calc(100vh - 120px);overflow:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 10px;border-bottom:1px solid var(--rule);border-right:1px solid var(--rule);text-align:left;vertical-align:top;min-width:88px}
th{position:sticky;top:0;background:var(--paper2);font-weight:600;white-space:nowrap;z-index:2}
td:first-child,th:first-child{position:sticky;left:0;background:var(--paper2);z-index:1;min-width:64px;font-weight:600}
th:first-child{z-index:3}
tr:hover td{background:var(--hover)}
tr:hover td:first-child{background:var(--paper2)}
td.long{min-width:240px}
th.srt{cursor:pointer;user-select:none}
th[data-sort=asc]::after{content:' \\25B2';color:var(--accent)}
th[data-sort=desc]::after{content:' \\25BC';color:var(--accent)}
.grip{position:absolute;top:0;right:0;width:8px;height:100%;cursor:col-resize;touch-action:none}
.grip:hover,.grip.on{background:var(--accent);opacity:.55}
table.fx{table-layout:fixed}
table.fx th,table.fx td{min-width:0;overflow-wrap:anywhere}
table.fx th{overflow:hidden;text-overflow:ellipsis}
.flt{margin:8px 0;padding:7px 10px;width:min(360px,100%);background:var(--paper2);color:var(--ink);border:1px solid var(--rule);border-radius:6px;font:inherit}
.foot{margin-top:36px;color:var(--muted);font-size:12px}
"""

JS = r"""
var KO=(navigator.language||'').indexOf('ko')===0;
var TIP=KO?'클릭 = 정렬(오름 → 내림 → 원래 순서) · 오른쪽 경계 드래그 = 열 너비 · 경계 더블클릭 = 너비 초기화'
          :'Click = sort (asc → desc → original) · drag right edge = column width · double-click edge = reset widths';
var FIND=KO?'이 표에서 찾기':'Filter this table';
// Sort key: date (YYYY-MM-DD, MM-DD) → leading number (#1, +164.4, −4.4%, $14.3B) → first signed percent → null (text sort)
function sortKey(s){
  s=s.trim().replace(/−/g,'-');
  var m=s.match(/^(\d{4})-(\d{2})-(\d{2})/);if(m)return +(m[1]+m[2]+m[3]);
  m=s.match(/^(\d{2})-(\d{2})(?!\d)/);if(m)return +(m[1]+m[2]);
  m=s.match(/^[#$€£¥₩]?\s*([+-]?\d[\d,]*\.?\d*)(?=$|[\s%·,()\/~]|[BMKTx](?![A-Za-z])|[배조억만주원])/);if(m)return parseFloat(m[1].replace(/,/g,''));
  m=s.match(/([+-]\d+(?:\.\d+)?)\s*%/);return m?parseFloat(m[1]):null;
}
document.querySelectorAll('table').forEach(function(t,ti){
  var rows=t.tBodies[0]?Array.from(t.tBodies[0].rows):[];
  rows.forEach(function(r){Array.from(r.cells).forEach(function(c){if(c.textContent.length>60)c.classList.add('long')})});
  var ths=t.tHead&&t.tHead.rows[0]?Array.from(t.tHead.rows[0].cells):[];
  if(ths.length>7)document.body.classList.add('wide');
  var dragEnd=0,store='colw:'+location.pathname+':'+ti+':'+ths.length;
  // Sorting — empty cells (and non-numeric cells in a numeric column) always sink to the bottom
  if(rows.length>1)ths.forEach(function(th,ci){
    th.classList.add('srt');th.title=TIP;
    th.addEventListener('click',function(e){
      if(e.target.closest('a,.grip')||Date.now()-dragEnd<300)return;
      var d=th.dataset.sort==='asc'?'desc':th.dataset.sort==='desc'?'':'asc';
      ths.forEach(function(x){delete x.dataset.sort});
      var idx=rows.map(function(_,i){return i});
      if(d){
        th.dataset.sort=d;
        var tx=rows.map(function(r){return r.cells[ci]?r.cells[ci].textContent.trim():''});
        var ks=tx.map(sortKey),filled=tx.filter(Boolean).length;
        var num=filled>0&&ks.filter(function(k){return k!==null}).length>=filled*0.8,sg=d==='asc'?1:-1;
        var bad=function(i){return num?ks[i]===null:!tx[i]};
        idx.sort(function(a,b){
          if(bad(a)||bad(b))return bad(a)-bad(b)||a-b;
          return sg*(num?ks[a]-ks[b]:tx[a].localeCompare(tx[b],undefined,{numeric:true}))||a-b;
        });
      }
      idx.forEach(function(i){t.tBodies[0].appendChild(rows[i])});
    });
  });
  // Column widths — the first drag freezes current widths (table-layout:fixed), then only that column changes
  var cols=null;
  function freeze(ws){
    ws=ws||ths.map(function(h){return h.getBoundingClientRect().width});
    var cg=document.createElement('colgroup');
    cols=ws.map(function(w){var c=document.createElement('col');c.style.width=w+'px';cg.appendChild(c);return c});
    t.insertBefore(cg,t.firstChild);t.classList.add('fx');fit();
  }
  function fit(){t.style.width=cols.reduce(function(s,c){return s+parseFloat(c.style.width)},0)+'px'}
  function thaw(){if(!cols)return;cols[0].parentNode.remove();cols=null;t.classList.remove('fx');t.style.width='';try{localStorage.removeItem(store)}catch(e){}}
  ths.forEach(function(th,ci){
    var g=document.createElement('span');g.className='grip';th.appendChild(g);
    g.addEventListener('pointerdown',function(e){
      e.preventDefault();if(!cols)freeze();
      var x0=e.clientX,w0=parseFloat(cols[ci].style.width);g.classList.add('on');g.setPointerCapture(e.pointerId);
      var mv=function(ev){cols[ci].style.width=Math.max(36,w0+ev.clientX-x0)+'px';fit()};
      var up=function(){
        g.classList.remove('on');g.removeEventListener('pointermove',mv);g.removeEventListener('pointerup',up);g.removeEventListener('pointercancel',up);dragEnd=Date.now();
        try{localStorage.setItem(store,JSON.stringify(cols.map(function(c){return parseFloat(c.style.width)})))}catch(e){}
      };
      g.addEventListener('pointermove',mv);g.addEventListener('pointerup',up);g.addEventListener('pointercancel',up);
    });
    g.addEventListener('dblclick',function(e){e.stopPropagation();thaw()});
  });
  try{var sv=JSON.parse(localStorage.getItem(store)||'null');if(Array.isArray(sv)&&sv.length===ths.length&&ths.length)freeze(sv)}catch(e){}
  if(rows.length<15)return;
  var i=document.createElement('input');i.className='flt';i.placeholder=FIND;
  i.addEventListener('input',function(){var q=i.value.trim().toLowerCase();rows.forEach(function(r){r.style.display=!q||r.textContent.toLowerCase().indexOf(q)>=0?'':'none'})});
  t.parentNode.parentNode.insertBefore(i,t.parentNode);
});
"""


def css(theme):
    if theme == "dark":
        return CSS.replace("%VARS%", DARK)
    if theme == "light":
        return CSS.replace("%VARS%", LIGHT)
    return CSS.replace("%VARS%", DARK) + "@media (prefers-color-scheme: light){:root{" + LIGHT + "}}\n"


def collect(inputs, outdir=None):
    """Input files/folders → (sorted list of absolute .md paths, common root folder)."""
    files, roots = [], []
    skip = os.path.normcase(os.path.abspath(outdir)) if outdir else None
    for p in inputs:
        p = os.path.abspath(p)
        if os.path.isdir(p):
            roots.append(p)
            for base, dirs, fs in os.walk(p):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS and d != "_html"
                                 and os.path.normcase(os.path.join(base, d)) != skip)
                files += [os.path.join(base, f) for f in sorted(fs) if f.lower().endswith(MD_EXT)]
        elif os.path.isfile(p):
            roots.append(os.path.dirname(p))
            files.append(p)
        else:
            raise FileNotFoundError(p)
    seen, out = set(), []
    for f in files:
        k = os.path.normcase(os.path.normpath(f))
        if k not in seen:
            seen.add(k)
            out.append(os.path.normpath(f))
    root = os.path.commonpath(roots) if roots else os.getcwd()
    return out, root


def _rel(target, start):
    """Relative URL path from folder `start` to `target`; falls back to a file:// URI across drives."""
    try:
        return quote(os.path.relpath(target, start).replace(os.sep, "/"), safe="/.-_~()")
    except ValueError:
        return Path(target).as_uri()


def _page(title, body, style, nav="", foot=""):
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{style}</style></head>\n<body><main>{nav}\n{body}"
            f'<p class="foot">{foot}</p></main><script>{JS}</script></body></html>\n')


def _write(dst, text):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, dst)


def bake(inputs, outdir=None, theme="auto", index_title="Index"):
    """Bake every .md under `inputs` into `outdir`. Returns (list of written .html paths, start page)."""
    files, root = collect(inputs, outdir)
    if not files:
        raise SystemExit("no .md files found")
    outdir = os.path.abspath(outdir) if outdir else os.path.join(root, "_html")
    tset = {os.path.normcase(f) for f in files}
    style = css(theme)
    md = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])

    def dest(src):
        return os.path.join(outdir, os.path.splitext(os.path.relpath(src, root))[0] + ".html")

    index = os.path.join(outdir, "index.html")
    make_index = len(files) > 1 and os.path.normcase(index) not in {os.path.normcase(dest(f)) for f in files}
    written, listing = [], []
    for src in files:
        dst = dest(src)
        sdir, ddir = os.path.dirname(src), os.path.dirname(dst)
        with open(src, encoding="utf-8-sig") as f:
            text = f.read()
        text = re.sub(r"\A---\r?\n.*?\r?\n---\r?\n", "", text, count=1, flags=re.S)   # YAML front matter
        body = md.render(text)

        def fix(m):
            url = html.unescape(m.group(2))
            if not url or url.startswith(("#", "/")) or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]+:", url):
                return m.group(0)
            path, sep, frag = url.partition("#")
            tgt = os.path.normpath(os.path.join(sdir, unquote(path)))
            new = _rel(dest(tgt) if os.path.normcase(tgt) in tset else tgt, ddir)
            return m.group(1) + html.escape(new + sep + frag, quote=True) + m.group(3)

        body = re.sub(r'(<(?:a href|img src)=")([^"]*)(")', fix, body)
        body = body.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
        m1 = re.search(r"^# (.+)$", text, re.M)
        rel = os.path.relpath(src, root).replace(os.sep, "/")
        title = m1.group(1).strip() if m1 else os.path.splitext(os.path.basename(src))[0]
        nav = f'<nav><a href="{_rel(index, ddir)}">&larr; {html.escape(index_title)}</a></nav>' if make_index else ""
        _write(dst, _page(title, body, style, nav, f"source = {html.escape(rel)} &middot; baked by md-table-view (edit the .md, then bake again)"))
        written.append(dst)
        listing.append((title, rel, _rel(dst, outdir)))
    if make_index:
        rows = "\n".join(f'<tr><td><a href="{html.escape(href, quote=True)}">{html.escape(t)}</a></td><td>{html.escape(r)}</td></tr>' for t, r, href in listing)
        body = (f"<h1>{html.escape(index_title)}</h1>\n"
                f'<div class="tw"><table><thead><tr><th>Title</th><th>Source</th></tr></thead>\n<tbody>\n{rows}\n</tbody></table></div>')
        _write(index, _page(index_title, body, style, foot=f"{len(listing)} pages &middot; baked by md-table-view"))
        written.append(index)
    return written, (index if make_index else written[0])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mdtableview", description="Bake Markdown into HTML with sortable, resizable tables.")
    ap.add_argument("inputs", nargs="+", help=".md files and/or folders (folders are scanned recursively)")
    ap.add_argument("-o", "--out", help="output folder (default: _html inside the common input folder)")
    ap.add_argument("--theme", choices=("auto", "dark", "light"), default="auto", help="auto follows the browser/OS setting (default)")
    ap.add_argument("--index-title", default="Index", help="title of the generated index page")
    ap.add_argument("--open", action="store_true", help="open the start page in the default browser")
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args(argv)
    written, start = bake(a.inputs, a.out, a.theme, a.index_title)
    print(f"baked {len(written)} page(s)")
    print("start:", start)
    if a.open:
        webbrowser.open(Path(start).as_uri())


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
