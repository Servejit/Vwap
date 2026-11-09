import re
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="VWAP 5-Low Analyzer", page_icon="📊", layout="wide")

st.title("📊 VWAP 5-Low Analyzer")
st.caption(
    "Upload multiple NSE equity quote CSV files. For each stock, the dashboard "
    "finds the five lowest VWAP values, averages them, and compares the latest VWAP."
)

st.info(
    "**Calculation:** % Change = ((Latest VWAP − Average of 5 Lowest VWAPs) "
    "÷ Average of 5 Lowest VWAPs) × 100"
)

uploads = st.file_uploader(
    "Upload multiple NSE quote CSV files",
    type=["csv"],
    accept_multiple_files=True,
    help="Select several stock CSV files together. Each file is analyzed separately.",
)


def numeric_series(series):
    """Convert formatted values such as 1,234.50 or ₹1,234.50 to numbers."""
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.strip()
        .replace({"": None, "-": None, "nan": None, "None": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def find_column(columns, wanted):
    normalized = {str(col).strip().upper(): col for col in columns}
    return normalized.get(wanted.upper())


def symbol_from_filename(filename):
    match = re.search(r"Quote[-_]Equity[-_]([A-Za-z0-9&.-]+)", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return Path(filename).stem


def analyze_file(upload):
    raw = pd.read_csv(upload)
    raw.columns = [str(column).strip() for column in raw.columns]

    vwap_col = find_column(raw.columns, "VWAP")
    if vwap_col is None:
        raise ValueError("VWAP column was not found.")

    date_col = find_column(raw.columns, "DATE")
    if date_col:
        raw["_DATE_PARSED"] = pd.to_datetime(
            raw[date_col], dayfirst=True, errors="coerce"
        )
        raw = raw.sort_values(
            "_DATE_PARSED", ascending=False, na_position="last"
        )

    raw["_VWAP_NUMERIC"] = numeric_series(raw[vwap_col])
    valid = raw[raw["_VWAP_NUMERIC"].notna()].copy()

    if len(valid) < 5:
        raise ValueError(
            f"Only {len(valid)} valid VWAP values found; at least 5 are required."
        )

    lowest = valid.nsmallest(5, "_VWAP_NUMERIC")
    five_low_values = sorted(lowest["_VWAP_NUMERIC"].astype(float).tolist())
    average_lowest = sum(five_low_values) / 5

    # Latest VWAP is taken from the most recent date when a DATE column exists.
    latest_row = valid.iloc[0]
    latest_vwap = float(latest_row["_VWAP_NUMERIC"])

    if average_lowest == 0:
        raise ValueError(
            "The average of the five lowest VWAP values is zero; percentage cannot be calculated."
        )

    percent_change = ((latest_vwap - average_lowest) / average_lowest) * 100

    latest_date = ""
    if date_col:
        date_value = latest_row.get(date_col, "")
        latest_date = str(date_value) if pd.notna(date_value) else ""

    return {
        "Stock": symbol_from_filename(upload.name),
        "Latest Date": latest_date,
        "Latest VWAP": latest_vwap,
        "5 Lowest VWAP Average": average_lowest,
        "% Change from Average": percent_change,
        "5 Lowest VWAP Values": ", ".join(
            f"{value:.2f}" for value in five_low_values
        ),
    }


if uploads:
    results = []
    errors = []

    for upload in uploads:
        try:
            upload.seek(0)
            results.append(analyze_file(upload))
        except Exception as exc:
            errors.append((upload.name, str(exc)))

    if results:
        st.subheader("VWAP Analysis Results")

        # Uploaded filename is intentionally excluded. Five lowest values are last.
        output_columns = [
            "Stock",
            "Latest Date",
            "Latest VWAP",
            "5 Lowest VWAP Average",
            "% Change from Average",
            "5 Lowest VWAP Values",
        ]
        summary = pd.DataFrame(results)[output_columns]

        def color_change(value):
            if value > 0:
                return "color: #16a34a; font-weight: bold"
            if value < 0:
                return "color: #dc2626; font-weight: bold"
            return "font-weight: bold"

        formatted = summary.style.format(
            {
                "Latest VWAP": "{:.2f}",
                "5 Lowest VWAP Average": "{:.2f}",
                "% Change from Average": "{:+.2f}%",
            }
        ).map(color_change, subset=["% Change from Average"])

        st.dataframe(
            formatted,
            use_container_width=True,
            hide_index=True,
        )

        # Download uses the same column order and two-decimal formatting as the screen.
        download_df = summary.copy()
        download_df["Latest VWAP"] = download_df["Latest VWAP"].map(lambda x: f"{x:.2f}")
        download_df["5 Lowest VWAP Average"] = download_df[
            "5 Lowest VWAP Average"
        ].map(lambda x: f"{x:.2f}")
        download_df["% Change from Average"] = download_df[
            "% Change from Average"
        ].map(lambda x: f"{x:+.2f}%")

        csv_bytes = download_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Download VWAP results (CSV)",
            data=csv_bytes,
            file_name="vwap_5_low_analysis.csv",
            mime="text/csv",
        )

    if errors:
        st.subheader("Files that could not be analyzed")
        for filename, message in errors:
            st.error(f"{filename}: {message}")
else:
    st.markdown(
        """
        **How it works**
        1. Upload multiple NSE quote CSV files at once.
        2. For each file, the app reads the `VWAP` column.
        3. It selects the five smallest valid VWAP values and calculates their average.
        4. It identifies the latest date's VWAP and calculates its percentage change from that average.
        5. It displays the five lowest VWAP values in the final column, each with two decimal places.
        """
    )

st.caption("This is a historical VWAP comparison, not a guaranteed BUY/SELL signal.")
