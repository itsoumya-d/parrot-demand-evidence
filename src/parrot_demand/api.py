from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from parrot_demand.engine import Evidence, Signal, TitleRecord, assess, rank

app = FastAPI(title="Parrot Demand Evidence")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")

RECORDS = [
    TitleRecord(
        "The Last Signal",
        "NZ",
        [
            Signal("search", [12, 13, 13, 14, 15, 15, 16, 17, 18, 20, 22, 24], "https://search.example/last-signal", 1.0),
            Signal("streaming", [400, 410, 405, 430, 450, 460, 470, 500, 530, 560, 610, 650], "https://stream.example/last-signal", 1.3),
            Signal("social", [70, 72, 71, 75, 76, 78, 80, 83, 87, 91, 96, 102], "https://social.example/last-signal", 0.9),
        ],
        [
            Evidence("https://search.example/last-signal", "Search interest for The Last Signal accelerated across every measured market this week.", "search"),
            Evidence("https://stream.example/last-signal", "Streaming completions and repeat viewing are up sharply versus the prior four-week baseline.", "streaming"),
        ],
        ("sci-fi", "prestige", "streaming-originals"),
    ),
    TitleRecord(
        "Night Market",
        "AU",
        [
            Signal("search", [55, 56, 58, 60, 61, 63, 64, 66, 68, 70, 72, 74], "https://search.example/night-market", 1.0),
            Signal("social", [90, 88, 86, 84, 81, 79, 76, 74, 71, 69, 66, 63], "https://social.example/night-market", 0.8),
            Signal("streaming", [200, 205, 210, 215, 220, 225, 230, 235, 240, 245, 250, 255], "https://stream.example/night-market", 1.1),
        ],
        [Evidence("https://stream.example/night-market", "Streaming demand is steady, while social conversation is cooling after the premiere window.", "streaming")],
        ("crime", "ensemble", "prestige"),
    ),
    TitleRecord(
        "Blue Orbit",
        "UK",
        [Signal("search", [30, 29, 31, 30, 29, 30, 31, 30], "https://search.example/blue-orbit", 1.0)],
        [],
        ("space", "family", "streaming-originals"),
    ),
    TitleRecord(
        "Paper Kingdom",
        "NZ",
        [Signal("search", [10, 11], "https://search.example/paper-kingdom", 1.0)],
        [],
        ("drama", "literary", "prestige"),
    ),
]

ASSESSMENTS = rank(RECORDS)


def payload():
    return [
        {
            "title": item.title,
            "market": item.market,
            "momentum": item.momentum,
            "confidence": item.confidence,
            "status": item.status,
            "drivers": [driver.__dict__ for driver in item.drivers],
            "evidence": [match.__dict__ for match in item.evidence],
            "overlap": item.overlap,
            "flags": list(item.flags),
            "explanation": item.explanation,
        }
        for item in ASSESSMENTS
    ]


def money(value: float) -> str:
    return f"{value:+.1%}"


