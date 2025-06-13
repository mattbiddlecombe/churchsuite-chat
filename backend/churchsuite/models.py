from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class Person(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tags: Optional[List[str]] = None

class Group(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    members: Optional[int] = None
    tags: Optional[List[str]] = None

class Event(BaseModel):
    id: str
    title: str
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None

class FamilyMember(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    relationship: Optional[str] = None

class Family(BaseModel):
    id: str
    members: List[FamilyMember]
    address: Optional[str] = None

class Transaction(BaseModel):
    id: str
    amount: float
    date: datetime
    person: Optional[Person] = None
    description: Optional[str] = None

class GivingAccount(BaseModel):
    id: str
    name: str
    account_type: str
    balance: float
    created_at: datetime
    updated_at: datetime


class GivingTransaction(BaseModel):
    id: str
    amount: float
    date: datetime
    account_id: str
    person_id: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class GivingSummary(BaseModel):
    total_donations: float
    total_donors: int
    average_donation: float
    recent_transactions: List[GivingTransaction]
    top_donors: List[Person]
    donation_trends: List[dict]  # List of {month: str, amount: float}


class ChurchSuiteResponse(BaseModel):
    data: List[Person] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
    links: dict = Field(default_factory=dict)
    description: Optional[str] = None
    balance: Optional[float] = None
    transactions: Optional[List[Transaction]] = None
    giving_accounts: Optional[List[GivingAccount]] = None
    giving_transactions: Optional[List[GivingTransaction]] = None
    giving_summary: Optional[GivingSummary] = None
    groups: Optional[List[Group]] = None
    events: Optional[List[Event]] = None
    families: Optional[List[Family]] = None
