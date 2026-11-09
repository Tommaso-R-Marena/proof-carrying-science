"""Exact finite-design falsification tests; no external measurements involved."""
import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from research.evidencekernel_stopping_v19.kernel import (
    FORMAT,RULE,RANK,Reject,digest,design,attempt_commitment,audit,prefix_rank
)
from research.evidencekernel_selective_v17.kernel import effect_stat

HERE=Path(__file__).parent

def protocol(n=4,k=2,H=3,x=None,cutoff=0,K=0):
    return {'format':FORMAT,'n':n,'k':k,'baseline_covariate':x or list(range(n)),
            'max_attempts':H,'accept_if_score_le':cutoff,'selection_rule':RULE,
            'candidate_law':'iid_with_replacement','null_ate_upper':'0','max_interval_misses':K,
            'confidence_alpha':'1/20','tie_rule':RANK}

def transcripts(d):
    """Enumerate exact possible terminal transcripts of variable length."""
    for t in range(1,d['H']+1):
        for prefix in itertools.product(d['rejected'],repeat=t-1):
            last=range(d['N']) if t==d['H'] else [i for i,a in enumerate(d['accepted']) if a]
            for terminal in last:
                yield prefix+(terminal,)

def report_for(p, d, seq, world):
    z=d['space'][seq[-1]]
    e={'attempts':[list(d['space'][j]) for j in seq],'selected_assignment':list(z),
       'observed_intervals':[str(world[i][int(i in z)]) for i in range(d['n'])]}
    pin=digest(p)
    return audit(p,e,protocol_pin=pin,attempts_pin=attempt_commitment(pin,e['attempts']))

