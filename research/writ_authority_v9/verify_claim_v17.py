"""Writ/17 bounded differential first-claim oracle.

Independent from the runtime. Compares executable local receiver state transitions
against a separately enumerated declaration, across all event sequences up to 6.
This is bounded verification, not a Lean kernel proof or OS refinement.
"""
from itertools import product
import json

EMPTY=("free",None)
EVENTS=[("reserve",0),("reserve",1),("write",0),("write",1),
        ("ack",0),("ack",1),("replay",0),("replay",1),("crash",None)]


def executable(state,event):
    phase,claimed=state
    kind,requested=event
    if phase=="free" and kind=="reserve":return ("claimed",requested)
    if phase=="claimed" and kind=="write" and requested==claimed:
        return ("written",claimed)
    if phase=="written" and kind=="ack" and requested==claimed:
        return ("signed",claimed)
    if phase=="signed" and kind=="replay" and requested==claimed:
        return state
    if kind=="crash":
        if phase in ("claimed","written"):return ("uncertain",claimed)
        if phase=="signed":return state
    return None


def independent_relation(state,event):
    legal=[]
    for b in (0,1):
        legal.extend([
            (EMPTY,("reserve",b),("claimed",b)),
            (("claimed",b),("write",b),("written",b)),
            (("written",b),("ack",b),("signed",b)),
            (("signed",b),("replay",b),("signed",b)),
            (("claimed",b),("crash",None),("uncertain",b)),
            (("written",b),("crash",None),("uncertain",b)),
            (("signed",b),("crash",None),("signed",b)),
        ])
    for source,act,target in legal:
        if source==state and act==event:return target
    return None


def main():
    checked=valid=0
    for length in range(7):
        for sequence in product(EVENTS,repeat=length):
            checked+=1
            a=b=EMPTY
            signed=[]
            for event in sequence:
                a=executable(a,event) if a is not None else None
                b=independent_relation(b,event) if b is not None else None
                assert a==b,(sequence,a,b)
                if a is None:break
                if event[0]=="ack":signed.append(event[1])
            if a is not None:
                valid+=1
                assert len(signed)<=1 and len(set(signed))<=1
    print(json.dumps({"result":"PASS","sequences_checked":checked,
                      "valid_sequences":valid,"max_length":6},sort_keys=True))


if __name__=="__main__":
    main()
