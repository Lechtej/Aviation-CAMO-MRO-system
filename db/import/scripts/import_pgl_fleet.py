# import_pgl_fleet.py (v0.2.3)
#
# Reads Floty_MRO_PGL_v1.1.1_FINAL.xlsx (sheet Fleet_ALL) and produces CSV exports:
# - export/airline_customers.csv
# - export/mro_customers.csv
# - export/aircraft.csv
# - export/aircraft_mro_access.csv
#
# The CSVs are then loaded into Postgres via psql scripts.

from __future__ import annotations

import argparse
import re
from pathlib import Path
import pandas as pd


def norm(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:30] if s else "unknown"


def mro_code(raw: str) -> str:
    v = raw.strip().lower()
    if "lotams" in v:
        return "lotams"
    if ("ls" in v and "technic" in v) or v == "lst":
        return "lst"
    return v


def normalize_lot(code: str, name: str, icao: str, iata: str) -> str:
    if icao.upper() == "LOT" or iata.upper() == "LO" or "polskie linie lotnicze" in name.lower() or re.search(r"\bpll\s*lot\b", name.lower()):
        return "lot"
    return code.lower()


def airline_code(icao: str, iata: str, name: str) -> str:
    if icao:
        return icao.lower()
    if iata:
        return iata.lower()
    return slug(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=str, required=True, help="Path to Floty_MRO_PGL_v1.1.1_FINAL.xlsx")
    ap.add_argument("--out", type=str, required=True, help="Output directory for CSV exports (export/)")
    args = ap.parse_args()

    xlsx = Path(args.xlsx)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    fleet = pd.read_excel(xlsx, sheet_name="Fleet_ALL").map(norm)
    airlines_sheet = pd.read_excel(xlsx, sheet_name="Airlines").map(norm)

    # Derive airline codes
    fleet["airline_code"] = fleet.apply(
        lambda r: normalize_lot(
            airline_code(r.get("Airline_ICAO",""), r.get("Airline_IATA",""), r.get("Airline","")),
            r.get("Airline",""),
            r.get("Airline_ICAO",""),
            r.get("Airline_IATA",""),
        ),
        axis=1,
    )
    fleet["mro_code"] = fleet["MRO"].apply(mro_code)

    # Normalize keys
    fleet["current_registration"] = fleet["Registration"].str.replace(" ", "", regex=False).str.upper()
    fleet["msn"] = fleet["MSN"].str.replace(" ", "", regex=False)

    # airline_customers.csv
    airline_customers = (
        fleet[["airline_code","Airline","Airline_IATA","Airline_ICAO"]]
        .drop_duplicates()
        .rename(columns={"Airline":"airline_name","Airline_IATA":"airline_iata","Airline_ICAO":"airline_icao"})
        .sort_values("airline_code")
    )
    airline_customers.to_csv(out/"airline_customers.csv", index=False)

    # mro_customers.csv
    airlines_sheet["mro_code"] = airlines_sheet["MRO"].apply(mro_code)
    airlines_sheet["airline_code"] = airlines_sheet.apply(
        lambda r: normalize_lot(
            airline_code(r.get("ICAO",""), r.get("IATA",""), r.get("Airline","")),
            r.get("Airline",""),
            r.get("ICAO",""),
            r.get("IATA",""),
        ),
        axis=1
    )
    mro_customers = airlines_sheet[["mro_code","airline_code"]].drop_duplicates().sort_values(["mro_code","airline_code"])
    mro_customers.to_csv(out/"mro_customers.csv", index=False)

    # aircraft.csv (one row per registration)
    aircraft = (
        fleet[["current_registration","msn","Manufacturer","Type","Subtype","Model","airline_code"]]
        .drop_duplicates(subset=["current_registration"])
        .rename(columns={"Manufacturer":"manufacturer","Type":"type","Subtype":"subtype","Model":"model"})
        .sort_values("current_registration")
    )
    aircraft.to_csv(out/"aircraft.csv", index=False)

    # aircraft_mro_access.csv (one row per registration per MRO)
    access = (
        fleet[["current_registration","mro_code"]]
        .drop_duplicates()
        .sort_values(["mro_code","current_registration"])
    )
    access.to_csv(out/"aircraft_mro_access.csv", index=False)

    # Summary for operator convenience
    total = aircraft.shape[0]
    lotams = access[access["mro_code"]=="lotams"].shape[0]
    lst = access[access["mro_code"]=="lst"].shape[0]
    unknown = access[~access["mro_code"].isin(["lotams","lst"])].shape[0]
    missing_msn = (aircraft["msn"]=="").sum()

    print("=== PGL Fleet export summary ===")
    print(f"aircraft_total_unique: {total}")
    print(f"aircraft_LOTAMS_unique: {lotams}")
    print(f"aircraft_LST_unique: {lst}")
    print(f"aircraft_unknown_MRO: {unknown}")
    print(f"aircraft_missing_MSN: {missing_msn}")

    if total != 929 or lotams != 316 or lst != 613 or unknown != 0:
        raise SystemExit("Dataset expectations not met; check XLSX contents / parsing.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
