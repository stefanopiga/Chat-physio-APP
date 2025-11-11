# Scripts Documentation Coverage Audit - Story 8.6

**Date:** 2025-11-11  
**Purpose:** File system vs documentation parity check for drift prevention

## Scripts Present in File System

### admin/ (3 scripts + 1 README)
- [x] `generate_jwt.py` - Documented
- [x] `generate_missing_embeddings.py` - Documented
- [x] `README.md` - Present

### ingestion/ (6 scripts + 1 README)
- [x] `ingest_single_document.py` - Documented
- [x] `verify_ingestion.py` - Documented
- [ ] `ingest_all_documents.py` - **NOT DOCUMENTED**
- [ ] `test_ingest_all_documents.py` - Test file (documentation optional)
- [ ] `test_integration_batch_ingestion.py` - Test file (documentation optional)
- [x] `README.md` - Present

### perf/ (6 scripts + 1 JS file)
- [x] `run_p95_with_warmup.ps1` - Documented
- [x] `run_p95.ps1` - Documented
- [x] `warmup_classification_cache.py` - Documented
- [x] `summarize_p95.py` - Documented
- [ ] `p95_local_test.js` - **NOT DOCUMENTED** (Node.js test script)
- [x] `.env.staging.local` - Config file (no documentation needed)
- [x] `ENV_STAGING_TEMPLATE.txt` - Config file (no documentation needed)

### validation/ (11 scripts + 2 shell scripts + 1 README)
- [x] `validate_rag_system.py` - Documented
- [x] `database_integrity_audit.py` - Documented
- [x] `run_chunk_integrity_check.ps1` - Documented
- [x] `run_chunk_integrity_check.sh` - Bash variant mentioned
- [x] `cleanup_test_data.py` - Documented
- [ ] `config_gap_analysis.py` - **NOT DOCUMENTED**
- [ ] `database_connectivity_test.py` - **NOT DOCUMENTED**
- [ ] `docker_health_check.py` - **NOT DOCUMENTED**
- [ ] `env_audit.py` - **NOT DOCUMENTED**
- [ ] `generate_test_tokens.py` - **NOT DOCUMENTED**
- [ ] `test_db_connection.py` - Test file (documentation optional)
- [ ] `verify_chunk_ids.py` - **NOT DOCUMENTED**
- [x] `README.md` - Present

### security/ (1 script)
- [x] `run_secret_scans.sh` - Documented (Bash only)

### ops/ (2 scripts)
- [x] `watcher-debug.ps1` - Documented
- [x] `watcher-debug.sh` - Bash variant (documentation optional)

## Coverage Summary

**Total Scripts:** 29 (excluding test files, config files, __pycache__)
**Documented:** 20
**Not Documented:** 9
**Coverage:** 69%

### Scripts Requiring Documentation (Priority Order)

**P1 - High Priority (Operational Scripts):**
1. `ingestion/ingest_all_documents.py` - Batch ingestion utility
2. `validation/config_gap_analysis.py` - Configuration validation
3. `validation/database_connectivity_test.py` - Database health check
4. `validation/docker_health_check.py` - Docker status check
5. `validation/env_audit.py` - Environment variables audit

**P2 - Medium Priority (Support Scripts):**
6. `validation/generate_test_tokens.py` - Test token generation
7. `validation/verify_chunk_ids.py` - Chunk ID verification
8. `perf/p95_local_test.js` - Node.js performance test

**P3 - Low Priority (Test Files - Optional):**
9. `ingestion/test_ingest_all_documents.py` - Unit tests
10. `ingestion/test_integration_batch_ingestion.py` - Integration tests
11. `validation/test_db_connection.py` - Connection tests

## Recommended Actions

1. Add documentation for P1 scripts (operational utilities)
2. Add documentation for P2 scripts (support utilities)
3. Consider adding brief notes for test files in respective README.md files
4. Maintain this coverage file for future drift checks

## Documentation Parity Status

**Status:** PARTIAL COVERAGE  
**Action Required:** Add 8 undocumented operational/support scripts  
**Drift Prevention:** Run this audit quarterly or before major releases

