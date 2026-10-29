"""Generate results/report.html from results/benchmarks.json (stdlib only, inline SVG).

The report shows raw tables for every record plus log-scale plots of runtime for the
lesion and OR families (the two scaling families), and summary statistics for the
random workload.  Nothing is filtered: every record in benchmarks.json appears.
"""
from __future__ import annotations

import html
import json
import math
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def fmt_t(x):
    return "" if x is None else f"{x:.4f}"


def svg_plot(title, series, xlabel, ylabel="seconds (log10)", width=560, height=320):
    """series: list of (name, color, [(x, y or None, timeout_flag)])."""
    pts = [(x, y) for _, _, s in series for (x, y, _) in s if y is not None and y > 0]
    if not pts:
        return "<p>(no data)</p>"
    xs = [p[0] for p in pts]
    ys = [math.log10(p[1]) for p in pts]
    x0, x1 = min(xs), max(xs)
    y0, y1 = math.floor(min(ys)), math.ceil(max(ys))
    if x1 == x0:
        x1 = x0 + 1
    if y1 == y0:
        y1 = y0 + 1
    L, R, T, B = 60, 140, 30, 40

    def sx(x):
        return L + (x - x0) / (x1 - x0) * (width - L - R)

    def sy(ly):
        return T + (y1 - ly) / (y1 - y0) * (height - T - B)

    out = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" '
           f'style="background:#fff;border:1px solid #ccc">',
           f'<text x="{width/2}" y="18" text-anchor="middle" font-size="13">{html.escape(title)}</text>']
    for ly in range(y0, y1 + 1):
        y = sy(ly)
        out.append(f'<line x1="{L}" y1="{y}" x2="{width-R}" y2="{y}" stroke="#eee"/>')
        out.append(f'<text x="{L-5}" y="{y+4}" text-anchor="end" font-size="10">1e{ly}</text>')
    for x in sorted(set(xs)):
        out.append(f'<text x="{sx(x)}" y="{height-B+14}" text-anchor="middle" font-size="10">{x}</text>')
    out.append(f'<text x="{(L+width-R)/2}" y="{height-6}" text-anchor="middle" font-size="11">'
               f'{html.escape(xlabel)}</text>')
    out.append(f'<text x="14" y="{height/2}" font-size="11" transform="rotate(-90 14 {height/2})" '
               f'text-anchor="middle">{html.escape(ylabel)}</text>')
    for i, (name, color, s) in enumerate(series):
        good = [(sx(x), sy(math.log10(y))) for (x, y, to) in s if y is not None and y > 0 and not to]
        if len(good) > 1:
            d = " ".join(f"{a:.1f},{b:.1f}" for a, b in good)
            out.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
        for (x, y, to) in s:
            if y is None or y <= 0:
                continue
            cx, cy = sx(x), sy(math.log10(y))
            if to:
                out.append(f'<text x="{cx}" y="{cy+4}" text-anchor="middle" font-size="12" '
                           f'fill="{color}">✕</text>')
            else:
                out.append(f'<circle cx="{cx}" cy="{cy}" r="3" fill="{color}"/>')
        ly = T + 16 * i + 10
        out.append(f'<rect x="{width-R+10}" y="{ly-8}" width="10" height="10" fill="{color}"/>')
        out.append(f'<text x="{width-R+25}" y="{ly+1}" font-size="11">{html.escape(name)}</text>')
    out.append(f'<text x="{width-R+10}" y="{T+16*len(series)+14}" font-size="10">✕ = timeout</text>')
    out.append("</svg>")
    return "\n".join(out)


def series_for(recs, xkey):
    res = []
    for meth, color in (("dp_naive", "#d62728"), ("dp_pruned", "#1f77b4"), ("sandwich", "#2ca02c")):
        s = []
        for r in recs:
            m = r[meth]
            to = m["status"] in ("timeout", "unresolved")
            s.append((xkey(r), m["time"], to))
        res.append((meth, color, s))
    s = [(xkey(r), r["sandwich"].get("check_time"), False) for r in recs]
    res.append(("cert check", "#9467bd", s))
    return res


def table(recs):
    cols = ["family", "params", "eps", "n_models", "n_experiments", "value",
            "dp_naive", "dp_pruned", "sandwich", "check", "core", "rounds", "policy nodes",
            "greedy", "nonadaptive"]
    rows = ["<table><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"]
    for r in recs:
        sw = r["sandwich"]
        val = sw.get("value")
        if val is None and r["dp_pruned"]["status"] == "ok":
            val = r["dp_pruned"]["value"]

        def m(k):
            x = r[k]
            st = x["status"]
            return f'{fmt_t(x["time"])} ({x.get("states")})' + ("" if st in ("ok", "optimal", "impossible")
                                                                 else f" <b>{st}</b>")
        cells = [r["family"], html.escape(json.dumps(r["params"])), r["eps"], r["n_models"],
                 r["n_experiments"], val, m("dp_naive"), m("dp_pruned"),
                 m("sandwich") + ("" if sw["status"] != "unresolved" else f' lb={sw.get("lower")}'),
                 fmt_t(sw.get("check_time")), sw.get("core_size"), sw.get("rounds"),
                 sw.get("cert_policy_nodes"), r["greedy"].get("cost"),
                 (r.get("nonadaptive") or {}).get("cost")]
        rows.append("<tr>" + "".join(f"<td>{'' if c is None else c}</td>" for c in cells) + "</tr>")
    rows.append("</table>")
    return "\n".join(rows)


