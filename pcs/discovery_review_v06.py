from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


DISCOVERY_FORMAT_V06 = "pcs-project-discovery-v1"


class V06DiscoveryReviewError(ValueError):
    pass


def _mermaid_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _md_escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|")


def render_discovery_review_v06(report: dict[str, Any]) -> str:
    if report.get("format") != DISCOVERY_FORMAT_V06:
        raise V06DiscoveryReviewError("cannot render non-v0.6 discovery report")

    summary = report.get("summary", {})
    selected_recs = set(report.get("selected_recommendations", []))
    selected_workflow = set(report.get("selected_workflow_inferences", []))
    workflow_map = report.get("workflow_map", {})
    inventory_by_id = {
        item["artifact_id"]: item
        for item in report.get("inventory", [])
        if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
    }

    lines = [
        "# PCS guided discovery review",
        "",
        "> Review boundary: this is a static discovery artifact. User code was not",
        "> executed. Confirmation does not prove source-code correctness, runtime",
        "> behavior, biological adequacy, or empirical validity.",
        "",
        f"Project: **{_md_escape(report.get('project_root_name', ''))}**",
        "",
        f"Subject: **{_md_escape(report.get('subject', ''))}**",
        "",
        "## Summary",
        "",
        f"- Files inventoried: **{summary.get('files_inventoried', 0)}**",
        f"- Scientific recommendations: **{summary.get('recommendations', 0)}**",
        f"- Selected scientific recommendations: **{summary.get('selected_recommendations', 0)}**",
        f"- Claims drafted: **{summary.get('claims_drafted', 0)}**",
        f"- Static source files analyzed: **{summary.get('workflow_sources_analyzed', 0)}**",
        f"- Workflow nodes drafted: **{summary.get('workflow_nodes_drafted', 0)}**",
        f"- Workflow edges inferred: **{summary.get('workflow_edges_inferred', 0)}**",
        f"- Unresolved workflow items: **{summary.get('workflow_unresolved_items', 0)}**",
        "",
        "## Scientific-check recommendations",
        "",
    ]

    recommendations = report.get("recommendations", [])
    if recommendations:
        for rec in recommendations:
            mark = "x" if rec.get("id") in selected_recs else " "
            confidence = float(rec.get("confidence", 0.0))
            lines.extend(
                [
                    f"- [{mark}] **{_md_escape(rec.get('detector', 'recommendation'))}** "
                    f"({confidence:.2f})",
                    f"  - Claim: {_md_escape(rec.get('claim', {}).get('statement', ''))}",
                    f"  - Check: {_md_escape(rec.get('check', {}).get('type', ''))}",
                    f"  - Why: {_md_escape(rec.get('reason', ''))}",
                ]
            )
    else:
        lines.append("- No supported scientific-check recommendation was detected.")

    lines.extend(["", "## Static workflow inferences", ""])
    sources = workflow_map.get("sources", []) if isinstance(workflow_map, dict) else []
    if sources:
        for source in sources:
            mark = "x" if source.get("id") in selected_workflow else " "
            reads = [
                inventory_by_id.get(aid, {}).get("path", aid)
                for aid in source.get("reads", [])
            ]
            writes = [
                inventory_by_id.get(aid, {}).get("path", aid)
                for aid in source.get("writes", [])
            ]
            lines.extend(
                [
                    f"- [{mark}] **{_md_escape(source.get('source_path', ''))}** "
                    f"({source.get('source_kind', 'source')}, "
                    f"confidence {float(source.get('confidence', 0.0)):.2f})",
                    f"  - Reads: {_md_escape(', '.join(reads) or 'none')}",
                    f"  - Writes: {_md_escape(', '.join(writes) or 'none')}",
                    f"  - Unresolved recognized references: "
                    f"{int(source.get('unresolved_reference_count', 0))}",
                    f"  - Boundary: {_md_escape(source.get('reason', 'static only'))}",
                ]
            )
    else:
        lines.append("- No static Python/Jupyter workflow dependency was resolved.")

    fence = chr(96) * 3
    lines.extend(["", "## Workflow graph", "", fence + "mermaid", "graph LR"])
    selected_sources = [
        source for source in sources if source.get("id") in selected_workflow
    ]
    if selected_sources:
        artifact_ids = {
            aid
            for source in selected_sources
            for aid in source.get("reads", []) + source.get("writes", [])
        }
        for aid in sorted(artifact_ids):
            label = str(inventory_by_id.get(aid, {}).get("path", aid)).replace('"', "'")
            lines.append(f'  {_mermaid_id("A", aid)}["{label}"]')
        for source in selected_sources:
            sid = _mermaid_id("S", source["id"])
            label = str(source.get("source_path", source["id"])).replace('"', "'")
            lines.append(f'  {sid}(["{label}"])')
            for aid in source.get("reads", []):
                lines.append(f'  {_mermaid_id("A", aid)} -->|read| {sid}')
            for aid in source.get("writes", []):
                lines.append(f'  {sid} -->|write| {_mermaid_id("A", aid)}')
    else:
        lines.append('  EMPTY["No selected workflow inference"]')
    lines.extend([fence, "", "## Unresolved review items", ""])

    unresolved = report.get("unresolved", [])
    if unresolved:
        for item in unresolved:
            kind = item.get("type", "unresolved")
            message = item.get("message") or item.get("source_path") or ""
            lines.append(f"- **{_md_escape(kind)}**: {_md_escape(message)}")
    else:
        lines.append("- None reported.")

    lines.extend(
        [
            "",
            "## Before confirmation",
            "",
            "Review pcs-manifest.draft.json directly. In particular:",
            "",
            "1. confirm each selected scientific claim says what you intend;",
            "2. confirm each selected workflow edge matches the intended artifact flow;",
            "3. inspect unresolved or dynamic references instead of guessing;",
            "4. remove any source or check recommendation you do not want to attest;",
            "5. only then run pcs confirm-v06.",
            "",
            "The CLI re-hashes selected artifacts at confirmation, and attest-v06",
            "checks the same snapshots again before signing.",
            "",
        ]
    )
    return "\n".join(lines)


def write_discovery_review_v06(
    report: dict[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    path = Path(output).resolve()
    if path.exists() and not overwrite:
        raise V06DiscoveryReviewError(
            f"refusing to overwrite existing discovery review: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_discovery_review_v06(report), encoding="utf-8")
    return path
