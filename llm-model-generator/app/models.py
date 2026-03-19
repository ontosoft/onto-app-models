import uuid
from datetime import datetime, timezone

from pydantic import EmailStr
from typing import Any, Dict
from sqlalchemy import DateTime, Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field,  SQLModel, Relationship


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)

# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    appmodels: list["AppModel"] = Relationship(back_populates="owner")  

# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int

class AppModelBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)


# Properties to receive via API on creation
class AppModelCreate(AppModelBase):
    rdf_content: str = Field(min_length=1)

# Properties to receive via API on update, all are optional
class AppModelUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    rdf_content: str = Field(min_length=1)  # type: ignore

class AppModel(AppModelBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    owner: User = Relationship(back_populates="appmodels")  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    # Use sa_column to tell SQLAlchemy to use the Postgres JSONB for knowledge graph storage
    knowledge_graph : Any = Field(default={}, sa_column=Column(JSONB))
    rdf_content: str = Field(default=None, sa_column=Column(Text))

# Properties to return via API
class AppModelPublic(AppModelBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None
    knowledge_graph: Any = Field(default={})

class AppModelsPublic(SQLModel):
    data: list[AppModelPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
