#!/usr/bin/env python3
"""Gera o terminal animado (estilo neofetch) do README do perfil.

Cria assets/terminal-dark.svg e assets/terminal-light.svg, mais os botões de links.
Estatísticas vêm da API GraphQL do GitHub:

    GITHUB_TOKEN=$(gh auth token) python3 scripts/terminal.py
    python3 scripts/terminal.py --demo     # prévia com números de exemplo, sem token

Só usa a biblioteca padrão do Python.
"""

import datetime as dt
import json
import os
import sys
import urllib.request
from collections import Counter
from html import escape
from pathlib import Path

# ============================================================================
# EDITE AQUI
# ============================================================================
USER = "cjdotcom"             # seu login no GitHub
NAME = "Gabriel"                 # aparece no `whoami` e no título
SHELL = "zsh"

PLAN = [                      # saída do `cat ~/.plan` (1 a 3 linhas curtas)
    "Desenvolvedor de Software focado em soluções práticas e bem arquitetadas.",
    "Gosto de resolver problemas reais com código limpo, reutilizável e performático.",
]

INFO = [                      # linhas fixas do neofetch: (rótulo, [itens])
    ("Código", ["Python", "JavaScript", "TypeScript", "SQL"]),
    ("Stack",  ["Node.js", "React Native", "Flask"]),
    ("Bancos", ["PostgreSQL", "SQL Server"]),
    ("Infra",  ["Git", "Docker", "Railway", "AWS"]),
    ("Local",  ["Brasil"]),
]

LINKS = [                     # botões abaixo do terminal: (arquivo, texto, url)
    # ("linkedin", "linkedin", "https://www.linkedin.com/in/seu-usuario"),
]

# Conteúdo extra no fim do README (aqui: a animação da cobrinha)
README_EXTRA = """
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/cjdotcom/cjdotcom/output/github-contribution-grid-snake-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/cjdotcom/cjdotcom/output/github-contribution-grid-snake.svg">
  <img alt="Animação da cobrinha comendo o gráfico de contribuições" src="https://raw.githubusercontent.com/cjdotcom/cjdotcom/output/github-contribution-grid-snake.svg">
</picture>
"""

# Comando final "divertido": (comando, cabeçalhos, valores [(texto, cor)])
EXTRA = ("docker ps --filter name=cafe",
         ["CONTAINER", "IMAGE", "STATUS", "PORTS"],
         [("a1b2c3", "text"), ("cafe:coado", "text"), ("Up {years} anos", "green"), ("0.0.0.0:8080", "peach")])
# ============================================================================

ASSETS = Path(__file__).resolve().parent.parent / "assets"
IGNORED_LANGUAGES = {"HTML", "CSS", "SCSS", "Makefile", "Dockerfile", "Jupyter Notebook"}

# Paleta Catppuccin (https://catppuccin.com/palette): mocha = escuro, latte = claro
THEMES = {
    "dark": dict(red="#f38ba8", peach="#fab387", yellow="#f9e2af", green="#a6e3a1", teal="#94e2d5",
                 sky="#89dceb", sapphire="#74c7ec", blue="#89b4fa", lavender="#b4befe", mauve="#cba6f7",
                 pink="#f5c2e7", flamingo="#f2cdcd", rosewater="#f5e0dc", maroon="#eba0ac",
                 text="#cdd6f4", subtext="#bac2de", dim="#a6adc8", muted="#7f849c", faint="#6c7086",
                 line="#313244", base="#1e1e2e", bar="#181825", ink="#11111b"),
    "light": dict(red="#d20f39", peach="#fe640b", yellow="#df8e1d", green="#40a02b", teal="#179299",
                  sky="#04a5e5", sapphire="#209fb5", blue="#1e66f5", lavender="#7287fd", mauve="#8839ef",
                  pink="#ea76cb", flamingo="#dd7878", rosewater="#dc8a78", maroon="#e64553",
                  text="#4c4f69", subtext="#5c5f77", dim="#6c6f85", muted="#8c8fa1", faint="#9ca0b0",
                  line="#ccd0da", base="#eff1f5", bar="#e6e9ef", ink="#4c4f69"),
}
SWATCHES = ["red", "peach", "yellow", "green", "teal", "sky", "sapphire", "blue",
            "lavender", "mauve", "pink", "flamingo", "rosewater", "maroon"]