class StoppingDesignTests(unittest.TestCase):
    def test_mass_and_prefix_rank_exactly_match_full_exhaustive_transcripts(self):
        for p in [protocol(3,1,2,cutoff=1),protocol(4,2,3,cutoff=2),
                  protocol(3,1,3,cutoff=0),protocol(4,2,2,cutoff=1000)]:
            d=design(p)
            weights=[0]*d['N'];ranks={}
            for seq in transcripts(d):
                t=len(seq);w=d['N']**(d['H']-t);idx=seq[-1];weights[idx]+=w
                r,M=prefix_rank(d,seq)
                key=(idx,t);ranks.setdefault(key,[]).append(r)
                self.assertEqual(M,d['R']**(t-1))
            self.assertEqual(weights,d['mass'])
            self.assertEqual(sum(weights),d['total'])
            for values in ranks.values():
                self.assertEqual(sorted(values),list(range(1,len(values)+1)))

    def test_superuniform_each_binary_world_under_variable_stop(self):
        # Exact global sample space with variable stopping-time weights.
        for p in [protocol(3,1,3,cutoff=1),protocol(4,2,2,cutoff=2)]:
            d=design(p)
            seqs=list(transcripts(d))
            for digits in itertools.product(range(4),repeat=d['n']):
                world=tuple(((v>>1)&1,v&1) for v in digits)
                stats=[effect_stat(world,z,d['n'],d['k']) for z in d['space']]
                observations=[]
                for seq in seqs:
                    idx=seq[-1];r,M=prefix_rank(d,seq);s=stats[idx]
                    gt=sum(m for m,a in zip(d['mass'],stats) if a>s)
                    eq=sum(m for m,a in zip(d['mass'],stats) if a==s)
                    observations.append((Fraction(gt,d['total'])+Fraction(r*eq,d['total']*M),d['N']**(d['H']-len(seq))))
                observed=sorted(set(pv for pv,_ in observations))
                for alpha in observed:
                    accepted_mass=sum(w for pv,w in observations if pv<=alpha)
                    self.assertLessEqual(Fraction(accepted_mass,d['total']),alpha)

    def test_composite_weak_null_rejection_coverage(self):
        p=protocol(3,1,2,cutoff=1);p['confidence_alpha']='1/10'
        d=design(p)
        for digits in itertools.product(range(4),repeat=3):
            w=tuple(((v>>1)&1,v&1) for v in digits)
            if sum(b-a for a,b in w)>0: continue
            rejects=0
            for seq in transcripts(d):
                r=report_for(p,d,seq,w)
                if Fraction(r['conditional_p'])<=Fraction(1,10):
                    rejects+=d['N']**(d['H']-len(seq))
            self.assertLessEqual(Fraction(rejects,d['total']),Fraction(1,10))

    def test_naively_assuming_uniform_allocation_breaks_five_percent_level(self):
        # Exact counterexample: stop after first balance-acceptable draw or
        # after the fourth attempt. Actual selected Z is *not uniform*.
        p=protocol(4,2,4,[0,1,2,3],2)
        d=design(p)
        self.assertEqual(d['mass'],[64,64,520,520,64,64])
        world=((1,1),(1,0),(1,0),(1,1))
        scores=[effect_stat(world,z,4,2) for z in d['space']]
        naive=correct=0
        for seq in transcripts(d):
            zid=seq[-1];r,M=prefix_rank(d,seq);threshold=scores[zid]
            weight=d['N']**(d['H']-len(seq))
            wrong=Fraction(sum(v>threshold for v in scores),d['N'])+Fraction(
                r*sum(v==threshold for v in scores),d['N']*M)
            right=Fraction(sum(m for m,v in zip(d['mass'],scores) if v>threshold),d['total'])+Fraction(
                r*sum(m for m,v in zip(d['mass'],scores) if v==threshold),d['total']*M)
            naive+=weight*(wrong<=Fraction(1,20))
            correct+=weight*(right<=Fraction(1,20))
        self.assertEqual(Fraction(naive,d['total']),Fraction(79,1296))
        self.assertEqual(Fraction(correct,d['total']),Fraction(13,1296))
        self.assertGreater(Fraction(naive,d['total']),Fraction(1,20))

    def test_mass_calculation_scales_without_enumerating_attempt_sequences(self):
        p=protocol(8,4,128,[0,0,0,0,1,1,1,1],4)
        d=design(p)
        self.assertEqual(len(d['space']),70)
        self.assertEqual(sum(d['mass']),70**128)
        self.assertGreater(len(str(d['total'])),200)

    def test_all_accepted_and_none_accepted_extremes(self):
        for cutoff in (0,10000):
            p=protocol(3,1,4,[0,1,2],cutoff);d=design(p)
            for seq in itertools.islice(transcripts(d),30):
                rank,M=prefix_rank(d,seq)
                self.assertTrue(1<=rank<=M)
            if cutoff==10000:self.assertEqual(d['R'],0)
            else:self.assertGreater(d['R'],0)

    def test_closeout_fails_on_hidden_early_acceptance(self):
        p=protocol(4,2,3,cutoff=2)
        d=design(p)
        accept=next(i for i,a in enumerate(d['accepted']) if a)
        bad=next(i for i,a in enumerate(d['accepted']) if not a)
        e={'attempts':[list(d['space'][accept]),list(d['space'][bad]),list(d['space'][bad])],
           'selected_assignment':list(d['space'][bad]),'observed_intervals':['01']*4}
        pin=digest(p)
        with self.assertRaisesRegex(Reject,'earlier stopping'):
            audit(p,e,protocol_pin=pin,attempts_pin=attempt_commitment(pin,e['attempts']))

    def test_missing_final_attempt_and_forged_transcript_rejected(self):
        p=protocol(4,2,3,cutoff=2);d=design(p)
        bad=next(i for i,a in enumerate(d['accepted']) if not a)
        good=next(i for i,a in enumerate(d['accepted']) if a)
        attempts=[list(d['space'][bad]),list(d['space'][good])]
        e={'attempts':attempts,'selected_assignment':attempts[-1],'observed_intervals':['01']*4}
        pin=digest(p);original_pin=attempt_commitment(pin,attempts)
        self.assertTrue(audit(p,e,protocol_pin=pin,attempts_pin=original_pin))
        e2={**e,'attempts':attempts[::-1]}
        with self.assertRaises(Reject):audit(p,e2,protocol_pin=pin,attempts_pin=original_pin)
        e3={**e,'attempts':attempts[:1],'selected_assignment':attempts[0]}
        with self.assertRaisesRegex(Reject,'stopped before'):
            audit(p,e3,protocol_pin=pin,attempts_pin=attempt_commitment(pin,e3['attempts']))
        with self.assertRaises(Reject):audit(p,e,protocol_pin=pin,attempts_pin='0'*64)

    def test_independent_javascript_agrees_on_demo_and_generated_trials(self):
        if subprocess.run(['node','--version'],capture_output=True).returncode: self.skipTest('node missing')
        for case in [0,1,2,3,4,5,6,7]:
            n=4 if case<4 else 5;k=2;H=3
            p=protocol(n,k,H,cutoff=[0,2,4,1000][case%4]);d=design(p)
            seq=list(transcripts(d))[(case*2)%len(list(transcripts(d)))]
            w=tuple(((i+case)%2,(i+case+1)%2) for i in range(n))
            e={'attempts':[list(d['space'][i]) for i in seq],
               'selected_assignment':list(d['space'][seq[-1]]),
               'observed_intervals':[str(w[i][int(i in d['space'][seq[-1]])]) for i in range(n)]}
            pin=digest(p);ap=attempt_commitment(pin,e['attempts'])
            py=audit(p,e,protocol_pin=pin,attempts_pin=ap)
            with tempfile.TemporaryDirectory() as tmp:
                a,b=Path(tmp)/'p.json',Path(tmp)/'e.json';a.write_text(json.dumps(p));b.write_text(json.dumps(e))
                cmd=['node',str(HERE/'independent.js'),str(a),str(b),pin,ap]
                result=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                js=json.loads(result.stdout)
            self.assertEqual(py,js)

if __name__=='__main__':unittest.main()
