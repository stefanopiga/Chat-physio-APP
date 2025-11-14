"""Pytest configuration and fixtures per test suite Story 2.5, 5.4.

Questo file configura:
- Caricamento variabili ambiente da .env.test
- Fixtures comuni (test_document, admin_token, test_client)
- Database test setup/teardown
- Mock configuration per external services
- Test environment isolation (Story 5.4)
"""
import os
import sys
import unittest.mock as mock
from pathlib import Path
import pytest
from dotenv import load_dotenv

# Carica variabili test PRIMA di import app modules
# Priority: .env.test.local (gitignored) > .env.test > .env
# Story 6.4: Legge .env dalla root del progetto (APPLICAZIONE/)
# Path: tests/conftest.py -> api/ -> apps/ -> APPLICAZIONE/
test_env_local = Path(__file__).parent.parent.parent.parent / ".env.test.local"
test_env = Path(__file__).parent.parent.parent.parent / ".env.test"
default_env = Path(__file__).parent.parent.parent.parent / ".env"

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Mock langchain imports per risolvere incompatibilità Pydantic 2.11
sys.modules['langchain_openai'] = mock.MagicMock()
sys.modules['langchain_core'] = mock.MagicMock()
sys.modules['langchain_core.language_models'] = mock.MagicMock()
sys.modules['langchain_core.prompts'] = mock.MagicMock()
sys.modules['langchain_core.output_parsers'] = mock.MagicMock()
sys.modules['langchain_core.runnables'] = mock.MagicMock()
sys.modules['langchain_core.messages'] = mock.MagicMock()
sys.modules['langchain_community'] = mock.MagicMock()
sys.modules['langchain_community.document_loaders'] = mock.MagicMock()
sys.modules['langchain_community.vectorstores'] = mock.MagicMock()
sys.modules['langchain_text_splitters'] = mock.MagicMock()

if test_env_local.exists():
    load_dotenv(test_env_local, override=True)
    print(f"[OK] Loaded test environment from: {test_env_local}")
elif test_env.exists():
    load_dotenv(test_env, override=True)
    print(f"[OK] Loaded test environment from: {test_env}")
else:
    load_dotenv(default_env, override=True)
    print(f"[WARN] Using default environment from: {default_env}")
    print("[WARN] Per test isolation, create .env.test.local con test-specific values")

# Force test environment AFTER dotenv load (Story 5.4 Task 1.3 FIX)
# Questo garantisce che TESTING e RATE_LIMITING_ENABLED siano sempre forzati
os.environ["TESTING"] = "true"
os.environ["RATE_LIMITING_ENABLED"] = "false"
print("[OK] Forced test environment: TESTING=true, RATE_LIMITING_ENABLED=false")

