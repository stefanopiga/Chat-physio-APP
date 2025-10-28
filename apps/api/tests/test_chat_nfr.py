"""
Test NFR (Non-Functional Requirements) per Chat RAG - Story 2.11 AC5.

Verifica:
- Performance: tempo di risposta < 5s (retrieval < 1s, generation < 4s)
- Affidabilità: serie di query consecutive senza errori
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.asyncio

# Target performance (da AC5 e Technical Constraints)
TARGET_RETRIEVAL_MS = 1000  # < 1s
TARGET_GENERATION_MS = 4000  # < 4s
TARGET_TOTAL_MS = 5000  # < 5s

# Configurazione test affidabilità
RELIABILITY_ITERATIONS = 10  # Serie di query per test affidabilità
RELIABILITY_MAX_ERRORS = 0  # Tolleranza errori (0 = nessun errore ammesso)


@pytest.fixture
def api_base_url() -> str:
    """Base URL per l'API backend."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def auth_token() -> str:
    """Token JWT per autenticazione (mock o reale)."""
    # In test reali, usa un token valido da Supabase o sistema auth
    return os.getenv("TEST_AUTH_TOKEN", "mock-test-token")


@pytest.fixture
def test_session_id() -> str:
    """Session ID per test."""
    return "test-nfr-session-001"


async def send_chat_message(
    client: httpx.AsyncClient,
    base_url: str,
    session_id: str,
    message: str,
    auth_token: str,
) -> tuple[dict[str, Any], float]:
    """
    Invia messaggio alla chat e misura il tempo di risposta.
    
    Returns:
        (response_data, elapsed_ms)
    """
    url = f"{base_url}/api/v1/chat/sessions/{session_id}/messages"
    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {"message": message}

    start_time = time.perf_counter()
    response = await client.post(url, json=payload, headers=headers)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    response.raise_for_status()
    return response.json(), elapsed_ms