def dashboard() -> str:
    strong = sum(1 for item in ASSESSMENTS if item.status == "strong")
    supported = sum(1 for item in ASSESSMENTS if item.evidence)
    avg_conf = sum(item.confidence for item in ASSESSMENTS) / len(ASSESSMENTS)
    rows = "".join(
        f"""
        <tr>
          <td><strong>{item.title}</strong><span class="sub">{item.market}</span></td>
          <td class="num {'up' if item.momentum > 0 else 'down'}">{money(item.momentum)}</td>
          <td><span class="status {item.status}">{item.status}</span></td>
          <td>{item.confidence:.0%}</td>
          <td>{item.evidence[0].quote if item.evidence else 'No supporting citation'}</td>
          <td class="flags">{', '.join(item.flags) or 'none'}</td>
        </tr>
        """
        for item in ASSESSMENTS
    )
    drivers = "".join(
        f"<li><strong>{item.title}</strong> · {item.explanation}</li>" for item in ASSESSMENTS
    )
    overlap = "".join(
        f"<li>{title}: {score:.0%}</li>" for title, score in ASSESSMENTS[0].overlap.items()
    )
    return f"""
    <!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Parrot demand evidence</title>
    <style>
      @font-face{{font-family:'Axiforma';src:url('/static/Axiforma-Regular.woff2') format('woff2');font-weight:400;font-style:normal;font-display:swap}}
      @font-face{{font-family:'Axiforma';src:url('/static/Axiforma-Bold.woff2') format('woff2');font-weight:700;font-style:normal;font-display:swap}}
      @font-face{{font-family:'Axiforma';src:url('/static/Axiforma-ExtraBold.woff2') format('woff2');font-weight:800;font-style:normal;font-display:swap}}
      :root{{--black:#000;--panel:#0c0c0c;--line:#262626;--white:#fff;--muted:#999;--green:#05c56b;--red:#f22e52;--yellow:#f7bc2d;--blue:#007aff;--radius:4px}}
      *{{box-sizing:border-box}}body{{margin:0;background:var(--black);color:var(--white);font-family:'Axiforma',Arial,sans-serif;font-size:16px;line-height:1.5}}
      .shell{{max-width:1240px;margin:0 auto;padding:32px 24px}}header{{border-bottom:1px solid var(--line);padding-bottom:22px;display:flex;justify-content:space-between;gap:24px;align-items:flex-start}}
      .kicker{{margin:0 0 8px;color:var(--green);font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}}h1{{font-size:clamp(42px,5vw,72px);line-height:.98;letter-spacing:-.035em;margin:0;max-width:900px;font-weight:800}}
      .lede{{max-width:760px;color:#bdbdbd;font-size:18px;margin:14px 0 0}}.tag{{border:1px solid var(--line);padding:12px 14px;color:var(--muted);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;line-height:1.7;white-space:nowrap}}
      .metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}.metric{{background:var(--panel);border:1px solid var(--line);padding:16px;border-radius:var(--radius)}}.metric span{{display:block;color:var(--muted);font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}}.metric strong{{display:block;margin-top:8px;font-size:28px;color:var(--white)}}.metric.green strong{{color:var(--green)}}
      .grid{{display:grid;grid-template-columns:1.7fr 1fr;gap:18px}}.panel{{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}}.panel-head{{display:flex;justify-content:space-between;align-items:baseline;padding:15px 18px;border-bottom:1px solid var(--line)}}.panel-head h2{{margin:0;font-size:20px}}.panel-head span{{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em}}
      table{{width:100%;border-collapse:collapse;text-align:left}}th{{padding:10px 12px;color:var(--muted);border-bottom:1px solid var(--line);font-size:9px;text-transform:uppercase;letter-spacing:.08em}}td{{padding:13px 12px;border-bottom:1px solid var(--line);font-size:12px;vertical-align:top}}tr:last-child td{{border-bottom:0}}.num{{text-align:right;font-variant-numeric:tabular-nums}}.up{{color:var(--green)}}.down{{color:var(--red)}}.sub{{display:block;color:var(--muted);font-size:10px;margin-top:2px}}
      .status{{display:inline-block;padding:3px 7px;border-radius:999px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.04em}}.status.strong{{background:#052a1a;color:var(--green)}}.status.mixed{{background:#332608;color:var(--yellow)}}.status.unsupported{{background:#321018;color:var(--red)}}.flags{{color:var(--muted);font-size:10px}}
      .side{{padding:18px}}.side h2{{font-size:20px;margin:0 0 10px}}.side p{{color:#bdbdbd;font-size:13px;margin:0 0 12px}}.side ul{{list-style:none;padding:0;margin:0}}.side li{{border-top:1px solid var(--line);padding:10px 0;font-size:12px;color:#d0d0d0}}.side li strong{{color:var(--white)}}.callout{{margin:14px 18px 18px;border-left:3px solid var(--green);background:#07160e;padding:12px 14px;color:#c9f7dc;font-size:12px}}
      footer{{display:flex;justify-content:space-between;gap:16px;margin-top:22px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:11px}}
      @media(max-width:920px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}header{{flex-direction:column}}}}
    </style></head><body><div class="shell">
      <header><div><p class="kicker">Parrot Analytics · Demand evidence graph</p><h1>Show the evidence behind the demand signal.</h1><p class="lede">Momentum, audience overlap and supporting citations for every title — with uncertainty exposed instead of hidden.</p></div><div class="tag">Python 3.12<br>SQL + APIs<br>NLP / RAG<br>Graph analysis</div></header>
      <section class="metrics"><div class="metric"><span>Titles assessed</span><strong>{len(ASSESSMENTS)}</strong></div><div class="metric green"><span>Strong evidence</span><strong>{strong}</strong></div><div class="metric"><span>With citations</span><strong>{supported}</strong></div><div class="metric green"><span>Mean confidence</span><strong>{avg_conf:.0%}</strong></div></section>
      <main class="grid"><section class="panel"><div class="panel-head"><h2>Demand evidence</h2><span>Live demo</span></div><table><thead><tr><th>Title</th><th class="num">Momentum</th><th>Status</th><th>Conf.</th><th>Lead citation</th><th>Flags</th></tr></thead><tbody>{rows}</tbody></table></section>
      <aside class="panel side"><h2>Audience overlap</h2><p>Shared audience segments between The Last Signal and the rest of the slate.</p><ul>{overlap}</ul><div class="callout"><strong>Why this exists</strong><br>Analysts should not have to choose between a number and a defensible story. This graph makes the evidence inspectable.</div></aside></main>
      <section class="panel" style="margin-top:18px"><div class="panel-head"><h2>Explainable drivers</h2><span>Uncertainty visible</span></div><div class="side"><ul>{drivers}</ul></div></section>
      <footer><span>Axiforma · #000000 · #05C56B · #F22E52 · #F7BC2D · 4px radius</span><span>Reference implementation for Parrot Analytics</span></footer>
    </div></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return dashboard()


@app.get("/api/assessments")
def assessments():
    return payload()


@app.get("/api/titles/{slug}")
def title(slug: str):
    for item in payload():
        if item["title"].lower().replace(" ", "-") == slug:
            return item
    return {"error": "not_found"}


@app.get("/static/health")
def health():
    return {"ok": True}
