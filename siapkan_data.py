"""Audit and prepare the inputs for Paper 4. This script does not estimate effects."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


TREATED = {
    "BRPT": "standard_exit",
    "BRMS": "standard_to_small_cap",
    "AVIA": "small_cap_exit",
    "CTRA": "small_cap_exit",
    "EMTK": "small_cap_exit",
    "JSMR": "small_cap_exit",
    "MTEL": "small_cap_exit",
    "RAJA": "small_cap_exit",
    "WIFI": "small_cap_exit",
}
ESTIMATION_START = "2026-04-17"
ESTIMATION_END = "2026-10-14"
PRE_REVIEW = "2026-11-11"
ANNOUNCEMENT = "2026-11-12"
IMPLEMENTATION = "2026-11-30"
MAIN_FOLLOWUP_END = "2026-12-01"
DATA_TARGET_END = "2026-12-14"
SOURCE_COLUMNS = {
    "Tanggal": "date", "Kode Saham": "ticker", "File Sumber": "source_file",
    "Remarks": "remarks", "Sebelumnya": "reference_price",
    "Penutupan": "close", "Open Price": "open_raw", "First Trade": "first_trade_raw",
    "Volume": "volume", "Non Regular Volume": "non_regular_volume",
    "Listed Shares": "listed_shares", "Foreign Buy": "foreign_buy",
    "Foreign Sell": "foreign_sell",
}
FEATURES = ["log_cap", "log_turnover_bp"]
MATCH_COLUMNS = [
    "treated_ticker", "change_type", "control_ticker", "rank",
    "match_level", "distance", "gap_log_cap_sd", "gap_log_turnover_sd",
    "treated_idx_ic", "control_idx_ic",
]


def load_stock_panel(path: Path) -> pd.DataFrame:
    panel = pd.read_excel(
        path, sheet_name="Data", usecols=list(SOURCE_COLUMNS),
        dtype={"Kode Saham": "string", "Remarks": "string", "File Sumber": "string"},
    ).rename(columns=SOURCE_COLUMNS)
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    panel["ticker"] = panel["ticker"].str.strip().str.upper()
    if panel[["date", "ticker"]].isna().any().any() or panel["ticker"].eq("").any():
        raise ValueError("Missing date or ticker.")
    if panel.duplicated(["date", "ticker"]).any():
        raise ValueError("Duplicate date and ticker.")
    source_date = panel["source_file"].str.extract(r"-(\d{8})\.xlsx$", expand=False)
    if not source_date.eq(panel["date"].dt.strftime("%Y%m%d")).fillna(False).all():
        raise ValueError("Date does not agree with source filename.")
    numeric_columns = list(SOURCE_COLUMNS.values())[4:]
    panel[numeric_columns] = panel[numeric_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(panel[numeric_columns].to_numpy(dtype=float)).all():
        raise ValueError("Missing or non-finite values in numeric input.")
    nonnegative = ["volume", "listed_shares", "foreign_buy", "foreign_sell"]
    if panel[nonnegative].lt(0).any().any():
        raise ValueError("Negative share counts in the source.")

    panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)
    industry_code = panel["remarks"].str.slice(14, 18)
    panel["idx_ic"] = industry_code.where(
        industry_code.str.fullmatch(r"[A-K][0-9]{3}", na=False)
    )
    panel["sector"] = panel["idx_ic"].str[0]
    panel["industry"] = panel["idx_ic"].str[:3]
    panel["return_price"] = (
        panel["close"].where(panel["close"].gt(0))
        / panel["reference_price"].where(panel["reference_price"].gt(0)) - 1
    )
    panel["open_valid"] = panel["open_raw"].where(panel["open_raw"].gt(0))
    positive_shares = panel["listed_shares"].where(panel["listed_shares"].gt(0))
    panel["market_cap_proxy"] = panel["close"].where(panel["close"].gt(0)) * positive_shares
    panel["turnover"] = panel["volume"] / positive_shares
    panel["net_foreign_shares"] = panel["foreign_buy"] - panel["foreign_sell"]
    panel["net_foreign_scaled"] = panel["net_foreign_shares"] / positive_shares
    lag = panel.groupby("ticker", sort=False)["close"].shift()
    panel["reference_differs_from_lag_close"] = lag.notna() & lag.ne(panel["reference_price"])
    return panel


def load_ihsg(path: Path) -> pd.DataFrame:
    market = pd.read_csv(path, dtype={"date": "string"})
    market["date"] = pd.to_datetime(market["date"], format="%Y-%m-%d", errors="raise")
    market["ihsg_close"] = pd.to_numeric(market["ihsg_close"], errors="raise")
    if market["date"].isna().any() or market["date"].duplicated().any():
        raise ValueError("Missing or duplicate IHSG dates.")
    if not np.isfinite(market["ihsg_close"]).all() or not market["ihsg_close"].gt(0).all():
        raise ValueError("IHSG closes must be positive and finite.")
    return market.sort_values("date").reset_index(drop=True)


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    history = panel.loc[panel["date"].between(ESTIMATION_START, ESTIMATION_END)].copy()
    history["traded"] = history["volume"].gt(0)
    features = history.groupby("ticker").agg(
        history_days=("date", "size"),
        trading_fraction=("traded", "mean"),
        median_cap=("market_cap_proxy", "median"),
        median_turnover=("turnover", "median"),
    )
    snapshot = panel.loc[panel["date"].eq(PRE_REVIEW), ["ticker", "idx_ic", "sector", "industry"]]
    features = snapshot.merge(features, on="ticker", how="left", validate="one_to_one")
    features["change_type"] = features["ticker"].map(TREATED)
    features["eligible"] = (
        features["history_days"].ge(108) & features["trading_fraction"].ge(0.80)
        & features["median_cap"].gt(0) & features["median_turnover"].notna()
        & features["sector"].notna() & features["ticker"].ne("GOTOM")
    )
    features["log_cap"] = np.log(features["median_cap"].where(features["median_cap"].gt(0)))
    features["log_turnover_bp"] = np.log1p(10_000 * features["median_turnover"])
    return features


def candidate_matches(features: pd.DataFrame, exclusions: set[str]) -> pd.DataFrame:
    eligible = features.loc[features["eligible"]].copy()
    controls = eligible.loc[~eligible["ticker"].isin(set(TREATED) | exclusions)]
    matches = []
    for ticker, change_type in TREATED.items():
        target = eligible.loc[eligible["ticker"].eq(ticker)]
        if target.empty:
            continue
        target = target.iloc[0]
        pool = controls.loc[controls["sector"].eq(target["sector"])].copy()
        scale = pool[FEATURES].std(ddof=0)
        if pool.empty or scale.isna().any() or scale.eq(0).any():
            continue
        gaps = (pool[FEATURES] - target[FEATURES].astype(float)).div(scale).abs()
        pool["distance"] = np.sqrt(gaps.pow(2).sum(axis=1))
        pool["gap_log_cap_sd"] = gaps["log_cap"]
        pool["gap_log_turnover_sd"] = gaps["log_turnover_bp"]
        pool["tier"] = pool["industry"].ne(target["industry"]).astype(int)
        within_caliper = gaps.le(1.5).all(axis=1)
        pool = pool.loc[within_caliper].sort_values(["tier", "distance", "ticker"]).head(3)
        for rank, (_, control) in enumerate(pool.iterrows(), start=1):
            matches.append({
                "treated_ticker": ticker, "change_type": change_type,
                "control_ticker": control["ticker"], "rank": rank,
                "match_level": "industry" if control["tier"] == 0 else "sector",
                "distance": control["distance"], "gap_log_cap_sd": control["gap_log_cap_sd"],
                "gap_log_turnover_sd": control["gap_log_turnover_sd"],
                "treated_idx_ic": target["idx_ic"], "control_idx_ic": control["idx_ic"],
            })
    return pd.DataFrame(matches, columns=MATCH_COLUMNS)


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stocks", required=True, type=Path)
    parser.add_argument("--ihsg", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--control-exclusions", type=Path, help="CSV with a ticker column")
    parser.add_argument("--export-panel", action="store_true", help="Write the prepared full panel")
    args = parser.parse_args()
    panel = load_stock_panel(args.stocks)
    market = load_ihsg(args.ihsg)
    stock_dates = pd.DatetimeIndex(panel["date"].unique()).sort_values()
    # Reindex to the stock calendar before taking returns so missing benchmark dates
    # cannot create multi-day returns on the next available observation.
    calendar = pd.DataFrame({"date": stock_dates}).merge(market, on="date", how="left")
    calendar["ihsg_return"] = calendar["ihsg_close"].pct_change(fill_method=None)
    panel = panel.merge(
        calendar[["date", "ihsg_close", "ihsg_return"]], on="date", how="left",
        validate="many_to_one",
    )
    features = build_features(panel)
    exclusions = set()
    if args.control_exclusions:
        exclusion_table = pd.read_csv(args.control_exclusions, dtype={"ticker": "string"})
        exclusions = set(exclusion_table["ticker"].dropna().str.strip().str.upper())
    matches = candidate_matches(features, exclusions)

    coverage = (
        panel.loc[panel["ticker"].isin(TREATED)]
        .groupby("ticker").agg(days=("date", "size"), positive_volume_days=("volume", lambda x: x.gt(0).sum()))
        .reindex(TREATED)
    )
    coverage["change_type"] = pd.Series(TREATED)
    coverage["eligible_for_matching"] = features.set_index("ticker")["eligible"].reindex(TREATED)
    coverage["candidate_controls"] = matches.groupby("treated_ticker").size().reindex(TREATED, fill_value=0)
    coverage.index.name = "ticker"
    corporate_action_flags = panel.loc[
        panel["reference_differs_from_lag_close"],
        ["date", "ticker", "reference_price", "close", "source_file"],
    ]
    historical_count = int(calendar["date"].between(ESTIMATION_START, ESTIMATION_END).sum())
    missing_benchmark = calendar.loc[calendar["ihsg_close"].isna(), "date"]
    audit = {
        "stock_workbook": args.stocks.name, "stock_sha256": file_hash(args.stocks),
        "ihsg_file": args.ihsg.name, "ihsg_sha256": file_hash(args.ihsg),
        "rows": len(panel), "tickers": int(panel["ticker"].nunique()), "sessions": len(stock_dates),
        "first_date": stock_dates.min().date().isoformat(), "last_date": stock_dates.max().date().isoformat(),
        "unique_date_ticker_verified": True, "source_filename_date_verified": True,
        "estimation_sessions": historical_count,
        "zero_volume_rows": int(panel["volume"].eq(0).sum()),
        "positive_volume_zero_open_rows": int((panel["volume"].gt(0) & panel["open_raw"].eq(0)).sum()),
        "volume_below_non_regular_rows": int(panel["volume"].lt(panel["non_regular_volume"]).sum()),
        "missing_idx_ic_rows": int(panel["idx_ic"].isna().sum()),
        "reference_price_flags": len(corporate_action_flags),
        "missing_ihsg_dates": missing_benchmark.dt.strftime("%Y-%m-%d").tolist(),
        "eligible_stocks_as_of_2026_11_11": int(features["eligible"].sum()),
        "candidate_links": len(matches), "unique_candidate_controls": int(matches["control_ticker"].nunique()),
        "affected_with_three_candidate_controls": int(coverage["candidate_controls"].eq(3).sum()),
        "affected_with_any_candidate_controls": int(coverage["candidate_controls"].gt(0).sum()),
        "additional_control_exclusions_applied": bool(args.control_exclusions),
        "announcement_in_data": bool(pd.Timestamp(ANNOUNCEMENT) in stock_dates),
        "implementation_in_data": bool(pd.Timestamp(IMPLEMENTATION) in stock_dates),
        "implementation_followup_in_data": bool(pd.Timestamp(MAIN_FOLLOWUP_END) in stock_dates),
        "target_end_in_data": bool(pd.Timestamp(DATA_TARGET_END) in stock_dates),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    coverage.to_csv(args.out / "cakupan_saham_terdampak.csv")
    matches.to_csv(args.out / "calon_pembanding.csv", index=False, float_format="%.6f")
    corporate_action_flags.to_csv(args.out / "flag_harga_referensi.csv", index=False)
    if args.export_panel:
        panel.to_csv(args.out / "panel_siap.csv", index=False)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
