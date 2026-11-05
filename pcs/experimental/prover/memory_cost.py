"""Independent physical compiler/RPC attempt ledger, including failures.

The inherited completed-response counter remains backward compatible. This
ledger measures actual execution attempts and full elapsed call time, including
rejected proofs, timeouts and generated module builds. It has no proof authority.
"""
import time
from .memory_environment import MemoryEnvironment
from .induction_environment import InductionEnvironment

class CostLedger:
    def __init__(self,*args,**kwargs):
        self.compiler_attempts=0;self.worker_request_attempts=0
        self.compiler_elapsed=0.;self.worker_elapsed=0.
        super().__init__(*args,**kwargs)

    def _run(self,arguments,build=False):
        self.compiler_attempts+=1;start=time.monotonic()
        try:return super()._run(arguments,build=build)
        finally:self.compiler_elapsed+=time.monotonic()-start

    def _worker_source(self,text):
        self.worker_request_attempts+=1;start=time.monotonic()
        try:return super()._worker_source(text)
        finally:self.worker_elapsed+=time.monotonic()-start

    @property
    def actual_calls(self):return self.compiler_attempts+self.worker_request_attempts

class MeasuredMemoryEnvironment(CostLedger,MemoryEnvironment):pass
class MeasuredInductionEnvironment(CostLedger,InductionEnvironment):pass
