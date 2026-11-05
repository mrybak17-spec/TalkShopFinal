#!/usr/bin/env python

"""This is a simple example of argparse use.
You can see this because this is __doc__
"""

# ======================================================================================
#                                     IMPORTS
# ======================================================================================
from __future__ import annotations

import argparse
from dataclasses import dataclass


def positive_int(txt: str) -> int:
    try:
        i = int(txt)
        if i <= 0:
            raise ValueError()
        return i
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"Value {txt} is not valid positive integer.")


@dataclass
class Config:
    in_path: str
    out_path: str
    depth: int

    @staticmethod
    def from_args() -> Config:
        prsr = argparse.ArgumentParser(description=__doc__)
        prsr.add_argument(
            "--depth", type=positive_int, default=10, help="Neural net depth"
        )
        prsr.add_argument(
            "-i", "--in_path", required=True, type=str, help="Input file path"
        )
        prsr.add_argument(
            "-o", "--out_path", required=True, type=str, help="Output file path"
        )

        args = prsr.parse_args()
        return Config(in_path=args.in_path, out_path=args.out_path, depth=args.depth)


# ======================================================================================
#                                      MAIN
# ======================================================================================
def main():
    cfg = Config.from_args()
    print(cfg)


if __name__ == "__main__":
    main()
