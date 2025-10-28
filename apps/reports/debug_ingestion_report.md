# Batch Ingestion Report

**Generated:** 2025-10-16 12:26:24 UTC

## Summary

- **Total Files:** 10
- **Success:** 1
- **Failed:** 9
- **Skipped:** 0
- **Total Chunks:** 21
- **Duration:** 2800.6s
- **Throughput:** 0.0 files/min

## Top Files by Chunks

| File | Chunks | Latency (ms) |
|------|--------|-------------|
| 8_Common_sense.docx | 21 | 9929 |

## Failed Files

| File | Error |
|------|-------|
| 10_Sindrome_radicolare_lombare_pt.1.docx | Sync job 855865fd-1eba-46de-a7ef-1feddd9ca597 did not complete within 300s (last payload: {'job_id': '855865fd-1eba-46de-a7ef-1feddd9ca597', 'status': 'PENDING', 'inserted': None, 'error': None}) |
| 11_Comunicazione_ed_educazione_dolore_persistente.docx | Sync job 8274de4a-1111-4a00-9036-e63f614711ea did not complete within 300s (last payload: {'job_id': '8274de4a-1111-4a00-9036-e63f614711ea', 'status': 'PENDING', 'inserted': None, 'error': None}) |
| 1_Radicolopatia_Lombare_COMPLETA.docx | Sync job 39f00714-18e6-4922-828d-cffaa594868e did not complete within 300s (last payload: {'job_id': '39f00714-18e6-4922-828d-cffaa594868e', 'status': 'PENDING', 'inserted': None, 'error': None}) |
| 2_Radicolopatia_Lombare_PT.2.docx | Sync job 53f221b7-fdcc-4484-8b7f-e246afbc6dda did not complete within 300s (last payload: {'job_id': '53f221b7-fdcc-4484-8b7f-e246afbc6dda', 'status': 'PENDING', 'inserted': None, 'error': None}) |
| 3_SPONDILOLISI-SPONDILOLISTESI.docx | Sync job a7ee9a40-83f5-4262-a5ac-dd3e64db2cde did not complete within 300s (last payload: {'job_id': 'a7ee9a40-83f5-4262-a5ac-dd3e64db2cde', 'status': 'PENDING', 'inserted': None, 'error': None}) |
| 4_STENOSI_SPINALE_LOMBARE.docx | Sync job 35c35828-330b-4a82-83cb-1b6babb3e2d6 did not complete within 300s (last payload: {'job_id': '35c35828-330b-4a82-83cb-1b6babb3e2d6', 'status': 'PENDING', 'inserted': None, 'error': None}) |
| 5_CHIRURGIA_VERTEBRALE_PT.1.docx | Sync job e71c09a9-d385-4a6c-844c-0f02966512da did not complete within 300s (last payload: {'job_id': 'e71c09a9-d385-4a6c-844c-0f02966512da', 'status': 'PENDING', 'inserted': None, 'error': None}) |
| 6_CHIRURGIA_VERTEBRALE_PT.2.docx | 502 Server Error: Bad Gateway for url: http://localhost/api/v1/admin/knowledge-base/sync-jobs/0a5ed0de-0f4f-4d50-8718-2da73898dffc |
| 7_role_of_belief_and_fear_in_lbp.docx | Sync job 4bbf7e12-098a-4eab-acb5-f050f0b7a546 failed: Error 23503:
Message: insert or update on table "document_chunks" violates foreign key constraint "fk_document_chunks_document_id"
Details: Key (document_id)=(8a1fefb0-3d9e-40bc-8a95-a9bfd8ee9a42) is not present in table "documents". |

