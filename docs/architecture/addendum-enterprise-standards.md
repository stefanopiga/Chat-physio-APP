# Addendum: Enterprise Standards (SLO/SLI, Threat Modeling, SBOM, API Governance)

Status: Active  
Version: 1.0  
Date: 2025-10-08

## Scope

Questo addendum raccoglie standard ufficiali e best practices per rafforzare affidabilità, sicurezza e governance del progetto. È una risorsa di riferimento rapida per il team.

## 1) Osservabilità e Affidabilità (SLO/SLI)

- Definizioni: SLI (indicatori misurabili), SLO (target sugli SLI), Error Budget (1 − SLO) come leva decisionale.
- Target iniziali raccomandati per API:
  - Disponibilità mensile ≥ 99.5%
  - Latenza p95 < 200 ms (GET/POST core)
  - Error rate < 1%
- Operativizzazione:
  - Definire SLI calcolabili da logs/metrics (OpenTelemetry/Prometheus).
  - Alert su esaurimento error budget, non su soglie statiche.
  - Riesame SLO trimestrale basato su dati reali.
- Fonti ufficiali:
  - Google SRE Book — Service Level Objectives
  - Google SRE Workbook — Implementing SLOs

## 2) Sicurezza Proattiva (Threat Modeling)

- Integrare un processo STRIDE nelle design review (per servizio/feature).
- Attività minime per sprint che modifica architettura/API:
  1. DFD aggiornato (trust boundaries, data stores, external entities)
  2. Threats per STRIDE classificate (likelihood × impact)
  3. Decisione Mitigate/Eliminate/Transfer/Accept con owner
  4. Link ai test/mitigazioni (risk-to-test matrix)
- Strumenti: OWASP Threat Dragon (UI) o pytm (as-code).
- Fonti ufficiali: OWASP Threat Modeling Cheat Sheet; Microsoft Threat Modeling (STRIDE).

## 3) Supply Chain Security (SBOM & Scanning)

- Generare SBOM ad ogni build/release (CycloneDX JSON) e archiviare con gli artifact.
- Scansione continua di vulnerabilità (Dependabot, Snyk, Trivy, OWASP Dependency-Track) contro NVD/OSV.
- Policy suggerite:
  - Blocco merge per CVE Critical/High non mitigati
  - SLA patch: Critical ≤ 7 giorni, High ≤ 14 giorni
  - Revisione introduzione nuove dipendenze (licenze, maintainer health)
- Fonti ufficiali: CycloneDX (ECMA-424), OWASP CycloneDX Project, OpenSSF SBOM Tools.

## 4) API Governance (Contratti e Versioning)

- Single source of truth: OpenAPI 3.x versionato nel repo (lint in CI).
- Breaking vs non-breaking changes codificati in una policy interna.
- Versioning esplicito (es. path `/v1/`, o header `api-version`).
- Deprecation comunicata con header standard (`Deprecation`, `Sunset`) e changelog.
- Gate di approvazione su diff OpenAPI (schema/paths) per evitare drift.
- Fonti ufficiali: Microsoft REST API Guidelines; OpenAPI Specification; Azure API Design.

## Integrazione nel Progetto

- Architecture Index: aggiungere sezione “Operations & Governance” con link a questo addendum.
- Cross-link:
  - FastAPI Best Practices → sezione Configuration/Testing/Docs rimanda a SLO/SLI e API Governance.
  - Security Compliance → rimando a Threat Modeling e SBOM.
- Roadmap consigliata (Q4):
  1. Definire SLO/SLI minimi per API; aggiungere alert basati su error budget
  2. Abilitare generazione SBOM in CI e scanning su PR
  3. Introdurre gate OpenAPI con diff approvato in review
  4. Avviare threat modeling leggero per modifiche architetturali (Story 5.2, 6.x)

## Riferimenti Ufficiali

- Google SRE Book / Workbook (SLO/SLI)  
- OWASP Threat Modeling (STRIDE)  
- CycloneDX (ECMA-424) + OpenSSF SBOM Tools  
- Microsoft REST API Guidelines + OpenAPI Specification


