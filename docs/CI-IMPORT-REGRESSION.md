# Run #53 CI Import Regression

## Symptom

`tests/test_api_integration.py` failed during collection with:

```text
ModuleNotFoundError: No module named 'telegram.downloader'
```

The failing import was `from telegram.downloader import TelegramDownloader` while loading `app/files/api.py`.

## Root cause

The application source tree uses `app/telegram` as a top-level Python package. A CI/test environment can also have an unrelated third-party top-level `telegram` package installed. If that package is resolved first, `telegram.downloader` does not refer to tgdrive's downloader.

The failing Run #53 commit already contained `app/telegram/downloader.py`; therefore this was a module-resolution collision, not a missing source file.

## Resolution

- Added `tests/conftest.py` to put the application source directory first in `sys.path` and evict a conflicting preloaded `telegram` module.
- Updated CI `PYTHONPATH` from `.:app` to `app:.` so tgdrive's application packages have deterministic precedence.

## Follow-up

The generic top-level package name `telegram` remains a maintainability risk. A future packaging cleanup may rename the internal package to a project-specific namespace, but that is intentionally deferred because it would touch the Telegram subsystem broadly.