# Verifica variabili critiche per E2E tests
REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "OPENAI_API_KEY",
    "DATABASE_URL",
]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    print(f"[WARN] Missing required env vars for E2E tests: {missing_vars}")
    print("[WARN] Integration tests will be SKIPPED")
    print("[WARN] Create .env.test.local with real values to enable E2E tests")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Force environment variables per test isolation (Story 5.4 Task 1.3).
    
    Ensures rate limiting is disabled and test mode is active for all tests.
    """
    os.environ["TESTING"] = "true"
    os.environ["RATE_LIMITING_ENABLED"] = "false"
    print("[OK] Test environment configured: TESTING=true, RATE_LIMITING_ENABLED=false")
    yield
    # No cleanup needed - processo test termina


@pytest.fixture(autouse=True)
def clean_rate_limit_store():
    """
    Cleanup rate limit store tra test (defense in depth) - Story 5.4 Task 1.4.
    
    Note: Dovrebbe essere no-op con rate limiting disabilitato, ma fornisce
    doppia protezione contro shared state tra test.
    
    Story 6.2 Task T7: Reset settings singleton cache per test isolation.
    """
    # Pre-test: Reset settings cache (Story 6.2)
    try:
        from api.config import reset_settings
        reset_settings()
    except ImportError:
        pass
    
    try:
        from api.services.rate_limit_service import rate_limit_service
        from api.stores import _rate_limit_store
        
        # Pre-test cleanup
        _rate_limit_store.clear()
        if hasattr(rate_limit_service, '_store'):
            rate_limit_service._store.clear()
    except ImportError:
        # Può fallire in alcuni test setup - ignora
        pass
    
    yield
    
    # Post-test: Reset settings cache again (Story 6.2)
    try:
        from api.config import reset_settings
        reset_settings()
    except ImportError:
        pass
    
    # Post-test cleanup
    try:
        from api.services.rate_limit_service import rate_limit_service
        from api.stores import _rate_limit_store
        
        _rate_limit_store.clear()
        if hasattr(rate_limit_service, '_store'):
            rate_limit_service._store.clear()
    except ImportError:
        pass


@pytest.fixture(scope="session")
def test_env_config():
    """Test environment configuration."""
    return {
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_service_key": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "database_url": os.getenv("DATABASE_URL"),
        "celery_enabled": os.getenv("CELERY_ENABLED", "false").lower() == "true",
        "admin_email": os.getenv("ADMIN_EMAIL", "test@example.com"),
    }


@pytest.fixture
def test_document():
    """Test document sample per pipeline E2E."""
    return {
        "document_text": """
        Caso clinico: Paziente con lombalgia acuta L4-L5.
        
        Anamnesi: Dolore insorto dopo sollevamento pesi. 
        Intensità VAS 7/10, irradiazione posteriore coscia destra.
        
        Valutazione: Ridotto ROM flessione lombare, test Lasègue positivo 45°.
        
        Trattamento: 
        - Manipolazione vertebrale HVLA L4-L5
        - Mobilizzazione articolare
        - Esercizi terapeutici core stability
        - Educazione posturale
        
        Follow-up: Miglioramento sintomatologia dopo 3 sessioni.
        Range of motion recuperato al 90%. VAS ridotto a 2/10.
        
        Prognosi: Favorevole con proseguimento esercizi domiciliari.
        """,
        "metadata": {
            "document_name": "test_lombalgia_e2e.txt",
            "source": "test_integration",
            "document_type": "caso_clinico",
        }
    }


@pytest.fixture
def test_document_large():
    """Large test document per performance testing."""
    # Generate documento con ~500 parole per test chunking
    base_text = """
    La lombalgia acuta rappresenta una condizione clinica frequente nella pratica fisioterapica.
    La valutazione biomeccanica è fondamentale per identificare le disfunzioni articolari.
    Il trattamento manuale comprende tecniche HVLA, mobilizzazione, e terapia dei tessuti molli.
    """
    
    repeated_text = (base_text + "\n") * 50  # ~500+ words
    
    return {
        "document_text": repeated_text,
        "metadata": {
            "document_name": "test_large_document.txt",
            "source": "test_performance",
        }
    }


@pytest.fixture
def admin_token(test_env_config):
    """Admin JWT token per test.
    
    Note: Se SUPABASE_JWT_SECRET disponibile, genera token reale.
    Altrimenti usa mock token per unit tests.
    """
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    if not jwt_secret:
        # Mock token per unit tests
        return "mock_admin_jwt_token"
    
    # Generate real JWT for integration tests
    try:
        import jwt
        from datetime import datetime, timedelta
        
        payload = {
            "sub": "test-admin-user-id",
            "email": test_env_config["admin_email"],
            "role": "admin",
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),  # Required: issued at timestamp
            "iss": os.getenv("SUPABASE_JWT_ISSUER", "test"),
        }
        
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        return token
    except ImportError:
        print("[WARN] PyJWT not available, using mock admin token")
        return "mock_admin_jwt_token"


@pytest.fixture
def test_client(test_env_config):
    """FastAPI test client per integration tests.
    
    Note: Usa context manager per gestire lifespan app (database pool init).
    """
    # Check se environment è configurato per integration tests
    if not all([
        test_env_config["supabase_url"],
        test_env_config["supabase_service_key"],
        test_env_config["openai_api_key"],
    ]):
        pytest.skip("Test environment not configured (missing required env vars)")
    
    # CRITICAL: Disable Celery BEFORE importing app (CELERY_ENABLED read at module import)
    os.environ["CELERY_ENABLED"] = "false"
    
    from fastapi.testclient import TestClient
    from api.main import app
    
    # CRITICAL: Use context manager per eseguire lifespan (db pool init)
    with TestClient(app) as client:
        yield client
    
    # Cleanup automatico via context manager (db pool close)


@pytest.fixture(scope="session")
def test_database_setup(test_env_config):
    """Setup test database con migrations.
    
    Note: Questo fixture esegue migrations su test database.
    Richiede DATABASE_URL configurato per test instance.
    """
    database_url = test_env_config["database_url"]
    
    if not database_url or "test" not in database_url.lower():
        pytest.skip("Test database not configured (DATABASE_URL must contain 'test')")
    
    # TODO: Run migrations
    # subprocess.run(["supabase", "db", "push"])
    
    yield
    
    # Cleanup: truncate tables dopo test suite
    # TODO: Implement cleanup logic


@pytest.fixture
def clean_test_database(test_database_setup):
    """Cleanup test database prima di ogni test.
    
    Trunca document_chunks e documents tables per test isolation.
    """
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url or "test" not in database_url.lower():
        pytest.skip("Test database not configured")
    
    # TODO: Implement truncate logic
    # import asyncpg
    # async with asyncpg.create_pool(database_url) as pool:
    #     async with pool.acquire() as conn:
    #         await conn.execute("TRUNCATE document_chunks, documents CASCADE")
    
    yield


def pytest_configure(config):
    """Pytest configuration hook."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires infrastructure)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (requires full stack)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (> 5s execution)"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip integration tests se environment non configurato."""
    skip_integration = pytest.mark.skip(reason="Test environment not configured (missing env vars)")
    
    # Check se variabili richieste sono presenti
    env_configured = all(os.getenv(var) for var in REQUIRED_ENV_VARS)
    
    if not env_configured:
        for item in items:
            if "integration" in item.keywords or "e2e" in item.keywords:
                item.add_marker(skip_integration)


# =============================================================================
# Async Fixtures for Watcher Tests (Story 6.3)
# =============================================================================

@pytest.fixture
async def test_db_connection():
    """
    Async DB connection fixture per test watcher async.
    
    Usage:
        @pytest.mark.asyncio
        async def test_async_operation(test_db_connection):
            result = await some_async_function(test_db_connection)
            assert result is not None
    
    Story 6.3: AC4 - Test migration ad async
    """
    import asyncpg
    
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    
    if not database_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL not configured")
    
    # Create connection with statement_cache_size=0 per pgbouncer compatibility
    conn = await asyncpg.connect(database_url, statement_cache_size=0)
    
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def mock_watcher_scan(test_db_connection):
    """
    Helper fixture per test scan_once async con DB connection.
    
    Provides:
    - IngestionConfig configurato per test
    - Empty inventory dict
    - Test Settings instance
    - DB connection dal pool
    
    Usage:
        @pytest.mark.asyncio
        async def test_watcher_operation(mock_watcher_scan):
            cfg, inventory, settings, conn = mock_watcher_scan
            docs = await scan_once(cfg, inventory, settings, conn=conn)
            assert len(docs) >= 0
    
    Story 6.3: AC4 - Test helper per async watcher tests
    """
    from api.ingestion.config import IngestionConfig
    from api.config import get_settings
    from pathlib import Path
    
    # Setup test config
    test_watch_dir = Path(__file__).parent / "test_data" / "watch"
    test_watch_dir.mkdir(parents=True, exist_ok=True)
    
    cfg = IngestionConfig(
        watch_dir=test_watch_dir,
        temp_dir=Path(__file__).parent / "test_data" / "temp",
    )
    cfg.temp_dir.mkdir(parents=True, exist_ok=True)
    
    inventory = {}
    settings = get_settings()
    
    yield (cfg, inventory, settings, test_db_connection)
    
    # Cleanup test directories
    import shutil
    if cfg.watch_dir.exists():
        shutil.rmtree(cfg.watch_dir)
    if cfg.temp_dir.exists():
        shutil.rmtree(cfg.temp_dir)


# =============================================================================
# Fixtures for Modular Router Tests (Story 5.2)
# =============================================================================

@pytest.fixture
def mock_admin_auth():
    """Mock admin authentication payload."""
    return {"sub": "admin-123", "role": "admin", "app_metadata": {"role": "admin"}}


@pytest.fixture
def mock_student_auth():
    """Mock student authentication payload (non-admin)."""
    return {"sub": "student-123", "role": "authenticated"}


@pytest.fixture
def client_admin():
    """Test client con JWT admin simulato."""
    from fastapi.testclient import TestClient
    from api.main import app
    from api.services.rate_limit_service import rate_limit_service
    from api import dependencies
    
    # Pulisci rate limit stores con reset completo (service + SlowAPI)
    rate_limit_service._store.clear()
    if hasattr(app.state, 'limiter') and hasattr(app.state.limiter, '_storage'):
        try:
            app.state.limiter._storage.clear()
        except (AttributeError, TypeError):
            pass  # SlowAPI storage potrebbe non essere disponibile
    
    # Mock admin auth
    def mock_verify_jwt_admin():
        return {"sub": "admin-123", "role": "admin", "app_metadata": {"role": "admin"}}
    
    # Override sia verify_jwt_token che _auth_bridge per coprire tutti i router
    app.dependency_overrides[dependencies.verify_jwt_token] = lambda: mock_verify_jwt_admin()
    app.dependency_overrides[dependencies._auth_bridge] = lambda: mock_verify_jwt_admin()
    
    with TestClient(app) as client:
        yield client
    
    # Cleanup completo dopo test
    rate_limit_service._store.clear()
    if hasattr(app.state, 'limiter') and hasattr(app.state.limiter, '_storage'):
        try:
            app.state.limiter._storage.clear()
        except (AttributeError, TypeError):
            pass
    app.dependency_overrides.clear()


@pytest.fixture
def client_student():
    """Test client con JWT student simulato."""
    from fastapi.testclient import TestClient
    from api.main import app
    from api.services.rate_limit_service import rate_limit_service
    from api import dependencies
    
    # Pulisci rate limit stores con reset completo (service + SlowAPI)
    rate_limit_service._store.clear()
    if hasattr(app.state, 'limiter') and hasattr(app.state.limiter, '_storage'):
        try:
            app.state.limiter._storage.clear()
        except (AttributeError, TypeError):
            pass
    
    # Mock student auth
    def mock_verify_jwt_student():
        return {"sub": "student-123", "role": "authenticated"}
    
    # Override sia verify_jwt_token che _auth_bridge per coprire tutti i router
    app.dependency_overrides[dependencies.verify_jwt_token] = lambda: mock_verify_jwt_student()
    app.dependency_overrides[dependencies._auth_bridge] = lambda: mock_verify_jwt_student()
    
    with TestClient(app) as client:
        yield client
    
    # Cleanup completo dopo test
    rate_limit_service._store.clear()
    if hasattr(app.state, 'limiter') and hasattr(app.state.limiter, '_storage'):
        try:
            app.state.limiter._storage.clear()
        except (AttributeError, TypeError):
            pass
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth():
    """Test client senza autenticazione."""
    from fastapi.testclient import TestClient
    from fastapi import HTTPException, status
    from api.main import app
    from api.services.rate_limit_service import rate_limit_service
    from api import dependencies
    
    # Pulisci rate limit stores con reset completo (service + SlowAPI)
    rate_limit_service._store.clear()
    if hasattr(app.state, 'limiter') and hasattr(app.state.limiter, '_storage'):
        try:
            app.state.limiter._storage.clear()
        except (AttributeError, TypeError):
            pass
    
    # Mock no auth (401)
    def mock_no_jwt():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token"
        )
    
    # Override sia verify_jwt_token che _auth_bridge per coprire tutti i router
    app.dependency_overrides[dependencies.verify_jwt_token] = mock_no_jwt
    app.dependency_overrides[dependencies._auth_bridge] = mock_no_jwt
    
    with TestClient(app) as client:
        yield client
    
    # Cleanup completo dopo test
    rate_limit_service._store.clear()
    if hasattr(app.state, 'limiter') and hasattr(app.state.limiter, '_storage'):
        try:
            app.state.limiter._storage.clear()
        except (AttributeError, TypeError):
            pass
    app.dependency_overrides.clear()


@pytest.fixture
def supabase_test_client():
    """Supabase client per test database operations."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_service_key:
        pytest.skip("Supabase test environment not configured")
    
    from supabase import create_client
    return create_client(supabase_url, supabase_service_key)


