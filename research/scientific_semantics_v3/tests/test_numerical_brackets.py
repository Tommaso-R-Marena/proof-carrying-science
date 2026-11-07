import ast
from decimal import Decimal
from pathlib import Path

import pytest

from research.scientific_semantics_v3.numerical import parse,reproduce,evaluate

SOURCE=Path(__file__).parents[1]/"fixtures/final/nist_misra1a/Misra1a.dat"


def test_actual_exposed_source_repaired_as_posthoc_reproduction():
    r=reproduce(SOURCE.read_bytes())
    assert r["status"]=="REPRODUCED_ROUNDED_COMPUTATION"
    assert r["rss_relative_discrepancy"]<1e-9
    assert r["exact_rational_rounding_enclosure"]["status"]=="UNSUPPORTED"
    assert any("Bracket" in s or "bracket" in s for s in r["assumptions"])
    assert r["authority"] is False and r["scientific_meaning"]=="OPEN"


@pytest.mark.parametrize("expression",["exp[-b2*x]+exp","exp[-b2*x][0]","exp[x,y]","exp[0:1]","x[0]","np.exp[-b2*x]","__import__['os']"])
def test_ambiguous_or_non_scalar_notation_remains_unsupported(expression):
    raw=SOURCE.read_bytes().replace(b"exp[-b2*x]",expression.encode())
    assert reproduce(raw)["status"]=="UNKNOWN"


def test_declared_exp_variable_cannot_implicitly_authorize_function_meaning():
    raw=SOURCE.read_bytes()+b"\nexp = 5\n"
    assert reproduce(raw)["status"]=="UNKNOWN"


def test_lowered_constants_keep_exact_original_lexemes():
    raw=SOURCE.read_bytes().replace(b"exp[-b2*x]",b"exp[-0.12345678901234567890123456789*b2*x]")
    parsed=parse(raw)
    literal=next(n for n in ast.walk(parsed["tree"]) if isinstance(n,ast.Constant) and type(n.value) is float)
    assert literal.source_literal=="0.12345678901234567890123456789"
    assert evaluate(literal,{},"decimal")==Decimal("0.12345678901234567890123456789")


def test_changed_observation_still_refutes_reproduction():
    raw=SOURCE.read_bytes();data=raw.split(b"Data:  y",1)
    if len(data)!=2:
        data=raw.split(b"Data:   y",1)
    # Alter the first y field using the independently parsed source table.
    parsed=parse(raw);y=parsed["rows"][0][0].encode()
    prefix,tail=raw.rsplit(b"Data:",1)
    altered=prefix+b"Data:"+tail.replace(y,b"99999",1)
    assert reproduce(altered)["status"]=="REFUTED"
