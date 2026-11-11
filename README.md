# VENDORA Analytics (Streamlit)
Business analytics only. Vending itself runs offline on the ESP8266.

## Data flow
The dashboard reads the `Daily`, `ProductDaily`, `Transactions`, `Live`, and
`LiveProducts` tabs from a Google Sheet shared as **Anyone with the link:
Viewer**. Configure the sheet ID in Streamlit secrets under
`1YFiLW-iSre378B0dXzDpiq9sC4JhnK6KLpTkqbKxAOY`.

The Apps Script backend writes finished daily totals at midnight and refreshes
the live tabs every 10 minutes. The machine remains offline-first.
The transaction tabs may be empty before the first sale or before a day closes;
the dashboard treats those tabs as having no transaction details yet.

## Run locally
pip install -r requirements.txt
streamlit run app.py

## Deploy (free)
1. Push this folder to a GitHub repo.
2. share.streamlit.io -> New app -> pick repo, branch main, file app.py -> Deploy.
