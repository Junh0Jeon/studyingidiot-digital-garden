from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import MssScreenCapture, PyAutoGuiInputController
from .automation import (
    AutomationAbortedError,
    AutomationProfile,
    AutomationProfileError,
    CraftingAutomationRunner,
    build_action_plan,
)
from .manifest import NodeManifestIndex
from .ocr import EasyOcrEngine
from .scanner import CandidateNodeScanner
from .selector import CraftingTable, GiftPrioritySelector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run three-stage Blue Archive crafting automation."
    )
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--craft-slot", type=int, choices=(1, 2, 3))
    scope.add_argument("--all", action="store_true", dest="all_crafts")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--crafting-table", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, default=Path("diagnostics"))
    parser.add_argument("--monitor", type=int, default=1)
    parser.add_argument("--gpu", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        profile = AutomationProfile.from_json(args.profile)
        manifest = NodeManifestIndex.from_files(args.manifest, args.crafting_table)
        table = CraftingTable.from_json(args.crafting_table)
    except (AutomationProfileError, ValueError) as error:
        print(json.dumps({"success": False, "reason": str(error)}, ensure_ascii=False, indent=2))
        return 2

    slots = (0, 1, 2) if args.all_crafts else (args.craft_slot - 1,)
    if not args.execute:
        print(
            json.dumps(
                {
                    "success": True,
                    "executed": False,
                    "scope": "all" if args.all_crafts else f"slot-{args.craft_slot}",
                    "plannedActions": list(
                        build_action_plan(slots, collect=args.all_crafts)
                    ),
                    "message": "Add --execute to perform clicks and consume materials.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    input_controller = PyAutoGuiInputController()
    scanner = CandidateNodeScanner(
        profile=profile.screen,
        manifest=manifest,
        screen_capture=MssScreenCapture(args.monitor),
        input_controller=input_controller,
        ocr_engine=EasyOcrEngine(gpu=args.gpu),
        diagnostics_root=args.diagnostics,
    )
    runner = CraftingAutomationRunner(
        profile=profile,
        scanner=scanner,
        selector=GiftPrioritySelector(table),
        input_controller=input_controller,
    )
    try:
        result = (
            runner.run_all(execute=True)
            if args.all_crafts
            else runner.run_single(args.craft_slot - 1, execute=True)
        )
    except AutomationAbortedError as error:
        print(
            json.dumps(
                {
                    "success": False,
                    "completedState": error.completed_state,
                    "reason": str(error.cause),
                    "actionLog": list(error.action_log),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
