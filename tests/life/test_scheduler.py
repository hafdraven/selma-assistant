"""Tests for the reminder scheduler loop (spec §6)."""
from __future__ import annotations

import threading

from selma.life.reminders import ReminderService


def test_scheduler_loop_rearms(reminders, fresh_api):
    # Create a reminder already in the past so it fires immediately.
    reminders.create("2020-01-01T00:00:00", label="Old")
    fired: list[str] = []
    ev = threading.Event()

    def cb(ruri):
        fired.append(ruri)
        ev.set()

    reminders.start(cb, interval=0.05)
    try:
        assert ev.wait(timeout=5.0)
    finally:
        reminders.stop()
    assert len(fired) == 1


def test_scheduler_does_not_fire_future(reminders):
    # A future reminder must not fire during a short polling window.
    reminders.create("2099-01-01T00:00:00", label="Far future")
    fired: list[str] = []

    def cb(ruri):
        fired.append(ruri)

    reminders.start(cb, interval=0.05)
    # Let a couple of poll cycles pass.
    import time
    time.sleep(0.2)
    reminders.stop()
    assert fired == []


def test_scheduler_callback_exception_does_not_kill_loop(reminders):
    reminders.create("2020-01-01T00:00:00", label="Old")
    calls = [0]
    fired: list[str] = []
    ev = threading.Event()

    def cb(ruri):
        calls.append(0)
        if not fired:
            fired.append(ruri)
            raise RuntimeError("boom")
        ev.set()

    # To test re-arm after exception, create a second reminder that becomes
    # due only after the first fires and errors. Simpler: verify the loop is
    # still alive by checking a second callback invocation set the event.
    reminders.start(cb, interval=0.05)
    try:
        # First call raises; we give it time, then add a new due reminder and
        # expect the still-alive loop to pick it up.
        import time
        time.sleep(0.15)
        reminders.create("2021-01-01T00:00:00", label="Old2")
        assert ev.wait(timeout=5.0)
    finally:
        reminders.stop()
    assert len(fired) >= 1