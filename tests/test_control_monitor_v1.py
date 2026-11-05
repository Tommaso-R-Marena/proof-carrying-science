from copy import deepcopy

from pcs.control_monitor_v1 import ControlMonitor, consistent_audit


def setup_monitor():
    effects = []
    policy = {"format": "pcs-control-policy-v1", "operation": "write_result", "max_actions": 1, "max_value": 255}
    monitor = ControlMonitor(policy, effects.append)
    request = {"nonce": "one", "operation": "write_result", "value": 42, "policy_sha256": monitor.policy_sha256}
    return monitor, effects, request


def test_no_effect_from_forged_approval_unsafe_operation_stale_policy_or_boolean_value():
    for mutation in [lambda x: x.update(approved=True), lambda x: x.update(operation="delete"),
                     lambda x: x.update(policy_sha256="0" * 64), lambda x: x.update(value=True),
                     lambda x: x.update(value=256)]:
        monitor, effects, request = setup_monitor()
        mutation(request)
        assert monitor.submit(request)["state"].startswith("REJECTED")
        assert effects == []


def test_consumed_action_cannot_replay_exceed_budget_or_execute_after_revocation():
    monitor, effects, request = setup_monitor()
    assert monitor.submit(request)["state"] == "EXECUTED"
    assert monitor.submit(request)["state"] == "REJECTED_REPLAY"
    request["nonce"] = "two"
    assert monitor.submit(request)["state"] == "REJECTED_BUDGET"
    assert effects == [42]
    monitor, effects, request = setup_monitor()
    monitor.revoke()
    assert monitor.submit(request)["state"] == "REJECTED_REVOKED"
    assert effects == []


def test_audit_tampering_is_detected_without_claiming_signature_authenticity():
    monitor, _, request = setup_monitor()
    monitor.submit(request)
    monitor.submit(request)
    assert consistent_audit(monitor.audit, monitor.policy_sha256)
    altered = deepcopy(monitor.audit)
    altered[1]["state"] = "EXECUTED"
    assert not consistent_audit(altered, monitor.policy_sha256)


def test_failed_effect_consumes_budget_and_is_not_retried():
    attempts = []
    def failing_effect(value):
        attempts.append(value)
        raise OSError("simulated partial write")
    monitor, _, request = setup_monitor()
    monitor._effect = failing_effect
    assert monitor.submit(request)["state"] == "EFFECT_FAILED_POSSIBLY_PARTIAL"
    assert monitor.submit(request)["state"] == "REJECTED_REPLAY"
    assert attempts == [42]


def test_concurrent_requests_cannot_bypass_shared_execution_budget():
    from concurrent.futures import ThreadPoolExecutor
    monitor, effects, request = setup_monitor()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(monitor.submit, [dict(request, nonce=str(i)) for i in range(32)]))
    assert sum(r['state'] == 'EXECUTED' for r in results) == 1
    assert effects == [42]
    assert consistent_audit(monitor.audit, monitor.policy_sha256)
