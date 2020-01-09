#!/usr/bin/env python

from . import BinaryTimeSeriesFile

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', default=5, type=int, metavar='n', help="print first n entries")
    parser.add_argument('-l', default=5, type=int, metavar='n', help="print last n entries")
    parser.add_argument('btsf_file')
    args = parser.parse_args()
    with BinaryTimeSeriesFile.openread(args.btsf_file) as f:
        print(f"{args.btsf_file} - Number of entries: {f.n_entries}")
        print(f"Metrics:")
        print('   '.join(f"{metric.identifier} ({metric.type})" for metric in f.metrics))
        if args.f or args.l and f.n_entries:
            if (args.f + args.l) < f.n_entries:
                print(f"first {args.f} entries:")
                for values in [f.read() for _ in range(args.f)]:
                    print(f"{values}")
                f.goto_entry(f.n_entries - args.l)
                print("...")
                print(f"last {args.l} entries:")
                for values in [f.read() for _ in range(args.l)]:
                    print(f"{values}")
            else:
                print("entries:")
                for _ in range(f.n_entries):
                    print(f"{f.read()}")

if __name__ == "__main__":
    main()
