# VWAP 5-Low Analyzer

A Streamlit dashboard for analyzing multiple NSE equity quote CSV files.

## What it calculates

For each uploaded file:

1. Reads the `VWAP` column.
2. Finds the five lowest valid VWAP values.
3. Calculates the average of those five values.
4. Finds the VWAP for the most recent date.
5. Calculates:

`% Change = ((Latest VWAP - Average of 5 Lowest VWAPs) / Average of 5 Lowest VWAPs) * 100`

A positive result means the latest VWAP is above the five-low average. A negative result means it is below.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Open https://share.streamlit.io/
2. Connect GitHub and select `Servejit/Vwap`.
3. Select branch `main` and file `app.py`.
4. Deploy.

Upload multiple NSE quote CSV files together. Each file is analyzed separately and the combined result can be downloaded as CSV.