@pytest.fixture
def student_token_in_db(supabase_test_client):
    """Crea student token di test in DB con isolation garantito (Story 5.4.2).
    
    Implementa:
    - Unique UUID per test instance (no collision)
    - Verified INSERT pattern (FK guaranteed)
    - Enhanced error messages
    - Deterministic cleanup
    """
    import secrets
    import uuid
    from datetime import datetime, timedelta, timezone
    import logging
    
    logger = logging.getLogger("api.tests")
    
    # Generate unique user ID per test instance (Story 5.4.2 Phase 2 Task 2.1)
    test_user_id = str(uuid.uuid4())
    logger.debug(f"[FIXTURE] Creating test user: {test_user_id}")
    
    # Step 1: Create parent user FIRST with verification
    try:
        user_result = supabase_test_client.table("users").insert({
            "id": test_user_id,
            "email": f"test-{test_user_id}@fisiorag.test",
            "role": "admin",
        }).execute()
        
        # Verify user created successfully
        if not user_result.data or len(user_result.data) == 0:
            raise AssertionError(
                f"User creation failed. "
                f"Response: {user_result}, "
                f"User ID: {test_user_id}"
            )
        
        created_user = user_result.data[0]
        logger.debug(f"[FIXTURE] User created successfully: {created_user['id']}")
        
    except Exception as e:
        logger.error(
            f"[FIXTURE] User creation failed. "
            f"User ID: {test_user_id}, "
            f"Error: {e}",
            exc_info=True
        )
        raise
    
    # Step 2: Create student token WITH verified FK
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=365)
    
    try:
        token_result = supabase_test_client.table("student_tokens").insert({
            "first_name": "Test",
            "last_name": f"Student-{test_user_id[:8]}",
            "token": token,
            "expires_at": expires_at.isoformat(),
            "is_active": True,
            "created_by_id": test_user_id,  # FK guaranteed to exist
        }).execute()
        
        # Verify token created successfully
        if not token_result.data or len(token_result.data) == 0:
            raise AssertionError(
                f"Token creation failed. "
                f"Response: {token_result}, "
                f"User ID: {test_user_id}"
            )
        
        created_token = token_result.data[0]
        logger.debug(f"[FIXTURE] Student token created: {created_token['id']}")
        
    except Exception as e:
        logger.error(
            f"[FIXTURE] Token creation failed. "
            f"User ID: {test_user_id}, "
            f"Error: {e}",
            exc_info=True
        )
        # Cleanup user prima di fail
        try:
            supabase_test_client.table("users").delete().eq("id", test_user_id).execute()
        except Exception:
            pass
        raise
    
    yield created_token
    
    # Cleanup: DELETE in correct order with verification (Story 5.4.1 + 5.4.2)
    logger.debug(f"[CLEANUP] Starting fixture teardown for token {created_token['id']}")
    
    try:
        # Step 1: Delete refresh_tokens (child of student_tokens)
        logger.debug(f"[CLEANUP] Deleting refresh_tokens for token {created_token['id']}")
        delete_refresh = supabase_test_client.table("refresh_tokens").delete().eq(
            "student_token_id", created_token["id"]
        ).execute()
        logger.debug(f"[CLEANUP] Refresh tokens deleted: {len(delete_refresh.data)} rows")
        
        # Step 2: Delete student_tokens (child of users)
        logger.debug(f"[CLEANUP] Deleting student_token {created_token['id']}")
        delete_token = supabase_test_client.table("student_tokens").delete().eq(
            "id", created_token["id"]
        ).execute()
        if not delete_token.data and delete_token.count != 0:
            logger.warning(f"[CLEANUP] Token delete returned unexpected result: {delete_token}")
        else:
            logger.debug("[CLEANUP] Student token deleted successfully")
        
        # Step 3: Delete users (parent) LAST
        logger.debug(f"[CLEANUP] Deleting user {test_user_id}")
        delete_user = supabase_test_client.table("users").delete().eq(
            "id", test_user_id
        ).execute()
        if not delete_user.data and delete_user.count != 0:
            logger.warning(f"[CLEANUP] User delete returned unexpected result: {delete_user}")
        else:
            logger.debug("[CLEANUP] User deleted successfully")
        
        logger.debug(f"[CLEANUP] Fixture teardown completed for token {created_token['id']}")
        
    except Exception as e:
        # Log but don't fail test on cleanup error (best-effort cleanup)
        logger.error(f"[CLEANUP] Failed: {e}", exc_info=True)


