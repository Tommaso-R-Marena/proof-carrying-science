"""Independent replay adversarial tests: production module is never imported by
the checker. No mocks or synthetic affirmative Lean authority responses.
"""
import hashlib
import json
import random
import unittest

from universal_relu import Net, Term
from relu_certificate_export import build_certificate
from relu_certificate_replay import replay, ReplayError, canonical, PREFIX

TARGET = Net((Term(1,2,1),))


class IndependentReplayTests(unittest.TestCase):
    def fixture(self):
        old = Net((Term(1,3,-3),))
        candidate = Net((Term(1,3,-1),))
        return old, candidate, build_certificate(old,candidate,TARGET)

    def rewrite(self, raw, modify):
        env = json.loads(raw)
        modify(env["body"])
        env["sha256"] = hashlib.sha256(PREFIX+canonical(env["body"])).hexdigest()
        return canonical(env)

    def test_replay_exposes_real_outside_benchmark_forgetting(self):
        old,new,raw = self.fixture()
        result = replay(raw)
        self.assertFalse(result.no_forgetting)
        self.assertEqual(result.counterexample,4)
        self.assertGreater(result.new_max_error,result.old_max_error)
        self.assertEqual(old.predict(4),TARGET.predict(4))
        self.assertNotEqual(new.predict(4),TARGET.predict(4))

    def test_positive_preservation_and_robustness(self):
        old=Net((Term(1,0,0),))
        result=replay(build_certificate(old,TARGET,TARGET))
        self.assertTrue(result.no_forgetting)
        self.assertTrue(result.no_worse_in_window)
        self.assertEqual(result.new_max_error,0)

    def test_randomized_independent_replay_and_brute_force(self):
        rng=random.Random(842)
        for _ in range(300):
            def model():
                return Net(tuple(Term(rng.randint(-3,3), rng.randint(-8,8),
                                      rng.randint(-10,10))
                                 for _ in range(rng.randint(0,6))),
                           rng.randint(-5,5))
            old,new,target=model(),model(),model()
            result=replay(build_certificate(old,new,target,low=-25,high=25))
            for x in range(-120,121):
                if result.no_forgetting and old.predict(x)==target.predict(x):
                    self.assertEqual(new.predict(x),target.predict(x))
            if not result.no_forgetting:
                x=result.counterexample
                self.assertEqual(old.predict(x),target.predict(x))
                self.assertNotEqual(new.predict(x),target.predict(x))
            self.assertEqual(result.old_max_error,
                max(abs(old.predict(x)-target.predict(x)) for x in range(-25,26)))
            self.assertEqual(result.new_max_error,
                max(abs(new.predict(x)-target.predict(x)) for x in range(-25,26)))

    def test_forged_cell_rejected_even_with_updated_hash(self):
        _,_,raw=self.fixture()
        forged=self.rewrite(raw, lambda b: b["cells"][0][2].__setitem__(0,"999"))
        with self.assertRaisesRegex(ReplayError,"forged affine"):
            replay(forged)

    def test_missing_cell_rejected_even_after_rehash(self):
        _,_,raw=self.fixture()
        forged=self.rewrite(raw, lambda b: b["cells"].pop())
        with self.assertRaises(ReplayError):replay(forged)

    def test_missing_breakpoint_rejected_even_after_rehash(self):
        _,_,raw=self.fixture()
        forged=self.rewrite(raw, lambda b: b["cuts"].pop())
        with self.assertRaises(ReplayError):replay(forged)

    def test_false_positive_rejected_even_after_rehash(self):
        _,_,raw=self.fixture()
        def change(body):
            body["claim"]["no_forgetting"]=True
            body["claim"]["counterexample"]=None
        with self.assertRaises(ReplayError):
            replay(self.rewrite(raw,change))

    def test_altered_model_rejected_even_after_rehash(self):
        _,_,raw=self.fixture()
        forged=self.rewrite(raw,lambda b: b["old"]["terms"][0].__setitem__(1,"7"))
        with self.assertRaises(ReplayError):replay(forged)

    def test_removed_window_endpoint_rejected(self):
        _,_,raw=self.fixture()
        forged=self.rewrite(raw,lambda b: b["window_points"].pop())
        with self.assertRaises(ReplayError):replay(forged)

    def test_canonical_wire_and_duplicate_keys(self):
        _,_,raw=self.fixture()
        invalid=[raw+b"\n",b" "+raw,b"",b"\xff",
                 raw.replace(b'"body":',b'"body":{},"body":',1),
                 b'{"body":1,"sha256":"abc"}',raw+b" "*1024]
        for sample in invalid:
            with self.subTest(sample=sample[:30]):
                with self.assertRaises(ReplayError):replay(sample)

    def test_decimals_are_strict(self):
        _,_,raw=self.fixture()
        for value in ("-0","01","+1","1.0"," 1","1 ","01"*80):
            with self.subTest(value=value):
                def change(body):
                    body["candidate"]["terms"][0][1]=value
                with self.assertRaises(ReplayError):
                    replay(self.rewrite(raw,change))

    def test_distant_exact_correctness_root(self):
        old=Net((Term(1,1,-1000000),Term(-1,-1,1000000)))
        new=Net((),1)
        target=Net(())
        result=replay(build_certificate(old,new,target,low=-10,high=10))
        self.assertFalse(result.no_forgetting)
        self.assertEqual(result.counterexample,1000000)

    def test_huge_window_no_enumeration(self):
        bound=10**12
        result=replay(build_certificate(Net(()),TARGET,TARGET,
                                        low=-bound,high=bound))
        self.assertEqual(result.new_max_error,0)
        self.assertEqual(result.old_max_error,2*bound+1)

    def test_220_units_permutation(self):
        rng=random.Random(2901)
        terms=tuple(Term(rng.randint(-3,3),rng.randint(-8,8),rng.randint(-10,10))
                    for _ in range(220))
        old=Net(terms,7)
        new=Net(tuple(reversed(terms)),7)
        result=replay(build_certificate(old,new,old,low=-20,high=20))
        self.assertTrue(result.no_forgetting)
        self.assertEqual(result.new_max_error,0)

if __name__=="__main__":
    unittest.main()
