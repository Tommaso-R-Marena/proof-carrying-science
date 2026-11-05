"""Deterministic *trained* PyTorch Iris classifier serialized as restricted ONNX.

Iris contains published flower measurements, not synthetic labels. The
model is trained locally, and a quantized float32 weight snapshot is exported
using standard TensorProto protobuf fields. No untrusted model code is loaded.
Official ONNX/ONNX Runtime validation remains separately required.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from tests.make_samples import fld

ROOT=Path(__file__).resolve().parents[1]

def serialize(w1,b1,w2,b2):
    def vi(name,shape):
        dims=b''.join(fld(1,fld(1,int(k))) for k in shape)
        return fld(1,name)+fld(2,fld(1,fld(1,1)+fld(2,dims)))
    def ten(name,arr):
        arr=np.asarray(arr,dtype='<f4')
        return b''.join(fld(1,int(v)) for v in arr.shape)+fld(2,1)+fld(8,name)+fld(9,arr.tobytes())
    def node(op,ins,out):return b''.join(fld(1,v) for v in ins)+fld(2,out)+fld(4,op)
    nodes=[('Gemm',['features','W1','B1'],'pre'),('Relu',['pre'],'hidden'),
           ('Gemm',['hidden','W2','B2'],'logits')]
    graph=b''.join(fld(1,node(*z)) for z in nodes)+fld(2,'pcs_iris_trained_mlp')
    graph+=fld(5,ten('W1',w1))+fld(5,ten('B1',b1))
    graph+=fld(5,ten('W2',w2))+fld(5,ten('B2',b2))
    graph+=fld(11,vi('features',[1,4]))+fld(12,vi('logits',[1,3]))
    return fld(1,8)+fld(7,graph)+fld(8,fld(2,13))

def make():
    import torch
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    torch.set_num_threads(1);torch.manual_seed(1991)
    data=load_iris();X=data.data.astype('float32');Y=data.target.astype('int64')
    train,test=train_test_split(np.arange(len(X)),test_size=.30,random_state=9,stratify=Y)
    scaler=StandardScaler().fit(X[train]);Xn=scaler.transform(X).astype('float32')
    net=torch.nn.Sequential(torch.nn.Linear(4,8),torch.nn.ReLU(),torch.nn.Linear(8,3))
    opt=torch.optim.Adam(net.parameters(),lr=.025)
    xt=torch.from_numpy(Xn[train]);yt=torch.from_numpy(Y[train]);
    for epoch in range(240):
        pred=net(xt);loss=torch.nn.functional.cross_entropy(pred,yt)
        opt.zero_grad();loss.backward();opt.step()
    with torch.no_grad():
        y_pred=net(torch.from_numpy(Xn[test])).argmax(dim=1).numpy()
        accuracy=float((y_pred==Y[test]).mean())
        all_logits=net(torch.from_numpy(Xn)).numpy()
    layers=[net[0],net[2]]
    w1=layers[0].weight.detach().numpy().T.copy();b1=layers[0].bias.detach().numpy().copy()
    w2=layers[1].weight.detach().numpy().T.copy();b2=layers[1].bias.detach().numpy().copy()
    raw=serialize(w1,b1,w2,b2)
    path=ROOT/'samples'/'demo_trained_iris_mlp.onnx';path.write_bytes(raw)
    # Choose a correct high-margin setosa held-out example; deterministic.
    candidates=[int(i) for i in test if Y[i]==0 and np.argmax(all_logits[i])==0]
    idx=max(candidates,key=lambda i:float(all_logits[i,0]-max(all_logits[i,1:])))
    center=Xn[idx].tolist()
    # Original normalized center is float32; widening by +/- 0.05 as decimals
    # is a reviewer-selected mathematical box, not an empirical measurement guarantee.
    box=[[str(float(x)-.05),str(float(x)+.05)] for x in center]
    props=[]
    for j in (1,2):
        c=[0,0,0];c[0]=-1;c[j]=1
        props.append({'output_coefficients':list(map(str,c)),'upper_limit':'-1/2'})
    profile={'source':'scikit-learn Iris (published real flower measurements)',
             'train_count':len(train),'test_count':len(test),
             'test_accuracy':accuracy,'selected_heldout_index':idx,
             'selected_true_class':int(Y[idx]),'input_space':'training-set standardized Iris measurements',
             'standard_scaler_mean':scaler.mean_.tolist(),'standard_scaler_scale':scaler.scale_.tolist(),
             'selected_input':center,'reviewer_box':box,'properties':props,
             'reproducibility':'torch.manual_seed(1991), train_test_split random_state=9, 240 Adam epochs; inference-only weights exported as ONNX protobuf'}
    (ROOT/'validation'/'v06_iris_profile.json').write_text(json.dumps(profile,indent=2)+'\n')
    return raw, profile, Xn, all_logits

if __name__=='__main__':
    raw,profile,Xn,logits=make()
    print('bytes',len(raw),'accuracy',profile['test_accuracy'],'index',profile['selected_heldout_index'],'sample logits',logits[profile['selected_heldout_index']])
