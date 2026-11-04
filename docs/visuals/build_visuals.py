#!/usr/bin/env python3
"""Generate the animated SVG diagrams used in the README and docs.

The SVGs are build products: edit this file, then run
    python3 docs/visuals/build_visuals.py
Never hand-edit the .svg files.

Motion rules (why the animations look the way they do):
  * CSS animations only, no SMIL, so `prefers-reduced-motion: reduce` can switch
    every animation off. With motion off, each diagram shows its complete,
    readable final state: animation only ever adds emphasis, never content.
  * One idea per animation: a cycle, a progression, a filter, a loop. Slow
    loops (8-16 s) so the README never feels busy.
  * Light and dark palettes via `prefers-color-scheme`, matching GitHub's theme.
  * Type is Atkinson Hyperlegible (Braille Institute, SIL OFL 1.1; see fonts/), chosen for
    legibility. GitHub shows README SVGs as images, which cannot load web fonts, so a small
    Latin subset (regular and bold) is embedded in each file. fonts/ holds the subsets and the licence.
"""
from __future__ import annotations

import base64
from pathlib import Path

OUT = Path(__file__).resolve().parent
FONTS = OUT / "fonts"


def font_face() -> str:
    faces = []
    for weight in (400, 700):
        data = base64.b64encode((FONTS / f"atkinson-hyperlegible-{weight}-subset.woff2").read_bytes()).decode()
        faces.append(f"@font-face {{ font-family: 'Atkinson Hyperlegible'; font-style: normal; font-weight: {weight}; "
                     f"src: url(data:font/woff2;base64,{data}) format('woff2'); }}")
    return "\n  ".join(faces)

PALETTE = """
  :root, svg { --bg:#fbfaf7; --panel:#ffffff; --ink:#1d1d1b; --muted:#6b6a66; --line:#e2dfd7;
    --accent:#2f5bd3; --accent-soft:#e6ecfb; --ok:#1e7a44; --ok-soft:#e3f3e9; --warn:#a36500; --warn-soft:#fdf0d6;
    --fail:#b3261e; --fail-soft:#fbe6e3; }
  @media (prefers-color-scheme: dark) {
    :root, svg { --bg:#0d1117; --panel:#161b22; --ink:#e6edf3; --muted:#8d96a0; --line:#30363d;
      --accent:#7ea2ff; --accent-soft:#1b2a4d; --ok:#56d38a; --ok-soft:#12301f; --warn:#f2c26b; --warn-soft:#3a2c10;
      --fail:#ff8a80; --fail-soft:#3d1a17; }
  }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
  text { font-family: 'Atkinson Hyperlegible', ui-sans-serif, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; fill: var(--ink); }
  .muted { fill: var(--muted); }
  .bg { fill: var(--bg); }
"""


def svg(w: int, h: int, title: str, desc: str, style: str, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="t d">\n<title id="t">{title}</title>\n<desc id="d">{desc}</desc>\n'
            f'<style>\n  {font_face()}{PALETTE}{style}</style>\n<rect class="bg" width="{w}" height="{h}" rx="16"/>\n{body}\n</svg>\n')


