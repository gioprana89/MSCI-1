"""Read-only dashboard for the November 2026 MSCI event study."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from visualisasi import FIGURES, LABELS, RESULTS

EVENT = "2026-11-12"
VARIANTS = {
    "screened": "Pembanding tersaring",
    "initial": "Pembanding awal",
    "exclude_may_aug": "Keluarkan perubahan Mei/Agustus",
}
SAMPLES = {
    "all_9": "Seluruh saham (9)",
    "without_BRMS": "Tanpa BRMS",
    "without_MTEL": "Tanpa MTEL",
    "without_RAJA_WIFI": "Tanpa RAJA dan WIFI",
}
OUTCOMES = {
    "abnormal_return_pp": "Return abnormal",
    "abnormal_turnover_bp": "Turnover abnormal",
    "net_foreign_deviation_bp": "Transaksi bersih asing",
}


@st.cache_data
def load_result(name, revision):
    return pd.read_csv(RESULTS / f"{name}.csv", keep_default_na=False)


def table(name):
    return load_result(name, (RESULTS / f"{name}.csv").stat().st_mtime_ns)


def chart(points, metric):
    fig, ax = plt.subplots(figsize=(8, 4.2), layout="constrained")
    points = points.sort_values("estimate")
    ax.barh(points["ticker"], points["estimate"], color="#21547B")
    ax.axvline(0, color="#687C90", lw=.9)
    ax.set_xlabel(LABELS[metric][1])
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=.20)
    ax.set_axisbelow(True)
    st.pyplot(fig)
    plt.close(fig)


def placebo_chart(history, summary):
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), layout="constrained")
    for ax, (metric, label) in zip(axes, OUTCOMES.items()):
        values = history.loc[history["metric"].eq(metric), "estimate"]
        actual = summary.loc[summary["metric"].eq(metric), "estimate"].iloc[0]
        ax.hist(values, bins=17, color="#5382A5", edgecolor="white")
        ax.axvline(actual, color="#A03035", lw=2)
        ax.set_title(label, fontsize=10)
        ax.set_xlabel(LABELS[metric][1], fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
    st.pyplot(fig)
    plt.close(fig)


def download(path: Path, label: str, mime: str):
    st.download_button(label, data=path.read_bytes(), file_name=path.name, mime=mime, key=path.name)


st.set_page_config(page_title="Paper 4 · MSCI Indonesia", page_icon="📊", layout="wide")
st.title("Reaksi saham terhadap pengumuman MSCI")
st.caption("BEI · 12 November 2026 · Data hingga 13 November · Analisis eksploratif pascapilot")
tab1, tab2, tab3, tab4 = st.tabs(["Ringkasan", "Hasil per Saham", "Uji Sensitivitas", "Metode & Unduhan"])
ranks = table("peringkat_placebo")
stocks = table("per_saham")
with tab1:
    key = ranks.query("variant == 'screened' and sample == 'all_9' and placebo_set == 'all_dates'").set_index("metric")
    columns = st.columns(3)
    for col, (metric, title) in zip(columns, OUTCOMES.items()):
        value = key.loc[metric, "estimate"]
        unit = "pp" if metric == "abnormal_return_pp" else "bp"
        col.metric(title, f"{value:+.2f} {unit}")
    st.caption("Rerata sembilan saham terhadap pembanding tersaring. pp adalah poin persentase. bp dihitung terhadap saham tercatat.")
    st.image(str(FIGURES / "Figure_3_Event_window.png"))
    st.info("Pengunduran diri Wapres pada 12 November dan perubahan IHSG terkait HSC pada 13 November membatasi atribusi.")
with tab2:
    variant = st.selectbox("Pembanding", list(VARIANTS), format_func=VARIANTS.get)
    metric = st.selectbox("Ukuran hasil", list(OUTCOMES), format_func=OUTCOMES.get)
    date = st.selectbox("Tanggal", ["2026-11-11", EVENT, "2026-11-13"], index=1)
    points = stocks.query("variant == @variant and metric == @metric and date == @date")
    chart(points, metric)
    st.dataframe(points[["ticker", "estimate", "n_controls", "controls"]], hide_index=True)
with tab3:
    sample = st.selectbox("Sampel", list(SAMPLES), format_func=SAMPLES.get)
    placebo = st.selectbox("Tanggal placebo", ["all_dates", "omit_other_msci_dates"],
                           format_func={"all_dates": "Seluruh tanggal", "omit_other_msci_dates": "Keluarkan lima tanggal MSCI lain"}.get)
    st.dataframe(ranks.query("sample == @sample and placebo_set == @placebo")[
        ["variant", "metric", "estimate", "median", "negative", "n", "extreme_placebo", "n_placebo", "tail_rank"]
    ], hide_index=True)
    st.caption("Tail rank adalah perbandingan historis eksploratif. Rentang placebo menggambarkan distribusi referensi.")
    st.markdown(f"**Distribusi placebo · {VARIANTS[variant]}**")
    history = table("placebo").query("sample == @sample and variant == @variant")
    if placebo == "omit_other_msci_dates":
        from analisis import OTHER_EVENTS

        history = history.loc[~history["date"].isin(OTHER_EVENTS)]
    placebo_chart(history, ranks.query("sample == @sample and variant == @variant and placebo_set == @placebo"))
    st.dataframe(table("leave_one_out"), hide_index=True)
with tab4:
    st.markdown("### Audit pembanding")
    st.dataframe(table("audit_saham"), hide_index=True)
    st.caption("Bobot MSCI dan kelengkapan keterbukaan emiten masih perlu diverifikasi.")
    st.markdown("### Kesetaraan sebelum peristiwa")
    st.dataframe(table("keseimbangan"), hide_index=True)
    st.markdown("### Unduhan")
    for name in ["audit_saham", "audit_pasangan", "per_saham", "peringkat_placebo", "placebo"]:
        download(RESULTS / f"{name}.csv", f"CSV · {name.replace('_', ' ')}", "text/csv")
    for path in sorted(FIGURES.glob("*.pdf")):
        download(path, f"PDF · {path.stem.replace('_', ' ')}", "application/pdf")
