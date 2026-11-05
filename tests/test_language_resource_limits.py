"""The controlled parser must abstain on resource abuse without stack exhaustion."""
import pytest

from pcs.experimental.prover.language import Parser, formalize, parse_lean


@pytest.mark.parametrize("count", [257, 995, 1480])
def test_parenthesis_exhaustion_is_unsupported(count):
    source = "For all propositions p, " + "(" * count + "p" + ")" * count
    assert len(source) <= 3000
    result = formalize(source)
    assert result["status"] == "unsupported"
    assert result["candidates"] == []
    assert result["reason"] == "statement nesting exceeds language bound"


def test_parenthesis_boundary_retains_meaning():
    source = "For all propositions p, " + "(" * 256 + "p" + ")" * 256
    assert formalize(source)["candidates"] == formalize("For all propositions p, p")["candidates"]


@pytest.mark.parametrize("body", ["¬" * 257 + "p", " → ".join(["p"] * 258)])
def test_other_recursive_syntax_cannot_evade_bound(body):
    with pytest.raises(ValueError, match="statement nesting"):
        Parser(body, {"p": "Prop"}).complete()


def test_lean_explanation_input_has_the_same_limit():
    with pytest.raises(ValueError, match="statement nesting"):
        parse_lean("(" * 995 + "True" + ")" * 995)
