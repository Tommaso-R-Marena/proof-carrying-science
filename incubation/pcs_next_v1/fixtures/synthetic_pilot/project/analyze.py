
"""Synthetic analysis script for PCS Next pilot (no network)."""
import csv
from pathlib import Path

def main():
    rows = list(csv.DictReader((Path(__file__).parent/"predictions.csv").open()))
    assert rows, "empty"
    print(len(rows))

if __name__ == "__main__":
    main()
