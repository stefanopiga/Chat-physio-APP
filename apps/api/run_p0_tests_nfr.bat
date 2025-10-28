@echo off
REM Story 6.4 NFR - Script per eseguire test Performance SLO (PERF-001)
REM Esegue test con marker @pytest.mark.integration

echo ========================================
echo Story 6.4 NFR - Performance SLO Tests
echo ========================================
echo.
echo Obiettivo: Validare retrieval p95 ^< 2s (PERF-001)
echo Test: test_performance_slo_retrieval_p95
echo.

REM Installa dipendenze se necessario
echo [1/3] Verificando dipendenze...
poetry --directory apps/api install

REM Esegui test performance SLO specifico
echo.
echo [2/3] Eseguendo test performance SLO...
poetry --directory apps/api run pytest apps/api/tests/test_rag_activation_e2e.py::test_performance_slo_retrieval_p95 -v -s --run-integration

REM Esegui tutti test con marker integration (opzionale)
echo.
echo [3/3] Eseguendo tutti test integration (opzionale)...
echo Premere CTRL+C per saltare, o INVIO per continuare...
pause > nul

poetry --directory apps/api run pytest apps/api/tests -m integration -v --run-integration

echo.
echo ========================================
echo Test completati
echo ========================================
echo.
echo Verificare output sopra per:
echo - Test PERF-001 PASSED
echo - p95 latency ^< 2000ms
echo - Log timing metrics (avg, p50, p95, p99)
echo.

pause

