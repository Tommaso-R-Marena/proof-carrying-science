"""Script-free scientific review. Presentation never grants check authority."""
from __future__ import annotations

from collections import Counter
import hashlib
import html
import json
import re


KERNEL_STATUSES = frozenset({
    "KERNEL_CHECKED_ABSTRACT_PARTIAL_SEMANTICS",
    "KERNEL_CHECKED_ABSTRACT_RESIDUAL_SEMANTICS",
    "KERNEL_CHECKED_FINITE_INTEGER_CONSERVATION",
})
COMPUTATION_STATUSES = frozenset({"REPRODUCED_COMPUTATION", "REPRODUCED_ROUNDED_COMPUTATION"})
SOURCE_STATUSES = frozenset({"SOURCE_DECLARATION_CHECKED", "SOURCE_REPORT_CHECKED", "SCOPED_EQUATION_CHECKED"})
SHA = re.compile(r"[0-9a-f]{64}\Z")
LABELS = {
    "proof": ("Formal proof checked", "A Lean receipt records a proof of the stated mathematical theorem. Its assumptions and scope still apply."),
    "computation": ("Computation reproduced", "A supported calculation reproduced the stated result under the recorded inputs, model and numerical assumptions."),
    "source": ("Source statement checked", "An independent checker matched a declaration, printed value or scoped equation to its source. Scientific meaning remains open."),
    "refuted": ("Contradiction found", "The stated check found a mismatch or counterexample within its scope. Review the evidence before using this result."),
    "unknown": ("Meaning or result unresolved", "This result has no accepted check for the intended scientific meaning. It needs review or an additional check."),
}


def _e(value):
    return html.escape(str(value), quote=True)


def _pretty(value):
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, default=str)


def _text(value):
    """Readable arithmetic and values without granting meaning to parser IR."""
    if value is None:
        return "not stated"
    if isinstance(value, list):
        return ", ".join(_text(v) for v in value) or "none recorded"
    if isinstance(value, dict):
        op = value.get("op")
        if op == "symbol":
            return str(value.get("name", "?"))
        if op == "number":
            return str(value.get("value", "?"))
        if op == "reaction_rate":
            return "rate of " + str(value.get("reaction", "?"))
        args = value.get("args", [])
        if op in {"add", "sub", "mul", "div", "pow"} and args:
            return "(" + {"add": " + ", "sub": " − ", "mul": " × ", "div": " / ", "pow": " ^ "}[op].join(_text(v) for v in args) + ")"
        if op == "neg":
            return "−" + _text(value.get("arg", args[0] if args else None))
        if op in {"function", "call"}:
            return str(value.get("name", value.get("function", "function"))) + "(" + ", ".join(_text(v) for v in args) + ")"
        return "; ".join(str(k).replace("_", " ") + ": " + _text(v) for k, v in value.items()) or "none recorded"
    return str(value)


def _receipt_complete(record):
    if record.get("status") == "KERNEL_CHECKED_FINITE_INTEGER_CONSERVATION":
        return (SHA.fullmatch(str(record.get("source_sha256", ""))) is not None
                and SHA.fullmatch(str(record.get("lean_binary_sha256", ""))) is not None
                and isinstance(record.get("certificate"), dict)
                and bool(record.get("axioms")) and bool(record.get("scope")))
    return (SHA.fullmatch(str(record.get("source_sha256", ""))) is not None
            and SHA.fullmatch(str(record.get("compiler_sha256", ""))) is not None
            and bool(record.get("axiom_audit")) and record.get("returncode") == 0
            and "version 4.28.0" in str(record.get("version", ""))
            and bool(record.get("stdout")) and bool(record.get("scope")))


def classify(record):
    """Fail closed on unknown verdicts, authority claims and incomplete receipts.

    The renderer checks receipt shape only. Authenticity belongs to package
    replay; a caller-supplied status is never itself proof authentication.
    """
    if not isinstance(record, dict):
        return "unknown", "Invalid check record."
    if (record.get("authority") is not False or record.get("scientific_meaning") not in (None, "OPEN")
            or record.get("production_authority") not in (None, False, "NONE")
            or record.get("scientific_meanings_certified", 0) != 0):
        return "unknown", "The record claims authority or certified meaning and was not accepted."
    status = record.get("status")
    if status in KERNEL_STATUSES:
        if _receipt_complete(record):
            return "proof", "Receipt shape is present; authenticate it by replaying the evidence package."
        return "unknown", "The formal verdict has no complete Lean receipt and was not accepted."
    if status in COMPUTATION_STATUSES:
        return "computation", ""
    if status in SOURCE_STATUSES:
        return "source", ""
    if status == "REFUTED":
        return "refuted", ""
    if status == "UNKNOWN":
        return "unknown", ""
    return "unknown", "Unrecognized verdict was not accepted: " + str(status or "not checked") + "."


