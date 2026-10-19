
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

load_dotenv()

# Use local PostgreSQL while developing CareerNova AI.
password = os.getenv("POSTGRES_PASSWORD")


database_url = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password=password,
    host="localhost",
    port=5432,
    database="careernova_db",
)

configured_url = os.getenv("DATABASE_URL")
if configured_url:
    try:
        configured_url = make_url(configured_url)
        # Keep provider connection strings on our installed psycopg2 driver.
        if configured_url.drivername in ('postgresql', 'postgres'):
            configured_url = configured_url.set(drivername='postgresql+psycopg2')
    except ArgumentError:
        # Older local setups used a non-URL placeholder; retain their PostgreSQL settings.
        configured_url = None

from deployment_config import production
if production() and not configured_url:
    raise RuntimeError('A valid DATABASE_URL is required in production')

engine = create_engine(
    configured_url or database_url,
    pool_pre_ping=True,
    connect_args={'connect_timeout':10},
    pool_size=5, max_overflow=5, pool_recycle=300,
)

if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("Local PostgreSQL connected successfully!")

            total = connection.execute(
                text("SELECT COUNT(*) FROM public.jobs")
            ).scalar_one()

            print(f"Total jobs: {total:,}")

    except Exception as error:
        print("Database connection or query failed:")
        print(type(error).__name__)
        print("Check PostgreSQL is running and the jobs table exists.")
