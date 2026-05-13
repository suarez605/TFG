from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from src.config import load_pipeline_config  # noqa: E402
from src.pipeline import PipelineRunner  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fallacy generation pipeline")
    parser.add_argument(
        "--config",
        default="src/settings.json",
        help="Path to JSON config file",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier. If omitted, a timestamp-based id is created",
    )

    stage_group = parser.add_mutually_exclusive_group()
    stage_group.add_argument(
        "--from-stage",
        choices=["generation", "corpus", "analysis", "all"],
        help="Stage to start from (runs this stage and all subsequent ones)",
    )
    stage_group.add_argument(
        "--stage",
        choices=["generation", "corpus", "analysis"],
        help="Run exactly one stage and stop",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_pipeline_config(args.config)

    runner = PipelineRunner(config=config, run_id=args.run_id)
    print(f"Run ID: {runner.run_id}")

    if args.stage:
        runner.run_stage(args.stage)
    else:
        runner.run(start_stage=args.from_stage or "generation")

    print("Pipeline finished")


if __name__ == "__main__":
    main()
