from api.services import chat_service


def test_record_ag_latency_ms_returns_percentiles():
    chat_service.ag_latency_samples_ms.clear()

    values = [120, 180, 250, 320, 480]
    summary = {}
    for value in values:
        summary = chat_service.record_ag_latency_ms(value)

    assert summary["count"] == len(values)
    assert summary["p50_ms"] == 250
    assert summary["p95_ms"] == 480


def test_percentiles_handle_empty_samples():
    chat_service.ag_latency_samples_ms.clear()
    assert chat_service.get_latency_p50() == 0
    assert chat_service.get_latency_p95() == 0
    assert chat_service.get_latency_p99() == 0
