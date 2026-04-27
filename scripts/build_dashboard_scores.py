from pathlib import Path

import pandas as pd


BASE = Path("csv_exports")
OUT = Path("data/schneider_esg_scores_from_tables.csv")
COMPANY = "Schneider Electric"

SOURCES = {
    "MSCI": {
        "methodology_source": "MSCI ESG Ratings Methodology",
        "methodology_url": "https://www.msci.com/downloads/documents/access/sustainability-and-climate-resources-and-disclosures/msci-sustainability-and-climate-methodologies/esg-ratings/core-methodologies/esg-ratings-methodology.pdf",
        "normalization_note": "Letter rating mapped to 0-100 scale: A=70, AA=85, AAA=95 in the current source table.",
    },
    "Sustainalytics": {
        "methodology_source": "Morningstar Sustainalytics ESG Risk Ratings Methodology",
        "methodology_url": "https://connect.sustainalytics.com/esg-risk-ratings-methodology",
        "normalization_note": "ESG Risk Score is inverted as normalized_score = 100 - Risk Score because lower raw risk is better.",
    },
    "CDP": {
        "methodology_source": "CDP Corporate Scoring Methodology / Understand your score",
        "methodology_url": "https://help.cdp.net/en-US/knowledgebase/article/KA-01160",
        "normalization_note": "Climate, Water, and Forest letter grades are mapped to numeric values, then averaged where available.",
    },
    "S&P CSA": {
        "methodology_source": "S&P Global CSA Methodology",
        "methodology_url": "https://www.spglobal.com/esg/csa/csa-resources/csa-methodology",
        "normalization_note": "Reported CSA total score is used directly; approximate values like ~87 are parsed as 87.",
    },
}


def parse_score(value):
    if pd.isna(value):
        return None
    text = str(value).strip().replace("~", "")
    try:
        return float(text)
    except ValueError:
        return None


def msci_rating_score(value):
    mapping = {"CCC": 15, "B": 25, "BB": 40, "BBB": 55, "A": 70, "AA": 85, "AAA": 95}
    return mapping.get(str(value).strip())


def grade_score(value):
    if pd.isna(value):
        return None
    mapping = {"A": 95, "A-": 88, "B": 75, "B-": 68, "C": 55, "C-": 48, "D": 35, "D-": 25}
    parts = [part.strip() for part in str(value).split("/")]
    values = [mapping[part] for part in parts if part in mapping]
    return sum(values) / len(values) if values else None


def qualitative_score(value):
    if pd.isna(value):
        return None
    mapping = {"Leader": 95, "High": 82, "Medium": 62, "Low": 40}
    return mapping.get(str(value).strip())


def clean_label(value):
    return "" if pd.isna(value) else str(value)


def base_row(year, provider, raw_score, normalized_score, e, s, g, confidence, ranking, keywords):
    source = SOURCES[provider]
    return {
        "company": COMPANY,
        "year": int(year),
        "provider": provider,
        "raw_score": raw_score,
        "normalized_score": normalized_score,
        "environment_score": e,
        "social_score": s,
        "governance_score": g,
        "confidence": confidence,
        "ranking": ranking,
        "keywords": keywords,
        "interpretation_basis": "Analyst interpretation based on public methodology",
        "methodology_source": source["methodology_source"],
        "methodology_url": source["methodology_url"],
        "normalization_note": source["normalization_note"],
    }


