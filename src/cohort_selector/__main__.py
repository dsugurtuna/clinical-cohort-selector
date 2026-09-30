"""Command-line interface: ``python -m cohort_selector <command>``."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .impact import ExclusionImpactAnalyser
from .integrator import PhenotypeIntegrator
from .stratifier import CohortStratifier


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cohort-selector")
    sub = parser.add_subparsers(dest="command", required=True)

    impact = sub.add_parser("impact", help="how many people an exclusion removes")
    impact.add_argument("master_csv")
    impact.add_argument("--pattern", default="E2", help="substring of genotype")

    strat = sub.add_parser("stratify", help="build recall lists")
    strat.add_argument("candidates_csv")
    strat.add_argument("--males", help="separate CSV of male candidates")
    strat.add_argument("--e4-per-stage", type=int, default=80)
    strat.add_argument("--e3e3-per-stage", type=int, default=80)
    strat.add_argument("--male-ratio", type=float, default=0.22)
    strat.add_argument("--seed", type=int, help="draw candidates in seeded order")
    strat.add_argument(
        "--exclude-e2",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="exclude e2/e4 participants (default: yes)",
    )
    strat.add_argument("--out", required=True, help="output directory")

    merge = sub.add_parser("merge", help="join genotypes with age and sex")
    merge.add_argument("genotype_csv", help="sample_id,participant_id,genotype")
    merge.add_argument("phenotype_file", help="sample_id age gender")
    merge.add_argument("output_csv")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "impact":
        analyser = ExclusionImpactAnalyser()
        print(analyser.format_report(analyser.analyse(args.master_csv, args.pattern)))
    elif args.command == "stratify":
        stratifier = CohortStratifier(exclude_e2=args.exclude_e2)
        result = stratifier.build_recall(
            args.candidates_csv,
            args.males,
            e4_per_stage=args.e4_per_stage,
            e3e3_per_stage=args.e3e3_per_stage,
            male_ratio=args.male_ratio,
            seed=args.seed,
        )
        for path in stratifier.export_recall(result, args.out):
            print(path)
        print(open(f"{args.out}/recall_summary.txt").read(), end="")
    else:
        report = PhenotypeIntegrator().merge(
            args.genotype_csv, args.phenotype_file, args.output_csv
        )
        print(
            f"matched {report.matched_records}; genotype-only "
            f"{report.unmatched_genotype}; phenotype-only {report.unmatched_phenotype}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
