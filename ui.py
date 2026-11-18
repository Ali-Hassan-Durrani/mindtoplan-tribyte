"""Look and feel for app.py: theme CSS (light/dark via CSS variables), restrained motion, small HTML helpers.
Pure presentation: no planning logic here."""
from html import escape

THEMES = {
    "light": {"bg": "#f7f8fa", "card": "#ffffff", "card2": "#f1f3f6", "text": "#1f2937", "muted": "#6b7280",
              "border": "#e5e7eb", "accent": "#1d4ed8", "ok": "#15803d", "bad": "#b91c1c", "warn": "#b45309",
              "info": "#1d4ed8"},
    "dark": {"bg": "#111418", "card": "#181c22", "card2": "#20252d", "text": "#e5e7eb", "muted": "#9ca3af",
             "border": "#2b313b", "accent": "#60a5fa", "ok": "#4ade80", "bad": "#f87171", "warn": "#fbbf24",
             "info": "#60a5fa"},
}


def css(theme):
    t = THEMES[theme]
    vars_ = ";".join(f"--{k}:{v}" for k, v in t.items())
    return f"""<style>
:root{{{vars_}}}
html,body,[data-testid="stAppViewContainer"],[data-testid="stHeader"],[data-testid="stMain"]{{background:var(--bg)!important;color:var(--text)!important}}
[data-testid="stSidebar"]{{background:var(--card)!important;border-right:1px solid var(--border)}}
[data-testid="stSidebar"] *,[data-testid="stMarkdownContainer"],[data-testid="stMarkdownContainer"] *,label,p,h1,h2,h3,h4,span,li{{color:var(--text)}}
[data-testid="stCaptionContainer"] *{{color:var(--muted)!important}}
.block-container{{padding-top:2.2rem;max-width:1180px}}
h3{{font-size:1.02rem!important;font-weight:650!important;letter-spacing:.01em;margin:1.2rem 0 .4rem!important}}
[data-testid="stExpander"] details{{background:var(--card);border:1px solid var(--border)!important;border-radius:6px}}
textarea,input,[data-baseweb="select"]>div,[data-testid="stFileUploaderDropzone"]{{background:var(--card)!important;color:var(--text)!important;border-color:var(--border)!important}}
.stButton button,.stDownloadButton button{{border-radius:6px;border:1px solid var(--border);background:var(--card);color:var(--text);transition:border-color .15s,color .15s}}
.stButton button:hover,.stDownloadButton button:hover{{border-color:var(--accent);color:var(--accent)}}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"]{{background:var(--accent);color:#fff;border-color:var(--accent)}}
button[role="tab"]{{color:var(--muted)!important}} button[role="tab"][aria-selected="true"]{{color:var(--text)!important;font-weight:600}}
[data-baseweb="tab-highlight"]{{background:var(--accent)!important}}
code,pre{{background:var(--card2)!important;color:var(--text)!important}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
.panel{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 16px;margin:8px 0 14px;animation:fade .25s ease-out both}}
.status{{display:flex;align-items:center;gap:14px;border-left:4px solid var(--muted)}}
.status.VALID{{border-left-color:var(--ok)}} .status.INVALID{{border-left-color:var(--bad)}} .status.NEEDS{{border-left-color:var(--warn)}}
.status .s{{font-weight:700;font-size:.95rem;letter-spacing:.04em}}
.status.VALID .s{{color:var(--ok)}} .status.INVALID .s{{color:var(--bad)}} .status.NEEDS .s{{color:var(--warn)}}
.crumbs{{font-size:.82rem;color:var(--muted);margin:0 0 6px}} .crumbs b{{color:var(--text);font-weight:600}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));background:var(--card);border:1px solid var(--border);border-radius:8px;margin:8px 0 14px;animation:fade .25s both}}
.stat{{padding:12px 16px;border-right:1px solid var(--border)}} .stat:last-child{{border-right:none}}
.stat .l{{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}}
.stat .v{{font-size:1.3rem;font-weight:650;color:var(--text);font-variant-numeric:tabular-nums}}
.stat .x{{font-size:.75rem;color:var(--muted)}}
.tbl{{width:100%;border-collapse:collapse;font-size:.88rem;font-variant-numeric:tabular-nums}}
.tbl th{{text-align:left;color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid var(--border);padding:6px 8px}}
.tbl td{{border-bottom:1px solid var(--border);padding:7px 8px;color:var(--text);vertical-align:top}}
.tbl tr:last-child td{{border-bottom:none}}
.tbl td.num{{text-align:right;white-space:nowrap}}
.dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:var(--muted)}}
.dot.PASS,.dot.ok{{background:var(--ok)}} .dot.FAIL,.dot.bad{{background:var(--bad)}} .dot.UNRESOLVED,.dot.warn{{background:var(--warn)}} .dot.info{{background:var(--info)}}
.tag{{display:inline-block;padding:0 7px;border-radius:4px;font-size:.75rem;font-weight:600;border:1px solid var(--border);color:var(--muted);margin-right:4px;line-height:1.6}}
.tag.ok{{color:var(--ok);border-color:color-mix(in srgb,var(--ok) 40%,var(--border))}}
.tag.bad{{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 40%,var(--border))}}
.tag.warn{{color:var(--warn);border-color:color-mix(in srgb,var(--warn) 40%,var(--border))}}
.tag.info,.tag.acc{{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 40%,var(--border))}}
.rej{{border-left:4px solid var(--bad)}} .q{{color:var(--text)}}
.muted{{color:var(--muted)}} .small{{font-size:.82rem}}
.tl{{display:flex;height:34px;border-radius:6px;overflow:hidden;border:1px solid var(--border);margin:4px 0 10px;transform-origin:left;animation:grow .35s ease-out both}}
.tl div{{display:flex;align-items:center;justify-content:center;font-size:.7rem;color:#fff;overflow:hidden;white-space:nowrap;border-right:1px solid rgba(255,255,255,.4);padding:0 4px}}
.bar{{display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--card2);border:1px solid var(--border);transform-origin:left;animation:grow .35s ease-out both}}
.legend{{margin:6px 0 10px}} .legend span{{display:inline-flex;align-items:center;gap:6px;margin-right:16px;font-size:.8rem;color:var(--muted)}}
.legend i{{width:10px;height:10px;border-radius:2px;display:inline-block}}
.roster{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px}}
.roster div{{border:1px solid var(--border);border-radius:6px;padding:6px 8px;font-size:.8rem;background:var(--card)}}
.roster b{{display:block;font-size:.75rem;color:var(--muted);font-weight:600}}
.diff{{display:grid;grid-template-columns:1.2fr 1fr 24px 1fr;gap:4px 10px;font-size:.9rem;font-variant-numeric:tabular-nums}}
.diff .new{{font-weight:650;color:var(--accent);animation:fade .4s both}}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important;transition:none!important}}}}
</style>"""


def e(x):
    return escape(str(x))


def tag(text, kind=""):
    return f'<span class="tag {kind}">{e(text)}</span>'


chip = tag   # same look; kept for callers


def dot(kind):
    return f'<span class="dot {kind}"></span>'


def stats(items):
    """items: (label, value, sub)"""
    return '<div class="stats">' + "".join(
        f'<div class="stat"><div class="l">{e(l)}</div><div class="v">{e(v)}</div><div class="x">{e(x)}</div></div>'
        for l, v, x in items) + "</div>"


def table(rows, cols, num=()):
    head = "".join(f"<th>{e(c)}</th>" for c in cols)
    body = "".join("<tr>" + "".join(
        f'<td class="{"num" if c in num else ""}">'
        f'{r.get(c, "") if str(r.get(c, "")).startswith("<span") else e(r.get(c, ""))}</td>' for c in cols) + "</tr>"
        for r in rows)
    return f'<table class="tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


STATUS_KIND = {"accepted": "ok", "partly accepted": "warn", "rejected": "bad", "superseded": "", "noted": "info",
               "optional": "info", "irrelevant": "", "needs review": "warn", "pending": "warn"}
STATUS_LABEL = {"accepted": "used", "noted": "pending approval"}
