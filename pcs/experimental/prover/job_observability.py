"""Bounded, source-correlated operational evidence; never proof authority."""
import json
import re
import time

STAGES={"checked_reuse","previous_policy","symbolic","grounded_induction",
        "previous_policy_extended_actions","symbolic_induction","memory_policy",
        "same_memory_structural","no_memory_structural","ordinary_Std",
        "exact_human_actions","hybrid_portfolio","serialization"}

class JobTrace:
    def __init__(self,request_id,core_sha,source_sha256):
        if not re.fullmatch(r"[0-9a-f]{32}",request_id) or not re.fullmatch(r"[0-9a-f]{40}",core_sha) or not re.fullmatch(r"[0-9a-f]{64}",source_sha256):
            raise ValueError("Invalid operational correlation")
        self.request_id=request_id;self.core_sha=core_sha;self.source_sha256=source_sha256
        self.started=time.monotonic();self.events=[]
    def emit(self,stage,status,*,wall_seconds=None,cpu_seconds=None,lean_attempts=None):
        if stage not in STAGES or status not in {"started","finished","failed"} or len(self.events)>=32:
            raise ValueError("Operational event bound")
        event={"format":"pcs-lean-job-event-v1","request_id":self.request_id,
               "core_sha":self.core_sha,"source_sha256":self.source_sha256,
               "sequence":len(self.events),"stage":stage,"status":status,
               "elapsed_seconds":time.monotonic()-self.started,"pcs_authority":False}
        for name,value in (("wall_seconds",wall_seconds),("cpu_seconds",cpu_seconds)):
            if value is not None:
                if type(value) not in {float,int} or not 0<=value<float('inf'):raise ValueError("Invalid measured duration")
                event[name]=value
        if lean_attempts is not None:
            if type(lean_attempts) is not int or lean_attempts<0:raise ValueError("Invalid checker accounting")
            event['recorded_Lean_execution_attempts']=lean_attempts
        self.events.append(event)
        print('PCS_LEAN_STAGE_V1:'+json.dumps(event,separators=(',',':')),flush=True)
        return event
    def measure(self,stage,operation):
        self.emit(stage,'started');wall=time.monotonic();cpu=time.process_time()
        try:result=operation()
        except Exception:
            self.emit(stage,'failed',wall_seconds=time.monotonic()-wall,cpu_seconds=time.process_time()-cpu)
            raise
        # This is the parent's CPU time; child Lean CPU is deliberately not
        # inferred. Existing verifier-owned attempt counters remain explicit.
        cost=result.get('cost',{}) if isinstance(result,dict) else {}
        attempts=cost.get('all_Lean_execution_attempts')
        self.emit(stage,'finished',wall_seconds=time.monotonic()-wall,cpu_seconds=time.process_time()-cpu,lean_attempts=attempts)
        return result
