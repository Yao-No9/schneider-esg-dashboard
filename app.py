from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
SCORES_PATH = DATA_DIR / "schneider_esg_scores_from_tables.csv"
METHOD_PATH = DATA_DIR / "provider_methodology_notes.csv"

PROVIDER_COLORS = {
    "MSCI": "#0072ce",
    "Sustainalytics": "#ff6b35",
    "CDP": "#3dcd58",
    "S&P CSA": "#6f3fd1",
}

SCHNEIDER_GREEN = "#3dcd58"
DEEP_GREEN = "#0b3d2e"
INK = "#111827"
MUTED = "#64748b"


st.set_page_config(
    page_title="Schneider ESG Score Divergence",
    page_icon="SE",
    layout="wide",
)


@st.cache_data
def load_scores(path: Path) -> pd.DataFrame:
    scores = pd.read_csv(path)
    scores["year"] = scores["year"].astype(int)
    scores["normalized_score"] = pd.to_numeric(scores["normalized_score"], errors="coerce")
    scores["confidence"] = pd.to_numeric(scores["confidence"], errors="coerce")
    return scores


@st.cache_data
def load_methodology(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def score_band(score: float) -> str:
    if score >= 80:
        return "High"
    if score >= 65:
        return "Medium-high"
    if score >= 50:
        return "Medium"
    return "Low"


def divergence_by_year(scores: pd.DataFrame) -> pd.DataFrame:
    grouped = scores.groupby("year")["normalized_score"]
    divergence = grouped.agg(["mean", "min", "max", "std"]).reset_index()
    divergence["spread"] = divergence["max"] - divergence["min"]
    divergence["std"] = divergence["std"].fillna(0)
    return divergence


def provider_profile(scores: pd.DataFrame) -> pd.DataFrame:
    latest_year = scores["year"].max()
    latest = scores[scores["year"] == latest_year].copy()
    previous = scores[scores["year"] == latest_year - 1][["provider", "normalized_score"]]
    previous = previous.rename(columns={"normalized_score": "previous_score"})
    latest = latest.merge(previous, on="provider", how="left")
    latest["yoy_change"] = latest["normalized_score"] - latest["previous_score"]
    latest["band"] = latest["normalized_score"].map(score_band)
    return latest.sort_values("normalized_score", ascending=False)


def provider_gap_table(scores: pd.DataFrame, methodology: pd.DataFrame, year: int) -> pd.DataFrame:
    year_scores = scores[scores["year"] == year].copy()
    year_scores = year_scores.merge(methodology, on="provider", how="left")
    year_scores["rank"] = year_scores["normalized_score"].rank(ascending=False, method="dense").astype(int)
    columns = [
        "rank",
        "provider",
        "raw_score",
        "normalized_score",
        "confidence",
        "key_lens",
        "methodology_gap",
        "data_gap",
        "weighting_difference",
    ]
    for optional_column in ["ranking", "keywords"]:
        if optional_column in year_scores.columns:
            columns.insert(5, optional_column)
    for source_column in ["interpretation_basis", "methodology_source", "methodology_url", "normalization_note"]:
        if source_column in year_scores.columns:
            columns.append(source_column)
    return year_scores[columns].sort_values(["rank", "provider"])


def normalization_notes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "provider": "S&P CSA",
                "source_scale": "0-100 CSA total score",
                "normalization": "Uses the reported numeric score directly; approximate values like ~87 are parsed as 87.",
                "direction": "Higher is stronger.",
            },
            {
                "provider": "Sustainalytics",
                "source_scale": "ESG Risk Score",
                "normalization": "Inverted as normalized_score = 100 - Risk Score because lower raw risk is better.",
                "direction": "Lower raw risk becomes higher normalized score.",
            },
            {
                "provider": "MSCI",
                "source_scale": "Letter rating from CCC to AAA",
                "normalization": "Mapped to a 0-100 scale: A=70, AA=85, AAA=95 in the current source table.",
                "direction": "Higher letter rating is stronger.",
            },
            {
                "provider": "CDP",
                "source_scale": "Environmental letter scores",
                "normalization": "Climate, Water, and Forest grades are mapped to numeric values, then averaged where available. Current mapping includes A=95, A-=88, B=75.",
                "direction": "Higher environmental grade is stronger.",
            },
        ]
    )


