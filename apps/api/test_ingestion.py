"""Test real ingestion with classification."""
from api.ingestion.config import IngestionConfig
from api.ingestion.watcher import scan_once, get_watcher_metrics_snapshot
from api.config import get_settings

print("\n[+] Loading settings...")
settings = get_settings()

print("[+] Creating ingestion config...")
cfg = IngestionConfig.from_env(settings)
print(f"    Watch dir: {cfg.watch_dir}")
print(f"    Temp dir: {cfg.temp_dir}")

print("\n[+] Scanning and ingesting documents...")
count = scan_once(cfg, {}, settings)
print(f"\n[+] Documenti elaborati: {count}")

print("\n[+] Getting metrics...")
metrics = get_watcher_metrics_snapshot(settings)
print(f"    Total docs: {metrics['documents_processed']}")
print(f"    Classification success: {metrics['classification']['success']}")
print(f"    Classification failures: {metrics['classification']['failure']}")
print(f"    Fallback count: {metrics['fallback']['count']}")
print(f"    Fallback ratio: {metrics['fallback']['ratio']}")

print("\n[+] Ingestion completed!")

