from api.ingestion.chunk_router import ChunkRouter
from api.ingestion.chunking.recursive import RecursiveCharacterStrategy
from api.ingestion.models import ClassificazioneOutput, DocumentStructureCategory


def test_router_fallback_without_classification():
    router = ChunkRouter()
    res = router.route("a" * 120, classification=None)
    assert res.strategy_name.startswith("fallback::")
    assert len(res.chunks) >= 1


def test_router_by_category_recursive():
    router = ChunkRouter()
    cl = ClassificazioneOutput(
        classificazione=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
        motivazione="denso",
        confidenza=0.9,
    )
    res = router.route("a" * 120, classification=cl)
    assert not res.strategy_name.startswith("fallback::")
    assert res.strategy_name.startswith("recursive_character_")


def test_router_by_category_tabular():
    router = ChunkRouter()
    cl = ClassificazioneOutput(
        classificazione=DocumentStructureCategory.DOCUMENTO_TABELLARE,
        motivazione="tabelle",
        confidenza=0.9,
    )
    res = router.route("Riga1\n\nRiga2 con dati\n\nRiga3", classification=cl)
    assert not res.strategy_name.startswith("fallback::")
    assert res.strategy_name == "tabular_structural"


def test_router_confidence_fallback():
    router = ChunkRouter()
    cl = ClassificazioneOutput(
        classificazione=DocumentStructureCategory.DOCUMENTO_TABELLARE,
        motivazione="bassa confidenza",
        confidenza=0.5,
    )
    res = router.route("x" * 120, classification=cl)
    assert res.strategy_name.startswith("fallback::")


def test_recursive_strategy_uses_configured_chunk_parameters():
    strategy = RecursiveCharacterStrategy(chunk_size=128, chunk_overlap=32)
    text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50
    result = strategy.split(text)

    assert result.strategy_name == "recursive_character_128_32"
    assert result.parameters == {"chunk_size": 128, "chunk_overlap": 32}
    assert result.chunks, "Expected at least one chunk"
    assert all(len(chunk) <= 128 for chunk in result.chunks)


def test_router_propagates_strategy_parameters():
    router = ChunkRouter(recursive=RecursiveCharacterStrategy(chunk_size=256, chunk_overlap=64))
    classification = ClassificazioneOutput(
        classificazione=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
        motivazione="contenuto denso",
        confidenza=0.95,
    )
    result = router.route("Contenuto " * 300, classification=classification)

    assert result.strategy_name == "recursive_character_256_64"
    assert result.parameters == {"chunk_size": 256, "chunk_overlap": 64}
