"""Retain the last observed receipt prefix across live broker operations.

This host-memory guard only refuses; every positive effect still comes from the
unchanged exact-byte native authority and transactional broker. It is not an
external monotonic root and cannot resist rollback of both storage and host state.
The registered v1 model experiment uses the frozen parent broker, not this wrapper.
"""
import json
import threading

from ..authority import decode_reply
from ..broker import Session as BaseSession


class Session(BaseSession):
    def _bind(self,path,authority):
        super()._bind(path,authority)
        self._mutex=threading.RLock()
        self._anchor=None
        self._candidate=None
        self._updating=False

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.audit()

    def _checkpoint_for(self,replay):
        return dict(generation=replay['state'][0],receipt=replay['receipt'],genesis=self.genesis)

    def _replay(self,c):
        replay=super()._replay(c)
        if self._anchor is not None:
            anchor=self._anchor
            if anchor['genesis']!=self.genesis:raise ValueError('Retained initial checkpoint differs')
            if anchor['receipt']==self.genesis:
                if anchor['generation']!=0:raise ValueError('Invalid initial checkpoint')
            else:
                rows=c.execute('SELECT record,sha256 FROM attempts ORDER BY id').fetchall()
                # The parent has independently replayed and hash-checked every
                # receipt. The retained prefix must occur in this exact chain,
                # including denied attempts which do not advance generation.
                matches=[json.loads(record) for record,sha in rows if sha==anchor['receipt']]
                if len(matches)!=1 or decode_reply(bytes.fromhex(matches[0]['reply_hex'])).after[0]!=anchor['generation']:
                    raise ValueError('Live receipt prefix rolled back or forked')
        if self._updating:self._candidate=self._checkpoint_for(replay)
        return replay

    def apply(self,raw,*,expected_generation):
        with self._mutex:
            self._candidate=None;self._updating=True
            try:
                result=super().apply(raw,expected_generation=expected_generation)
                if result['status'] in {'COMMITTED','BLOCKED'}:
                    # Capture the independently replayed staged receipt BEFORE
                    # commit. Reopening the mutable database here could adopt an
                    # attacker-restored snapshot between commitment and anchoring.
                    if self._candidate is None:raise ValueError('Committed receipt checkpoint absent')
                    self._anchor=dict(self._candidate)
                return result
            finally:
                self._candidate=None;self._updating=False

    def audit(self):
        with self._mutex:
            replay=super().audit()
            # Observing a valid descendant also advances the retained prefix.
            # Later restoring an older snapshot must not undo that observation.
            self._anchor=self._checkpoint_for(replay)
            return replay
