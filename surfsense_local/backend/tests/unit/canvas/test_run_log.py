from concurrent.futures import ThreadPoolExecutor

from modules.canvas.runlog.log import (
    MAX_ENTRIES,
    NULL_HANDLE,
    LogRead,
    RunLog,
)


def test_a_new_log_is_idle_and_empty() -> None:
    """Before any run, and after the API restarts, there is nothing to show."""
    assert RunLog().read(None, 0) == LogRead(
        run=0, kind=None, state="idle", entries=[], next=0
    )


def test_a_run_numbers_its_entries_from_one_and_reads_after_a_number() -> None:
    """The panel asks only for what it has not seen."""
    log = RunLog()
    handle = log.start("sync")
    for code in ("a", "b", "c"):
        handle.add(code)

    whole = log.read(1, 0)
    later = log.read(1, 2)

    assert [e.n for e in whole.entries] == [1, 2, 3]
    assert [e.code for e in later.entries] == ["c"]
    assert later.next == 3
    assert whole.state == "running"
    assert whole.kind == "sync"


def test_finish_sets_the_state_and_later_writes_are_dropped() -> None:
    """A finished run is a record; nothing more is added to it."""
    log = RunLog()
    handle = log.start("check")
    handle.add("a")

    handle.finish("done")
    handle.add("late")

    read = log.read(1, 0)
    assert read.state == "done"
    assert [e.code for e in read.entries] == ["a"]


def test_starting_a_run_replaces_the_log_and_drops_the_old_handles_writes() -> None:
    """A newer run never mixes with an older one still working."""
    log = RunLog()
    first = log.start("sync")
    first.add("old")
    second = log.start("check")
    second.add("new")

    first.add("stale")

    read = log.read(2, 0)
    assert read.run == 2
    assert read.kind == "check"
    assert [e.code for e in read.entries] == ["new"]


def test_a_read_naming_another_run_returns_the_whole_current_log() -> None:
    """A page that remembers an older run starts over from this one."""
    log = RunLog()
    log.start("sync")
    second = log.start("sync")
    for code in ("a", "b", "c"):
        second.add(code)

    assert [e.code for e in log.read(1, 2).entries] == ["a", "b", "c"]


def test_the_log_keeps_the_newest_thousand_entries_and_keeps_counting() -> None:
    """A very long sync drops its oldest lines and never breaks a reader."""
    log = RunLog()
    handle = log.start("sync")
    for _ in range(1200):
        handle.add("x")

    read = log.read(1, 5)

    assert len(read.entries) == MAX_ENTRIES
    assert [read.entries[0].n, read.entries[-1].n] == [201, 1200]
    assert read.next == 1200


def test_writes_from_many_threads_are_all_kept() -> None:
    """The sync writes from a worker thread while the route reads."""
    log = RunLog()
    handle = log.start("sync")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: [handle.add("x") for _ in range(50)], range(8)))

    numbers = [e.n for e in log.read(1, 0).entries]
    assert sorted(numbers) == list(range(1, 401))


def test_a_parameter_that_is_not_plain_never_raises() -> None:
    """Writing a line must never break a sync."""
    log = RunLog()
    handle = log.start("sync")

    handle.add("x", thing=object(), count=3, name="Bio", ok=True)

    (entry,) = log.read(1, 0).entries
    assert isinstance(entry.params["thing"], str)
    assert entry.params["count"] == 3
    assert entry.params["name"] == "Bio"
    assert entry.params["ok"] is True


def test_errors_counts_error_level_entries() -> None:
    """The run's closing line says how many things went wrong."""
    handle = RunLog().start("sync")

    handle.add("a")
    handle.add("b", "error")
    handle.add("c")

    assert handle.errors == 1
    NULL_HANDLE.add("a", "error")
    assert NULL_HANDLE.errors == 0
