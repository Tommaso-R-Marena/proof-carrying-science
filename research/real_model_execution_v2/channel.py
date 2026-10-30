"""Bounded nonblocking JSONL IO with whole-frame read AND write deadlines."""
import math
import os
import selectors
import time

from pcs.jsonio import strict_json_loads
from research.progress_supervisor_v1.certificate import encode


class Channel:
    def __init__(self, fd, *, limit=65536, timeout=300):
        if type(limit) is not int or not 1<=limit<=65536:
            raise ValueError("bounded frame size required")
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=300:
            raise ValueError("bounded finite whole-frame deadline required")
        self.fd,self.limit,self.timeout,self.pending=fd,limit,timeout,bytearray()
        os.set_blocking(fd,False)

    def _wait(self, event, deadline):
        remaining=deadline-time.monotonic()
        if remaining<=0:
            raise TimeoutError("model channel deadline")
        with selectors.DefaultSelector() as s:
            s.register(self.fd,event)
            if not s.select(remaining):
                raise TimeoutError("model channel deadline")

    def read(self):
        end=time.monotonic()+self.timeout
        while True:
            newline=self.pending.find(b"\n")
            if newline>=0:
                if newline>self.limit:raise ValueError("oversized model frame")
                raw=bytes(self.pending[:newline]);del self.pending[:newline+1]
                try:return strict_json_loads(raw.decode("utf-8",errors="strict"))
                except (ValueError,RecursionError) as e:raise ValueError("invalid strict model JSON") from e
            if len(self.pending)>self.limit:raise ValueError("oversized model frame")
            self._wait(selectors.EVENT_READ,end)
            try:chunk=os.read(self.fd,min(4096,self.limit+1-len(self.pending)))
            except BlockingIOError:continue
            if not chunk:raise EOFError("model closed without a complete frame")
            self.pending.extend(chunk)

    def write(self, value):
        data=encode(value)
        if len(data)>self.limit:raise ValueError("oversized outbound model frame")
        view=memoryview(data+b"\n");end=time.monotonic()+self.timeout
        while view:
            self._wait(selectors.EVENT_WRITE,end)
            try:count=os.write(self.fd,view)
            except BlockingIOError:continue
            if count<=0:raise BrokenPipeError("model pipe write failed")
            view=view[count:]

    def eof(self):
        if self.pending:raise ValueError("unexpected trailing model output")
        self._wait(selectors.EVENT_READ,time.monotonic()+self.timeout)
        if os.read(self.fd,1):raise ValueError("unexpected trailing model output")
