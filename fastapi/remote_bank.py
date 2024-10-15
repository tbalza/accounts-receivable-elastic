from fastapi import FastAPI
from sqlalchemy import create_engine, select, Column, Integer, Float, String, Date
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import func
from pydantic import BaseModel
from typing import List
from typing import Optional
from datetime import date

app = FastAPI()

# Database setup
DATABASE_URL = "sqlite:///./databases/remote_bank.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define model
class RemoteBank(Base):
    __tablename__ = 'bank_remote'  # define the table name
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    type = Column(String)
    sender = Column(String)
    description = Column(String)
    amount = Column(Float)

# Pydantic models to validate data
class Transaction(BaseModel):
    id: int
    date: date
    type: Optional[str] = None
    sender: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None

# Create the tables in db
Base.metadata.create_all(bind=engine)

# Endpoint to get all transactions
@app.get("/transactions/", response_model=List[Transaction])
# GET http://localhost:8000/transactions/
def read_transactions():
    with Session(engine) as session:
        stmt = select(RemoteBank)
        results = session.execute(stmt).scalars().all()
        return results

# Endpoint to get transactions within a date range
# GET http://localhost:8000/transactions/date_range/?start_date=2022-01-01&end_date=2022-12-31 # yyyy-mm-dd
@app.get("/transactions/date_range/", response_model=List[Transaction])
def read_transactions_by_date(start_date: date, end_date: date):
    with Session(engine) as session:
        # Ensure start_date is the nearest available date after the given start_date if not found
        adjusted_start = session.query(func.min(RemoteBank.date)).filter(RemoteBank.date >= start_date).scalar()
        # Ensure end_date is the nearest available date before the given end_date if not found
        adjusted_end = session.query(func.max(RemoteBank.date)).filter(RemoteBank.date <= end_date).scalar()

        # If no transactions are found in the range, return an empty list
        if not adjusted_start or not adjusted_end:
            return []

        # Query for transactions within the adjusted date range
        stmt = select(RemoteBank).where(RemoteBank.date.between(adjusted_start, adjusted_end))
        results = session.execute(stmt).scalars().all()
        return results