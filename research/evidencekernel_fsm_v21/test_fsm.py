"""Independent small-model checks of the finite-state design and CDF."""
from fractions import Fraction
from itertools import product
import unittest
from research.evidencekernel_fsm_v21.kernel import design, conditional_right_cdf, audit, attempt_commitment
from research.evidencekernel_selective_v17.kernel import digest, effect_stat

def protocol():
    n,k,N=4,2,6
    return {
        "format":"pcs-evidencekernel-finite-state-v21",
        "n":n,"k":k,"max_attempts":3,"initial_state":0,
        "baseline_covariate":[0,2,5,9],
        "candidate_law":"registered_finite_state_outcome_blind",
        "candidate_weights_by_state":[[1]*N]+[
            [int(j==i) for j in range(N)] for i in range(N)],
        "reject_next_state":[list(range(1,N+1))]+[[0]*N for _ in range(N)],
        "accept_if_score_le_by_state":[0]*(N+1),
        "selection_rule":"first_state_acceptable_else_last",
        "null_ate_upper":"0","max_interval_misses":0,
        "confidence_alpha":"1/20",
        "tie_rule":"conditional_lex_right_cdf_given_selected_and_stop"
    }

class ExactFSMTests(unittest.TestCase):
    def test_dependent_uniform_marginals_counterexample(self):
        p=protocol()
        d=design(p)
        self.assertTrue(all(not x for row in d["accepted"] for x in row))
        self.assertEqual(d["mass"],[Fraction(1,6)]*6)
        bad=good=Fraction(0)
        for first in range(6):
            for terminal in range(6):
                ids=[first,first,terminal]
                u,event,point=conditional_right_cdf(d,ids)
                self.assertEqual(u,Fraction(first+1,6))
                self.assertEqual(event,Fraction(1,6))
                self.assertEqual(point,Fraction(1,36))
                if Fraction(6*first+first+1,36)<=Fraction(1,20):
                    bad+=Fraction(1,36)
                if u<=Fraction(1,20):
                    good+=Fraction(1,36)
        self.assertEqual(bad,Fraction(1,6))
        self.assertEqual(good,0)

    def test_all_four_unit_sharp_worlds_superuniform(self):
        d=design(protocol())
        for digits in product(range(4),repeat=4):
            world=tuple(((v>>1)&1,v&1) for v in digits)
            stats=[effect_stat(world,z,4,2) for z in d["space"]]
            points=[]
            for first in range(6):
                for terminal in range(6):
                    u,*_=conditional_right_cdf(d,[first,first,terminal])
                    observed=stats[terminal]
                    gt=sum((q for q,t in zip(d["mass"],stats) if t>observed),Fraction(0))
                    eq=sum((q for q,t in zip(d["mass"],stats) if t==observed),Fraction(0))
                    points.append((gt+u*eq,Fraction(1,36)))
            for alpha in set(x for x,_ in points):
                self.assertLessEqual(sum((w for x,w in points if x<=alpha),Fraction(0)),alpha)

    def test_validated_bounded_ATE_replay_and_tampering(self):
        p=protocol()
        d=design(p)
        ids=[0,0,1]
        e={"attempts":[list(d["space"][i]) for i in ids],
           "selected_assignment":list(d["space"][ids[-1]]),
           "observed_intervals":["01"]*4}
        pin=digest(p)
        ap=attempt_commitment(pin,e["attempts"])
        r=audit(p,e,protocol_pin=pin,attempts_pin=ap)
        self.assertEqual(r["conditional_rank"],"1/6")
        self.assertEqual(r["state_history"],[0,1,0])
        self.assertTrue(Fraction(0) <= Fraction(r["conditional_p"]) <= 1)
        with self.assertRaises(ValueError):
            audit(p,e,protocol_pin=pin,attempts_pin="0"*64)

if __name__=="__main__":
    unittest.main()
