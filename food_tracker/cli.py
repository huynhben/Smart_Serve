"""Command line interface for the food tracker application."""

from __future__ import annotations

import argparse
from datetime import date
from typing import Iterable

from .ai import FoodRecognitionEngine
from .tracker import FoodTracker


def _format_macros(macros: dict) -> str:
    return ", ".join(f"{nutrient}: {amount:.1f}g" for nutrient, amount in macros.items()) or "-"


def _print_daily_log(log) -> None:
    print(f"\n=== {log.day.isoformat()} ===")
    for entry in log.entries:
        macros = _format_macros(entry.macronutrients)
        time = entry.timestamp.strftime("%H:%M")
        print(
            f"[{time}] {entry.food.name} x{entry.quantity:g} "
            f"({entry.calories:.0f} kcal, {macros})"
        )
    print(f"Total: {log.total_calories():.0f} kcal | Macros: {_format_macros(log.total_macros())}")


class CLI:
    def __init__(self) -> None:
        recogniser = FoodRecognitionEngine()
        self.tracker = FoodTracker(recogniser=recogniser)

    def run(self, argv: Iterable[str] | None = None) -> None:
        parser = argparse.ArgumentParser(description="AI-assisted food tracking")
        sub = parser.add_subparsers(dest="command", required=True)

        scan = sub.add_parser("scan", help="Recognise a food from text or a voice transcript")
        scan.add_argument("description", help="Description of the food, e.g. 'grilled chicken salad'")
        scan.add_argument("--top", type=int, default=3, help="Number of matches to return")

        add = sub.add_parser("add", help="Log a food item manually")
        add.add_argument("name")
        add.add_argument("serving_size")
        add.add_argument("calories", type=float)
        add.add_argument("--quantity", type=float, default=1.0)
        add.add_argument("--carbs", type=float, default=0.0)
        add.add_argument("--protein", type=float, default=0.0)
        add.add_argument("--fat", type=float, default=0.0)

        log_cmd = sub.add_parser("log", help="Log a recognised food")
        log_cmd.add_argument("description")
        log_cmd.add_argument("--quantity", type=float, default=1.0)

        summary = sub.add_parser("summary", help="Show a summary for today or a given date")
        summary.add_argument("--date", help="Date in YYYY-MM-DD format. Defaults to today.")

        list_foods = sub.add_parser("foods", help="List known foods from the AI model")
        list_foods.add_argument("--limit", type=int, default=20)

        goals = sub.add_parser("goals", help="View or update nutrition goals")
        goals.add_argument("--calories", type=float, help="Daily calorie target")
        goals.add_argument("--protein", type=float, help="Daily protein target in grams")
        goals.add_argument("--carbs", type=float, help="Daily carbs target in grams")
        goals.add_argument("--fat", type=float, help="Daily fat target in grams")
        goals.add_argument("--clear", action="store_true", help="Reset all saved goals")

        stats = sub.add_parser("stats", help="Show weekly insights and streaks")

        args = parser.parse_args(list(argv) if argv is not None else None)

        if args.command == "scan":
            self._handle_scan(args.description, args.top)
        elif args.command == "add":
            self._handle_manual_add(args)
        elif args.command == "log":
            self._handle_log(args.description, args.quantity)
        elif args.command == "summary":
            target_date = date.fromisoformat(args.date) if args.date else date.today()
            self._handle_summary(target_date)
        elif args.command == "foods":
            self._handle_foods(args.limit)
        elif args.command == "goals":
            self._handle_goals(args)
        elif args.command == "stats":
            self._handle_stats()

    def _handle_scan(self, description: str, top_k: int) -> None:
        results = self.tracker.scan_description(description, top_k=top_k)
        if not results:
            print("No matches found. Try providing more detail or add the item manually.")
            return
        print(f"Top {len(results)} matches for '{description}':")
        for idx, result in enumerate(results, start=1):
            macros = _format_macros(result.item.macronutrients)
            print(
                f"{idx}. {result.item.name} ({result.item.calories:.0f} kcal) "
                f"[{macros}] confidence={result.confidence:.2f}"
            )

    def _handle_manual_add(self, args: argparse.Namespace) -> None:
        macros = {
            "carbs": args.carbs,
            "protein": args.protein,
            "fat": args.fat,
        }
        entry = self.tracker.manual_food_entry(
            name=args.name,
            serving_size=args.serving_size,
            calories=args.calories,
            quantity=args.quantity,
            macronutrients=macros,
        )
        print(
            f"Logged {entry.food.name} x{entry.quantity:g} "
            f"({entry.calories:.0f} kcal, {_format_macros(entry.macronutrients)})"
        )

    def _handle_log(self, description: str, quantity: float) -> None:
        results = self.tracker.scan_description(description)
        if not results:
            print("Could not recognise the food. Use 'add' to create a manual entry.")
            return
        best_match = results[0]
        entry = self.tracker.log_food(best_match.item, quantity=quantity)
        print(
            f"Logged {entry.food.name} x{entry.quantity:g} "
            f"({entry.calories:.0f} kcal, {_format_macros(entry.macronutrients)})"
        )

    def _handle_summary(self, target_day: date) -> None:
        log = self.tracker.entries_for_day(target_day)
        if not log.entries:
            print(f"No entries for {target_day.isoformat()} yet.")
            return
        _print_daily_log(log)

    def _handle_foods(self, limit: int) -> None:
        print(f"Listing {limit} foods known by the recognition engine:")
        for item in self.tracker.recogniser.known_items()[:limit]:
            macros = _format_macros(item.macronutrients)
            print(f"- {item.name} ({item.calories:.0f} kcal per {item.serving_size}) [{macros}]")

    def _handle_goals(self, args: argparse.Namespace) -> None:
        macros = {
            nutrient: getattr(args, nutrient)
            for nutrient in ("protein", "carbs", "fat")
            if getattr(args, nutrient) is not None
        }
        calories = args.calories
        if args.clear:
            macros = {nutrient: None for nutrient in ("protein", "carbs", "fat")}
            calories = None

        if calories is not None or macros:
            updated = self.tracker.update_goals(calories=calories, macronutrients=macros or None)
            macro_text = _format_macros(updated.macronutrients)
            cal_text = f"{updated.calories:.0f} kcal" if updated.calories else "not set"
            print(f"Saved goals: Calories {cal_text} | Macros {macro_text}")
        else:
            goals = self.tracker.nutrition_goals()
            macro_text = _format_macros(goals.macronutrients)
            cal_text = f"{goals.calories:.0f} kcal" if goals.calories else "not set"
            print(f"Current goals -> Calories: {cal_text} | Macros: {macro_text}")

    def _handle_stats(self) -> None:
        today = self.tracker.progress_for_day()
        weekly = self.tracker.weekly_overview()
        lifetime = self.tracker.lifetime_stats()

        print("\n=== Today's Progress ===")
        cal = today["calories"]
        if cal["target"]:
            print(f"Calories: {cal['consumed']:.0f}/{cal['target']:.0f} kcal ({(cal['progress'] or 0)*100:.0f}%)")
        else:
            print(f"Calories logged: {cal['consumed']:.0f} kcal")

        if today["macronutrients"]:
            print("Macros:")
            for nutrient, payload in today["macronutrients"].items():
                if payload["target"]:
                    percent = f" ({(payload['progress'] or 0)*100:.0f}%)"
                else:
                    percent = ""
                print(
                    f"  - {nutrient.title()}: {payload['consumed']:.1f}"
                    + (f"/{payload['target']:.1f}g{percent}" if payload["target"] else "g")
                )

        print("\n=== Weekly Overview ===")
        print(f"Active days last week: {weekly['active_days']}")
        print(f"Average calories (active days): {weekly['average_calories']:.0f} kcal")
        print(f"Current streak: {weekly['current_streak']} days")

        print("\n=== Lifetime Stats ===")
        print(f"Entries logged: {lifetime['total_entries']}")
        print(f"Total calories logged: {lifetime['total_calories']:.0f} kcal")
        if lifetime["most_logged_food"]:
            top = lifetime["most_logged_food"]
            print(f"Most logged food: {top['name']} ({top['count']}x)")


def run(argv: Iterable[str] | None = None) -> None:
    CLI().run(argv)


if __name__ == "__main__":
    run()
