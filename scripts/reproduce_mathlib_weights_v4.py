import gzip,hashlib,json,time
from pathlib import Path
import torch
from pcs.experimental.prover.premise_policy_v4 import PremisePolicy,save_training_checkpoint,load_training_checkpoint
from pcs.experimental.prover.premise_learning_v4 import train_supervised
from pcs.experimental.prover.induction_ir import digest
folder=Path('research/mathlib-learning-v4-kernel-checked'); out=Path('research/mathlib-weight-reproduction-v4')
if out.exists():raise ValueError('Preserve immutable reproduction')
out.mkdir(); episodes=json.load(gzip.open(folder/'checked-training.json.gz','rt'));catalog=json.load(gzip.open(folder/'catalog.json.gz','rt'))
protocol=json.loads((folder/'protocol.json').read_text());trained=json.loads((folder/'training-summary.json').read_text())['models']
assert digest(episodes)==protocol['training_data_sha256'] and digest(catalog)==protocol['catalog_sha256']
rows=[]
for r in trained:
 torch.manual_seed(r['seed']);model=PremisePolicy(catalog,architecture=r['architecture']);tick=time.monotonic()
 optimizer,stats=train_supervised(model,episodes,epochs=10,seed=r['seed'])
 file=out/f"{r['architecture']}-{r['seed']}-resume.json"
 sha=save_training_checkpoint(file,model,optimizer,{'next_epoch':stats['next_epoch'],'protocol_sha256':digest(protocol)})
 resumed,optimizer,progress=load_training_checkpoint(file,sha,catalog)
 optimizer,second=train_supervised(resumed,episodes,epochs=20,seed=r['seed'],optimizer=optimizer,start_epoch=progress['next_epoch'],restore_rng=True)
 original=PremisePolicy.load(folder/r['checkpoint'],r['checkpoint_sha256'],catalog)
 equal={name:torch.equal(value,original.state_dict()[name]) for name,value in resumed.state_dict().items()}
 assert all(equal.values())
 rows.append({'architecture':r['architecture'],'seed':r['seed'],'checkpoint_sha256':r['checkpoint_sha256'],'all_parameter_tensors_bitwise_equal':True,'tensor_comparisons':len(equal),'wall_seconds':time.monotonic()-tick,'actual_optimizer_rng_resume':True,'original_checkpoint_bytes_unchanged':hashlib.sha256((folder/r['checkpoint']).read_bytes()).hexdigest()==r['checkpoint_sha256']})
 print(json.dumps(rows[-1]),flush=True)
(out/'summary.json').write_text(json.dumps({'format':'pcs-independent-supervised-weight-reproduction-v4','scope':'Retraining from the previously independently checked eligible training data; never reads final proof solutions; metadata timing is not byte-identical','models':rows},indent=2)+'\n')