def _inventory(interpretation, supplied):
    raw = supplied.get("artifacts", []) if isinstance(supplied, dict) and isinstance(supplied.get("artifacts"), list) else supplied
    entries = list(interpretation.get("artifacts", []))
    blobs = {}
    if isinstance(raw, list):
        entries.extend(x for x in raw if isinstance(x, dict))
    elif isinstance(raw, dict):
        for path, value in raw.items():
            if isinstance(value, bytes):
                blobs[path] = value
                entries.append({"path": path, "sha256": hashlib.sha256(value).hexdigest(), "size": len(value)})
    by_path = {str(a.get("path")): a for a in entries}
    return by_path, blobs


def _prefix(summary):
    prefix = summary.get("source_download_prefix", "parent/intake/objects/")
    if not isinstance(prefix, str) or not re.fullmatch(r"(?:[A-Za-z0-9_-]+/)+", prefix):
        return None
    return prefix


def _source(source, inventory, blobs, prefix):
    if not isinstance(source, dict):
        return "<p>No source location recorded. Supply the missing source before relying on this statement.</p>"
    path = str(source.get("path", "Unknown file")); sha = str(source.get("sha256", ""))
    transformation = source.get("transformation")
    start, end = source.get("byte_start"), source.get("byte_end")
    quote = str(source.get("quote", ""))
    original_sha = source.get("original_sha256", sha)
    item = inventory.get(path, {})
    binary_derived = bool(transformation) and (path.lower().endswith((".pdf", ".docx")) or isinstance(transformation, dict) and any(k in transformation for k in ("derived_text_sha256", "derived_text", "adapter")))
    transformation_html = "<p><strong>Extraction provenance:</strong> " + _e(_text(transformation)) + "</p>" if transformation else ""
    if binary_derived:
        heading = "Read the derived text and original file"
        locator = "Derived text excerpt. These text offsets do not identify a quote in the original binary file."
    else:
        heading = "Read the source and download the original"
        locator = "Captured source excerpt"
        raw = blobs.get(path)
        if raw is not None and type(start) is int and type(end) is int and 0 <= start <= end <= len(raw):
            if hashlib.sha256(raw).hexdigest() == sha and raw[start:end] == quote.encode("utf-8"):
                locator = "Exact original UTF-8 byte excerpt"
            else:
                locator = "Source binding mismatch: this excerpt was not confirmed against the supplied bytes"
    location = source.get("locator", {})
    span = f"; bytes {start}–{end}" if type(start) is int and type(end) is int else "; byte range not recorded"
    download = "<p>Original download unavailable: no valid captured file digest or safe download prefix.</p>"
    valid_sha = isinstance(original_sha, str) and SHA.fullmatch(original_sha)
    matches = item.get("sha256") in (sha, original_sha) or raw_matches(inventory, original_sha)
    if prefix and valid_sha and matches:
        download = '<p><a class="source-download" download href="' + _e(prefix + original_sha) + '">Download original file: ' + _e(path) + '</a></p>'
    return "<details class=\"source-detail\"><summary>" + heading + "</summary><p>" + _e(path + span) + "</p><p>" + _e(locator) + ".</p>" + transformation_html + ("<p>Location: " + _e(_text(location)) + "</p>" if location else "") + "<pre class=\"source-quote\">" + _e(quote or "No excerpt recorded.") + "</pre>" + download + "<p class=\"digest\">Original file SHA-256: " + _e(original_sha) + "</p></details>"


def raw_matches(inventory, sha):
    return any(a.get("sha256") == sha for a in inventory.values())


def _conditions(claim):
    parts = []
    for key, label in (("assumptions", "Assumptions"), ("conditions", "Conditions"), ("domain", "Mathematical domain")):
        value = claim.get(key)
        parts.append("<p><strong>" + label + ":</strong> " + _e(_text(value) if value else "not explicitly stated; review needed") + ".</p>")
    return "<details><summary>Assumptions, conditions and missing meaning</summary>" + "".join(parts) + "</details>"