def random_summary(recs):
    rs = [r for r in recs if r["family"] == "random"]
    if not rs:
        return ""
    out = ["<table><tr><th>size (n,k,r)</th><th>#inst</th><th>mean dp_naive s</th>"
           "<th>mean dp_pruned s</th><th>mean sandwich s</th><th>sandwich faster than pruned DP</th>"
           "<th>greedy suboptimal</th><th>adaptive &lt; nonadaptive</th></tr>"]
    groups = {}
    for r in rs:
        p = r["params"]
        groups.setdefault((p["n"], p["k"], p["r"]), []).append(r)
    for key, g in sorted(groups.items()):
        def mean(k):
            return sum(x[k]["time"] for x in g) / len(g)
        faster = sum(1 for x in g if x["sandwich"]["time"] < x["dp_pruned"]["time"])
        gs = sum(1 for x in g if Fraction(str(x["greedy"].get("gap") or 0)) > 0)
        na = 0
        for x in g:
            v = x["sandwich"].get("value")
            c = (x.get("nonadaptive") or {}).get("cost")
            if v not in (None, "inf") and c not in (None, "inf"):
                try:
                    if Fraction(str(v)) < Fraction(str(c)):
                        na += 1
                except (ValueError, ZeroDivisionError):
                    pass
        out.append(f"<tr><td>{key}</td><td>{len(g)}</td><td>{mean('dp_naive'):.4f}</td>"
                   f"<td>{mean('dp_pruned'):.4f}</td><td>{mean('sandwich'):.4f}</td>"
                   f"<td>{faster}/{len(g)}</td><td>{gs}/{len(g)}</td><td>{na}/{len(g)}</td></tr>")
    out.append("</table>")
    return "\n".join(out)


def main():
    path = os.path.join(ROOT, "results", "benchmarks.json")
    with open(path) as f:
        data = json.load(f)
    recs = data["records"]
    lesion8 = [r for r in recs if r["family"] == "lesion" and r["params"]["n"] == 8]
    lesion16 = [r for r in recs if r["family"] == "lesion" and r["params"]["n"] == 16]
    orr = [r for r in recs if r["family"] == "or"]
    parts = ["<!doctype html><html><head><meta charset='utf-8'><title>PRISM benchmark report</title>",
             "<style>body{font-family:sans-serif;max-width:1200px;margin:auto;padding:1em}"
             "table{border-collapse:collapse;font-size:11px}td,th{border:1px solid #ccc;padding:2px 4px}"
             "th{background:#f3f3f3}</style></head><body>",
             "<h1>PRISM benchmark report</h1>",
             "<p>Generated by <code>python/benchmarks/make_report.py</code> from "
             "<code>results/benchmarks.json</code>. All records are shown; nothing is filtered. "
             "Times are wall-clock seconds of single-threaded CPython (stdlib only); numbers in "
             "parentheses are expanded DP states. Every optimal value was cross-checked between the "
             "naive DP, pruned DP and sandwich methods (the run aborts on disagreement), and every "
             "sandwich certificate was re-checked by the independent Python checker "
             "(column <i>check</i>).</p>",
             f"<p>Machine: <code>{html.escape(json.dumps(data['machine']))}</code></p>",
             "<h2>Scaling families</h2>",
             "<p><b>Lesion family</b> (designed to favour the core-guided sandwich: nuisance switches "
             "multiply the model count by 2^k without changing the adversarial core). "
             "<b>OR family</b> is a negative control: its smallest adversarial core has n+1 models and "
             "the explicit model space has 2^n models; the sandwich is not expected to win.</p>",
             svg_plot("lesion family, n=8 pathway steps", series_for(lesion8, lambda r: r["params"]["k"]),
                      "k nuisance switches (|M| = 8·2^k)"),
             svg_plot("lesion family, n=16", series_for(lesion16, lambda r: r["params"]["k"]),
                      "k nuisance switches"),
             svg_plot("OR family (negative control)", series_for(orr, lambda r: r["params"]["n"]),
                      "n regulators"),
             "<h2>Random workload (held-out seeds 1000–1009)</h2>",
             random_summary(recs),
             "<h2>All records</h2>", table(recs),
             "<h2>Accounting caveats</h2><ul>"
             "<li>All methods (including the sandwich) operate on an explicitly enumerated model list "
             "in this prototype; the sandwich's advantage on the lesion family comes from running the "
             "exponential DP only on the small core and validating the candidate policy on the full "
             "space in time linear in |K| per policy leaf. No symbolic representation of K is used, so "
             "the |K| term is still paid.</li>"
             "<li>Peak memory (tracemalloc) is measured in a separate run and only for some records; see "
             "the CSV.</li>"
             "<li>Speedups are specific to these generators, this machine and CPython; they are not "
             "asymptotic theorems except where stated in docs/THEOREMS.md.</li></ul>",
             "</body></html>"]
    out = os.path.join(ROOT, "results", "report.html")
    with open(out, "w") as f:
        f.write("\n".join(parts))
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    sys.exit(main())
