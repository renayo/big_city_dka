#!/usr/bin/env python3
"""
CDC NCHS Natality Public Use File Downloader & Extractor
=========================================================
Downloads fixed-width natality microdata from the CDC FTP server and
extracts birth date/time distribution fields into compact CSV files.

Available years with Time of Birth (DOB_TT): 2014–2024

Data source:
  https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality/
User guides:
  https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/

Field layout (constant across 2014–2024, record length 1330):
  Positions 9–12   DOB_YY  Birth year
  Positions 13–14  DOB_MM  Birth month (01–12)
  Positions 19–22  DOB_TT  Time of birth HHMM (0000–2359; 9999=Not Stated)
  Position  23     DOB_WK  Day of week (1=Sun … 7=Sat)

Usage
-----
  # Download 2020–2022, extract everything, save full records:
  python cdc_natality_downloader.py --years 2020 2021 2022

  # Download 2018–2022, keep only 10 % random sample per year:
  python cdc_natality_downloader.py --years 2018 2019 2020 2021 2022 --sample 0.10

  # Download all available years, save summary tables only (no raw CSV):
  python cdc_natality_downloader.py --years all --summary-only

  # Dry-run: show what would be downloaded without doing it:
  python cdc_natality_downloader.py --years 2022 --dry-run

Dependencies:  requests, pandas, tqdm
  pip install requests pandas tqdm
"""

import argparse
import io
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

BASE_URL = (
    "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality/"
)
DOC_URL = (
    "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/"
    "Dataset_Documentation/DVS/natality/"
)

# Years for which DOB_TT (time of birth) is present in the public-use file.
# Hour of birth was added with the 2014 revision of the birth certificate.
AVAILABLE_YEARS = list(range(2014, 2025))  # 2014–2024 inclusive

# Fixed-width field specifications (0-indexed Python slices)
# Source: UserGuide2022.pdf (layout is identical across 2014–2024)
FIELDS = {
    "dob_yy": slice(8, 12),    # positions  9–12
    "dob_mm": slice(12, 14),   # positions 13–14
    "dob_tt": slice(18, 22),   # positions 19–22  (HHMM; 9999=Not Stated)
    "dob_wk": slice(22, 23),   # position  23     (1=Sun…7=Sat)
}

RECORD_LENGTH = 1330  # bytes per record (all years 2014–2024)

