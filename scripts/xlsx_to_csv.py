# scripts/xlsx_to_csv.py
# Aviation-AMO-MRO-system — XLSX→CSV export for db/import/staging/load_from_csv.sql
#
# Reads sheets from XLSX:
#   Airlines, Fleet_ALL, Fleet_LOTAMS, Fleet_LS_Technics, Fleet_Unknown, Summary
#
# Generates 4 CSV into output folder (overwrite):
#   airline_customers.csv         airline_code, airline_name, airline_iata, airline_icao
#   mro_customers.csv             mro_code, airline_code
#   aircraft.csv                  current_registration, msn, manufacturer, type, subtype, model, airline_code
#   aircraft_mro_access.csv       current_registration, mro_code
#
# Validations:
# - prints columns per used sheet
# - required columns present (explicit)
# - headers EXACT
# - current_registration non-empty where required
# - airline_code non-empty where required
#
# Windows-safe: UTF-8, pathlib paths

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


def log(msg: str) -> None:
    print(f"[xlsx_to_csv] {msg}")


def die(msg: str, code: int = 2) -> None:
    print(f"[xlsx_to_csv] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


REQUIRED_SHEETS = [
    "Airlines",
    "Fleet_ALL",
    "Fleet_LOTAMS",
    "Fleet_LS_Technics",
    "Fleet_Unknown",
    "Summary",
]

REQ_COLS = {
    "Airlines": ["Airline", "IATA", "ICAO"],
    "Fleet_ALL": ["Airline", "Airline_IATA", "Airline_ICAO", "Registration", "MSN", "Manufacturer", "Type", "Subtype", "Model"],
    "Fleet_LOTAMS": ["Airline", "Airline_IATA", "Airline_ICAO", "Registration"],
    "Fleet_LS_Technics": ["Airline", "Airline_IATA", "Airline_ICAO", "Registration"],
}


def norm_str(x) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def slugify(s: str) -> str:
    s = norm_str(s).lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def derive_airline_code(icao: str, iata: str, name: str) -> Tuple[str, str]:
    """
    Prefer ICAO, else IATA, else slug(name). Returns (code, source).
    """
    icao_n = norm_str(icao).lower()
    if icao_n:
        return icao_n, "icao"
    iata_n = norm_str(iata).lower()
    if iata_n:
        return iata_n, "iata"
    name_n = slugify(name)
    if name_n:
        return name_n, "name"
    return "", "none"


def assert_sheets(xlsx: Path) -> List[str]:
    try:
        xl = pd.ExcelFile(xlsx)
    except Exception as e:
        die(f"Cannot open XLSX: {xlsx}\n{e}")

    available = xl.sheet_names
    missing = [s for s in REQUIRED_SHEETS if s not in available]
    if missing:
        die(f"Missing required sheets in XLSX: {', '.join(missing)}\nAvailable sheets: {', '.join(available)}")

    return available


def read_sheet(xlsx: Path, sheet: str) -> pd.DataFrame:
    try:
        return pd.read_excel(xlsx, sheet_name=sheet)
    except Exception as e:
        die(f"Failed reading sheet '{sheet}' from {xlsx}\n{e}")
        raise


def print_columns(dfs: Dict[str, pd.DataFrame]) -> None:
    log("=== XLSX sheets / columns ===")
    for sheet, df in dfs.items():
        log(f"- {sheet}: {list(df.columns)}")
    log("=== end columns ===\n")


def require_columns(sheet: str, df: pd.DataFrame, required: List[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        die(f"Sheet '{sheet}' missing columns: {missing}\nPresent columns: {list(df.columns)}")


def validate_non_empty(df: pd.DataFrame, col: str, name: str) -> None:
    s = df[col].astype(str).str.strip()
    bad = df[s == ""]
    if not bad.empty:
        die(f"Validation failed: {name} has {len(bad)} empty '{col}' values (must be non-empty).")


def enforce_headers(df: pd.DataFrame, expected: List[str], name: str) -> None:
    if list(df.columns) != expected:
        die(f"Header mismatch for {name}\nExpected: {expected}\nActual:   {list(df.columns)}")


def write_csv(df: pd.DataFrame, path: Path, expected_headers: List[str]) -> None:
    enforce_headers(df, expected_headers, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def build_airline_customers(df_airlines: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    require_columns("Airlines", df_airlines, REQ_COLS["Airlines"])

    rows = []
    src_counts = {"icao": 0, "iata": 0, "name": 0, "none": 0}

    for _, r in df_airlines.iterrows():
        name = norm_str(r.get("Airline"))
        iata = norm_str(r.get("IATA"))
        icao = norm_str(r.get("ICAO"))

        code, src = derive_airline_code(icao=icao, iata=iata, name=name)
        src_counts[src] = src_counts.get(src, 0) + 1

        rows.append(
            {
                "airline_code": code,
                "airline_name": name,
                "airline_iata": iata,
                "airline_icao": icao,
            }
        )

    out = pd.DataFrame(rows, columns=["airline_code", "airline_name", "airline_iata", "airline_icao"])
    out = out.sort_values(by=["airline_code", "airline_name"], kind="stable")
    out = out.drop_duplicates(subset=["airline_code"], keep="first").reset_index(drop=True)

    validate_non_empty(out, "airline_code", "airline_customers.csv")
    return out, src_counts


def build_aircraft(df_fleet_all: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    require_columns("Fleet_ALL", df_fleet_all, REQ_COLS["Fleet_ALL"])

    rows = []
    src_counts = {"icao": 0, "iata": 0, "name": 0, "none": 0}

    for _, r in df_fleet_all.iterrows():
        reg = norm_str(r.get("Registration")).upper()
        msn = norm_str(r.get("MSN"))
        manufacturer = norm_str(r.get("Manufacturer"))
        typ = norm_str(r.get("Type"))
        subtype = norm_str(r.get("Subtype"))
        model = norm_str(r.get("Model"))

        name = norm_str(r.get("Airline"))
        iata = norm_str(r.get("Airline_IATA"))
        icao = norm_str(r.get("Airline_ICAO"))
        airline_code, src = derive_airline_code(icao=icao, iata=iata, name=name)
        src_counts[src] = src_counts.get(src, 0) + 1

        rows.append(
            {
                "current_registration": reg,
                "msn": msn,
                "manufacturer": manufacturer,
                "type": typ,
                "subtype": subtype,
                "model": model,
                "airline_code": airline_code,
            }
        )

    out = pd.DataFrame(
        rows,
        columns=["current_registration", "msn", "manufacturer", "type", "subtype", "model", "airline_code"],
    )

    validate_non_empty(out, "current_registration", "aircraft.csv")
    validate_non_empty(out, "airline_code", "aircraft.csv")
    return out, src_counts


def build_mro_relations(
    df_lotams: pd.DataFrame,
    df_lst: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, int]]:
    require_columns("Fleet_LOTAMS", df_lotams, REQ_COLS["Fleet_LOTAMS"])
    require_columns("Fleet_LS_Technics", df_lst, REQ_COLS["Fleet_LS_Technics"])

    mro_rows = []
    access_rows = []
    src_counts = {"icao": 0, "iata": 0, "name": 0, "none": 0}

    def consume(df: pd.DataFrame, mro_code: str) -> None:
        nonlocal mro_rows, access_rows, src_counts
        for _, r in df.iterrows():
            name = norm_str(r.get("Airline"))
            iata = norm_str(r.get("Airline_IATA"))
            icao = norm_str(r.get("Airline_ICAO"))
            airline_code, src = derive_airline_code(icao=icao, iata=iata, name=name)
            src_counts[src] = src_counts.get(src, 0) + 1

            reg = norm_str(r.get("Registration")).upper()

            # relations
            mro_rows.append({"mro_code": mro_code, "airline_code": airline_code})
            access_rows.append({"current_registration": reg, "mro_code": mro_code})

    consume(df_lotams, "lotams")
    consume(df_lst, "lst")

    mro_df = pd.DataFrame(mro_rows, columns=["mro_code", "airline_code"]).drop_duplicates().reset_index(drop=True)
    access_df = pd.DataFrame(access_rows, columns=["current_registration", "mro_code"]).drop_duplicates().reset_index(drop=True)

    validate_non_empty(mro_df, "mro_code", "mro_customers.csv")
    validate_non_empty(mro_df, "airline_code", "mro_customers.csv")
    validate_non_empty(access_df, "current_registration", "aircraft_mro_access.csv")
    validate_non_empty(access_df, "mro_code", "aircraft_mro_access.csv")

    return mro_df, access_df, src_counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True, help="Path to XLSX (e.g. db/import/source/Floty_MRO_PGL_v1.1.1_FINAL.xlsx)")
    ap.add_argument("--out", required=True, help="Output folder (e.g. db/import/staging)")
    args = ap.parse_args()

    xlsx = Path(args.xlsx).resolve()
    out_dir = Path(args.out).resolve()

    if not xlsx.exists():
        die(f"XLSX not found: {xlsx}")

    assert_sheets(xlsx)

    dfs = {s: read_sheet(xlsx, s) for s in REQUIRED_SHEETS}
    print_columns(dfs)

    # strict input validation for used sheets
    for sheet in ["Airlines", "Fleet_ALL", "Fleet_LOTAMS", "Fleet_LS_Technics"]:
        require_columns(sheet, dfs[sheet], REQ_COLS[sheet])

    airline_customers, src_air = build_airline_customers(dfs["Airlines"])
    aircraft, src_fleet_all = build_aircraft(dfs["Fleet_ALL"])
    mro_customers, aircraft_mro_access, src_mro = build_mro_relations(dfs["Fleet_LOTAMS"], dfs["Fleet_LS_Technics"])

    # enforce exact output headers + write
    p1 = out_dir / "airline_customers.csv"
    p2 = out_dir / "mro_customers.csv"
    p3 = out_dir / "aircraft.csv"
    p4 = out_dir / "aircraft_mro_access.csv"

    write_csv(airline_customers, p1, ["airline_code", "airline_name", "airline_iata", "airline_icao"])
    write_csv(mro_customers, p2, ["mro_code", "airline_code"])
    write_csv(aircraft, p3, ["current_registration", "msn", "manufacturer", "type", "subtype", "model", "airline_code"])
    write_csv(aircraft_mro_access, p4, ["current_registration", "mro_code"])

    # summary
    log("=== CSV write summary ===")
    log(f"- {p1.name}: {len(airline_customers)} rows")
    log(f"- {p2.name}: {len(mro_customers)} rows")
    log(f"- {p3.name}: {len(aircraft)} rows")
    log(f"- {p4.name}: {len(aircraft_mro_access)} rows")

    log("=== CSV headers (exact) ===")
    log(f"- {p1.name}: {list(airline_customers.columns)}")
    log(f"- {p2.name}: {list(mro_customers.columns)}")
    log(f"- {p3.name}: {list(aircraft.columns)}")
    log(f"- {p4.name}: {list(aircraft_mro_access.columns)}")

    log("=== airline_code derivation stats ===")
    log(f"- Airlines: {src_air}")
    log(f"- Fleet_ALL: {src_fleet_all}")
    log(f"- Fleet_LOTAMS/LST: {src_mro}")

    log("OK.")


if __name__ == "__main__":
    main()