def metric_delta(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}"


scores = load_scores(SCORES_PATH)
methodology = load_methodology(METHOD_PATH)

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-mark">SE</div>
            <div>
                <div class="brand-name">Schneider Electric</div>
                <div class="brand-subtitle">ESG intelligence console</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Upload provider score CSV",
        type=["csv"],
        help="Use the same columns as data/schneider_esg_scores_from_tables.csv.",
    )
    if uploaded is not None:
        scores = pd.read_csv(uploaded)
        scores["year"] = scores["year"].astype(int)
        scores["normalized_score"] = pd.to_numeric(scores["normalized_score"], errors="coerce")
        scores["confidence"] = pd.to_numeric(scores["confidence"], errors="coerce")

    companies = sorted(scores["company"].unique())
    selected_company = st.selectbox("Company", companies, index=0)

    company_scores = scores[scores["company"] == selected_company].copy()
    providers = sorted(company_scores["provider"].unique())
    selected_providers = st.multiselect("Providers", providers, default=providers)
    selected_year = st.slider(
        "Comparison year",
        min_value=int(company_scores["year"].min()),
        max_value=int(company_scores["year"].max()),
        value=int(company_scores["year"].max()),
        step=1,
    )

company_scores = company_scores[company_scores["provider"].isin(selected_providers)]

