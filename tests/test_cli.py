from __future__ import annotations

from types import SimpleNamespace
from datetime import datetime, date

from food_tracker import cli
from food_tracker.models import FoodItem, FoodEntry, DailyLog


def test_format_macros():
    # Python's default rounding is "round half to even" (banker's rounding),
    # so 1.25 formats to 1.2 with one decimal place.
    assert cli._format_macros({"protein": 10, "fat": 1.25}) == "protein: 10.0g, fat: 1.2g"


def test_print_daily_log(capsys):
    item = FoodItem(name="Test Food", serving_size="100g", calories=50, macronutrients={"protein": 5})
    entry = FoodEntry(food=item, quantity=2.0, timestamp=datetime(2024, 1, 1, 12, 0))
    log = DailyLog(day=date(2024, 1, 1), entries=[entry])

    cli._print_daily_log(log)
    out = capsys.readouterr().out
    assert "Test Food" in out
    assert "Total:" in out


def make_fake_tracker():
    class FakeRecogniser:
        def __init__(self, items):
            self._items = items

        def known_items(self):
            return self._items

        def recognise(self, description, top_k=3):
            return [SimpleNamespace(item=self._items[0], confidence=0.9)]

    class FakeTracker:
        def __init__(self, recogniser):
            self.recogniser = recogniser
            self._entries: list[FoodEntry] = []

        def scan_description(self, description: str, top_k: int = 3):
            return self.recogniser.recognise(description, top_k=top_k)

        def manual_food_entry(self, name, serving_size, calories, quantity=1.0, macronutrients=None):
            item = FoodItem(name=name, serving_size=serving_size, calories=calories, macronutrients=macronutrients or {})
            entry = FoodEntry(food=item, quantity=quantity, timestamp=datetime.utcnow())
            self._entries.append(entry)
            return entry

        def log_food(self, food_item, quantity=1.0):
            entry = FoodEntry(food=food_item, quantity=quantity, timestamp=datetime.utcnow())
            self._entries.append(entry)
            return entry

        def entries_for_day(self, target_day: date) -> DailyLog:
            entries = [e for e in self._entries if e.timestamp.date() == target_day]
            return DailyLog(day=target_day, entries=entries)

    item = FoodItem(name="Fake Item", serving_size="1pc", calories=123, macronutrients={"protein": 3})
    recogniser = FakeRecogniser([item])
    return FakeTracker(recogniser), recogniser, item


def test_cli_run_foods_and_scan_and_add_and_summary(capsys, monkeypatch):
    # Prepare fake tracker/recogniser and patch CLI to use them
    fake_tracker, recogniser, item = make_fake_tracker()

    monkeypatch.setattr(cli, "FoodRecognitionEngine", lambda: recogniser)
    monkeypatch.setattr(cli, "FoodTracker", lambda recogniser: fake_tracker)

    command = cli.CLI()

    # foods
    command.run(["foods", "--limit", "1"])
    out = capsys.readouterr().out
    assert "Fake Item" in out

    # scan
    command.run(["scan", "some description"])  # uses fake recognise
    out = capsys.readouterr().out
    assert "Top" in out and "Fake Item" in out

    # add (manual)
    command.run(["add", "NewFood", "50g", "200", "--quantity", "2", "--protein", "5"])
    out = capsys.readouterr().out
    assert "Logged" in out or "Logged NewFood" in out

    # summary for today (may be empty or include recent manual add)
    command.run(["summary"])  # default is today
    out = capsys.readouterr().out
    assert "Total:" in out or "No entries for" in out