LANG_COLORS = {"Python": "green", "Go": "sapphire", "TypeScript": "blue", "JavaScript": "yellow",
               "Rust": "peach", "Java": "red", "Shell": "teal", "C#": "mauve", "PHP": "lavender"}

# Logo em pixel-art: um tríscele (símbolo celta). 'X' = preenchido
LOGO = [
    ".........XXXXXX.........",
    "........XXX..XXXX.......",
    ".......XXX.....XX.......",
    ".......XX..XX...XX......",
    ".......XX.XXXX..XX......",
    ".......XX..X.XX.XX......",
    ".......XX....XX.XX......",
    "........XXXXXX..XX......",
    ".........XXXX...XX......",
    "...............XX.......",
    "....XXXXX....XXX........",
    "..XXXXXXXXXXXXX.........",
    ".XXX.....XXXXX...XXXXX..",
    ".XX...X...XXXX..XX..XXX.",
    "XX..XXXXX..XXX.XX....XXX",
    "XX.XXX.XXX.XX..XX.XX..XX",
    "XX.XX...XX..XX.XX..XX.XX",
    "XX..XX..XX..XX..XXXX..XX",
    "XX......XX..XX...XX...XX",
    ".XX....XX....XX......XX.",
    "..XXXXXXX.....XXXXXXXX..",
    "....XXX........XXXXXX...",
]


def logo_colors(p):
    return {"X": "#ffffff" if p["base"] == "#1e1e2e" else "#000000"}


# --- dados ------------------------------------------------------------------

def graphql(token, query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": f"{USER}-terminal"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    for err in body.get("errors", []):
        print(f"aviso: {err.get('message')}", file=sys.stderr)
    if not body.get("data"):
        sys.exit("A consulta GraphQL não retornou dados")
    return body["data"]


def fetch_stats(token, now):
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    user = graphql(token, f'{{ user(login: "{USER}") {{ createdAt '
                          f'repositories(ownerAffiliations: OWNER, privacy: PUBLIC) {{ totalCount }} '
                          f'followers {{ totalCount }} }} }}')["user"]
    created = dt.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))

    years = range(created.year, now.year + 1)
    blocks = "\n".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", '
        f'to: "{iso(min(now, dt.datetime(y, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)))}") '
        f'{{ contributionCalendar {{ totalContributions weeks {{ contributionDays {{ date contributionCount }} }} }} }}'
        for y in years)
    data = graphql(token, f"""{{ user(login: "{USER}") {{
      {blocks}
      recent: contributionsCollection(from: "{iso(now - dt.timedelta(days=365))}", to: "{iso(now)}") {{
        commitContributionsByRepository(maxRepositories: 100) {{
          contributions {{ totalCount }}
          repository {{ isFork languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{ edges {{ size node {{ name }} }} }} }}
        }}
      }}
    }} }}""")["user"]

    days = {}
    for y in years:
        for week in data[f"y{y}"]["contributionCalendar"]["weeks"]:
            for d in week["contributionDays"]:
                days[dt.date.fromisoformat(d["date"])] = d["contributionCount"]

    day = now.date()
    if not days.get(day):              # hoje ainda não acabou
        day -= dt.timedelta(days=1)
    streak = 0
    while days.get(day):
        streak += 1
        day -= dt.timedelta(days=1)
    best = run = 0
    for d in sorted(days):
        run = run + 1 if days[d] else 0
        best = max(best, run)

    weights = Counter()
    for item in data["recent"]["commitContributionsByRepository"]:
        repo = item["repository"]
        if not repo or repo["isFork"]:
            continue
        edges = [e for e in repo["languages"]["edges"] if e["node"]["name"] not in IGNORED_LANGUAGES]
        total = sum(e["size"] for e in edges) or 1
        for e in edges:
            weights[e["node"]["name"]] += item["contributions"]["totalCount"] * e["size"] / total
    total = sum(weights.values()) or 1

    return {
        "created": created,
        "repos": user["repositories"]["totalCount"],
        "followers": user["followers"]["totalCount"],
        "contributions": data[f"y{now.year}"]["contributionCalendar"]["totalContributions"],
        "streak": streak,
        "best": best,
        "languages": [(n, w / total) for n, w in weights.most_common()],
    }


