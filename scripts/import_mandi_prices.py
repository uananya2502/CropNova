"""Import downloaded AGMARKNET CSV or yearly Parquet files into CropNova."""

import argparse
import csv
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mandi_data import FIELDS, data_path, normalized, observation


def input_rows(path):
    if path.suffix.lower() == ".parquet":
        try:
            from pyarrow.parquet import ParquetFile
        except ImportError as exc:
            raise SystemExit("Install pyarrow to import Parquet files, or use a CSV file.") from exc
        for batch in ParquetFile(path).iter_batches(columns=FIELDS):
            yield from batch.to_pylist()
    else:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            # The AGMARKNET export and prepared Parquet use slightly different headers.
            headers = {name.strip().casefold().replace(" ", "_"): name
                       for name in (reader.fieldnames or [])}
            if not all(field.casefold() in headers for field in FIELDS):
                raise ValueError(f"{path.name} is missing required columns: {', '.join(FIELDS)}")
            for row in reader:
                yield {name: row[headers[name.casefold()]] for name in FIELDS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--state", action="append", default=[], help="Optional state filter, repeatable")
    args = parser.parse_args()
    states = {normalized(state) for state in args.state}
    target = data_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=target.parent,
                            delete=False) as stream:
        temporary = Path(stream.name)
        try:
            writer = csv.writer(stream)
            writer.writerow(FIELDS)
            for source in args.files:
                for row in input_rows(source):
                    if states and normalized(row.get("State")) not in states:
                        continue
                    parsed = observation(row)
                    if parsed:
                        labels, day, price = parsed
                        writer.writerow((*labels, day.isoformat(), price))
                        count += 1
            if not count:
                raise ValueError("No usable rows found. The existing price file was kept.")
            stream.close()
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    print(f"Imported {count:,} observations into {target}")


if __name__ == "__main__":
    main()
