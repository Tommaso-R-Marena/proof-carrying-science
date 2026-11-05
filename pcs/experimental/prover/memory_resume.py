"""Hash-bound CPU Adam/RNG continuation in bounded JSON, never pickle."""
import hashlib,json,math
from pathlib import Path
import torch
from .memory_model import MemoryNetwork

def save(model,optimizer,folder,metadata):
    folder=Path(folder)
    if folder.exists():raise ValueError('fresh resume directory required')
    if not isinstance(optimizer,torch.optim.Adam) or len(optimizer.param_groups)!=1 or any(p.device.type!='cpu' for p in model.parameters()):raise ValueError('CPU single-group Adam required')
    group=optimizer.param_groups[0]
    if [id(p) for p in group['params']]!=[id(p) for p in model.parameters()]:raise ValueError('optimizer/model binding mismatch')
    if any(group[k] for k in ['amsgrad','maximize','capturable','differentiable']) or group.get('fused') or group.get('foreach'):raise ValueError('unsupported Adam mode')
    state=optimizer.state_dict();encoded={}
    for index,row in state['state'].items():
        if set(row)!={'step','exp_avg','exp_avg_sq'}:raise ValueError('unsupported Adam state')
        encoded[str(index)]={k:v.detach().cpu().tolist() for k,v in row.items()}
    folder.mkdir(parents=True);model_sha=model.save(folder/'model.json',metadata)
    value={'format':'pcs-cpu-adam-resume-v1','torch':torch.__version__,'model_sha256':model_sha,
        'hyperparameters':{k:group[k] for k in ['lr','betas','eps','weight_decay']},
        'state':encoded,'rng_state':torch.get_rng_state().tolist(),'metadata':metadata}
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if len(raw)>4_000_000:raise ValueError('resume size bound')
    (folder/'optimizer.json').write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def load(folder,expected_sha):
    folder=Path(folder);raw=(folder/'optimizer.json').read_bytes()
    if len(raw)>4_000_000 or hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('resume integrity')
    value=json.loads(raw)
    if set(value)!={'format','torch','model_sha256','hyperparameters','state','rng_state','metadata'} or value['format']!='pcs-cpu-adam-resume-v1' or value['torch']!=torch.__version__:raise ValueError('resume version')
    hp=value['hyperparameters']
    if set(hp)!={'lr','betas','eps','weight_decay'} or type(hp['betas']) is not list or len(hp['betas'])!=2:raise ValueError('Adam configuration')
    numbers=[hp['lr'],hp['eps'],hp['weight_decay'],*hp['betas']]
    if any(type(x) not in {int,float} or not math.isfinite(x) for x in numbers) or not 0<hp['lr']<=1 or not 0<hp['eps']<1 or hp['weight_decay']!=0 or any(not 0<=b<1 for b in hp['betas']):raise ValueError('Adam numeric bounds')
    model=MemoryNetwork.load(folder/'model.json',value['model_sha256']);parameters=list(model.parameters())
    optimizer=torch.optim.Adam(parameters,**{**hp,'betas':tuple(hp['betas'])});state={}
    if type(value['state']) is not dict:raise ValueError('Adam state map')
    for key,row in value['state'].items():
        if not key.isdecimal() or key!=str(int(key)) or not 0<=int(key)<len(parameters) or set(row)!={'step','exp_avg','exp_avg_sq'}:raise ValueError('Adam parameter state')
        step=row['step']
        if type(step) not in {int,float} or not math.isfinite(step) or not 0<=step<=10_000_000 or int(step)!=step:raise ValueError('Adam step')
        tensors={k:torch.tensor(row[k],dtype=parameters[int(key)].dtype) for k in ['exp_avg','exp_avg_sq']}
        if any(t.shape!=parameters[int(key)].shape or not torch.isfinite(t).all() for t in tensors.values()) or (tensors['exp_avg_sq']<0).any():raise ValueError('Adam tensor integrity')
        state[int(key)]={**tensors,'step':torch.tensor(float(step))}
    groups=optimizer.state_dict()['param_groups'];optimizer.load_state_dict({'state':state,'param_groups':groups})
    rng=value['rng_state']
    if type(rng) is not list or len(rng)>10000 or any(type(x) is not int or not 0<=x<=255 for x in rng):raise ValueError('RNG state bound')
    torch.set_rng_state(torch.tensor(rng,dtype=torch.uint8))
    return model,optimizer,value['metadata']
