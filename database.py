
import os
from getpass import getpass

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

password = os.getenv("POSTGRES_PASSWORD")

if not password:
    password = getpass("Enter PostgreSQL password: ")

database_url = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password=password,
    host="localhost",
    port=5432,
    database="careernova_db",
)

engine = create_engine(database_url, pool_pre_ping=True)

with engine.connect() as connection:
    total = connection.execute(
        text("SELECT COUNT(*) FROM public.jobs")
    ).scalar_one()

    print("PostgreSQL connected successfully!")
    print(f"Total jobs: {total:,}")