# ------------------------------------------------------------------ hero: five parts on a ring
def hero() -> str:
    import math
    cx, cy, r = 820, 220, 130
    parts = [("Rails", "what output stays inside"), ("Memory", "truth between sessions"),
             ("Moves", "the workflow itself"), ("Checks", "sensors, then a judge"),
             ("Loop", "every miss, a fix")]
    period = 10.0
    nodes = []
    for i, (name, sub) in enumerate(parts):
        a = -math.pi / 2 + i * 2 * math.pi / len(parts)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        lx = x + (24 if math.cos(a) > 0.2 else -24 if math.cos(a) < -0.2 else 0)
        anchor = "start" if math.cos(a) > 0.2 else "end" if math.cos(a) < -0.2 else "middle"
        ly = y - 46 if math.sin(a) < -0.5 else y + 44 if math.sin(a) > 0.5 else y + 6
        if anchor != "middle":
            ly = y - 4
        delay = i * period / len(parts)
        nodes.append(
            f'<g class="node" style="animation-delay:{delay:.2f}s">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="17" class="dot"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="17" class="halo" style="animation-delay:{delay:.2f}s;transform-origin:{x:.1f}px {y:.1f}px"/>'
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" class="label">{name}</text>'
            f'<text x="{lx:.1f}" y="{ly + 20:.1f}" text-anchor="{anchor}" class="sub muted">{sub}</text></g>')
    style = f"""
  .ring {{ fill:none; stroke:var(--line); stroke-width:2; }}
  .ring-flow {{ fill:none; stroke:var(--accent); stroke-width:2; stroke-dasharray:6 14; animation: flow 6s linear infinite; }}
  .dot {{ fill:var(--panel); stroke:var(--accent); stroke-width:2.5; }}
  .halo {{ fill:var(--accent); opacity:.0; animation: halo {period}s ease-out infinite; }}
  .orbit {{ transform-origin:{cx}px {cy}px; animation: spin {period}s linear infinite; }}
  .orbit circle {{ fill:var(--accent); }}
  .label {{ font-size:20px; font-weight:650; }}
  .sub {{ font-size:14px; }}
  .h1 {{ font-size:46px; font-weight:750; letter-spacing:-.5px; }}
  .lede {{ font-size:19px; }}
  .chip {{ fill:var(--accent-soft); }}
  .chiptext {{ font-size:14px; font-weight:600; fill:var(--accent); }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  @keyframes flow {{ to {{ stroke-dashoffset:-40; }} }}
  @keyframes halo {{ 0% {{ opacity:.35; transform:scale(1); }} 18% {{ opacity:0; transform:scale(2.1); }} 100% {{ opacity:0; transform:scale(2.1); }} }}
"""
    body = f"""
<text x="64" y="150" class="h1">Harness Atelier</text>
<text x="64" y="194" class="lede muted">A Claude skill that builds the harness around the AI,</text>
<text x="64" y="222" class="lede muted">fitted to how a designer or team really works.</text>
<rect x="64" y="258" width="196" height="34" rx="17" class="chip"/><text x="162" y="280" text-anchor="middle" class="chiptext">interview → map → build</text>
<rect x="272" y="258" width="168" height="34" rx="17" class="chip"/><text x="356" y="280" text-anchor="middle" class="chiptext">verified, not assumed</text>
<circle cx="{cx}" cy="{cy}" r="{r}" class="ring"/>
<circle cx="{cx}" cy="{cy}" r="{r}" class="ring-flow"/>
<g class="orbit"><circle cx="{cx}" cy="{cy - r}" r="6"/></g>
{''.join(nodes)}
"""
    return svg(1200, 440, "Harness Atelier: five parts of a design harness",
               "A ring of five parts, Rails, Memory, Moves, Checks and Loop, with a marker travelling around it. "
               "Each part lights up as the marker passes.", style, body)


