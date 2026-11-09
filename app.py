import io
import re
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="VWAP 5-Low Analyzer", page_icon="📊", layout="wide")

st.title("📊 VWAP 5-Low Analyzer")
st.caption("Upload one or more NSE equity quote CSV files. The app finds the five lowest VWAP values in each file, calculates their average, and compares the latest VWAP with that average.")

st.info(
    "**Calculation:** % change = ((Latest VWAP − Average of 5 lowest VWAPs) "
    "÷ Average of 5 lowest VWAPs) × 100"
)

uploads = st.file_uploader(
    "Upload multiple NSE quote CSV files",
    type=["csv"],
    accept_multiple_files=True,
    help="You can select several files together. Each file is analyzed separately.",
)

def numeric_series(series):
    """Convert Indian/NSE formatted numbers (including comma separators) to numeric."""
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
    # NSE files commonly look like Quote-Equity-SBIN-EQ-....csv
    match = re.search(r"Quote[-_]Equity[-_]([A-Za-z0-9&.-]+)", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return Path(filename).stem


def analyze_file(upload):
    raw = pd.read_csv(upload)
    raw.columns = [str(c).strip() for c in raw.columns]

    vwap_col = find_column(raw.columns, "VWAP")
    if vwap_col is None:
        raise ValueError("VWAP column was not found.")

    date_col = find_column(raw.columns, "DATE")
    if date_col:
        raw["_DATE_PARSED"] = pd.to_datetime(raw[date_col], dayfirst=True, errors="coerce")
        # NSE quote files are usually newest-first. Sort explicitly so latest is reliable.
        raw = raw.sort_values("_DATE_PARSED", ascending=False, na_position="last")

    raw["_VWAP_NUMERIC"] = numeric_series(raw[vwap_col])
    valid = raw[raw["_VWAP_NUMERIC"].notna()].copy()

    if len(valid) < 5:
        raise ValueError(f"Only {len(valid)} valid VWAP values found; at least 5 are required.")

    lowest = valid.nsmallest(5, "_VWAP_NUMERIC").copy()
    average_lowest = float(lowest["_VWAP_NUMERIC"].mean())

    # Latest value means the value on the most recent DATE, not the last row as uploaded.
    latest_row = valid.iloc[0]
    latest_vwap = float(latest_row["_VWAP_NUMERIC"])

    if average_lowest == 0:
        raise ValueError("Average of the five lowest VWAP values is zero; percentage cannot be calculated.")

    percent_change = ((latest_vwap - average_lowest) / average_lowest) * 100
    latest_date = ""
    if date_col:
        date_value = latest_row.get(date_col, "")
        latest_date = str(date_value) if pd.notna(date_value) else ""

    lowest_rows = []
    for _, row in lowest.iterrows():
        date_value = row.get(date_col, "") if date_col else ""
        lowest_rows.append({
            "Date": str(date_value) if pd.notna(date_value) else "",
            "VWAP": float(row["_VWAP_NUMERIC"]),
        })

    return {
        "Stock": symbol_from_filename(upload.name),
        "File": upload.name,
        "Latest Date": latest_date,
        "Latest VWAP": latest_vwap,
        "5 Lowest VWAP Average": average_lowest,
        "% Change from Average": percent_change,
        "Lowest 5": lowest_rows,
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
        st.subheader("Results")
        summary = pd.DataFrame([
            {key: value for key, value in result.items() if key != "Lowest 5"}
            for result in results
        ])
        summary["Latest VWAP"] = summary["Latest VWAP"].round(2)
        summary["5 Lowest VWAP Average"] = summary["5 Lowest VWAP Average"].round(2)
        summary["% Change from Average"] = summary["% Change from Average"].round(2)

        def color_change(value):
            if value > 0:
                return "color: #16a34a; font-weight: bold"
            if value < 0:
                return "color: #dc2626; font-weight: bold"
            return "font-weight: bold"

        st.dataframe(
            summary.style.map(color_change, subset=["% Change from Average"]),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Five lowest VWAP values")
        for result in results:
            with st.expander(f"{result['Stock']} — {result['File']}"):
                st.write(f"**Latest date:** {result['Latest Date'] or 'Not available'}")
                st.write(f"**Latest VWAP:** {result['Latest VWAP']:.2f}")
                st.write(f"**Average of five lowest:** {result['5 Lowest VWAP Average']:.2f}")
                st.write(f"**% change:** {result['% Change from Average']:+.2f}%")
                low_df = pd.DataFrame(result["Lowest 5"])
                low_df["VWAP"] = low_df["VWAP"].map(lambda x: f"{x:.2f}")
                st.dataframe(low_df, use_container_width=True, hide_index=True)

        csv_bytes = summary.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Download all stock results (CSV)",
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
        3. It selects the five smallest valid VWAP values and calculates their arithmetic average.
        4. It identifies the latest date's VWAP and calculates its percentage change from that average.
        5. It shows a combined stock-wise table and lets you download the results.
        """
    )

st.caption("This is a historical VWAP comparison, not a guaranteed BUY/SELL signal.")
