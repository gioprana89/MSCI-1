"""Build the audit, event estimates, and synchronous historical placebos."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from siapkan_data import TREATED, build_features, file_hash, load_ihsg, load_stock_panel

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "inputs"
EVENT = "2026-11-12"
EVENT_DATES = ["2026-11-11", EVENT, "2026-11-13"]
OTHER_EVENTS = {"2026-05-13", "2026-05-29", "2026-06-24", "2026-08-13", "2026-08-31"}
METRICS = ["abnormal_return_pp", "abnormal_turnover_bp", "net_foreign_deviation_bp"]


def audit_controls(panel, features, source, candidates):
    retained = set(source["msci_retained_candidates"])
    hsc = source["hsc_candidates"] | source["hsc_affected"]
    group = {tuple(pair) for pair in source["same_group_pairs"]}
    event = panel.loc[panel["date"].isin(pd.to_datetime(EVENT_DATES))].copy()
    event["nontrading"] = event["volume"].eq(0)
    previous = panel.groupby("ticker", sort=False)["listed_shares"].shift()
    event["shares_changed"] = previous.loc[event.index].notna() & previous.loc[event.index].ne(event["listed_shares"])
    quality = event.groupby("ticker").agg(
        event_days=("date", "size"),
        zero_volume_days=("nontrading", "sum"),
        reference_change_days=("reference_differs_from_lag_close", "sum"),
        shares_change_days=("shares_changed", "sum"),
    )
    audit = []
    for ticker in sorted(set(candidates["control_ticker"]) | set(TREATED)):
        linked = candidates.loc[candidates["control_ticker"].eq(ticker), "treated_ticker"]
        linked = sorted(set(linked))
        q = quality.loc[ticker]
        audit.append({
            "ticker": ticker, "role": "affected" if ticker in TREATED else "candidate",
            "matched_to": " ".join(linked),
            "msci_nov_status": ("affected" if ticker in TREATED else
                                "reported_retained" if ticker in retained else
                                "not_in_reported_standard_small_cap_list"),
            "msci_weight_change": "unverified",
            "hsc_list_row": hsc.get(ticker, ""),
            "identified_group_links": " ".join(t for t in linked if (t, ticker) in group),
            "issuer_disclosure_check": "partial_public_source_screen",
            "issuer_event": source["issuer_events"].get(ticker, {}).get("note", ""),
            "issuer_event_source": source["issuer_events"].get(ticker, {}).get("url", ""),
            **q.to_dict(),
            "history_days": int(features.loc[ticker, "history_days"]),
            "history_positive_volume_fraction": features.loc[ticker, "trading_fraction"],
        })
    audit = pd.DataFrame(audit)
    link_audit = candidates.copy()
    flags = audit.set_index("ticker")
    reasons = []
    for row in link_audit.itertuples():
        t, c = row.treated_ticker, row.control_ticker
        q = flags.loc[c]
        notes = []
        if c in retained:
            notes.append("reported_retained")
        if c in hsc:
            notes.append("HSC")
        if (t, c) in group:
            notes.append("identified_group_link")
        if c in source["issuer_events"]:
            notes.append("documented_issuer_event")
        if q.event_days != 3 or q.zero_volume_days or q.reference_change_days or q.shares_change_days:
            notes.append("event_window_data_flag")
        reasons.append(" | ".join(notes))
    link_audit["screen_exclusion"] = reasons
    screened = (link_audit.loc[link_audit["screen_exclusion"].eq("")]
                .drop_duplicates(["treated_ticker", "control_ticker"])
                .groupby("treated_ticker", sort=False).head(3).copy())
    if set(screened["treated_ticker"]) != set(TREATED):
        raise ValueError("Screened matches do not cover every affected ticker.")
    screened["variant"] = "screened"
    screened["rank"] = screened.groupby("treated_ticker", sort=False).cumcount() + 1
    return audit, link_audit, screened


def estimate_responses(panel, market, tickers):
    sample = panel.loc[panel["ticker"].isin(tickers)]
    matrices = {column: sample.pivot(index="date", columns="ticker", values=column).sort_index()
                for column in ("return_price", "turnover", "net_foreign_scaled")}
    returns = matrices["return_price"]
    dates = returns.index
    market = market.set_index("date")["ihsg_close"].reindex(dates).pct_change(fill_method=None)
    hist = dates[(dates >= "2026-04-17") & (dates <= "2026-10-14")]
    if len(hist) != 120:
        raise ValueError("Expected 120 historical sessions.")
    out = []
    for i, evaluation in enumerate([*np.array_split(hist, 6), pd.to_datetime(EVENT_DATES)]):
        evaluation = pd.DatetimeIndex(evaluation)
        training = hist.difference(evaluation)
        fit_x = np.column_stack([np.ones(len(training)), market.loc[training]])
        y = returns.loc[training].to_numpy()
        eval_x = np.column_stack([np.ones(len(evaluation)), market.loc[evaluation]])
        if not np.isfinite(fit_x).all() or not np.isfinite(y).all() or not np.isfinite(eval_x).all():
            raise ValueError("Incomplete return history for selected controls.")
        coef = np.linalg.lstsq(fit_x, y, rcond=None)[0]
        values = [
            100 * (returns.loc[evaluation].to_numpy() - eval_x @ coef),
            10000 * (matrices["turnover"].loc[evaluation] - matrices["turnover"].loc[training].median()).to_numpy(),
            10000 * (matrices["net_foreign_scaled"].loc[evaluation] -
                     matrices["net_foreign_scaled"].loc[training].median()).to_numpy(),
        ]
        for name, result in zip(METRICS, values):
            if not np.isfinite(result).all():
                raise ValueError("Incomplete outcomes.")
            wide = pd.DataFrame(result, index=evaluation, columns=returns.columns)
            wide.index.name = "date"
            frame = wide.stack().rename("value").reset_index()
            frame["metric"] = name
            frame["period"] = "event" if i == 6 else "placebo"
            frame["training_days"] = len(training)
            out.append(frame)
    return pd.concat(out, ignore_index=True)


def matched_estimates(responses, matches, raw_returns):
    wide = responses.pivot(index=["date", "period", "metric", "training_days"], columns="ticker", values="value")
    entries = []
    balance = []
    for (variant, affected), links in matches.groupby(["variant", "treated_ticker"], sort=False):
        donors = links["control_ticker"].tolist()
        frame = (wide[affected] - wide[donors].mean(axis=1)).rename("estimate").reset_index()
        frame = frame.assign(variant=variant, ticker=affected, n_controls=len(donors), controls=" ".join(donors))
        entries.append(frame)
        historical = raw_returns.loc["2026-04-17":"2026-10-14"]
        target = historical[affected]
        comparison = historical[donors].mean(axis=1)
        gaps = 100 * (target - comparison)
        balance.append({
            "variant": variant, "ticker": affected, "controls": " ".join(donors),
            "n_controls": len(donors), "industry_matches": links["match_level"].eq("industry").sum(),
            "max_size_gap_sd": links["gap_log_cap_sd"].max(),
            "max_liquidity_gap_sd": links["gap_log_turnover_sd"].max(),
            "preperiod_return_correlation": target.corr(comparison),
            "preperiod_daily_return_gap_mean_pp": gaps.mean(),
            "preperiod_daily_return_gap_rmse_pp": np.sqrt(gaps.pow(2).mean()),
        })
    return pd.concat(entries, ignore_index=True), pd.DataFrame(balance)


def summarize(matched):
    base_cols = ["variant", "date", "period", "metric"]
    subsets = {"all_9": set(), "without_BRMS": {"BRMS"}, "without_MTEL": {"MTEL"},
               "without_RAJA_WIFI": {"RAJA", "WIFI"}}
    aggregate = []
    for name, exclusions in subsets.items():
        x = matched.loc[~matched["ticker"].isin(exclusions)]
        s = x.groupby(base_cols).agg(
            estimate=("estimate", "mean"), median=("estimate", "median"),
            n=("estimate", "size"), negative=("estimate", lambda x: x.lt(0).sum()),
        ).reset_index()
        aggregate.append(s.assign(sample=name))
    aggregate = pd.concat(aggregate, ignore_index=True)
    event = aggregate.loc[aggregate["period"].eq("event")].copy()
    historical = aggregate.loc[aggregate["period"].eq("placebo")].copy()
    ranks = []
    for e in event.loc[event["date"].eq(EVENT)].itertuples():
        hist = historical.loc[
            historical["variant"].eq(e.variant) & historical["sample"].eq(e.sample) &
            historical["metric"].eq(e.metric)
        ]
        for key, dist in [("all_dates", hist), ("omit_other_msci_dates", hist.loc[
            ~hist["date"].dt.strftime("%Y-%m-%d").isin(OTHER_EVENTS)
        ])]:
            values = dist["estimate"]
            count = int(values.abs().ge(abs(e.estimate) - 1e-12).sum())
            ranks.append({
                "variant": e.variant, "sample": e.sample, "metric": e.metric, "placebo_set": key,
                "estimate": e.estimate, "median": e.median, "negative": e.negative, "n": e.n,
                "n_placebo": len(values), "extreme_placebo": count, "tail_rank": (1 + count) / (1 + len(values)),
                "placebo_q025": values.quantile(.025), "placebo_q975": values.quantile(.975),
            })
    day0 = matched.loc[matched["date"].eq(EVENT)].copy()
    sums = day0.groupby(["variant", "metric"])["estimate"].transform("sum")
    loo = day0.assign(omitted_ticker=day0["ticker"], leave_one_out=(sums - day0["estimate"]) / 8)
    return event, historical, pd.DataFrame(ranks), loo[["variant", "metric", "omitted_ticker", "leave_one_out"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stocks", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    panel = load_stock_panel(args.stocks)
    market = load_ihsg(INPUT / "ihsg_20260401_20261113.csv")
    source = json.loads((INPUT / "audit_sources.json").read_text())
    candidates = pd.concat([
        pd.read_csv(INPUT / "calon_pembanding_awal.csv").assign(variant="initial"),
        pd.read_csv(INPUT / "calon_pembanding_sensitivitas.csv").assign(variant="exclude_may_aug"),
    ], ignore_index=True)
    features = build_features(panel).set_index("ticker")
    audit, links, screened = audit_controls(panel, features, source, candidates)
    matches = pd.concat([screened, links], ignore_index=True)
    tickers = set(matches["control_ticker"]) | set(TREATED)
    raw_returns = panel.loc[panel["ticker"].isin(tickers)].pivot(index="date", columns="ticker", values="return_price").sort_index()
    responses = estimate_responses(panel, market, tickers)
    matched, balance = matched_estimates(responses, matches, raw_returns)
    event, historical, ranks, loo = summarize(matched)
    args.out.mkdir(parents=True, exist_ok=True)
    files = {
        "audit_saham": audit, "audit_pasangan": links, "pasangan": matches, "keseimbangan": balance,
        "per_saham": matched.loc[matched["period"].eq("event")],
        "ringkasan_peristiwa": event, "placebo": historical, "peringkat_placebo": ranks, "leave_one_out": loo,
    }
    for name, frame in files.items():
        frame.to_csv(args.out / f"{name}.csv", index=False, float_format="%.10f")
    meta = {"stock_sha256": file_hash(args.stocks), "ihsg_sha256": file_hash(INPUT / "ihsg_20260401_20261113.csv"),
            "audit_sources_sha256": file_hash(INPUT / "audit_sources.json"),
            "event_date": EVENT, "sample_cutoff": panel["date"].max().strftime("%Y-%m-%d"), "n_rows": len(panel),
            "status": "post-pilot exploratory", "msci_controls_source": source["msci_source"], "hsc_source": source["hsc_source"]}
    (args.out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(ranks.query("sample == 'all_9' and placebo_set == 'all_dates'").to_string(index=False))


if __name__ == "__main__":
    main()