st.markdown(
    """
    <style>
    :root {
        --se-green: #3dcd58;
        --se-green-dark: #0b3d2e;
        --se-mint: #e9f9ed;
        --se-ink: #111827;
        --se-muted: #64748b;
        --se-line: #dbe7df;
        --se-panel: #fbfefc;
    }
    .stApp {
        background:
            linear-gradient(135deg, rgba(61, 205, 88, 0.13), rgba(255,255,255,0) 32rem),
            linear-gradient(180deg, #f8fbf8 0%, #ffffff 36rem);
    }
    .block-container {
        padding-top: 1rem;
        max-width: 1380px;
    }
    section[data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, #0b3d2e 0%, #102b25 100%);
    }
    section[data-testid="stSidebar"] * {
        color: #f8fff9;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stSlider p {
        color: #d8f7dd !important;
        font-weight: 650;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] div,
    section[data-testid="stSidebar"] [data-baseweb="tag"] {
        color: #111827;
    }
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 7px 0 18px;
        border-bottom: 1px solid rgba(216, 247, 221, 0.22);
        margin-bottom: 18px;
    }
    .brand-mark {
        width: 42px;
        height: 42px;
        border-radius: 7px;
        display: grid;
        place-items: center;
        background: var(--se-green);
        color: #06351f !important;
        font-weight: 900;
        letter-spacing: 0;
        box-shadow: 0 8px 24px rgba(61, 205, 88, 0.25);
    }
    .brand-name {
        font-size: 1rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .brand-subtitle {
        color: #bff2c8 !important;
        font-size: 0.78rem;
        margin-top: 4px;
    }
    .se-hero {
        position: relative;
        overflow: hidden;
        border: 1px solid var(--se-line);
        border-radius: 8px;
        padding: 28px 30px;
        margin-bottom: 18px;
        color: #ffffff;
        background:
            linear-gradient(120deg, rgba(8, 53, 37, 0.98), rgba(14, 94, 57, 0.92)),
            repeating-linear-gradient(90deg, rgba(255,255,255,0.08) 0 1px, transparent 1px 44px),
            repeating-linear-gradient(0deg, rgba(255,255,255,0.06) 0 1px, transparent 1px 44px);
    }
    .se-hero:after {
        content: "";
        position: absolute;
        right: 28px;
        top: 24px;
        width: 31%;
        height: 68%;
        border: 1px solid rgba(156, 255, 176, 0.36);
        border-left: 5px solid var(--se-green);
        transform: skewX(-13deg);
        opacity: 0.85;
    }
    .se-eyebrow {
        color: #bff2c8;
        font-size: 0.82rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 9px;
    }
    .se-hero h1 {
        margin: 0;
        color: #ffffff;
        font-size: clamp(2rem, 4vw, 3.55rem);
        line-height: 1.02;
        letter-spacing: 0;
    }
    .se-hero p {
        max-width: 760px;
        color: #edfdf0;
        margin: 12px 0 0;
        font-size: 1.02rem;
    }
    .se-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 20px;
    }
    .se-chip {
        border: 1px solid rgba(216, 247, 221, 0.36);
        border-radius: 999px;
        padding: 6px 10px;
        background: rgba(255,255,255,0.08);
        color: #f8fff9;
        font-size: 0.82rem;
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        border: 1px solid var(--se-line);
        border-radius: 8px;
        padding: 16px 17px;
        background: linear-gradient(180deg, #ffffff, var(--se-panel));
        border-top: 4px solid var(--se-green);
        box-shadow: 0 10px 28px rgba(11, 61, 46, 0.07);
        min-height: 118px;
    }
    div[data-testid="stMetric"] label {
        color: var(--se-muted) !important;
        font-weight: 750;
    }
    div[data-testid="stMetricValue"] {
        color: var(--se-ink);
        font-weight: 850;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1px solid var(--se-line);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px 7px 0 0;
        padding: 10px 14px;
        font-weight: 750;
    }
    .stTabs [aria-selected="true"] {
        background: var(--se-mint);
        color: var(--se-green-dark);
        border-bottom: 3px solid var(--se-green);
    }
    .se-section-label {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        color: var(--se-green-dark);
        font-weight: 850;
        margin-bottom: 6px;
    }
    .se-section-label:before {
        content: "";
        width: 9px;
        height: 9px;
        border-radius: 2px;
        background: var(--se-green);
    }
    .provider-card {
        border: 1px solid var(--se-line);
        border-radius: 8px;
        padding: 13px 14px;
        margin-bottom: 10px;
        background: #ffffff;
        box-shadow: 0 8px 22px rgba(11, 61, 46, 0.05);
    }
    .provider-topline {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    .provider-name {
        font-weight: 850;
        color: var(--se-ink);
    }
    .provider-score {
        font-size: 1.45rem;
        font-weight: 900;
        color: var(--se-green-dark);
    }
    .provider-bar {
        height: 9px;
        border-radius: 999px;
        background: #e5f5e9;
        overflow: hidden;
    }
    .provider-fill {
        height: 100%;
        border-radius: 999px;
    }
    .provider-meta {
        display: flex;
        justify-content: space-between;
        color: var(--se-muted);
        font-size: 0.82rem;
        margin-top: 7px;
    }
    .driver-panel {
        border: 1px solid var(--se-line);
        border-radius: 8px;
        padding: 16px;
        min-height: 170px;
        background: linear-gradient(180deg, #ffffff, #f7fff8);
    }
    .driver-panel h3 {
        margin: 0 0 8px;
        font-size: 1rem;
        color: var(--se-green-dark);
    }
    .driver-panel p {
        margin: 0;
        color: #334155;
    }
    .small-note {color: #5f6b7a; font-size: 0.9rem;}
    h2, h3 {
        color: var(--se-green-dark);
        letter-spacing: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="se-hero">
        <div class="se-eyebrow">Energy management | ESG rating divergence</div>
        <h1>Schneider Electric ESG Signal Console</h1>
        <p>Compare provider ratings through an electrification and sustainability lens: where scores align, where they split, and which methodology assumptions drive the gap.</p>
        <div class="se-chip-row">
            <span class="se-chip">MSCI</span>
            <span class="se-chip">Sustainalytics</span>
            <span class="se-chip">CDP</span>
            <span class="se-chip">S&P CSA</span>
            <span class="se-chip">0-100 normalized scale</span>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

if company_scores.empty:
    st.warning("No data available for the selected provider set.")
    st.stop()

latest_profile = provider_profile(company_scores)
divergence = divergence_by_year(company_scores)
latest_divergence = divergence[divergence["year"] == selected_year].iloc[0]

metric_cols = st.columns(4)
metric_cols[0].metric("Average normalized score", f"{latest_divergence['mean']:.1f}")
metric_cols[1].metric("Provider spread", f"{latest_divergence['spread']:.1f} pts")
metric_cols[2].metric("Highest score", f"{latest_divergence['max']:.1f}")
metric_cols[3].metric("Lowest score", f"{latest_divergence['min']:.1f}")

tab_scores, tab_drivers, tab_time, tab_data = st.tabs(
    ["Provider Scores", "Why Scores Differ", "Score History", "Data Notes"]
)

with tab_scores:
    left, right = st.columns([1.25, 1])

    year_scores = company_scores[company_scores["year"] == selected_year].copy()
    year_scores = year_scores.sort_values("normalized_score", ascending=True)
    year_scores["color"] = year_scores["provider"].map(PROVIDER_COLORS)

    with left:
        st.markdown(f'<div class="se-section-label">{selected_year} normalized score comparison</div>', unsafe_allow_html=True)
        score_chart = (
            alt.Chart(year_scores)
            .mark_bar(cornerRadiusEnd=5)
            .encode(
                x=alt.X("normalized_score:Q", title="Normalized score", scale=alt.Scale(domain=[0, 100])),
                y=alt.Y("provider:N", title=None, sort="-x"),
                color=alt.Color(
                    "provider:N",
                    scale=alt.Scale(domain=list(PROVIDER_COLORS), range=list(PROVIDER_COLORS.values())),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("provider:N", title="Provider"),
                    alt.Tooltip("raw_score:N", title="Raw score"),
                    alt.Tooltip("normalized_score:Q", title="Normalized", format=".1f"),
                    alt.Tooltip("confidence:Q", title="Confidence", format=".0f"),
                ],
            )
            .properties(height=380)
        )
        target_rule = (
            alt.Chart(pd.DataFrame({"target": [90]}))
            .mark_rule(color=SCHNEIDER_GREEN, strokeDash=[6, 4], size=2)
            .encode(x="target:Q")
        )
        st.altair_chart(score_chart + target_rule, width="stretch")
        st.caption("Normalized score uses 100 as stronger ESG performance or lower ESG risk.")

    with right:
        st.markdown('<div class="se-section-label">Latest provider readout</div>', unsafe_allow_html=True)
        for row in latest_profile.itertuples(index=False):
            color = PROVIDER_COLORS.get(row.provider, SCHNEIDER_GREEN)
            st.markdown(
                f"""
                <div class="provider-card">
                    <div class="provider-topline">
                        <div class="provider-name">{row.provider}</div>
                        <div class="provider-score">{row.normalized_score:.1f}</div>
                    </div>
                    <div class="provider-bar">
                        <div class="provider-fill" style="width:{row.normalized_score:.1f}%; background:{color};"></div>
                    </div>
                    <div class="provider-meta">
                        <span>Raw: {row.raw_score}</span>
                        <span>YoY {metric_delta(row.yoy_change)} | Confidence {row.confidence:.0f}%</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.dataframe(
        provider_gap_table(company_scores, methodology, selected_year),
        width="stretch",
        hide_index=True,
        column_config={
            "normalized_score": st.column_config.NumberColumn("Normalized", format="%.1f"),
            "confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%d%%"),
        },
    )

