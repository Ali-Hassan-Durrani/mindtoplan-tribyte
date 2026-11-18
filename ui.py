"""Look and feel for app.py: theme CSS (light/dark via CSS variables), animations, small HTML helpers.
Pure presentation: no planning logic here."""
from html import escape

THEMES = {
    "light": {"bg": "#f6f7fb", "card": "#ffffff", "card2": "#eef1f7", "text": "#1d2433", "muted": "#5b6474",
              "border": "#dde2ec", "accent": "#4f46e5", "ok": "#16a34a", "bad": "#dc2626", "warn": "#d97706",
              "info": "#2563eb", "shadow": "0 1px 3px rgba(16,24,40,.08), 0 4px 14px rgba(16,24,40,.06)"},
    "dark": {"bg": "#0f1320", "card": "#181d2e", "card2": "#212840", "text": "#e6e9f2", "muted": "#9aa3b8",
             "border": "#2c3450", "accent": "#818cf8", "ok": "#22c55e", "bad": "#f87171", "warn": "#fbbf24",
             "info": "#60a5fa", "shadow": "0 1px 3px rgba(0,0,0,.4), 0 6px 18px rgba(0,0,0,.35)"},
}


def css(theme):
    t = THEMES[theme]
    vars_ = ";".join(f"--{k}:{v}" for k, v in t.items())
    return f"""<style>
:root{{{vars_}}}
html,body,[data-testid="stAppViewContainer"],[data-testid="stHeader"],[data-testid="stMain"]{{background:var(--bg)!important;color:var(--text)!important}}
[data-testid="stSidebar"]{{background:var(--card)!important;border-right:1px solid var(--border)}}
[data-testid="stSidebar"] *,[data-testid="stMarkdownContainer"],[data-testid="stMarkdownContainer"] *,label,p,h1,h2,h3,h4,span,li,[data-testid="stCaptionContainer"]{{color:var(--text)}}
[data-testid="stCaptionContainer"] *{{color:var(--muted)!important}}
[data-testid="stExpander"] details{{background:var(--card);border:1px solid var(--border)!important;border-radius:10px}}
[data-testid="stExpander"] summary:hover{{color:var(--accent)}}
textarea,input,[data-baseweb="select"]>div,[data-testid="stFileUploaderDropzone"]{{background:var(--card2)!important;color:var(--text)!important;border-color:var(--border)!important}}
.stButton button,.stDownloadButton button{{border-radius:10px;border:1px solid var(--border);background:var(--card2);color:var(--text);transition:transform .15s,box-shadow .15s}}
.stButton button:hover,.stDownloadButton button:hover{{transform:translateY(-1px);box-shadow:var(--shadow);border-color:var(--accent);color:var(--accent)}}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"]{{background:var(--accent);color:#fff;border-color:var(--accent)}}
button[role="tab"]{{color:var(--muted)!important}} button[role="tab"][aria-selected="true"]{{color:var(--accent)!important}}
[data-baseweb="tab-highlight"]{{background:var(--accent)!important}}
code{{background:var(--card2)!important;color:var(--text)!important}}
pre{{background:var(--card2)!important}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
@keyframes pulse{{0%,100%{{box-shadow:0 0 0 0 var(--pc)}}50%{{box-shadow:0 0 0 8px transparent}}}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes flash{{0%{{background:var(--accent);color:#fff}}100%{{background:transparent}}}}
@property --n{{syntax:'<integer>';initial-value:0;inherits:false}}
@keyframes count{{from{{--n:0}}}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px 18px;margin:6px 0 12px;box-shadow:var(--shadow);animation:fadeUp .35s ease-out both;transition:transform .18s,box-shadow .18s}}
.card:hover{{transform:translateY(-2px)}}
.hero{{display:flex;gap:18px;align-items:center;flex-wrap:wrap}}
.badge{{--pc:var(--ok);padding:10px 18px;border-radius:999px;font-weight:700;font-size:1.15rem;color:#fff;animation:pulse 2.4s ease-in-out 2}}
.badge.VALID{{background:var(--ok);--pc:color-mix(in srgb,var(--ok) 45%,transparent)}}
.badge.INVALID{{background:var(--bad);--pc:color-mix(in srgb,var(--bad) 45%,transparent)}}
.badge.NEEDS{{background:var(--warn);--pc:color-mix(in srgb,var(--warn) 45%,transparent)}}
.hero-text{{font-size:1.02rem;color:var(--text);flex:1;min-width:240px}}
.steps{{display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 14px}}
.step{{flex:1;min-width:150px;padding:10px 14px;border-radius:12px;border:1px solid var(--border);background:var(--card);color:var(--muted);font-weight:600;animation:fadeUp .3s both}}
.step.done{{color:var(--ok);border-color:color-mix(in srgb,var(--ok) 50%,var(--border))}}
.step.now{{color:#fff;background:var(--accent);border-color:var(--accent)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:6px 0 12px}}
.kpi{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px 14px;box-shadow:var(--shadow);animation:fadeUp .35s both;transition:transform .18s}}
.kpi:hover{{transform:translateY(-2px)}}
.kpi .l{{font-size:.78rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}}
.kpi .v{{font-size:1.55rem;font-weight:700;color:var(--text)}}
.kpi .s{{font-size:.78rem;color:var(--muted)}}
.count{{animation:count .4s ease-out both;counter-reset:n var(--n)}}
.count::after{{content:counter(n)}}
.check{{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;border-radius:12px;background:var(--card);border:1px solid var(--border);border-left:5px solid var(--muted);animation:fadeUp .35s both}}
.check.PASS{{border-left-color:var(--ok)}} .check.FAIL{{border-left-color:var(--bad)}} .check.UNRESOLVED{{border-left-color:var(--warn)}} .check.NOTED{{border-left-color:var(--info)}}
.check .t{{font-weight:650}} .check .d{{font-size:.82rem;color:var(--muted)}}
.chip{{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.78rem;font-weight:650;margin:2px 4px 2px 0;border:1px solid transparent}}
.chip.ok{{background:color-mix(in srgb,var(--ok) 16%,transparent);color:var(--ok);border-color:color-mix(in srgb,var(--ok) 40%,transparent)}}
.chip.bad{{background:color-mix(in srgb,var(--bad) 16%,transparent);color:var(--bad);border-color:color-mix(in srgb,var(--bad) 40%,transparent)}}
.chip.warn{{background:color-mix(in srgb,var(--warn) 16%,transparent);color:var(--warn);border-color:color-mix(in srgb,var(--warn) 40%,transparent)}}
.chip.info{{background:color-mix(in srgb,var(--info) 16%,transparent);color:var(--info);border-color:color-mix(in srgb,var(--info) 40%,transparent)}}
.chip.mute{{background:var(--card2);color:var(--muted);border-color:var(--border)}}
.chip.acc{{background:color-mix(in srgb,var(--accent) 16%,transparent);color:var(--accent);border-color:color-mix(in srgb,var(--accent) 40%,transparent)}}
.rej{{border-left:5px solid var(--bad)}} .rej .q{{font-style:italic;color:var(--text)}}
.tbl{{width:100%;border-collapse:collapse;font-size:.9rem}}
.tbl th{{text-align:left;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border);padding:6px 8px}}
.tbl td{{border-bottom:1px solid var(--border);padding:6px 8px;color:var(--text);vertical-align:top}}
.tbl tr:hover td{{background:var(--card2)}}
.tl{{display:flex;height:46px;border-radius:10px;overflow:hidden;border:1px solid var(--border);transform-origin:left;animation:grow .4s ease-out both}}
.tl div{{display:flex;align-items:center;justify-content:center;font-size:.72rem;color:#fff;overflow:hidden;white-space:nowrap;border-right:1px solid rgba(255,255,255,.35);padding:0 4px}}
.bar{{display:flex;height:22px;border-radius:999px;overflow:hidden;background:var(--card2);border:1px solid var(--border);transform-origin:left;animation:grow .4s ease-out both}}
.legend span{{display:inline-flex;align-items:center;gap:6px;margin-right:14px;font-size:.82rem;color:var(--muted)}}
.legend i{{width:12px;height:12px;border-radius:3px;display:inline-block}}
.diff{{display:grid;grid-template-columns:1.3fr 1fr auto 1fr;gap:6px 10px;align-items:center}}
.diff .new{{font-weight:700;border-radius:6px;padding:2px 6px;animation:flash .4s ease-out both}}
.muted{{color:var(--muted)}} .h{{font-size:1.1rem;font-weight:700;margin-bottom:6px}}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important;transition:none!important}}}}
</style>"""


def e(x):
    return escape(str(x))


def chip(text, kind="mute"):
    return f'<span class="chip {kind}">{e(text)}</span>'


def kpi(label, value, sub="", count=False):
    v = (f'<span class="count" style="--n:{int(value)}"></span>' if count and isinstance(value, (int, float))
         else e(value))
    return f'<div class="kpi"><div class="l">{e(label)}</div><div class="v">{v}</div><div class="s">{e(sub)}</div></div>'


def table(rows, cols):
    head = "".join(f"<th>{e(c)}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{r.get(c, '') if str(r.get(c, '')).startswith('<span') else e(r.get(c, ''))}</td>"
                                     for c in cols) + "</tr>" for r in rows)
    return f'<table class="tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


STATUS_CHIP = {"accepted": "ok", "partly accepted": "warn", "rejected": "bad", "superseded": "mute",
               "noted": "info", "optional": "info", "irrelevant": "mute", "needs review": "warn", "pending": "warn"}