DAY_LABELS = {
    "1": "Sun", "2": "Mon", "3": "Tue",
    "4": "Wed", "5": "Thu", "6": "Fri", "7": "Sat",
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def zip_name(year: int) -> str:
    """Return the zip filename for a given year."""
    return f"Nat{year}us.zip"


def dat_name(year: int) -> str:
    """Return the expected .dat filename inside the zip."""
    # The inner file is typically Nat{year}us.txt or Nat{year}PublicUS.c20190509.r20190717.txt
    # We'll detect it at runtime; this is the common pattern.
    return f"Nat{year}us.txt"


def download_zip(year: int, dest_dir: Path, chunk_size: int = 1 << 20) -> Path:
    """
    Download the natality zip for *year* to *dest_dir*.
    Returns the local path to the downloaded zip.
    Skips download if the file already exists.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    local_zip = dest_dir / zip_name(year)

    if local_zip.exists():
        print(f"  [cache] {local_zip.name} already present, skipping download.")
        return local_zip

    url = BASE_URL + zip_name(year)
    print(f"  Downloading {url} …")

    resp = requests.get(url, stream=True, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(
            f"HTTP {resp.status_code} for {url}\n"
            "  Check that the year is in AVAILABLE_YEARS and the CDC FTP is reachable."
        )

    total = int(resp.headers.get("Content-Length", 0)) or None
    with (
        open(local_zip, "wb") as fh,
        tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            desc=f"  {zip_name(year)}",
            leave=False,
        ) as bar,
    ):
        for chunk in resp.iter_content(chunk_size):
            fh.write(chunk)
            bar.update(len(chunk))

    print(f"  Saved → {local_zip}  ({local_zip.stat().st_size / 1e6:.1f} MB)")
    return local_zip


def find_dat_member(zf: zipfile.ZipFile, year: int) -> str:
    """
    Locate the .txt / .dat data member inside the zip.
    The naming convention varies slightly across years.
    """
    candidates = [n for n in zf.namelist() if n.lower().endswith((".txt", ".dat"))]
    if not candidates:
        raise FileNotFoundError(
            f"No .txt/.dat member found in zip for {year}. "
            f"Members: {zf.namelist()}"
        )
    # Prefer the one that starts with 'Nat'
    nat_files = [c for c in candidates if c.lower().startswith("nat")]
    return nat_files[0] if nat_files else candidates[0]


def extract_records(
    local_zip: Path,
    year: int,
    sample_frac: float = 1.0,
    rng_seed: int = 42,
) -> pd.DataFrame:
    """
    Stream through the fixed-width data file inside *local_zip*,
    parse the date/time fields, and return a DataFrame.

    If sample_frac < 1.0, a random sample of that fraction is returned.
    """
    import random
    rng = random.Random(rng_seed)

    rows = []
    with zipfile.ZipFile(local_zip) as zf:
        member = find_dat_member(zf, year)
        print(f"  Parsing member: {member}")

        with zf.open(member) as raw:
            # Wrap in TextIOWrapper for line-by-line reading
            text = io.TextIOWrapper(raw, encoding="latin-1", errors="replace")
            n_read = n_skipped = 0

            for line in text:
                if len(line.rstrip("\n\r")) < RECORD_LENGTH - 5:
                    # Short line — trailing newline or header; skip
                    continue

                if sample_frac < 1.0 and rng.random() > sample_frac:
                    n_skipped += 1
                    continue

                yy  = line[FIELDS["dob_yy"]].strip()
                mm  = line[FIELDS["dob_mm"]].strip()
                tt  = line[FIELDS["dob_tt"]].strip()
                wk  = line[FIELDS["dob_wk"]].strip()
                rows.append((yy, mm, tt, wk))
                n_read += 1

                if n_read % 500_000 == 0:
                    print(f"    … {n_read:,} records parsed", flush=True)

    print(f"  Records parsed: {n_read:,}  (skipped by sampling: {n_skipped:,})")

    df = pd.DataFrame(rows, columns=["dob_yy", "dob_mm", "dob_tt", "dob_wk"])

    # ── Clean & type-cast ────────────────────────────────────────────────────
    df["dob_yy"] = pd.to_numeric(df["dob_yy"], errors="coerce").astype("Int16")
    df["dob_mm"] = pd.to_numeric(df["dob_mm"], errors="coerce").astype("Int8")
    df["dob_wk"] = pd.to_numeric(df["dob_wk"], errors="coerce").astype("Int8")

    # Time of birth: keep raw HHMM string, also derive integer hour
    df["dob_tt_raw"] = df["dob_tt"]
    df["dob_tt"] = pd.to_numeric(df["dob_tt"], errors="coerce")
    # 9999 → Not Stated
    not_stated = df["dob_tt"] == 9999
    df.loc[not_stated, "dob_tt"] = pd.NA
    # Derive hour (0–23) and minute (0–59) from HHMM integer
    df["birth_hour"] = (df["dob_tt"] // 100).astype("Int8")
    df["birth_minute"] = (df["dob_tt"] % 100).astype("Int8")
    # Sanity: null out impossible values
    df.loc[df["birth_hour"] > 23,   "birth_hour"]   = pd.NA
    df.loc[df["birth_minute"] > 59, "birth_minute"] = pd.NA

    return df


def build_summary(df: pd.DataFrame, year: int) -> dict[str, pd.DataFrame]:
    """
    Return a dict of summary DataFrames:
      hour_dist      – counts & % by hour of day (0–23)
      month_dist     – counts & % by birth month
      dow_dist       – counts & % by day of week
      time_stated    – count of stated vs not-stated birth times
    """
    n_total = len(df)

    def pct_table(series, label, sort=True):
        counts = series.value_counts(dropna=False, sort=sort).rename("count")
        pct    = (counts / n_total * 100).rename("pct")
        return pd.concat([counts, pct], axis=1).rename_axis(label)

    hour_dist  = pct_table(df["birth_hour"], "hour", sort=False).sort_index()
    month_dist = pct_table(df["dob_mm"],     "month", sort=False).sort_index()
    dow_dist   = pct_table(df["dob_wk"],     "day_of_week", sort=False).sort_index()
    dow_dist.index = dow_dist.index.map(lambda x: DAY_LABELS.get(str(int(x)), str(x)) if pd.notna(x) else "NA")

    time_stated = pd.DataFrame({
        "status": ["stated", "not_stated"],
        "count":  [df["birth_hour"].notna().sum(), df["birth_hour"].isna().sum()],
    })
    time_stated["pct"] = time_stated["count"] / n_total * 100

    return {
        "hour_dist":   hour_dist,
        "month_dist":  month_dist,
        "dow_dist":    dow_dist,
        "time_stated": time_stated,
    }


def save_outputs(
    df: pd.DataFrame,
    summaries: dict[str, pd.DataFrame],
    year: int,
    out_dir: Path,
    save_raw: bool,
) -> None:
    """Write CSV outputs to *out_dir*."""
    out_dir.mkdir(parents=True, exist_ok=True)

    if save_raw:
        raw_path = out_dir / f"natality_{year}_datetime.csv"
        df.to_csv(raw_path, index=False)
        print(f"  Raw CSV     → {raw_path}  ({raw_path.stat().st_size / 1e6:.1f} MB)")

    for name, tbl in summaries.items():
        path = out_dir / f"natality_{year}_{name}.csv"
        tbl.to_csv(path)
        print(f"  Summary CSV → {path}")


def print_summary(summaries: dict[str, pd.DataFrame], year: int) -> None:
    """Pretty-print key summary tables to stdout."""
    print(f"\n{'─'*60}")
    print(f"  Year {year} — Time-of-birth coverage")
    print(f"{'─'*60}")
    ts = summaries["time_stated"]
    for _, row in ts.iterrows():
        print(f"    {row['status']:>12s}:  {int(row['count']):>10,}  ({row['pct']:.1f}%)")

    print(f"\n  Birth hour distribution (0–23 UTC local hospital time):")
    hd = summaries["hour_dist"]
    for idx, row in hd.iterrows():
        if pd.isna(idx):
            print(f"    {'NA':>3s}  {int(row['count']):>8,}  {row['pct']:>5.2f}%  (not stated)")
            continue
        pct = float(row["pct"]) if pd.notna(row["pct"]) else 0.0
        bar = "█" * int(pct / 0.5)
        print(f"    {int(idx):>2}h  {int(row['count']):>8,}  {pct:>5.2f}%  {bar}")

    print(f"\n  Birth day-of-week:")
    for idx, row in summaries["dow_dist"].iterrows():
        label = str(idx) if pd.notna(idx) else "NA"
        print(f"    {label:>3s}  {int(row['count']):>8,}  {row['pct']:>5.2f}%")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Download & parse CDC NCHS natality microdata for birth date/time distributions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--years",
        nargs="+",
        default=["2022"],
        help=(
            "Years to process. Use integers (e.g. 2020 2021 2022) "
            f"or 'all' for {AVAILABLE_YEARS[0]}–{AVAILABLE_YEARS[-1]}. "
            "Default: 2022."
        ),
    )
    p.add_argument(
        "--sample",
        type=float,
        default=1.0,
        metavar="FRAC",
        help=(
            "Random sampling fraction 0 < FRAC ≤ 1.0. "
            "E.g. --sample 0.10 keeps ~10%% of records. Default: 1.0 (all records)."
        ),
    )
    p.add_argument(
        "--download-dir",
        type=Path,
        default=Path("./cdc_natality_raw"),
        help="Directory for downloaded zip files. Default: ./cdc_natality_raw",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./cdc_natality_output"),
        help="Directory for output CSV files. Default: ./cdc_natality_output",
    )
    p.add_argument(
        "--summary-only",
        action="store_true",
        help="Save only summary tables (no per-record raw CSV). Saves disk space.",
    )
    p.add_argument(
        "--no-download",
        action="store_true",
        help=(
            "Skip downloading; use zips already present in --download-dir. "
            "Useful if you downloaded manually from the CDC FTP."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without downloading or parsing.",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling. Default: 42.",
    )
    return p.parse_args()


def resolve_years(raw: list[str]) -> list[int]:
    if raw == ["all"]:
        return AVAILABLE_YEARS
    years = []
    for token in raw:
        try:
            y = int(token)
        except ValueError:
            print(f"Warning: '{token}' is not a valid year or 'all'; skipping.")
            continue
        if y not in AVAILABLE_YEARS:
            print(
                f"Warning: {y} is not in the available range "
                f"{AVAILABLE_YEARS[0]}–{AVAILABLE_YEARS[-1]}; "
                "hour-of-birth data may be absent."
            )
        years.append(y)
    return sorted(set(years))


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    years = resolve_years(args.years)

    if not years:
        print("No valid years specified. Exiting.")
        sys.exit(1)

    print(f"\nCDC NCHS Natality Downloader")
    print(f"  Years        : {years}")
    print(f"  Sample frac  : {args.sample:.2%}")
    print(f"  Download dir : {args.download_dir}")
    print(f"  Output dir   : {args.output_dir}")
    print(f"  Summary only : {args.summary_only}")
    print(f"  Dry run      : {args.dry_run}")
    print()

    if args.dry_run:
        for year in years:
            url = BASE_URL + zip_name(year)
            doc_url = DOC_URL + f"UserGuide{year}.pdf"
            print(f"  Would download: {url}")
            print(f"  User guide    : {doc_url}")
        print("\nDry run complete — nothing was downloaded.")
        return

    all_summaries = {}

    for year in years:
        print(f"\n{'═'*60}")
        print(f"  Processing year {year}")
        print(f"{'═'*60}")

        # 1. Download
        if args.no_download:
            local_zip = args.download_dir / zip_name(year)
            if not local_zip.exists():
                print(f"  ERROR: {local_zip} not found and --no-download is set. Skipping.")
                continue
            print(f"  Using cached zip: {local_zip}")
        else:
            try:
                local_zip = download_zip(year, args.download_dir)
            except Exception as exc:
                print(f"  Download failed for {year}: {exc}")
                continue

        # 2. Parse
        try:
            df = extract_records(local_zip, year, sample_frac=args.sample, rng_seed=args.seed)
        except Exception as exc:
            print(f"  Parse failed for {year}: {exc}")
            continue

        # 3. Summarise
        summaries = build_summary(df, year)
        all_summaries[year] = summaries
        print_summary(summaries, year)

        # 4. Save
        save_outputs(
            df,
            summaries,
            year,
            args.output_dir,
            save_raw=not args.summary_only,
        )

    # ── Combined summary across all processed years ──────────────────────────
    if len(all_summaries) > 1:
        print(f"\n{'═'*60}")
        print("  Combined hour distribution across all years")
        print(f"{'═'*60}")
        combined = pd.concat(
            {y: s["hour_dist"]["count"] for y, s in all_summaries.items()},
            axis=1,
        )
        combined.columns.name = "year"
        combined["total"] = combined.sum(axis=1)
        combined_path = args.output_dir / "natality_combined_hour_dist.csv"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        combined.to_csv(combined_path)
        print(f"\n  Combined CSV → {combined_path}")
        print(combined.to_string())

    print(f"\n{'═'*60}")
    print("  Done.")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
