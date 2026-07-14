from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import MssScreenCapture, PyAutoGuiInputController
from .manifest import NodeManifestIndex
from .models import ScreenProfile
from .ocr import EasyOcrEngine
from .scanner import CandidateNodeScanner, ScanAbortedError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Click and OCR-read the five Blue Archive crafting nodes."
    )
    parser.add_argument("--stage", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--crafting-table", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, default=Path("diagnostics"))
    parser.add_argument("--monitor", type=int, default=1)
    parser.add_argument("--gpu", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = ScreenProfile.from_json(args.profile)
    manifest = NodeManifestIndex.from_files(args.manifest, args.crafting_table)
    scanner = CandidateNodeScanner(
        profile=profile,
        manifest=manifest,
        screen_capture=MssScreenCapture(args.monitor),
        input_controller=PyAutoGuiInputController(),
        ocr_engine=EasyOcrEngine(gpu=args.gpu),
        diagnostics_root=args.diagnostics,
    )
    try:
        batch = scanner.scan_candidate_nodes(args.stage)
    except ScanAbortedError as error:
        failure = error.failure
        print(
            json.dumps(
                {
                    "success": False,
                    "stage": failure.stage,
                    "slotIndex": failure.slot_index,
                    "reason": failure.reason,
                    "diagnosticDirectory": (
                        str(failure.diagnostic_directory)
                        if failure.diagnostic_directory
                        else None
                    ),
                    "nearestCandidates": list(failure.nearest_candidates),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(json.dumps({"success": True, **batch.to_dict()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
