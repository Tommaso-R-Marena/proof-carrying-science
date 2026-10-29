"""Exact rational linear algebra with residual certificates."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import List, Sequence, Tuple


Matrix = List[List[Fraction]]
Vector = List[Fraction]


def _q(x) -> Fraction:
    return x if isinstance(x, Fraction) else Fraction(x)


def mat_mul(A: Matrix, B: Matrix) -> Matrix:
    n, m, p = len(A), len(A[0]), len(B[0])
    assert len(B) == m
    out = [[Fraction(0) for _ in range(p)] for _ in range(n)]
    for i in range(n):
        for k in range(m):
            for j in range(p):
                out[i][j] += A[i][k] * B[k][j]
    return out


def mat_vec(A: Matrix, x: Vector) -> Vector:
    return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]


def vec_sub(a: Vector, b: Vector) -> Vector:
    return [a[i] - b[i] for i in range(len(a))]


def inf_norm_vec(x: Vector) -> Fraction:
    return max((abs(v) for v in x), default=Fraction(0))


def inf_norm_mat(A: Matrix) -> Fraction:
    return max((sum(abs(v) for v in row) for row in A), default=Fraction(0))


@dataclass
class LinearResidualCertificate:
    A: Matrix
    b: Vector
    x_hat: Vector
    residual: Vector
    residual_inf_norm: Fraction

    def to_json(self) -> dict:
        return {
            "residual_inf_norm": str(self.residual_inf_norm),
            "residual": [str(r) for r in self.residual],
            "x_hat": [str(x) for x in self.x_hat],
        }


def residual_certificate(A: Matrix, b: Vector, x_hat: Vector) -> LinearResidualCertificate:
    Ax = mat_vec(A, x_hat)
    r = vec_sub(Ax, b)
    return LinearResidualCertificate(A, b, x_hat, r, inf_norm_vec(r))


def solve_2x2(A: Matrix, b: Vector) -> Vector:
    """Exact Cramer solve for 2×2; raises if det = 0."""
    a, b12, c, d = A[0][0], A[0][1], A[1][0], A[1][1]
    det = a * d - b12 * c
    if det == 0:
        raise ZeroDivisionError("singular matrix")
    x = (d * b[0] - b12 * b[1]) / det
    y = (-c * b[0] + a * b[1]) / det
    return [x, y]


def gershgorin_disks(A: Matrix) -> List[Tuple[Fraction, Fraction]]:
    """Return (center, radius) disks with rational centers/radii on the real line projection.

    For real matrices, each eigenvalue lies in ∪_i [a_ii - R_i, a_ii + R_i]
    where R_i = Σ_{j≠i} |a_ij|.
    """
    disks = []
    n = len(A)
    for i in range(n):
        center = A[i][i]
        radius = sum(abs(A[i][j]) for j in range(n) if j != i)
        disks.append((center, radius))
    return disks


def gershgorin_real_enclosure(A: Matrix) -> Tuple[Fraction, Fraction]:
    disks = gershgorin_disks(A)
    lo = min(c - r for c, r in disks)
    hi = max(c + r for c, r in disks)
    return lo, hi
