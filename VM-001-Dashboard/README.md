# VM-001 Smart Vending Intelligence

A production-style Streamlit dashboard for the VM-001 smart vending machine at VESIT Campus, Mumbai. Stage 1 provides MongoDB-backed overview, inventory management, sales analytics, alerts, refill management, and machine metadata views.

## Features

- MongoDB Atlas connection through Streamlit Secrets or local environment variables
- Empty-safe views with no fabricated sales, stock, or prediction records
- Inventory CRUD, validated stock adjustments, and stock logs
- Sales analytics from the `sales` collection with interactive Plotly charts
- Duplicate-resistant low-stock and out-of-stock alert generation
- Validated refill workflow with refill and stock log records
- Database-reported machine status and metadata editing
- Explainable replenishment analytics using validated stored predictions or historical sales baselines

## Technology

Python 3.11+, Streamlit, PyMongo, MongoDB Atlas, Pandas, NumPy, Plotly, and python-dotenv.

## Folder structure

```text
VM-001-Dashboard/
├── app.py
├── config.py
├── database.py
├── requirements.txt
├── .gitignore
├── README.md
├── .streamlit/secrets.toml.example
├── assets/logo.png
├── components/
├── pages/
├── services/
└── utils/
```

## Local setup

```bash
cd VM-001-Dashboard
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Put your real Atlas connection string in `.streamlit/secrets.toml`:

```toml
MONGO_URI = "mongodb+srv://..."
DATABASE_NAME = "VendingMachineDB"
```

Never commit that file. For local fallback, set `MONGO_URI` and `DATABASE_NAME` in a `.env` file.

Run the dashboard:

```bash
streamlit run app.py
```

## MongoDB Atlas setup

Create a database named `VendingMachineDB` with the collections `machines`, `products`, `sales`, `stock_logs`, `refill_logs`, `predictions`, and `alerts`. Configure an application database user and allow the Streamlit deployment network in Atlas Network Access. The app filters machine-specific records with `machine_id = VM-001`.

## GitHub and Streamlit Community Cloud

Create a repository named `VM-001-Dashboard` and push the project without `.streamlit/secrets.toml`, `.env`, or virtual environments. In Streamlit Community Cloud, select the repository, set the main file to `app.py`, and add `MONGO_URI` and `DATABASE_NAME` under App settings > Secrets.

## Prediction analytics

The prediction page uses the selected historical window and configurable refill lead time to calculate average sales per hour, estimated stockout time, target refill quantity, and explainable refill priority. A stored prediction is used only when it has a product ID and finite non-negative `predicted_demand`; the newest valid document wins. Otherwise the row is labeled `Statistical Estimate — Not ML Forecast` and is calculated from successful sales records. Products without sales history are labeled `Insufficient Data` rather than receiving an invented forecast.
