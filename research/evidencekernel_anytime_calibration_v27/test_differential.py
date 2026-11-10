"""Independent JS BigInt verification across 120 exact small models and full demo."""
import json,random,subprocess,unittest
from pathlib import Path
from fractions import Fraction as F
from research.evidencekernel_anytime_calibration_v27 import kernel as k

P=Path(__file__).parent
class DifferentialTests(unittest.TestCase):
    def test_independent_mixture_and_upper_120_cases(self):
        rng=random.Random(1977)
        data=[]
        for _ in range(120):
            n=rng.randint(1,28);s=rng.randint(0,n);D=rng.choice([16,32,64,100])
            ratios=[F(1,2),F(3,4),F(7,8)]
            u=F(rng.randint(1,D-1),D);beta=F(1,rng.choice([4,8,16,32]))
            upper=k.invert_upper(n,s,beta,D,ratios)
            data.append({'n':n,'s':s,'D':D,'u':str(u),'beta':str(beta),
                         'python_e':str(k.e_upper(n,s,u,ratios)),
                         'python_upper':str(upper[0]),'python_mixture':str(upper[1]),
                         'crossed':upper[2]})
        js="""const fs=require('node:fs');const k=require('./independent.js');
 const rows=JSON.parse(fs.readFileSync(0,'utf8'));const ratios=['1/2','3/4','7/8'].map(require('../evidencekernel_propensity_v25/independent').rat);
 const v25=require('../evidencekernel_propensity_v25/independent');
 const result=rows.map(r=>{const u=v25.rat(r.u),beta=v25.rat(r.beta),out=k.invertUpper(r.n,r.s,beta,r.D,ratios);
 return [v25.out(k.eUpper(r.n,r.s,u,ratios)),v25.out(out[0]),v25.out(out[1]),out[2]]});
 process.stdout.write(JSON.stringify(result));"""
        done=subprocess.run(['node','-e',js],cwd=P,input=json.dumps(data),text=True,capture_output=True,timeout=35)
        self.assertEqual(done.returncode,0,done.stderr)
        actual=json.loads(done.stdout)
        for expected,jsout in zip(data,actual):
            self.assertEqual(jsout,[expected['python_e'],expected['python_upper'],expected['python_mixture'],expected['crossed']])

    def test_complete_json_reports_agree(self):
        files=['example_contract.json','example_records.json','example_study_protocol.json','example_study_records.json']
        pins=['example_contract_pin.txt','example_records_pin.txt','example_study_pin.txt','example_evidence_pin.txt']
        cmd=['node','independent.js']+files+[(P/x).read_text().strip() for x in pins]
        out=subprocess.run(cmd,cwd=P,text=True,capture_output=True,timeout=40)
        self.assertEqual(out.returncode,0,out.stderr)
        self.assertEqual(json.loads(out.stdout),json.loads((P/'example_report.json').read_text()))

if __name__=='__main__':unittest.main()
