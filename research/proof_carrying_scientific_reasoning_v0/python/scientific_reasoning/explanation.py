from __future__ import annotations

from .certificates import Certificate


def explain(cert: Certificate) -> str:
    lines = [
        "Assured conclusion (formal derivation only):",
        f"  {cert.conclusion}",
        f"Authority of conclusion: {cert.final_authority}",
        f"Support premise ids: {list(cert.final_support)}",
        "Premises:",
    ]
    for p in cert.premises:
        lines.append(f"  [{p.id}] {p.authority.value}: {p.formula}")
    lines.append("Steps:")
    for s in cert.steps:
        lines.append(f"  {s['rule']}: {s['formula']} (auth={s['authority']}, S={s['support']})")
    lines.append(
        "This certificate does NOT establish empirical truth of empiricalAsserted/"
        "assumption/hypothesis premises."
    )
    return "\n".join(lines)
