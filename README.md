# VENDORA Analytics (Streamlit)
Business analytics only. Vending itself runs offline on the ESP8266.

## Data flow
The dashboard reads the `Daily`, `ProductDaily`, `Transactions`, `Live`, and
`LiveProducts` tabs from a Google Sheet shared as **Anyone with the link:
Viewer**. Add the sheet ID as `SHEET_ID` in Streamlit secrets, or enter it in
the sidebar. Select **Sample data** to run the dashboard without a sheet.

The Apps Script backend writes finished daily totals at midnight and refreshes
the live tabs every 10 minutes. The machine remains offline-first.

## Run locally
pip install -r requirements.txt
streamlit run app.py

## Deploy (free)
1. Push this folder to a GitHub repo.
2. share.streamlit.io -> New app -> pick repo, branch main, file app.py -> Deploy.