@pytest.fixture
def refresh_token_in_db(supabase_test_client, student_token_in_db):
    """Crea refresh token di test in DB (setup + teardown)."""
    import secrets
    from datetime import datetime, timedelta, timezone
    
    refresh_token = secrets.token_urlsafe(64)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=365)
    
    result = supabase_test_client.table("refresh_tokens").insert({
        "student_token_id": student_token_in_db["id"],
        "token": refresh_token,
        "expires_at": expires_at.isoformat(),
        "is_revoked": False,
    }).execute()
    
    created_refresh = result.data[0]
    
    yield created_refresh
    
    # Cleanup (Story 5.4.1 Phase 1: DELETE instead of soft update)
    try:
        supabase_test_client.table("refresh_tokens").delete().eq(
            "id", created_refresh["id"]
        ).execute()
    except Exception as e:
        # Log but don't fail test on cleanup error
        import logging
        logging.getLogger("api").warning(f"Test cleanup failed (non-critical): {e}")


@pytest.fixture
def admin_token_in_db(supabase_test_client):
    """Crea admin user con UUID valido e JWT token (Story 5.4.3).
    
    Implementa:
    - UUID valido per admin user (no validation errors)
    - User creato in DB con role admin
    - JWT token con payload valido
    - Deterministic cleanup
    
    Returns:
        dict: {"user_id": str, "token": str}
    """
    import uuid
    import jwt
    import logging
    from datetime import datetime, timedelta, timezone
    
    logger = logging.getLogger("api.tests")
    
    # Generate unique admin user ID per test instance
    admin_user_id = str(uuid.uuid4())
    logger.debug(f"[FIXTURE] Creating admin user: {admin_user_id}")
    
    # Step 1: Create admin user in DB with verification
    try:
        user_result = supabase_test_client.table("users").insert({
            "id": admin_user_id,
            "email": f"admin-{admin_user_id[:8]}@fisiorag.test",
            "role": "admin",
        }).execute()
        
        # Verify user created successfully
        if not user_result.data or len(user_result.data) == 0:
            raise AssertionError(
                f"Admin user creation failed. "
                f"Response: {user_result}, "
                f"User ID: {admin_user_id}"
            )
        
        logger.debug(f"[FIXTURE] Admin user created: {admin_user_id}")
        
    except Exception as e:
        logger.error(
            f"[FIXTURE] Admin user creation failed. "
            f"User ID: {admin_user_id}, "
            f"Error: {e}",
            exc_info=True
        )
        raise
    
    # Step 2: Create JWT token with valid UUID
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    if not jwt_secret:
        # Cleanup e skip test se JWT secret non disponibile
        try:
            supabase_test_client.table("users").delete().eq("id", admin_user_id).execute()
        except Exception:
            pass
        pytest.skip("SUPABASE_JWT_SECRET not configured for integration tests")
    
    try:
        payload = {
            "sub": admin_user_id,  # UUID valido (no validation errors)
            "email": f"admin-{admin_user_id[:8]}@fisiorag.test",
            "role": "admin",
            "app_metadata": {"role": "admin"},
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "iss": os.getenv("SUPABASE_JWT_ISSUER", "test"),
        }
        
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        logger.debug("[FIXTURE] Admin JWT token generated")
        
    except Exception as e:
        logger.error(f"[FIXTURE] JWT generation failed: {e}", exc_info=True)
        # Cleanup user prima di fail
        try:
            supabase_test_client.table("users").delete().eq("id", admin_user_id).execute()
        except Exception:
            pass
        raise
    
    yield {
        "user_id": admin_user_id,
        "token": token
    }
    
    # Cleanup: DELETE admin user con child entities (Story 5.4.3 Phase 2)
    logger.debug(f"[CLEANUP] Starting admin user teardown: {admin_user_id}")
    
    try:
        # Step 1: Delete student_tokens created by admin (if any)
        logger.debug(f"[CLEANUP] Deleting student tokens created by admin {admin_user_id}")
        delete_tokens = supabase_test_client.table("student_tokens").delete().eq(
            "created_by_id", admin_user_id
        ).execute()
        logger.debug(f"[CLEANUP] Student tokens deleted: {len(delete_tokens.data) if delete_tokens.data else 0} rows")
        
        # Step 2: Delete admin user (parent) LAST
        logger.debug(f"[CLEANUP] Deleting admin user {admin_user_id}")
        delete_user = supabase_test_client.table("users").delete().eq(
            "id", admin_user_id
        ).execute()
        if not delete_user.data and delete_user.count != 0:
            logger.warning(f"[CLEANUP] Admin user delete returned unexpected result: {delete_user}")
        else:
            logger.debug("[CLEANUP] Admin user deleted successfully")
        
        logger.debug("[CLEANUP] Admin user teardown completed")
        
    except Exception as e:
        # Log but don't fail test on cleanup error (best-effort cleanup)
        logger.error(f"[CLEANUP] Admin user cleanup failed: {e}", exc_info=True)