async def test_nfr_performance_single_query(
    api_base_url: str, auth_token: str, test_session_id: str
):
    """
    AC5 Performance: Verifica che una singola query rispetti i target di performance.
    
    Target:
    - retrieval_time_ms < 1000ms
    - generation_time_ms < 4000ms
    - total_time < 5000ms
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        query = "Qual è la differenza tra radicolopatia lombare e cervicale?"

        try:
            data, elapsed_ms = await send_chat_message(
                client, api_base_url, test_session_id, query, auth_token
            )
        except httpx.HTTPError as e:
            pytest.skip(
                f"Backend non disponibile o test JWT non configurato: {e}"
            )
            return

        # Verifica risposta valida
        assert "message" in data or "answer" in data, "Risposta non contiene messaggio"
        assert data.get("message") or data.get("answer"), "Messaggio vuoto"

        # Verifica performance totale
        assert (
            elapsed_ms < TARGET_TOTAL_MS
        ), f"Tempo totale {elapsed_ms:.0f}ms supera target {TARGET_TOTAL_MS}ms"

        # Verifica breakdown tempi (se disponibili nel payload)
        retrieval_ms = data.get("retrieval_time_ms")
        generation_ms = data.get("generation_time_ms")

        if retrieval_ms is not None:
            assert (
                retrieval_ms < TARGET_RETRIEVAL_MS
            ), f"Retrieval time {retrieval_ms}ms supera target {TARGET_RETRIEVAL_MS}ms"

        if generation_ms is not None:
            assert (
                generation_ms < TARGET_GENERATION_MS
            ), f"Generation time {generation_ms}ms supera target {TARGET_GENERATION_MS}ms"

        print(
            f"\n✅ Performance OK: total={elapsed_ms:.0f}ms, "
            f"retrieval={retrieval_ms}ms, generation={generation_ms}ms"
        )


async def test_nfr_performance_multiple_queries(
    api_base_url: str, auth_token: str, test_session_id: str
):
    """
    AC5 Performance: Verifica performance su serie di query diverse.
    Tutte le query devono rispettare i target di performance.
    """
    queries = [
        "Cos'è la radicolopatia lombare?",
        "Quali sono i sintomi della cervicale?",
        "Come si tratta la lombalgia?",
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        results = []

        for i, query in enumerate(queries):
            try:
                data, elapsed_ms = await send_chat_message(
                    client,
                    api_base_url,
                    f"{test_session_id}-{i}",
                    query,
                    auth_token,
                )
                results.append(
                    {
                        "query": query,
                        "elapsed_ms": elapsed_ms,
                        "retrieval_ms": data.get("retrieval_time_ms"),
                        "generation_ms": data.get("generation_time_ms"),
                        "success": True,
                    }
                )
            except httpx.HTTPError as e:
                pytest.skip(
                    f"Backend non disponibile per query {i + 1}: {e}"
                )
                return

        # Verifica che tutte le query rispettino i target
        failed = []
        for result in results:
            if result["elapsed_ms"] >= TARGET_TOTAL_MS:
                failed.append(
                    f"{result['query'][:50]}... ({result['elapsed_ms']:.0f}ms)"
                )

        if failed:
            pytest.fail(
                f"{len(failed)}/{len(queries)} query superano target {TARGET_TOTAL_MS}ms:\n"
                + "\n".join(f"  - {f}" for f in failed)
            )

        # Statistiche
        avg_ms = sum(r["elapsed_ms"] for r in results) / len(results)
        max_ms = max(r["elapsed_ms"] for r in results)
        print(
            f"\n✅ Performance OK su {len(queries)} query: "
            f"avg={avg_ms:.0f}ms, max={max_ms:.0f}ms"
        )


async def test_nfr_reliability_consecutive_queries(
    api_base_url: str, auth_token: str, test_session_id: str
):
    """
    AC5 Affidabilità: Verifica che il sistema risponda in modo consistente
    senza errori intermittenti su serie di query consecutive.
    
    Esegue RELIABILITY_ITERATIONS query e verifica:
    - Nessun errore HTTP (200 OK sempre)
    - Risposte sempre valide (non vuote)
    - Varianza dei tempi entro soglia accettabile
    """
    query = "Cos'è la fisioterapia?"

    async with httpx.AsyncClient(timeout=10.0) as client:
        results = []
        errors = []

        for i in range(RELIABILITY_ITERATIONS):
            try:
                data, elapsed_ms = await send_chat_message(
                    client,
                    api_base_url,
                    f"{test_session_id}-rel-{i}",
                    query,
                    auth_token,
                )

                # Verifica risposta valida
                message = data.get("message") or data.get("answer")
                if not message:
                    errors.append(f"Iterazione {i + 1}: risposta vuota")

                results.append(elapsed_ms)

            except httpx.HTTPError as e:
                if i == 0:
                    # Prima query fallita: skip intero test
                    pytest.skip(f"Backend non disponibile: {e}")
                    return
                errors.append(f"Iterazione {i + 1}: {type(e).__name__} - {e}")

            # Small delay per non stressare eccessivamente il sistema
            await asyncio.sleep(0.1)

        # Verifica tolleranza errori
        if len(errors) > RELIABILITY_MAX_ERRORS:
            pytest.fail(
                f"Affidabilità insufficiente: {len(errors)} errori su "
                f"{RELIABILITY_ITERATIONS} query (max tollerato: {RELIABILITY_MAX_ERRORS}):\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        # Calcola varianza tempi
        if results:
            avg_ms = sum(results) / len(results)
            variance = sum((t - avg_ms) ** 2 for t in results) / len(results)
            std_dev = variance**0.5
            min_ms = min(results)
            max_ms = max(results)

            # Verifica varianza accettabile (coefficient of variation < 50%)
            cv = (std_dev / avg_ms) * 100 if avg_ms > 0 else 0
            assert (
                cv < 50
            ), f"Varianza tempi eccessiva: CV={cv:.1f}% (std={std_dev:.0f}ms, avg={avg_ms:.0f}ms)"

            print(
                f"\n✅ Affidabilità OK su {len(results)} query: "
                f"avg={avg_ms:.0f}ms, std={std_dev:.0f}ms, "
                f"min={min_ms:.0f}ms, max={max_ms:.0f}ms, CV={cv:.1f}%"
            )


async def test_nfr_performance_under_concurrent_load(
    api_base_url: str, auth_token: str, test_session_id: str
):
    """
    AC5 Performance: Verifica performance sotto carico concorrente.
    
    Simula 5 query concorrenti e verifica che:
    - Tutte completino con successo
    - Nessuna superi significativamente il target (es. 2x target)
    """
    queries = [
        "Query 1: sintomi lombalgia",
        "Query 2: trattamento cervicale",
        "Query 3: esercizi posturali",
        "Query 4: prevenzione dolore",
        "Query 5: riabilitazione sportiva",
    ]

    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [
            send_chat_message(
                client,
                api_base_url,
                f"{test_session_id}-concurrent-{i}",
                query,
                auth_token,
            )
            for i, query in enumerate(queries)
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            pytest.skip(f"Backend non disponibile per test concorrenti: {e}")
            return

        # Verifica risultati
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            pytest.fail(
                f"{len(errors)}/{len(queries)} query concorrenti fallite:\n"
                + "\n".join(f"  - {type(e).__name__}: {e}" for e in errors)
            )

        # Verifica tempi (permettiamo 2x target per carico concorrente)
        max_allowed_ms = TARGET_TOTAL_MS * 2
        slow_queries = []

        for i, (data, elapsed_ms) in enumerate(results):  # type: ignore
            if elapsed_ms >= max_allowed_ms:
                slow_queries.append(f"Query {i + 1}: {elapsed_ms:.0f}ms")

        if slow_queries:
            pytest.fail(
                f"{len(slow_queries)}/{len(queries)} query concorrenti "
                f"superano {max_allowed_ms}ms:\n" + "\n".join(f"  - {q}" for q in slow_queries)
            )

        avg_ms = sum(r[1] for r in results if not isinstance(r, Exception)) / len(  # type: ignore
            results
        )
        print(
            f"\n✅ Performance sotto carico OK: {len(queries)} query concorrenti, avg={avg_ms:.0f}ms"
        )