def demo_stats(now):
    return {"created": now - dt.timedelta(days=365 * 5 + 120), "repos": 27, "followers": 42,
            "contributions": 812, "streak": 9, "best": 31,
            "languages": [("Python", .52), ("TypeScript", .21), ("Go", .12), ("Shell", .08), ("SQL", .04)]}


def plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


def uptime(created, now):
    months = (now.year - created.year) * 12 + now.month - created.month - (now.day < created.day)
    y, m = divmod(months, 12)
    return f"{plural(y, 'ano', 'anos')}, {plural(m, 'mês', 'meses')}" if m else plural(y, "ano", "anos")


# --- desenho ----------------------------------------------------------------

W, PAD, FS, LH, CH = 880, 28, 14, 21, 8.7
CELL = 216 // len(LOGO[0])   # tamanho de cada pixel do logo
TYPE = 0.065
FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', 'DejaVu Sans Mono', monospace")
STYLE = f"""
text {{ font-family: {FONT}; font-size: {FS}px; white-space: pre; }}
.b {{ font-weight: 700; }}
.a {{ opacity: 0; animation: on .01s linear forwards; }}
.cur {{ animation: on .01s linear forwards, blink 1.1s steps(1) infinite; }}
@keyframes on {{ to {{ opacity: 1; }} }}
@keyframes blink {{ 50% {{ opacity: 0; }} }}
@media (prefers-reduced-motion: reduce) {{ .a {{ animation: none !important; opacity: 1; }} }}
"""


def delay(t):
    return f' class="a" style="animation-delay:{t:.2f}s"'


def span(text, fill, bold=False):
    weight = ' class="b"' if bold else ""
    return f'<tspan fill="{fill}"{weight}>{escape(text)}</tspan>'


class Screen:
    def __init__(self, p):
        self.p, self.out, self.y, self.t = p, [], 70, 0.5

    def cmd(self, command, cursor=False):
        p, start = self.p, self.t
        parts = [span("~", p["sapphire"], True), span(" ❯ ", p["green"], True)]
        for i, ch in enumerate(command):
            self.t += TYPE * (0.6 + (i * 7 % 5) / 5)
            parts.append(f'<tspan fill="{p["text"]}"{delay(self.t)}>{escape(ch)}</tspan>')
        if cursor:
            parts.append(f'<tspan fill="{p["rosewater"]}" class="a cur" '
                         f'style="animation-delay:{self.t:.2f}s,{self.t:.2f}s">█</tspan>')
        self.out.append(f'<text x="{PAD}" y="{self.y}"{delay(start)}>{"".join(parts)}</text>')
        self.y += LH
        self.t += 0.35

    def line(self, *parts, x=PAD, step=0.06):
        self.out.append(f'<text x="{x}" y="{self.y}"{delay(self.t)}>{"".join(parts)}</text>')
        self.y += LH
        self.t += step

    def gap(self, pause=0.3):
        self.y += LH * 0.6
        self.t += pause