with tab_drivers:
    st.markdown('<div class="se-section-label">Main reasons provider scores diverge</div>', unsafe_allow_html=True)
    gap_table = provider_gap_table(company_scores, methodology, selected_year)

    driver_cols = st.columns(3)
    driver_cols[0].markdown(
        '<div class="driver-panel"><h3>Methodology gaps</h3><p>Providers do not evaluate the same question. Some emphasize unmanaged financial risk, while others reward disclosure breadth or operational performance.</p></div>',
        unsafe_allow_html=True,
    )
    driver_cols[1].markdown(
        '<div class="driver-panel"><h3>Data gaps</h3><p>Coverage depends on public filings, questionnaire response depth, estimation models, controversies, and reporting boundaries.</p></div>',
        unsafe_allow_html=True,
    )
    driver_cols[2].markdown(
        '<div class="driver-panel"><h3>Weighting differences</h3><p>Climate, supply chain, governance, product exposure, and industry materiality are weighted differently across providers.</p></div>',
        unsafe_allow_html=True,
    )

    st.divider()
    for row in gap_table.itertuples(index=False):
        with st.expander(f"{row.provider}: rank {row.rank}, normalized score {row.normalized_score:.1f}"):
            source_name = getattr(row, "methodology_source", None)
            source_url = getattr(row, "methodology_url", None)
            basis = getattr(row, "interpretation_basis", "Analyst interpretation based on public methodology")
            st.caption(basis)
            if source_name and source_url:
                st.markdown(f"**Source:** [{source_name}]({source_url})")
            st.write(f"**Methodology gap:** {row.methodology_gap}")
            st.write(f"**Data gap:** {row.data_gap}")
            st.write(f"**Weighting difference:** {row.weighting_difference}")
            st.write(f"**Provider lens:** {row.key_lens}")

