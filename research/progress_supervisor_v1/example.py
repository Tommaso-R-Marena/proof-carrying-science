"""Authored finite tool model, with the original fairness obstruction retained."""
from pcs.action_shield_v1 import MODEL_FORMAT

def model(*,review_may_stall=False):
    triples=[(0,0,1),(0,4,0),(0,6,6),(1,1,2),(1,1,3),(2,2,3),
             (2,3,4),(2,3,5),(2,5,3),(3,3,4),(4,4,4),(6,4,6)]
    if review_may_stall:triples.append((0,0,0))
    return dict(format=MODEL_FORMAT,states=list(range(7)),actions=list(range(7)),initial=[0],safe=[0,1,2,3,4,6],forbidden=[5],
        transitions=[dict(source=s,action=a,target=t) for s,a,t in sorted(triples)],
        assumptions=[dict(id=k,statement=v,status='OPEN') for k,v in sorted({
         'model_completeness':'All possible tool outcomes are exactly covered by this finite relation.',
         'shield_enforcement':'Every executed tool transition is mediated by this supervisor.',
         'state_observation':'Trusted observations identify the modeled state and actual tool outcome.'}.items())])
