# Test Design: Story 2.1

Date: 2025-09-18
Designer: Quinn (Test Architect)

## Test Strategy Overview

- Total test scenarios: 6
- Unit tests: 5 (83%)
- Integration tests: 1 (17%)
- E2E tests: 0 (0%)
- Priority distribution: P0: 2, P1: 3, P2: 1

## Test Scenarios by Acceptance Criteria

### AC1: Il servizio accede a una directory di file

| ID           | Level | Priority | Test                                      | Justification                 |
| ------------ | ----- | -------- | ----------------------------------------- | ----------------------------- |
| 2.1-UNIT-001 | Unit  | P1       | Config path creation and permissions      | Pure config/IO checks         |

### AC2: Scansiona file nuovi/modificati

| ID           | Level       | Priority | Test                                               | Justification            |
| ------------ | ----------- | -------- | -------------------------------------------------- | ------------------------ |
| 2.1-UNIT-002 | Unit        | P1       | Inventory updates on file content change           | Hash-based dedup logic   |
| 2.1-INT-001  | Integration | P1       | End-to-end scan of directory writes artifacts      | Multi-component flow     |

### AC3: Il testo viene estratto correttamente (.pdf/.docx)

| ID           | Level | Priority | Test                              | Justification         |
| ------------ | ----- | -------- | --------------------------------- | --------------------- |
| 2.1-UNIT-003 | Unit  | P0       | DOCX text extraction              | Critical parse path   |
| 2.1-UNIT-004 | Unit  | P0       | PDF text extraction               | Critical parse path   |

### AC4: Il contenuto viene salvato temporaneamente

| ID           | Level | Priority | Test                                         | Justification       |
| ------------ | ----- | -------- | -------------------------------------------- | ------------------- |
| 2.1-UNIT-005 | Unit  | P1       | Content and metadata files written per hash  | Persistence logic   |

### AC5: Gestisce errori di parsing

| ID           | Level | Priority | Test                                        | Justification        |
| ------------ | ----- | -------- | ------------------------------------------- | -------------------- |
| 2.1-UNIT-006 | Unit  | P2       | Error path persists Document with status    | Error handling path  |

## Risk Coverage

- Parsing robustness for malformed PDFs/DOCX addressed by unit tests.
- Inventory consistency verified.

## Recommended Execution Order

1. P0 Unit tests (2.1-UNIT-003, 2.1-UNIT-004)
2. P1 Unit/Integration tests (2.1-UNIT-002, 2.1-UNIT-005, 2.1-INT-001)
3. P2 Unit test (2.1-UNIT-006)
