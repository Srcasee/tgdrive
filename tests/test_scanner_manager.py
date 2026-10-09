import asyncio

from ingestion.scanner_manager import ScannerManager


def test_reconcile_sources_starts_only_missing_tasks():
    async def run():
        manager = ScannerManager()
        started = asyncio.Event()
        release = asyncio.Event()
        calls = []

        async def runner(source):
            calls.append(source["id"])
            started.set()
            await release.wait()

        sources = [{"id": 1}, {"id": 2}]
        await manager.reconcile_sources(10, sources, runner)
        await started.wait()
        await manager.reconcile_sources(10, sources, runner)

        assert set(manager.tasks) == {(10, 1), (10, 2)}
        assert sorted(calls) == [1, 2]

        release.set()
        await manager.stop_all()

    asyncio.run(run())


def test_reconcile_sources_cancels_removed_source():
    async def run():
        manager = ScannerManager()
        cancelled = asyncio.Event()

        async def runner(source):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        await manager.reconcile_sources(10, [{"id": 1}, {"id": 2}], runner)
        await asyncio.sleep(0)
        await manager.reconcile_sources(10, [{"id": 2}], runner)

        assert (10, 1) not in manager.tasks
        assert (10, 2) in manager.tasks
        assert cancelled.is_set()
        await manager.stop_all()

    asyncio.run(run())


def test_stop_accounts_except_cancels_tasks_for_disabled_accounts():
    async def run():
        manager = ScannerManager()

        async def runner(source):
            await asyncio.Event().wait()

        await manager.reconcile_sources(10, [{"id": 1}], runner)
        await manager.reconcile_sources(20, [{"id": 2}], runner)
        await asyncio.sleep(0)
        await manager.stop_accounts_except({20})

        assert set(manager.tasks) == {(20, 2)}
        await manager.stop_all()

    asyncio.run(run())
