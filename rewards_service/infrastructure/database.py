import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def get_engine(database_url: str = None):
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./data/rewards.db")
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def get_session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(engine):
    from rewards_service.infrastructure.models import CustomerAccountModel, RewardTransactionModel  # noqa: F401
    Base.metadata.create_all(bind=engine)
