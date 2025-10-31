"""
Test suite per Chat Service.

Coverage:
- track_ag_latency()
- get_latency_p95()
- get_latency_p99()
- get_llm()
"""
from unittest.mock import patch, MagicMock


def test_track_ag_latency_stores_samples():
    """Test: track_ag_latency memorizza samples."""
    from api.services.chat_service import track_ag_latency, ag_latency_samples_ms
    
    # Pulisci samples
    ag_latency_samples_ms.clear()
    
    # Track latency
    track_ag_latency(150)
    track_ag_latency(200)
    track_ag_latency(180)
    
    assert len(ag_latency_samples_ms) == 3
    assert 150 in ag_latency_samples_ms
    assert 200 in ag_latency_samples_ms
    assert 180 in ag_latency_samples_ms
    
    # Cleanup
    ag_latency_samples_ms.clear()


def test_track_ag_latency_max_samples():
    """Test: track_ag_latency limita a max 10000 samples."""
    from api.services.chat_service import track_ag_latency, ag_latency_samples_ms
    
    ag_latency_samples_ms.clear()
    
    # Track 10001 samples
    for i in range(10001):
        track_ag_latency(100 + i)
    
    # Verifica limite
    assert len(ag_latency_samples_ms) == 10000
    
    # Cleanup
    ag_latency_samples_ms.clear()


def test_get_latency_p95_calculation():
    """Test: get_latency_p95 calcola percentile corretto."""
    from api.services.chat_service import get_latency_p95, ag_latency_samples_ms
    
    ag_latency_samples_ms.clear()
    
    # Setup samples: 1-100 ms
    for i in range(1, 101):
        ag_latency_samples_ms.append(i)
    
    p95 = get_latency_p95()
    
    # P95 di 1-100 dovrebbe essere ~95
    assert 94 <= p95 <= 96
    
    # Cleanup
    ag_latency_samples_ms.clear()


def test_get_latency_p99_calculation():
    """Test: get_latency_p99 calcola percentile corretto."""
    from api.services.chat_service import get_latency_p99, ag_latency_samples_ms
    
    ag_latency_samples_ms.clear()
    
    # Setup samples: 1-100 ms
    for i in range(1, 101):
        ag_latency_samples_ms.append(i)
    
    p99 = get_latency_p99()
    
    # P99 di 1-100 dovrebbe essere ~99
    assert 98 <= p99 <= 100
    
    # Cleanup
    ag_latency_samples_ms.clear()


def test_get_latency_zero_samples():
    """Test: latency 0 quando nessun sample."""
    from api.services.chat_service import get_latency_p95, get_latency_p99, ag_latency_samples_ms
    
    ag_latency_samples_ms.clear()
    
    assert get_latency_p95() == 0
    assert get_latency_p99() == 0


@patch('api.services.chat_service.get_settings')
@patch('api.services.chat_service.ChatOpenAI')
def test_get_llm_returns_instance(mock_chat_openai, mock_get_settings):
    """Test: get_llm ritorna istanza ChatOpenAI con configurazione centrale."""
    from types import SimpleNamespace
    from api.services.chat_service import get_llm

    mock_instance = MagicMock()
    mock_chat_openai.return_value = mock_instance
    mock_get_settings.return_value = SimpleNamespace(
        llm_config_refactor_enabled=True,
        openai_model="gpt-5-nano",
        openai_temperature_chat=None,
    )

    llm = get_llm()

    assert llm == mock_instance
    mock_chat_openai.assert_called_once_with(model="gpt-5-nano")

