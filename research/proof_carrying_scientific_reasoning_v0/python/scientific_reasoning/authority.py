from __future__ import annotations

from .meet_tables import RANK as _RANK_STR, TIE_ORDER as _TIE_STR, meet_str
from .syntax import Authority

_RANK = {Authority[k]: v for k, v in _RANK_STR.items()}
_TIE = {Authority[k]: v for k, v in _TIE_STR.items()}


def rank(a: Authority) -> int:
    return _RANK[a]


def meet(a: Authority, b: Authority) -> Authority:
    return Authority(meet_str(a.value, b.value))
