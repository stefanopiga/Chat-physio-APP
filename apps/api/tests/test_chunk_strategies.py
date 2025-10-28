from api.ingestion.chunking.recursive import RecursiveCharacterStrategy
from api.ingestion.chunking.tabular import TabularStructuralStrategy


def test_recursive_strategy_basic():
    s = RecursiveCharacterStrategy(chunk_size=50, chunk_overlap=10)
    text = "a" * 120
    res = s.split(text)
    assert len(res.chunks) >= 2
    assert res.strategy_name.startswith("recursive_character_")


def test_tabular_strategy_sections_and_fallback():
    s = TabularStructuralStrategy(min_section_len=20)
    text = "Sezione 1\n\nSezione 2 con dati\n\nSezione 3"  # 3 sezioni separate
    res = s.split(text)
    assert len(res.chunks) >= 2
    assert res.strategy_name == "tabular_structural"
