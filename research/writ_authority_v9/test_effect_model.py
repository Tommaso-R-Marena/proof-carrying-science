"""Counterexamples for state-inconsistent signed execution histories."""
import unittest
from research.writ_authority_v9.effect_model import replay, EffectHistoryError

def record(name, effect_id=1):
    return {'event':name,'effect_id':effect_id}

class EffectTraceTests(unittest.TestCase):
    def test_lease_before_delivery_and_terminal_sticky(self):
        good=(record('admit'),record('dispatch_lease'),record('delivered'))
        self.assertEqual(replay(good,{1:'delivered'}),{1:'delivered'})
        for bad in (good+(record('delivered'),),
                    good+(record('cancel_effect'),),
                    (record('admit'),record('delivered')),
                    (record('admit'),record('dispatch_lease'),
                     record('dispatch_uncertain'),record('dispatch_lease'))):
            with self.subTest(bad=bad), self.assertRaises(EffectHistoryError):
                replay(bad,{1:'delivered'})
    def test_cross_agent_effects_do_not_conflate_ids(self):
        events=(record('admit',1),record('admit',2),
                record('dispatch_lease',2),record('dispatch_uncertain',2),
                record('cancel_effect',1))
        self.assertEqual(replay(events,{1:'canceled',2:'uncertain'}),
                         {1:'canceled',2:'uncertain'})
        with self.assertRaisesRegex(EffectHistoryError,'outbox disagrees'):
            replay(events,{1:'delivered',2:'uncertain'})
    def test_lease_is_not_proof_of_delivery(self):
        self.assertEqual(replay((record('admit'),record('dispatch_lease')),
                                {1:'working'}),{1:'working'})
        with self.assertRaises(EffectHistoryError):
            replay((record('admit'),record('dispatch_lease')),{1:'delivered'})
    def test_unknown_event_fails_closed(self):
        with self.assertRaises(EffectHistoryError):
            replay((record('admit'),record('magic_delivery')),{1:'delivered'})

if __name__=='__main__':
    unittest.main()
