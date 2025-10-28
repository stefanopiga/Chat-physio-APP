#!/usr/bin/env python3
"""
Warmup script per pre-popolare classification cache Redis.

Usage:
    python scripts/perf/warmup_classification_cache.py --base-url http://localhost --admin-token <token>

Story 2.9: Classification Performance Optimization
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


SAMPLE_DOCUMENTS = [
    {
        "document_text": "Documento test p95 – benchmark latenza.",
        "metadata": {"document_name": "p95-benchmark.txt", "source": "warmup"},
    },
    {
        "document_text": """
La lombalgia aspecifica rappresenta una condizione clinica complessa 
caratterizzata da dolore localizzato nella regione lombare senza una 
causa patologica strutturale identificabile. Il trattamento fisioterapico 
si basa su esercizi di stabilizzazione del core, terapia manuale e 
educazione terapeutica del paziente.
        """.strip(),
        "metadata": {"document_name": "lombalgia-clinica.txt", "source": "warmup"},
    },
    {
        "document_text": """
ANATOMIA DELLA COLONNA VERTEBRALE
La colonna vertebrale è composta da 33 vertebre suddivise in:
- 7 vertebre cervicali (C1-C7)
- 12 vertebre toraciche (T1-T12)
- 5 vertebre lombari (L1-L5)
- 5 vertebre sacrali fuse (S1-S5)
- 4 vertebre coccigee

Le vertebre sono separate da dischi intervertebrali che fungono da 
ammortizzatori e permettono i movimenti della colonna.
        """.strip(),
        "metadata": {"document_name": "anatomia-vertebrale.txt", "source": "warmup"},
    },
    {
        "document_text": """
PROTOCOLLO ESERCIZI RIABILITATIVI POST-DISTORSIONE CAVIGLIA

Fase 1 (Settimana 1-2):
- Mobilizzazione attiva dolore-free
- Esercizi isometrici
- Controllo edema con crioterapia

Fase 2 (Settimana 3-4):
- Rinforzo muscolare progressivo
- Propriocezione su superfici stabili
- ROM completo caviglia

Fase 3 (Settimana 5-6):
- Esercizi pliometrici
- Propriocezione avanzata
- Ritorno graduale allo sport
        """.strip(),
        "metadata": {"document_name": "protocollo-caviglia.txt", "source": "warmup"},
    },
    {
        "document_text": """
ABSTRACT
Background: Lower back pain (LBP) affects 80% of adults at some point. 
Methods: Randomized controlled trial with 120 participants comparing 
manual therapy vs exercise therapy.
Results: Both groups showed significant improvement (p<0.05). Effect size 
Cohen's d=0.72 for manual therapy, d=0.68 for exercise.
Conclusion: Both interventions are effective for non-specific LBP.
        """.strip(),
        "metadata": {
            "document_name": "rct-manual-therapy.txt",
            "source": "warmup",
        },
    },
]


def warmup_cache(
    base_url: str, admin_token: str, documents: List[Dict[str, Any]], iterations: int
) -> Dict[str, Any]:
    """Popola cache inviando documenti via sync-jobs endpoint."""
    url = f"{base_url}/api/v1/admin/knowledge-base/sync-jobs"
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }

    total_docs = len(documents) * iterations
    logger.info(f"Warmup cache: invio {total_docs} documenti ({len(documents)} unici × {iterations} iterazioni)")

    success = 0
    failed = 0
    total_latency_ms = 0.0

    for iteration in range(iterations):
        for idx, doc in enumerate(documents):
            doc_id = f"{iteration}-{idx}"
            try:
                start = time.perf_counter()
                response = requests.post(url, headers=headers, json=doc, timeout=30)
                latency_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 200:
                    success += 1
                    total_latency_ms += latency_ms
                    logger.debug(f"✓ Doc {doc_id}: {latency_ms:.0f}ms")
                else:
                    failed += 1
                    logger.warning(
                        f"✗ Doc {doc_id}: HTTP {response.status_code} - {response.text[:100]}"
                    )
            except Exception as exc:
                failed += 1
                logger.error(f"✗ Doc {doc_id}: {exc}")

    avg_latency_ms = total_latency_ms / success if success > 0 else 0

    result = {
        "total": total_docs,
        "success": success,
        "failed": failed,
        "avg_latency_ms": round(avg_latency_ms, 2),
    }

    logger.info(
        f"Warmup completato: {success}/{total_docs} documenti processati (avg: {avg_latency_ms:.0f}ms)"
    )

    return result


def get_cache_stats(base_url: str, admin_token: str) -> Dict[str, Any]:
    """Recupera statistiche cache da admin endpoint."""
    url = f"{base_url}/api/v1/admin/knowledge-base/classification-cache/metrics"
    headers = {"Authorization": f"Bearer {admin_token}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("cache", {})
    except Exception as exc:
        logger.error(f"Errore recupero stats cache: {exc}")
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Warmup classification cache per test performance"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost",
        help="Base URL API (default: http://localhost)",
    )
    parser.add_argument(
        "--admin-token",
        required=True,
        help="Admin bearer token per autenticazione",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Numero iterazioni set documenti (default: 3)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Abilita logging debug"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Classification Cache Warmup - Story 2.9")
    logger.info("=" * 60)

    # Stats pre-warmup
    logger.info("\n[1/3] Statistiche cache PRE-warmup:")
    stats_before = get_cache_stats(args.base_url, args.admin_token)
    if stats_before:
        logger.info(f"  Hits: {stats_before.get('hits', 0)}")
        logger.info(f"  Misses: {stats_before.get('misses', 0)}")
        hit_rate = stats_before.get('hit_rate') or 0
        logger.info(f"  Hit rate: {hit_rate:.2%}")
    else:
        logger.warning("  Cache stats non disponibili")

    # Warmup
    logger.info("\n[2/3] Esecuzione warmup...")
    warmup_result = warmup_cache(
        args.base_url, args.admin_token, SAMPLE_DOCUMENTS, args.iterations
    )

    if warmup_result["failed"] > 0:
        logger.warning(
            f"⚠️ {warmup_result['failed']}/{warmup_result['total']} documenti falliti"
        )

    # Stats post-warmup
    logger.info("\n[3/3] Statistiche cache POST-warmup:")
    time.sleep(1)  # Attesa breve per propagazione metriche
    stats_after = get_cache_stats(args.base_url, args.admin_token)
    if stats_after:
        logger.info(f"  Hits: {stats_after.get('hits', 0)}")
        logger.info(f"  Misses: {stats_after.get('misses', 0)}")
        hit_rate = stats_after.get('hit_rate') or 0
        logger.info(f"  Hit rate: {hit_rate:.2%}")
        logger.info(
            f"  Latency hit P95: {stats_after.get('latency_ms', {}).get('hit', {}).get('p95', 'N/A')}ms"
        )
        logger.info(
            f"  Latency miss P95: {stats_after.get('latency_ms', {}).get('miss', {}).get('p95', 'N/A')}ms"
        )
    else:
        logger.warning("  Cache stats non disponibili")

    logger.info("\n" + "=" * 60)
    logger.info("✓ Warmup completato. Procedere con test k6.")
    logger.info("=" * 60)

    return 0 if warmup_result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