with tab_time:
    st.markdown('<div class="se-section-label">Scores over time</div>', unsafe_allow_html=True)
    history = company_scores.pivot_table(
        index="year",
        columns="provider",
        values="normalized_score",
        aggfunc="mean",
    ).sort_index()
    history_long = company_scores[["year", "provider", "normalized_score"]].copy()
    history_chart = (
        alt.Chart(history_long)
        .mark_line(point=alt.OverlayMarkDef(size=70), strokeWidth=3)
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("normalized_score:Q", title="Normalized score", scale=alt.Scale(domain=[70, 100])),
            color=alt.Color(
                "provider:N",
                scale=alt.Scale(domain=list(PROVIDER_COLORS), range=list(PROVIDER_COLORS.values())),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("year:O", title="Year"),
                alt.Tooltip("provider:N", title="Provider"),
                alt.Tooltip("normalized_score:Q", title="Score", format=".1f"),
            ],
        )
        .properties(height=420)
    )
    st.altair_chart(history_chart, width="stretch")

    spread_history = divergence.set_index("year")[["spread", "std"]]
    st.markdown('<div class="se-section-label">Divergence trend</div>', unsafe_allow_html=True)
    st.area_chart(spread_history, height=260)

with tab_data:
    st.subheader("Data model")
    st.write(
        "The dashboard is using the converted Schneider ESG tables from csv_exports. Provider-native scales are normalized to 0-100 so the four scoring systems can be compared on one view."
    )
    st.dataframe(company_scores.sort_values(["year", "provider"]), width="stretch", hide_index=True)

    st.subheader("Provider methodology reference")
    st.dataframe(methodology, width="stretch", hide_index=True)

    st.subheader("Normalization methodology")
    st.write(
        "All providers are converted to `normalized_score` on a 0-100 scale, where 100 means stronger ESG performance or lower ESG risk. Methodology/data/weighting explanations are analyst interpretation based on public methodology, with provider source links retained in the data."
    )
    st.dataframe(normalization_notes(), width="stretch", hide_index=True)

    st.download_button(
        "Download filtered scores",
        data=company_scores.to_csv(index=False).encode("utf-8"),
        file_name="filtered_esg_scores.csv",
        mime="text/csv",
    )
