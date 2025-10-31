"""Test scan_once with proper env loading."""
import os
from pathlib import Path

from api.ingestion.config import IngestionConfig
from api.ingestion.watcher import scan_once, get_watcher_metrics_snapshot
from api.config import get_settings

# Ensure we're in correct directory
os.chdir(Path(__file__).parent)
print(f"Working directory: {os.getcwd()}")
print(f".env exists: {Path('.env').exists()}")
print(f".env (hidden): {Path('.env').exists() or Path('.env').is_file()}")

print("\n[+] Loading settings...")
settings = get_settings()
print(f"    SUPABASE_URL: {settings.supabase_url[:40]}...")

print("\n[+] Creating ingestion config...")
cfg = IngestionConfig.from_env(settings)
print(f"    Watch dir: {cfg.watch_dir}")
print(f"    Temp dir: {cfg.temp_dir}")

print("\n[+] Scanning watch directory...")
count = scan_once(cfg, {}, settings)
print(f"    Documenti elaborati: {count}")

print("\n[+] Getting metrics...")
metrics = get_watcher_metrics_snapshot(settings)
print(f"    Total docs: {metrics['documents_processed']}")
print(f"    Fallback count: {metrics['fallback']['count']}")
print(f"    Classification success: {metrics['classification']['success']}")

print("\n✅ Scan completed successfully!")

