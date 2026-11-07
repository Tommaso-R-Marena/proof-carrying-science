"""Offline illustrative simulation. Real Ed25519 signatures, synthetic SQLite effects."""
import hashlib
import json
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .gate import Denied, Gate, digest, public_hex, sign

T = 1_800_000_000


def run():
    owner, reviewer, manager, worker = [Ed25519PrivateKey.generate() for _ in range(4)]
    with tempfile.TemporaryDirectory() as scratch:
        gate = Gate(Path(scratch)/"effects.db", root_public=public_hex(owner),
                    reviewer_public=public_hex(reviewer), clock=lambda: T)
        leases = [sign(owner, "grant", {"id":"root-lease","issuer":public_hex(owner),
            "subject":public_hex(manager),"parent":None,"caps":["append:public/report", "append:private/notes"],
            "delegate":True,"epoch":0,"not_before":T-10,"expires":T+100})]
        leases += [sign(manager, "grant", {"id":"child-lease","issuer":public_hex(manager),
            "subject":public_hex(worker),"parent":"root-lease","caps":["append:public/report", "append:private/notes"],
            "delegate":False,"epoch":0,"not_before":T-10,"expires":T+50})]

        def request(cap, payload, reqid):
            snap = gate.snapshot()
            target = cap.split(":",1)[1]
            body = {"id":reqid,"agent":public_hex(worker),"cap":cap,"payload":payload,
                    "expected_version":snap["version"],"epoch":snap["epoch"],
                    "preimage_sha256":hashlib.sha256(snap["resources"][target].encode("ascii")).hexdigest()}
            return sign(worker,"action",body)

        def review(req, nonce):
            a=req["body"]
            return sign(reviewer,"review",{"id":nonce,"action_sha256":digest(a),
                "chain_sha256":digest(leases),"epoch":a["epoch"],"expected_version":a["expected_version"],
                "preimage_sha256":a["preimage_sha256"],"expires":T+30})

        outcome = []
        safe=request("append:public/report","summary", "safe")
        gated=gate.apply(safe,leases)
        outcome.append({"case":"ordinary delegated report","decision":"accept","version":gated["version"]})
        private=request("append:private/notes","internal", "private")
        for name, candidate, approval in [
            ("private write without reviewer",private,None),
            ("forged reviewer signature",private,sign(worker,"review",review(private,"r2")["body"])),
        ]:
            try: gate.apply(candidate,leases,approval)
            except Denied: outcome.append({"case":name,"decision":"deny"})
            else: raise RuntimeError("unexpected unsafe acceptance")
        approved=review(private,"r3")
        gate.apply(private,leases,approved)
        outcome.append({"case":"private write, exact reviewer approval","decision":"accept"})
        stale = private
        try: gate.apply(stale,leases,approved)
        except Denied: outcome.append({"case":"replay exact approval after state advanced","decision":"deny"})
        else: raise RuntimeError("replay accepted")
        command=sign(owner,"rotate",{"id":"revoke-all", "kind":"rotate", "expected_version":2, "epoch":0})
        gate.rotate_epoch(command)
        new_action=request("append:public/report","post-revocation","revoked")
        try: gate.apply(new_action,leases)
        except Denied: outcome.append({"case":"delegation after revocation epoch","decision":"deny"})
        else: raise RuntimeError("revocation bypassed")
        last=gate.snapshot()
        return {"experiment":"synthetic local authority, no external effects", "outcomes":outcome,
                "verified_events":gate.replay(expected_head=last["head"])["events_verified"],
                "accepted":sum(o["decision"]=="accept" for o in outcome),
                "rejected":sum(o["decision"]=="deny" for o in outcome)}


if __name__ == "__main__":
    print(json.dumps(run(),indent=2))