# ------------------------------------------------------------------ workflow: seven phases
def workflow() -> str:
    phases = [("0", "Look", "inventory first"), ("1", "Interview", "a real project"), ("2", "Map", "sign-off here"),
              ("3", "Generate", "never overwrites"), ("4", "Tailor", "failures → fixes"), ("5", "Verify", "run, don't claim"),
              ("6", "Hand over", "open questions")]
    n = len(phases)
    x0, x1, y = 90, 1110, 128
    step = (x1 - x0) / (n - 1)
    period = 14.0
    items = []
    for i, (num, name, sub) in enumerate(phases):
        x = x0 + i * step
        d = i * (period * 0.7) / (n - 1)
        key = " key" if name == "Map" else ""
        items.append(
            f'<g class="ph{key}"><circle cx="{x:.1f}" cy="{y}" r="24" class="pc" style="animation-delay:{d:.2f}s"/>'
            f'<text x="{x:.1f}" y="{y + 7}" text-anchor="middle" class="pn" style="animation-delay:{d:.2f}s">{num}</text>'
            f'<text x="{x:.1f}" y="{y + 62}" text-anchor="middle" class="pname">{name}</text>'
            f'<text x="{x:.1f}" y="{y + 84}" text-anchor="middle" class="psub muted">{sub}</text></g>')
    length = x1 - x0
    style = f"""
  .track {{ stroke:var(--line); stroke-width:4; stroke-linecap:round; }}
  .fill {{ stroke:var(--accent); stroke-width:4; stroke-linecap:round; stroke-dasharray:{length}; stroke-dashoffset:0;
          animation: grow {period}s ease-in-out infinite; }}
  .pc {{ fill:var(--accent); stroke:var(--accent); stroke-width:2; animation: light {period}s ease-in-out infinite backwards; }}
  .pn {{ font-size:18px; font-weight:700; fill:var(--panel); animation: lightn {period}s ease-in-out infinite backwards; }}
  .key .pc {{ stroke-width:5; }}
  .pname {{ font-size:19px; font-weight:650; }}
  .psub {{ font-size:14px; }}
  .cap {{ font-size:15px; font-weight:600; fill:var(--accent); }}
  @keyframes grow {{ 0% {{ stroke-dashoffset:{length}; }} 70% {{ stroke-dashoffset:0; }} 92% {{ stroke-dashoffset:0; opacity:1; }} 100% {{ stroke-dashoffset:0; opacity:0; }} }}
  @keyframes light {{ 0% {{ fill:var(--panel); }} 6% {{ fill:var(--accent); }} 92% {{ fill:var(--accent); }} 100% {{ fill:var(--panel); }} }}
  @keyframes lightn {{ 0% {{ fill:var(--accent); }} 6% {{ fill:var(--panel); }} 92% {{ fill:var(--panel); }} 100% {{ fill:var(--accent); }} }}
"""
    mapx = x0 + 2 * step
    body = f"""
<text x="{x0 - 24}" y="52" class="pname">Seven phases, one build</text>
<text x="{mapx:.1f}" y="{y - 44}" text-anchor="middle" class="cap">cheapest moment to correct</text>
<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" class="track"/>
<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" class="fill"/>
{''.join(items)}
"""
    return svg(1200, 250, "The seven phases of a harness build",
               "Look, Interview, Map, Generate, Tailor, Verify, Hand over. A progress line fills from left to right and "
               "each phase lights up in turn. Map is marked as the cheapest moment to correct the structure.", style, body)


# ------------------------------------------------------------------ checks: three filters
def checks() -> str:
    period = 9.0
    lanes = [  # (y, stops_at, kind)
        (118, 1, "fail"), (150, 3, "ok"), (182, 2, "warn"), (214, 3, "ok"), (246, 1, "fail"), (278, 3, "ok")]
    gates = [(330, "Sensors", "deterministic, cheap", "placeholders · schema · leaks · off-system values"),
             (640, "Evaluator", "a separate agent", "scope · research fit · rails · a11y · taste"),
             (950, "People", "judgement only", "lead → leadership → client")]
    stop_x = {1: 300, 2: 610, 3: 1110}
    style = f"""
  .gate {{ fill:var(--panel); stroke:var(--line); stroke-width:1.5; }}
  .gname {{ font-size:19px; font-weight:650; }}
  .gsub {{ font-size:14px; }}
  .gdet {{ font-size:13px; }}
  .item {{ animation-duration:{period}s; animation-iteration-count:infinite; animation-timing-function:cubic-bezier(.5,0,.3,1); animation-fill-mode:backwards; }}
  .ok {{ fill:var(--ok); }} .warn {{ fill:var(--warn); }} .fail {{ fill:var(--fail); }}
  .h {{ font-size:22px; font-weight:700; }}
  .bar {{ fill:var(--accent); opacity:.85; }}
""" + "".join(
        f"  @keyframes go{i} {{ 0% {{ transform:translateX(0); opacity:0; }} 6% {{ opacity:1; }} "
        f"55% {{ transform:translateX({stop_x[s] - 70}px); opacity:1; }} 80% {{ transform:translateX({stop_x[s] - 70}px); opacity:{1 if s == 3 else .25}; }} "
        f"100% {{ transform:translateX({stop_x[s] - 70}px); opacity:0; }} }}\n"
        for i, (_, s, _) in enumerate(lanes))
    gate_svg = "".join(
        f'<rect x="{x}" y="96" width="14" height="206" rx="7" class="bar"/>'
        f'<text x="{x + 7}" y="330" text-anchor="middle" class="gname">{n}</text>'
        f'<text x="{x + 7}" y="350" text-anchor="middle" class="gsub muted">{s}</text>'
        f'<text x="{x + 7}" y="372" text-anchor="middle" class="gdet muted">{d}</text>'
        for x, n, s, d in gates)
    items = "".join(
        f'<rect x="70" y="{y - 9}" width="18" height="18" rx="4" class="item {k}" '
        f'style="animation-name:go{i};animation-delay:{i * 0.35:.2f}s;transform:translateX({stop_x[s] - 70}px)"/>'
        for i, (y, s, k) in enumerate(lanes))
    body = f"""
<text x="56" y="56" class="h">Problems stop at the cheapest gate that can catch them</text>
<text x="56" y="80" class="gsub muted">red: caught by a script · amber: caught by the evaluator · green: reaches people, ready for review</text>
{gate_svg}
{items}
"""
    return svg(1200, 400, "The check ladder: sensors, evaluator, people",
               "Pieces of work move right through three gates. Some stop at the deterministic sensors, some at the "
               "separate evaluator agent, and only clean work reaches the human reviewers.", style, body)


