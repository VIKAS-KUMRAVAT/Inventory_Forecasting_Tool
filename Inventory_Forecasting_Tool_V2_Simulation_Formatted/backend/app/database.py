from databases import Database
from sqlalchemy import create_engine, MetaData

# Use a plain postgresql URL without +asyncpg for databases.Database
DATABASE_URL = "postgresql://postgres:Shopping%401@localhost:5432/inventory_db"

# Async database instance for FastAPI
database = Database(DATABASE_URL)

# SQLAlchemy engine for synchronous operations or migrations
engine = create_engine(DATABASE_URL)

metadata = MetaData()
