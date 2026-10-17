"""Run the fixed repaired benchmark with the explicit Equation 7 feature loader."""
import argparse
from pathlib import Path
from common import HERE
from evaluate_repaired import run
from normalization_features import VARIANT, load_matrix

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['plan','run'],default='plan')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(VARIANT,args.mode,args.output,HERE/'benchmark_normalization_protocol.json',
        feature_loader=load_matrix,
        preflight_receipt=HERE/'output/2026-10-15-normalization-comparison/preflight.json')