# ------------------------------------------------------------------ loop: miss becomes a fix
def loop() -> str:
    rows = [("Same comment, two review rounds", "a rule in CLAUDE.md or ux-context"),
            ("One-off UI built twice", "a component in system/"),
            ("A grep could have caught it", "a sensor in harness_check.py"),
            ("Only judgement catches it", "a line in the gate rubric"),
            ("Someone re-explains context", "a line in the brief or ux-context"),
            ("A rule quietly stops holding", "an eval case, re-run until 3 of 3")]
    period = 12.5
    each = period / len(rows)
    rws = []
    for i, (miss, fix) in enumerate(rows):
        y = 112 + i * 44
        d = i * each
        rws.append(
            f'<g class="row" style="animation-delay:{d:.2f}s">'
            f'<rect x="420" y="{y - 26}" width="720" height="38" rx="10" class="rowbg" style="animation-delay:{d:.2f}s"/>'
            f'<text x="440" y="{y}" class="miss">{miss}</text>'
            f'<text x="770" y="{y}" class="arrow muted">→</text>'
            f'<text x="800" y="{y}" class="fix">{fix}</text></g>')
    style = f"""
  .circ {{ fill:none; stroke:var(--line); stroke-width:10; }}
  .circflow {{ fill:none; stroke:var(--accent); stroke-width:10; stroke-linecap:round; stroke-dasharray:90 450;
              transform-origin:200px 210px; animation: rot 6s linear infinite; }}
  .ctext {{ font-size:20px; font-weight:700; }}
  .csub {{ font-size:14px; }}
  .h {{ font-size:22px; font-weight:700; }}
  .miss {{ font-size:16px; }}
  .fix {{ font-size:16px; font-weight:650; fill:var(--accent); }}
  .arrow {{ font-size:18px; }}
  .rowbg {{ fill:var(--accent-soft); opacity:0; animation: hl {period}s ease-in-out infinite; }}
  @keyframes rot {{ to {{ transform: rotate(360deg); }} }}
  @keyframes hl {{ 0% {{ opacity:0; }} 4% {{ opacity:1; }} 18% {{ opacity:1; }} 24% {{ opacity:0; }} 100% {{ opacity:0; }} }}
"""
    body = f"""
<circle cx="200" cy="210" r="86" class="circ"/>
<circle cx="200" cy="210" r="86" class="circflow"/>
<text x="200" y="206" text-anchor="middle" class="ctext">a miss</text>
<text x="200" y="230" text-anchor="middle" class="csub muted">becomes a fix,</text>
<text x="200" y="248" text-anchor="middle" class="csub muted">not a reminder</text>
<text x="420" y="56" class="h">The learning loop</text>
{''.join(rws)}
"""
    return svg(1200, 390, "The learning loop: every miss becomes a permanent fix",
               "A rotating loop labelled 'a miss becomes a fix, not a reminder' beside five rows that light up in turn: "
               "a repeated comment becomes a rule, a repeated one-off UI a component, a greppable problem a sensor, "
               "a judgement problem a rubric line, re-explained context a line in the brief, and a rule that stops holding an eval case.", style, body)


