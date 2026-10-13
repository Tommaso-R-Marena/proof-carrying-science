"""The language interface uses the existing typed IR and exposes fidelity scope."""
from pcs.experimental.prover import mathlib_cli_v4

class Environment:
    catalog=[]
    def __init__(self,**kwargs):pass
    def solve(self,formal,**kwargs):return {'status':'unknown','receipt':None,'pcs_authority':False}
    def close(self):pass

def test_supported_explanation_round_trip_does_not_claim_a_proof(monkeypatch):
    monkeypatch.setattr(mathlib_cli_v4,'MathlibEnvironmentV4',Environment)
    result=mathlib_cli_v4.run('For all natural numbers n, n + 0 equals n.',english=True)
    assert result['status']=='unknown' and result['pcs_authority'] is False
    assert result['explanation']['status']=='supported_restricted_fragment'
    assert result['explanation']['render_parse_round_trip'] is True
    assert result['explanation']['english_ir_round_trip'] is True
    assert 'kernel certified' in result['explanation']['scope']

def test_richer_statement_abstains_from_unsupported_explanation(monkeypatch):
    monkeypatch.setattr(mathlib_cli_v4,'MathlibEnvironmentV4',Environment)
    result=mathlib_cli_v4.run('∀ (s : Set Nat), s = s')
    assert result['explanation']['status']=='unsupported_fragment'
    assert result['status']=='unknown'

def test_unsupported_english_never_opens_a_lean_process(monkeypatch):
    def forbidden(**kwargs):raise AssertionError('uninterpreted English must abstain')
    monkeypatch.setattr(mathlib_cli_v4,'MathlibEnvironmentV4',forbidden)
    result=mathlib_cli_v4.run('Every connected graph is exciting.',english=True)
    assert result['status']=='unsupported' and result['pcs_authority'] is False


def test_initialization_failure_is_unresolved_not_success(monkeypatch):
    def unavailable(**kwargs):raise RuntimeError('Lean worker initialization failed')
    monkeypatch.setattr(mathlib_cli_v4,'MathlibEnvironmentV4',unavailable)
    result=mathlib_cli_v4.run('For all natural numbers n, n equals n.',english=True)
    assert result['status']=='unknown' and result['phase']=='environment_initialization'
    assert result['automatic_training_authorization'] is False and result['pcs_authority'] is False


def test_search_exhaustion_preserves_missing_kernel_receipt(monkeypatch):
    class Exhausted(Environment):
        def solve(self,*args,**kwargs):raise RuntimeError('Mathlib resource exhaustion')
    monkeypatch.setattr(mathlib_cli_v4,'MathlibEnvironmentV4',Exhausted)
    result=mathlib_cli_v4.run('For all natural numbers n, n equals n.',english=True)
    assert result['status']=='unknown' and result['result']['receipt'] is None
    assert result['result']['phase']=='proof_search'
