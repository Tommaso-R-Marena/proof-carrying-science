import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("lean_audit", Path(__file__).parents[1] / "scripts/audit_lean_source.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_nested_comments_strings_and_escaped_quotes_do_not_forge_declarations():
    code = module.active_code('/- axiom documentation /- unsafe -/ sorry -/\n-- admit\ndef text := "extern \\" native_decide"\ntheorem actual : True := by trivial')
    assert not module.FORBIDDEN.search(code)
    assert 'theorem actual' in code


@pytest.mark.parametrize("token", ["sorry", "admit", "axiom", "unsafe", "implemented_by", "extern", "native_decide"])
def test_active_admissions_and_escape_hatches_are_rejected_including_indented_tactics(token):
    assert module.FORBIDDEN.search(module.active_code(f'/- harmless -/\ntheorem t : True := by\n  {token}\n'))


def test_comment_cannot_hide_following_code_and_incomplete_lexing_fails():
    assert module.FORBIDDEN.search(module.active_code('/- explanation -/ axiom bad : False'))
    with pytest.raises(ValueError):
        module.active_code('/- unclosed')


def test_char_literals_and_primed_identifiers_do_not_change_comment_or_string_state():
    source = r'''def chars := ['"', '\\', '\n', '\'', '-']
theorem t {a a' : Nat} : a = a' → True := by trivial
/- outer /- inner -/ -/
axiom forbidden : False'''
    code = module.active_code(source)
    assert 'a\'' in code
    assert module.FORBIDDEN.search(code).group() == 'axiom'


def test_raw_strings_preserve_following_active_code():
    code = module.active_code('def s := r##"sorry " /- axiom --"##\nunsafe def bad := 1')
    assert module.FORBIDDEN.search(code).group() == 'unsafe'
    with pytest.raises(ValueError):
        module.active_code('r#"unterminated')