def render(interpretation, checks, inventory_or_artifacts, summary):
    """Return a complete standalone HTML review of v3-shaped interpretations."""
    if not isinstance(interpretation, dict) or not isinstance(summary, dict) or not isinstance(checks, list):
        raise ValueError("review requires an interpretation, check list, inventory and summary")
    inventory, blobs = _inventory(interpretation, inventory_or_artifacts)
    prefix = _prefix(summary)
    claims = interpretation.get("claims", [])
    claim_titles = {c.get("id"): str(c.get("entity", c.get("subject", "Statement"))) + " — " + str(c.get("quantity_role", c.get("kind", "statement"))).replace("_", " ") for c in claims}
    by_claim = {}
    for check in checks:
        if isinstance(check, dict) and check.get("claim_id"):
            by_claim.setdefault(check["claim_id"], []).append(check)
    classified = [(record if isinstance(record, dict) else {"status": "UNKNOWN", "rejected_record": record}, *classify(record)) for record in checks]
    counts = Counter(category for _, category, _ in classified)
    suspect_summary = summary.get("authority") not in (False, None) or summary.get("scientific_meanings_certified", 0) != 0
    alert = '<p class="alert">The summary claims authority or certified scientific meaning. Those claims are not accepted by this review.</p>' if suspect_summary else ""
    overview = summary.get("study_overview", interpretation.get("study_overview"))
    if overview is None:
        overview = summary.get("project_description", "Review the proposed statements, compare each with its source, and resolve the questions below before drawing scientific conclusions.")
    overview_html = _e(_text(overview))
    flagged = []
    for record, category, reason in classified:
        if category in {"refuted", "unknown"}:
            ref = record.get("claim_id") if isinstance(record, dict) else None
            title = record.get("artifact_path", claim_titles.get(ref, "Evidence check")) if isinstance(record, dict) else "Check"
            link = '<a href="#claim-' + _e(ref) + '">Review related statement</a>' if ref else '<a href="#checks">Read the check record</a>'
            flagged.append("<li><strong>" + LABELS[category][0] + ":</strong> " + _e(str(title)) + ". " + _e(reason or record.get("reason", record.get("scope", "Inspect the recorded evidence."))) + " " + link + "</li>")
    for unresolved in interpretation.get("unresolved", []):
        flagged.append("<li>" + _e(unresolved.get("reason", unresolved.get("statement", "Unsupported source meaning"))) + _source(unresolved.get("source"), inventory, blobs, prefix) + "</li>")
    for missing in summary.get("missing_assets", []):
        flagged.append("<li><strong>Missing asset:</strong> " + _e(_text(missing)) + "</li>")
    if not flagged:
        flagged.append("<li>No contradiction was reported by these checks. Scientific meaning, completeness and empirical validity still require review.</li>")
    next_checks = summary.get("next_checks", ["Resolve missing files, units, model domains and scientific assumptions.", "Compare reported results with the captured sources and reproduce the intended analysis.", "Replay the evidence package before relying on a formal receipt or reproduced computation."])
    if not isinstance(next_checks, list):
        next_checks = [next_checks]
    cards = []
    for number, claim in enumerate(claims, 1):
        results = by_claim.get(claim.get("id"), [])
        labels = [LABELS[classify(r)[0]][0] for r in results] or [LABELS["unknown"][0]]
        entity = claim.get("entity", claim.get("subject", "Statement " + str(number)))
        role = str(claim.get("quantity_role", claim.get("kind", "statement"))).replace("_", " ")
        value = _text(claim.get("value")) if "value" in claim else _text(claim.get("lhs")) + " = " + _text(claim.get("rhs"))
        title = str(entity) + " — " + role
        cards.append('<article class="claim" id="claim-' + _e(claim.get("id", number)) + '"><h3>' + _e(title) + '</h3><p class="statement">' + _e(value) + '</p><p><strong>' + _e("; ".join(dict.fromkeys(labels))) + '</strong>. Scientific meaning remains open.</p><p>Units: ' + _e(claim.get("unit") or "not stated") + '. Scope: ' + _e(claim.get("scope", "not stated")) + '.</p>' + _source(claim.get("source"), inventory, blobs, prefix) + _conditions(claim) + '</article>')
    grouped = []
    for category in ("proof", "computation", "source", "refuted", "unknown"):
        label, description = LABELS[category]
        records = []
        for record, found, reason in classified:
            if found != category:
                continue
            scope = record.get("scope", record.get("reason", "The record below states the exact fields checked."))
            proof_titles = {"KERNEL_CHECKED_ABSTRACT_PARTIAL_SEMANTICS": "Abstract partial-expression theorem", "KERNEL_CHECKED_ABSTRACT_RESIDUAL_SEMANTICS": "Abstract residual-sum theorem", "KERNEL_CHECKED_FINITE_INTEGER_CONSERVATION": "Finite integer conservation theorem"}
            title = record.get("artifact_path", claim_titles.get(record.get("claim_id"), proof_titles.get(record.get("status"), "Evidence check")))
            records.append('<article class="check ' + category + '"><h4>' + _e(title) + '</h4><p>' + _e(scope) + '</p>' + ('<p>' + _e(reason) + '</p>' if reason else '') + '<details><summary>Exactly what was checked: evidence record</summary><pre>' + _e(_pretty(record)) + '</pre></details></article>')
        grouped.append('<section class="check-group" data-evidence-class="' + category + '"><h3>' + label + ' <span class="count">' + str(counts[category]) + '</span></h3><p>' + description + '</p>' + ("".join(records) or '<p>No accepted result in this category.</p>') + '</section>')
    assets = ''.join('<li>' + _e(path) + ' <span class="digest">' + _e(a.get("sha256", "digest missing")) + '</span></li>' for path, a in sorted(inventory.items()))
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>PCS scientific review</title><style>
    :root{color-scheme:light;font-family:system-ui,sans-serif;color:#14263a;background:#f3f6f8}*{box-sizing:border-box}body{margin:0;font-size:17px;line-height:1.6}main{max-width:1080px;margin:auto;padding:1.5rem}header{background:#142d43;color:#fff;padding:2rem;border-radius:14px}header p{max-width:70ch}a{color:#075997;text-decoration-thickness:2px;text-underline-offset:3px}header a{color:#fff}nav{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}h1{font-size:clamp(1.9rem,5vw,2.8rem);line-height:1.15;margin:0 0 1rem}h2{font-size:1.5rem;line-height:1.3;margin-top:2rem}h3{font-size:1.15rem;line-height:1.4}h4{font-size:1rem}article,.panel,.check-group{background:#fff;border:1px solid #bdcbd5;border-radius:10px;padding:1.1rem;margin:1rem 0}article article{background:#fafcfd}.priority{border-left:5px solid #9d4716}.alert{border:2px solid #a43817;padding:1rem;background:#fff0e8}.count{font-size:.9rem;padding:.1rem .5rem;border-radius:1rem;background:#e5edf3}.statement{font-size:1.1rem}summary{cursor:pointer;color:#075997;font-weight:600;padding:.6rem 0}details{border-top:1px solid #d7e0e6;margin-top:.7rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;font: .85rem/1.55 ui-monospace,monospace;background:#edf2f5;padding:1rem;border-radius:6px;max-width:100%}.digest{font-size:.8rem;overflow-wrap:anywhere;color:#445b6c;display:block}p,li,h3,h4,a{overflow-wrap:anywhere}li{margin:.5rem 0}ul,ol{padding-left:1.4rem}:focus-visible{outline:3px solid #b24c00;outline-offset:4px}.skip{position:absolute;top:-100px;left:1rem;background:white;padding:.7rem;z-index:10}.skip:focus{top:1rem}.notice{font-size:.95rem}footer{margin:2rem 0;color:#445b6c}@media(max-width:500px){main{padding:.7rem}header{padding:1.1rem}article,.panel,.check-group{padding:.8rem}body{font-size:16px}}
    </style></head><body><a class="skip" href="#questions">Skip to contradictions and open questions</a><main><header><p>PCS · Scientific review</p><h1>What do these research files establish?</h1><p>''' + overview_html + '''</p><p>''' + str(len(inventory)) + ''' captured files · ''' + str(len(claims)) + ''' proposed statements · ''' + str(len(checks)) + ''' check records</p><p class="notice">No scientific conclusions are certified. Source checks, reproduced computations and formal proofs have different scopes. Scientific meaning, empirical validity and completeness remain open.</p><nav aria-label="Review sections"><a href="#questions">Contradictions and questions</a><a href="#statements">Statements and sources</a><a href="#checks">Evidence classes</a><a href="#assets">Captured files</a></nav></header>''' + alert + '''<section id="questions" class="panel priority"><h2>Contradictions and open questions</h2><ul>''' + ''.join(flagged) + '''</ul><h3>Next checks</h3><ol>''' + ''.join('<li>' + _e(_text(step)) + '</li>' for step in next_checks) + '''</ol></section><section id="statements"><h2>Statements and their sources</h2><p>Open each source, then inspect its assumptions. Unstated units or conditions require review.</p>''' + (''.join(cards) or '<p>No supported statements were extracted. Inspect the captured files and supply missing assets or an appropriate adapter.</p>') + '''</section><section id="checks"><h2>Five different kinds of evidence</h2><p>Labels describe individual checks. A valid looking receipt must still be authenticated by replay; this page does not run a proof checker.</p>''' + ''.join(grouped) + '''</section><section id="assets" class="panel"><h2>Captured files</h2><ul>''' + (assets or '<li>No file inventory was supplied.</li>') + '''</ul></section><footer>This is an automated evidence review, not a certification of scientific conclusions. Imported text is displayed as data. No scripts or external assets are required by this page.</footer></main></body></html>'''