def build_rows():
    rows = []

    sp = pd.read_csv(BASE / "Schneider_ESG_full_tables_S_P_CSA.csv")
    for _, row in sp.iterrows():
        item = base_row(
            row["Year"],
            "S&P CSA",
            row["Total"],
            parse_score(row["Total"]),
            parse_score(row.get("E")),
            parse_score(row.get("S")),
            parse_score(row.get("G")),
            88 if pd.notna(row.get("Ranking")) else 75,
            row.get("Ranking"),
            row.get("Keywords"),
        )
        item.update(
            {
                "methodology_gap": "CSA uses a questionnaire-led sector assessment, so detailed evidence and response coverage can move scores differently than public-data providers.",
                "data_gap": "Earlier years may have incomplete E/S/G pillars; ranking and keywords are retained from the source table.",
                "weighting_difference": "Sector materiality spreads weight across climate, energy efficiency, human capital, innovation, and governance.",
            }
        )
        rows.append(item)

    sustainalytics = pd.read_csv(BASE / "Schneider_ESG_full_tables_Sustainalytics.csv")
    for _, row in sustainalytics.iterrows():
        risk = parse_score(row["Risk Score"])
        item = base_row(
            row["Year"],
            "Sustainalytics",
            row["Risk Score"],
            100 - risk if risk is not None else None,
            100 - parse_score(row.get("E")) if parse_score(row.get("E")) is not None else None,
            100 - parse_score(row.get("S")) if parse_score(row.get("S")) is not None else None,
            100 - parse_score(row.get("G")) if parse_score(row.get("G")) is not None else None,
            85,
            row.get("Ranking"),
            row.get("Keywords"),
        )
        item.update(
            {
                "methodology_gap": "Sustainalytics is risk-oriented: lower raw ESG Risk Score is better, so it is inverted for 0-100 comparison.",
                "data_gap": "Risk components reflect exposure and unmanaged risk, not the same evidence base as questionnaire or disclosure scores.",
                "weighting_difference": "Unmanaged financially material risk carries more weight than broad disclosure volume.",
            }
        )
        rows.append(item)

    msci = pd.read_csv(BASE / "Schneider_ESG_full_tables_MSCI.csv")
    for _, row in msci.iterrows():
        item = base_row(
            row["Year"],
            "MSCI",
            row["Rating"],
            msci_rating_score(row["Rating"]),
            qualitative_score(row.get("E")),
            qualitative_score(row.get("S")),
            qualitative_score(row.get("G")),
            82 if pd.notna(row.get("Ranking")) else 72,
            row.get("Ranking"),
            row.get("Keywords"),
        )
        item.update(
            {
                "methodology_gap": "MSCI ratings are peer-relative letter grades; they are mapped to a normalized scale for dashboard comparison.",
                "data_gap": "Qualitative E/S/G labels are mapped to numeric values, so pillar scores are directional rather than raw provider points.",
                "weighting_difference": "Industry-relative financial materiality and controversy management can outweigh broad disclosure completeness.",
            }
        )
        rows.append(item)

    cdp = pd.read_csv(BASE / "Schneider_ESG_full_tables_CDP.csv")
    for _, row in cdp.iterrows():
        climate = grade_score(row.get("Climate"))
        water = grade_score(row.get("Water"))
        forest = grade_score(row.get("Forest"))
        values = [value for value in [climate, water, forest] if value is not None]
        item = base_row(
            row["Year"],
            "CDP",
            f"Climate {clean_label(row.get('Climate'))}; Water {clean_label(row.get('Water'))}; Forest {clean_label(row.get('Forest'))}",
            sum(values) / len(values) if values else None,
            climate,
            None,
            None,
            84 if pd.notna(row.get("Ranking")) else 74,
            row.get("Ranking"),
            row.get("Keywords"),
        )
        item.update(
            {
                "methodology_gap": "CDP is environment-disclosure focused, so its normalized score reflects climate, water, and forest grades rather than full ESG coverage.",
                "data_gap": "Social and governance pillars are not native CDP fields in the source table and are left blank.",
                "weighting_difference": "Environmental disclosure and transition performance dominate the aggregate.",
            }
        )
        rows.append(item)

    return rows


def main():
    columns = [
        "company",
        "year",
        "provider",
        "raw_score",
        "normalized_score",
        "environment_score",
        "social_score",
        "governance_score",
        "confidence",
        "ranking",
        "keywords",
        "interpretation_basis",
        "methodology_source",
        "methodology_url",
        "normalization_note",
        "methodology_gap",
        "data_gap",
        "weighting_difference",
    ]
    data = pd.DataFrame(build_rows())[columns].sort_values(["year", "provider"])
    OUT.parent.mkdir(exist_ok=True)
    data.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Wrote {OUT} with shape {data.shape}")


if __name__ == "__main__":
    main()
