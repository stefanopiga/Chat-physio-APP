@echo off
cd /d "%~dp0"
echo Running P0 Tests for Story 2.12...
echo.
python -m pytest --override-ini addopts="" tests/test_settings_llm.py tests/test_llm_integration.py tests/routers/test_chat.py::test_ag_endpoint_uses_settings_for_llm -v --tb=short
echo.
echo Tests completed. Check output above.
pause





