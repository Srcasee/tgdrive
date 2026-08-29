# Deployment Notes

## Known non-blocking issues recorded after CI Run #78

### FastAPI lifecycle deprecation

`app/core/app.py` still uses FastAPI `on_event()` startup/shutdown handlers. FastAPI reports these APIs as deprecated and recommends lifespan event handlers. This currently does not block startup or tests, but should be migrated during a later Core cleanup for forward compatibility.

### Python version coverage

The PostgreSQL CI workflow currently tests Python 3.12, while the current real deployment server uses Python 3.11.2. TGDrive is intended to select a compatible Python runtime from the deployment server rather than bind deployment to one Python version. The server has successfully installed the current dependencies under Python 3.11.2, but CI does not yet test a Python 3.11 matrix. Future CI work should define and test the supported Python range explicitly.

## CI verification

Run #78 (`8f2bf4f`) passed with 35 tests. The previous PostgreSQL `filename NOT NULL` error was addressed by explicit repository validation and regression coverage.

## Staged deployment principle

Database initialization, Core startup, optional proxy runtime, Telegram runtime, scanning, and real download performance testing are verified independently so a failure does not require restarting the entire deployment process.
