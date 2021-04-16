#!/usr/bin/env python

from . import BinaryTimeSeriesFile


def info(args):
    with BinaryTimeSeriesFile.openread(args.btsf_file) as f:
        print(f"{args.btsf_file} - Number of entries: {f.n_entries}")
        print(f"Metrics:")
        print("   ".join(f"{metric.identifier} ({metric.type})" for metric in f.metrics))
        if args.f or args.l and f.n_entries:
            if (args.f + args.l) < f.n_entries:
                print(f"first {args.f} entries:")
                for values in [next(f) for _ in range(args.f)]:
                    print(f"{values}")
                f.goto_entry(f.n_entries - args.l)
                print("...")
                print(f"last {args.l} entries:")
                for values in [next(f) for _ in range(args.l)]:
                    print(f"{values}")
            else:
                print("entries:")
                for _ in range(f.n_entries):
                    print(f"{next(f)}")


def export(args):
    import sys

    sys.stderr.write(
        f"Exporting {args.btsf_file} to {args.out_file.name} (format: {args.format})\n"
    )
    with BinaryTimeSeriesFile.openread(args.btsf_file) as f:
        if args.format == "csv":
            args.out_file.write(
                "; ".join(f"{metric.identifier}" for metric in f.metrics) + "\n"
            )
            for values in f:
                args.out_file.write("; ".join(str(v) for v in values) + "\n")
        elif args.format == "tabular":
            args.out_file.write(
                " ".join("{:20.20s}".format(m.identifier) for m in f.metrics) + "\n"
            )
            for values in f:
                args.out_file.write(
                    " ".join("{:20.20}".format(str(v)) for v in values) + "\n"
                )
        else:
            raise NotImplementedError


def main():
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True

    info_parser = subparsers.add_parser("info")
    info_parser.add_argument(
        "-f", default=5, type=int, metavar="n", help="print first n entries"
    )
    info_parser.add_argument(
        "-l", default=5, type=int, metavar="n", help="print last n entries"
    )
    info_parser.add_argument("btsf_file")
    info_parser.set_defaults(func=info)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument(
        "--format", "-f", choices=("tabular", "csv"), default="tabular"
    )
    export_parser.add_argument("btsf_file")
    export_parser.add_argument(
        "out_file", type=argparse.FileType("w"), default="-", nargs="?"
    )
    export_parser.set_defaults(func=export)

    args = parser.parse_args()
    args.func(args)
