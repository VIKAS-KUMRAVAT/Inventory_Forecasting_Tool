from databases import Database
from sqlalchemy import create_engine, MetaData

DATABASE_URL = "postgresql+asyncpg://postgres:Shopping%401@localhost:5432/inventory_db"

# Async database instance for FastAPI
database = Database(DATABASE_URL)

# SQLAlchemy engine for migrations or sync tasks (optional)
engine = create_engine(DATABASE_URL.replace('+asyncpg', ''))

metadata = MetaData()