# ------------------------------------------------------------------ evals: the harness checks itself
def evals() -> str:
    rows = [("Scripts", "sensors, guard, records and dashboard give the right result", "free, seconds"),
            ("Behaviour", "Claude follows the rules in a throwaway copy, 3 runs each", "a few dollars"),
            ("Gate", "catches planted problems; invents none on a clean copy", "per project"),
            ("Flows", "no unlinked boxes, no dead ends, labelled branches", "per project")]
    period = 10.0
    dots, labels = [], []
    for r, (name, what, cost) in enumerate(rows):
        y = 124 + r * 58
        labels.append(f'<text x="56" y="{y}" class="name">{name}</text>'
                      f'<text x="56" y="{y + 20}" class="what muted">{what}</text>'
                      f'<text x="1144" y="{y + 10}" text-anchor="end" class="cost muted">{cost}</text>')
        for k in range(3):
            d = r * 0.9 + k * 0.45
            anim = "flip" if (r, k) == (1, 1) else "pass"
            dots.append(f'<circle cx="{780 + k * 44}" cy="{y + 4}" r="13" class="dot" style="animation-name:{anim};animation-delay:{d:.2f}s"/>')
    style = f"""
  .h {{ font-size:22px; font-weight:700; }}
  .sub {{ font-size:14px; }}
  .name {{ font-size:18px; font-weight:700; }}
  .what {{ font-size:14px; }}
  .cost {{ font-size:13px; }}
  .runs {{ font-size:13px; }}
  .dot {{ fill:var(--ok); animation-duration:{period}s; animation-iteration-count:infinite; animation-fill-mode:backwards; }}
  .note {{ font-size:13px; fill:var(--fail); opacity:0; animation: note {period}s ease-in-out infinite; animation-delay:1.35s; }}
  @keyframes pass {{ 0% {{ fill:var(--line); }} 8% {{ fill:var(--ok); }} 100% {{ fill:var(--ok); }} }}
  @keyframes flip {{ 0% {{ fill:var(--line); }} 8% {{ fill:var(--fail); }} 40% {{ fill:var(--fail); }} 48% {{ fill:var(--ok); }} 100% {{ fill:var(--ok); }} }}
  @keyframes note {{ 0% {{ opacity:0; }} 8% {{ opacity:1; }} 40% {{ opacity:1; }} 48% {{ opacity:0; }} 100% {{ opacity:0; }} }}
"""
    body = f"""
<text x="56" y="56" class="h">The harness checks itself</text>
<text x="56" y="80" class="sub muted">The gate checks the work. Evals check the harness: a rule only counts as holding at 3 of 3 runs.</text>
<text x="824" y="96" text-anchor="middle" class="runs muted">run 1 · 2 · 3</text>
{''.join(labels)}
{''.join(dots)}
<text x="824" y="226" text-anchor="middle" class="note">fails → becomes a task → fixed → re-run</text>
<text x="56" y="370" class="sub muted">Every miss in the failure register and every rule the owner adds gets a case. Nothing fixes itself: a failure is a task with an owner.</text>
"""
    return svg(1200, 400, "The harness checks itself: evals in four layers",
               "Four rows, Scripts, Behaviour, Gate and Flows, each with three run dots that turn green in turn. One behaviour run "
               "turns red first, is labelled 'fails, becomes a task, fixed, re-run', then turns green: a rule counts as holding "
               "only at three passes out of three.", style, body)


def main() -> None:
    for name, fn in [("hero", hero), ("workflow", workflow), ("checks", checks), ("loop", loop), ("evals", evals)]:
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8")
        print(f"wrote docs/visuals/{name}.svg")


if __name__ == "__main__":
    main()
