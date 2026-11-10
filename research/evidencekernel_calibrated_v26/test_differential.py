"""Separate Node.js BigInt calibration oracle, randomized exact cases and full report."""
from __future__ import annotations
import json
from fractions import Fraction as F
from pathlib import Path
import random
import subprocess
import unittest
from research.evidencekernel_calibrated_v26 import kernel as py

HERE=Path(__file__).parent

class CrossLanguageTests(unittest.TestCase):
    def test_cross_language_complete_synthetic_report(self):
        args=[str(HERE/n) for n in ('calibration_contract.json','calibration_records.json',
                                    'study_protocol.json','study_records.json')]
        pins=[(HERE/n).read_text().strip() for n in
              ('calibration_contract_pin.txt','calibration_records_pin.txt',
               'study_protocol_pin.txt','study_records_pin.txt')]
        result=subprocess.run(['node',str(HERE/'independent.js'),*args,*pins],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),json.loads((HERE/'example_report.json').read_text()))

    def test_exact_randomized_binomial_grid_differential(self):
        rng=random.Random(26002)
        rows=[]
        for i in range(130):
            n=rng.randint(16,125)
            x=rng.randint(0,n)
            D=rng.choice([16,32,64,100,256])
            beta=rng.choice([F(1,4),F(1,10),F(1,20),F(1,300)])
            upper,tail=py.find_upper(n,x,beta,D)
            rows.append({'n':n,'x':x,'D':D,'beta':str(beta),
                         'upper':str(upper),'tail':str(tail)})
        script="""
        const fs=require('fs');const m=require(process.argv[1]);
        const rows=JSON.parse(fs.readFileSync(0,'utf8'));
        const out=rows.map(r=>{const [u,t]=m.findUpper(r.n,r.x,require(process.argv[2]).rat(r.beta),r.D);
          return [require(process.argv[2]).out(u),require(process.argv[2]).out(t)];});
        console.log(JSON.stringify(out));
        """
        result=subprocess.run(['node','-e',script,str(HERE/'independent.js'),
                               str(HERE.parent/'evidencekernel_propensity_v25'/'independent.js')],
                              input=json.dumps(rows),capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[[v['upper'],v['tail']] for v in rows])

    def test_anytime_calibration_cross_language(self):
        import tempfile
        from research.evidencekernel_calibrated_v26.test_kernel import frozen
        c,r,p,e=frozen()
        c['sample_size_policy']='anytime_within_registered_range'
        c['minimum_sample_sizes']=[500,500,500]
        cp=py.digest(c);rp=py.calibration_evidence_pin(cp,r)
        cert=py.calibrate(c,r,contract_pin=cp,records_pin=rp)
        p['propensity_upper_by_state']=cert['propensity_ceiling_by_state']
        pp=py.digest(p);ep=py.v25.evidence_digest(pp,e)
        expected=py.audit(c,r,p,e,calibration_contract_pin=cp,
          calibration_records_pin=rp,study_protocol_pin=pp,study_records_pin=ep)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)
            for name,value in zip(('c','r','p','e'),(c,r,p,e)):
                (path/(name+'.json')).write_text(json.dumps(value))
            got=subprocess.run(['node',str(HERE/'independent.js'),
              *(str(path/(n+'.json')) for n in ('c','r','p','e')),
              cp,rp,pp,ep],capture_output=True,text=True,timeout=30)
            self.assertEqual(got.returncode,0,got.stderr)
            self.assertEqual(json.loads(got.stdout),expected)

    def test_both_independent_parsers_fail_on_duplicate_calibration_json(self):
        import tempfile
        from research.evidencekernel_calibrated_v26.test_kernel import frozen
        c,r,p,e=frozen()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)
            inputs=[c,r,p,e]
            for name,item in zip(('c','r','p','e'),inputs):
                (path/(name+'.json')).write_text(json.dumps(item))
            (path/'r.json').write_text('{"stage":"prestudy","stage":"prestudy"}')
            result=subprocess.run(['node',str(HERE/'independent.js'),
              *(str(path/(n+'.json')) for n in ('c','r','p','e')),
              *(['0'*64]*4)],capture_output=True,text=True,timeout=30)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('duplicate JSON key',result.stderr)

if __name__=='__main__':unittest.main()
