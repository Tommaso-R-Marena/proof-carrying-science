"""Independent Python-vs-Node test of entire exact design and ATE inversion."""
import json
import random
import subprocess
import unittest
from pathlib import Path
from kernel import FORMAT, audit, design, digest

HERE=Path(__file__).parent


class IndependentComparison(unittest.TestCase):
    def test_differential_random_trials(self):
        rnd=random.Random(10926)
        for trial in range(35):
            n=rnd.randint(3,6);k=rnd.randint(1,n-1);b=rnd.randint(1,5)
            law=rnd.choice(['iid_with_replacement','ordered_without_replacement'])
            x=[rnd.randint(-2,3) for _ in range(n)]
            p={'format':FORMAT,'n':n,'k':k,'baseline_covariate':x,'candidate_draws':b,
               'candidate_law':law,'selection_rule':'minimum_absolute_baseline_imbalance_first_tie',
               'null_ate_upper':rnd.choice(['-1/2','0','1/2']),
               'max_interval_misses':rnd.randint(0,2),'confidence_alpha':rnd.choice(['1/20','1/4']),
               'randomizer_support':16,'randomizer_rule':'independent_right_endpoint_uniform'}
            if law=='ordered_without_replacement' and b>len(design({**p,'candidate_draws':1})[0]):continue
            space,scores,mass,total=design(p)
            if law=='ordered_without_replacement':
                attempts=rnd.sample(range(len(space)),b)
            else:
                attempts=[rnd.randrange(len(space)) for _ in range(b)]
            win=min(attempts,key=lambda i:scores[i]);z=space[win]
            e={'attempts':[list(space[i]) for i in attempts],
               'selected_assignment':list(z),
               'observed_intervals':[rnd.choice(['0','1','01']) for _ in range(n)]}
            pin=digest(p)
            u=rnd.choice([None,1,4,8,15,16])
            py=audit(p,e,external_pin=pin,external_uniform_index=u)
            cmd=['node','-e',"const m=require('./independent.js');const p=JSON.parse(process.argv[1]),e=JSON.parse(process.argv[2]);console.log(JSON.stringify(m.audit(p,e,process.argv[3],process.argv[4]===undefined?null:Number(process.argv[4]))))",json.dumps(p),json.dumps(e),pin]+([] if u is None else [str(u)])
            r=subprocess.run(cmd,cwd=HERE,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            js=json.loads(r.stdout)
            self.assertEqual(py,js,f'Differential mismatch in case {trial}')

    def test_large_draw_histogram(self):
        p={'format':FORMAT,'n':8,'k':4,'baseline_covariate':[0,0,0,0,1,1,1,1],
           'candidate_draws':2048,'candidate_law':'iid_with_replacement',
           'selection_rule':'minimum_absolute_baseline_imbalance_first_tie',
           'null_ate_upper':'0','max_interval_misses':0,'confidence_alpha':'1/20',
           'randomizer_support':16,'randomizer_rule':'independent_right_endpoint_uniform'}
        _,_,mass,total=design(p)
        self.assertEqual(total,70**2048)
        cmd=['node','-e',"const d=require('./independent.js').design(JSON.parse(process.argv[1]));console.log(JSON.stringify({denom:String(d.denom),mass:d.mass.map(String)}))",json.dumps(p)]
        r=subprocess.run(cmd,cwd=HERE,text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr)
        js=json.loads(r.stdout)
        self.assertEqual(js['denom'],str(total))
        self.assertEqual(js['mass'],list(map(str,mass)))


if __name__=='__main__':unittest.main()