def render(theme, s, now):
    p = THEMES[theme]
    sc = Screen(p)
    label = lambda t: span(t, p["peach"] if theme == "dark" else p["maroon"], True)
    val = lambda t, c="text": span(t, p[c])
    dot = val(" · ", "faint")
    joined = lambda items: [x for i, it in enumerate(items) for x in ([dot] if i else []) + [val(it)]]

    sc.cmd("whoami")
    sc.line(val(NAME))
    sc.gap(0.2)

    sc.cmd("cat ~/.plan")
    for row in PLAN:
        sc.line(val(row, "subtext"))
    sc.gap()

    sc.cmd("neofetch")
    top, start = sc.y - FS, sc.t

    colors = logo_colors(p)
    for r, row in enumerate(LOGO):
        rects = "".join(f'<rect x="{PAD + c * CELL}" y="{top + r * CELL}" width="{CELL - 1}" '
                        f'height="{CELL - 1}" rx="1.5" fill="{colors[k]}"/>'
                        for c, k in enumerate(row) if k != ".")
        if rects:
            sc.out.append(f'<g{delay(start + r * 0.02)}>{rects}</g>')

    x = PAD + len(LOGO[0]) * CELL + 40
    vx = x + 10 * CH
    rows = [(k, joined(v)) for k, v in INFO] + [
        ("Uptime", [val(uptime(s["created"], now)), val(" no GitHub", "muted")]),
        ("Repos", [val(f"{s['repos']} públicos"), dot, val(plural(s["followers"], "seguidor", "seguidores"))]),
        ("Shell", [val(SHELL)]),
        ("Commits", [val(f"{s['contributions']:,}".replace(",", "."), "green"), val(f" em {now.year}")]),
        ("Streak", [val(plural(s["streak"], "dia", "dias"), "green"), dot, val(f"recorde {s['best']}")]),
    ]
    sc.y, sc.t = top + FS, start
    sc.line(span(NAME, p["mauve"], True), val("@"), span(USER, p["mauve"], True), x=x)
    sc.y -= 6
    sc.line(val("─" * len(f"{NAME}@{USER}"), "faint"), x=x)
    sc.y += 2
    for k, parts in rows:
        sc.line(label(k), f'<tspan x="{vx}">{"".join(parts)}</tspan>', x=x)

    langs = list(s["languages"][:5])
    if langs:
        shown = sum(v for _, v in langs)
        if shown < 0.995:
            langs.append(("outras", 1 - shown))
        pool = iter(c for c in SWATCHES if c not in LANG_COLORS.values())
        fills = {n: p["faint"] if n == "outras" else p[LANG_COLORS.get(n) or next(pool)] for n, _ in langs}
        bar_w = W - PAD - vx
        sc.line(label("Langs"), x=x, step=0)
        by, bx, segs = sc.y - LH - 10, vx, []
        for n, share in langs:
            segs.append(f'<rect x="{bx:.1f}" y="{by}" width="{bar_w * share:.1f}" height="10" fill="{fills[n]}"/>')
            bx += bar_w * share
        sc.out.append(f'<clipPath id="bar"><rect x="{vx}" y="{by}" width="{bar_w}" height="10" rx="5"/></clipPath>'
                      f'<g clip-path="url(#bar)"{delay(sc.t)}>{"".join(segs)}</g>')
        sc.t += 0.06
        legend, lx = [], vx
        for n, share in langs:
            item = f"● {n} {share * 100:.0f}%"
            if legend and lx + len(item) * CH > W - PAD:
                sc.line(*legend, x=vx)
                legend, lx = [], vx
            legend.append(f'<tspan x="{lx:.1f}" fill="{fills[n]}">●</tspan>{span(item[1:], p["dim"])}')
            lx += len(item) * CH + 18
        sc.line(*legend, x=vx)

    sc.y += 6
    sc.out.append(f'<g{delay(sc.t)}>' + "".join(
        f'<rect x="{x + i * 24}" y="{sc.y - FS}" width="24" height="16" fill="{p[c]}"/>'
        for i, c in enumerate(SWATCHES)) + "</g>")
    sc.y = max(sc.y + LH, top + len(LOGO) * CELL + FS)
    sc.t = max(sc.t, start + len(LOGO) * 0.02)
    sc.gap()

    if EXTRA:
        command, header, cells = EXTRA
        years = str(max(1, (now - s["created"]).days // 365))
        cols, c = [], 0
        for h, (v, _) in zip(header, cells):
            cols.append(c)
            c += max(len(h), len(v.format(years=years))) + 3
        sc.cmd(command)
        sc.line(*(f'<tspan x="{PAD + c * CH:.1f}" fill="{p["muted"]}">{escape(h)}</tspan>'
                  for c, h in zip(cols, header)))
        sc.line(*(f'<tspan x="{PAD + c * CH:.1f}" fill="{p[col]}">{escape(v.format(years=years))}</tspan>'
                  for c, (v, col) in zip(cols, cells)))
        sc.gap()

    sc.cmd("", cursor=True)

    h = sc.y + 12
    title = f"{NAME}@{USER}: ~ — {SHELL}"
    lights = "".join(f'<circle cx="{22 + i * 20}" cy="20" r="6" fill="{p[c]}"/>'
                     for i, c in enumerate(["red", "yellow", "green"]))
    desc = f"Terminal rodando neofetch para {NAME} ({USER}). " + " ".join(PLAN)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-labelledby="t d" xml:space="preserve">
<title id="t">{escape(USER)} — neofetch</title>
<desc id="d">{escape(desc)}</desc>
<style>{STYLE}</style>
<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="12" fill="{p['base']}" stroke="{p['line']}"/>
<path d="M.5 40V12.5A12 12 0 0 1 12.5 .5h{W - 25}a12 12 0 0 1 12 12V40z" fill="{p['bar']}"/>
<line x1=".5" y1="40" x2="{W - .5}" y2="40" stroke="{p['line']}"/>
{lights}
<text x="{W / 2}" y="25" text-anchor="middle" fill="{p['muted']}" style="font-size:12px">{escape(title)}</text>
{chr(10).join(sc.out)}
</svg>
"""


def button(theme, text):
    p = THEMES[theme]
    w = round(len(text) * CH + 62)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="34" viewBox="0 0 {w} 34" role="img" aria-label="{escape(text)}">
<style>text {{ font-family: {FONT}; font-size: 14px; }}</style>
<rect x=".5" y=".5" width="{w - 1}" height="33" rx="8" fill="{p['bar']}" stroke="{p['line']}"/>
<text x="16" y="22"><tspan fill="{p['green']}" font-weight="700">❯</tspan><tspan fill="{p['text']}" dx="8">{escape(text)}</tspan><tspan fill="{p['muted']}" dx="8">↗</tspan></text>
</svg>
"""


def picture(file, alt, height=None):
    base = f"https://github.com/{USER}/{USER}/raw/main/assets"
    size = f'height="{height}"' if height else 'width="100%"'
    return (f'<picture>\n'
            f'  <source media="(prefers-color-scheme: dark)" srcset="{base}/{file}-dark.svg">\n'
            f'  <source media="(prefers-color-scheme: light)" srcset="{base}/{file}-light.svg">\n'
            f'  <img src="{base}/{file}-dark.svg" {size} alt="{escape(alt)}">\n'
            f'</picture>')


def readme():
    info = ". ".join(f"{k}: {', '.join(v)}" for k, v in INFO)
    alt = f"Terminal rodando neofetch para {NAME} ({USER}). {' '.join(PLAN)} {info}."
    buttons = "&nbsp;\n".join(f'<a href="{url}">{picture(key, text, 34)}</a>' for key, text, url in LINKS)
    return (f"<!-- Gerado por scripts/terminal.py e atualizado diariamente por "
            f".github/workflows/terminal.yml. Edite o script, não este arquivo. -->\n"
            f'<div align="center">\n\n{picture("terminal", alt)}\n\n{buttons}\n{README_EXTRA}\n</div>\n')


def main():
    now = dt.datetime.now(dt.timezone.utc)
    if "--demo" in sys.argv:
        stats = demo_stats(now)
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("Defina GITHUB_TOKEN (ou rode com --demo para uma prévia).")
        stats = fetch_stats(token, now)
    ASSETS.mkdir(exist_ok=True)
    for theme in THEMES:
        (ASSETS / f"terminal-{theme}.svg").write_text(render(theme, stats, now))
        for key, text, _ in LINKS:
            (ASSETS / f"{key}-{theme}.svg").write_text(button(theme, text))
    (ASSETS.parent / "README.md").write_text(readme())
    print(f"commits {stats['contributions']} · streak {stats['streak']} (recorde {stats['best']})")


if __name__ == "__main__":
    main()
