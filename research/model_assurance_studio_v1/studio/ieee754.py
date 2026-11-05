"""Exact value-semantics of IEEE-754 binary32, roundTiesToEven.

No host floating point is used by the rounder. Negative zero is identified with
positive zero: this is a numeric-value model, NOT a bit-level signed-zero or
exception-flag model. Non-finite results fail closed. The reference execution
model that uses this module explicitly forbids FMA, reassociation and FTZ/DAZ.
"""
from __future__ import annotations
from fractions import Fraction
import struct

MANTISSA_BITS=23
MAX_FINITE=Fraction((1<<24)-1, 1) * (1<<104)  # (2^24 - 1) * 2^(127-23)
MIN_SUBNORMAL=Fraction(1,1<<149)

class UnsupportedFP32(ValueError):
    pass


def _pow2(k:int)->Fraction:
    return Fraction(1<<k,1) if k>=0 else Fraction(1,1<<-k)


def _round_integer_even(q:Fraction)->int:
    n,rem=divmod(q.numerator,q.denominator)
    if 2*rem>q.denominator or (2*rem==q.denominator and (n&1)):
        n+=1
    return n


def from_bits(bits:int)->Fraction:
    if type(bits)!=int or not 0<=bits<1<<32:
        raise UnsupportedFP32('invalid binary32 word')
    exponent=(bits>>23)&255
    fraction=bits & ((1<<23)-1)
    if exponent==255:
        raise UnsupportedFP32('nonfinite binary32 word')
    if exponent==0:
        value=Fraction(fraction,1<<149)
    else:
        value=Fraction((1<<23)+fraction,1)*_pow2(exponent-127-23)
    return -value if (bits>>31) else value


def round_bits(value:Fraction)->int:
    """Round rational -> finite binary32 bits with exact nearest-even ties.

    Refuses overflow to infinity rather than returning a non-finite bound.
    Zero sign isn't a property of this numeric semantics.
    """
    q=Fraction(value)
    sign=(1<<31) if q<0 else 0
    q=abs(q)
    if not q:
        return sign
    if q>MAX_FINITE*2:
        raise UnsupportedFP32('binary32 overflow')
    # Find floor(log2(q)) using only exact integer comparisons.
    e=q.numerator.bit_length()-q.denominator.bit_length()
    if q<_pow2(e):e-=1
    elif q>=_pow2(e+1):e+=1
    if e < -126:
        mantissa=_round_integer_even(q * (1<<149))
        if mantissa==0:return sign
        if mantissa >=1<<23:
            return sign | (1<<23) # smallest normal float
        return sign | mantissa
    mantissa=_round_integer_even(q/_pow2(e-23))
    if mantissa >= 1<<24:
        mantissa=1<<23;e+=1
    if e>127:
        raise UnsupportedFP32('binary32 overflow')
    return sign | ((e+127)<<23) | (mantissa-(1<<23))


def round_value(value:Fraction)->Fraction:
    return from_bits(round_bits(Fraction(value)))


def float_to_bits(f:float)->int:
    return struct.unpack('<I',struct.pack('<f',f))[0]


def interval_round(interval:tuple[Fraction,Fraction])->tuple[Fraction,Fraction]:
    lo,hi=interval
    if lo>hi:raise UnsupportedFP32('inverted float interval')
    return round_value(lo),round_value(hi)


def add_interval(a,b):
    return interval_round((a[0]+b[0],a[1]+b[1]))


def times_constant(a,w):
    p=a[0]*w;q=a[1]*w
    return interval_round((min(p,q),max(p,q)))


def exact_word(value)->str:
    return f'{round_bits(Fraction(value)):08x}'
