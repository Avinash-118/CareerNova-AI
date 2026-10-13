
from pathlib import Path
from getpass import getpass
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent
PARQUET_FILE = BASE_DIR / "jobs_metadata.parquet"

password = getpass("Enter your PostgreSQL postgres password: ")

database_url = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password=password,
    host="localhost",
    port=5432,
    database="careernova_db"
)

engine = create_engine(database_url, pool_pre_ping=True)

print("Reading job dataset...")
jobs = pd.read_parquet(PARQUET_FILE)

print(f"Total jobs: {len(jobs):,}")
print(f"Columns: {list(jobs.columns)}")

# Replace existing jobs table on each full import.
# Do not run this if you have added independent data to that table.
print("Importing jobs into PostgreSQL...")

jobs.to_sql(
    name="jobs",
    con=engine,
    schema="public",
    if_exists="replace",
    index=False,
    chunksize=1000,
    method="multi"
)

with engine.connect() as connection:
    count = connection.execute(
        text("SELECT COUNT(*) FROM public.jobs")
    ).scalar_one()

print(f"Successfully imported {count:,} jobs!")
engine.dispose()
