from dotenv import load_dotenv
import uuid
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Float,
    ForeignKeyConstraint,
    MetaData,
)

from sqlalchemy.orm import (
    declarative_base,
    relationship,
)
import urllib
import os
from datetime import datetime

load_dotenv()
AZURE_CONNECT_STRING = os.getenv("AZURE_CONNECT_STRING")
params = urllib.parse.quote(str(AZURE_CONNECT_STRING))
conn_str = 'mssql+pyodbc:///?odbc_connect={}'.format(params)
engine = create_engine(conn_str,echo=True)

metadata = MetaData()
Base = declarative_base()

class User(Base):
    __tablename__ = "user"

    wallet_addr = Column(String(42), primary_key=True)
    fname = Column(String)
    lname = Column(String)

    miners = relationship("Miner",
                          back_populates="user",
                          cascade="all, delete-orphan")
    stats = relationship("UserStat",
                         back_populates="user",
                         cascade="all, delete-orphan")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    # used for updating a users name, etc.
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

class UserStat(Base):
    __tablename__ = "userStat"

    time = Column(DateTime, default=datetime.now(), primary_key=True)
    wallet_addr = Column(String(42),
                         ForeignKey("user.wallet_addr",
                                    ondelete="CASCADE"),
                         primary_key=True)
    user = relationship("User", back_populates="stats")

    balance = Column(Float)
    est_revenue = Column(Float)
    valid_shares = Column(Integer)
    stale_shares = Column(Integer)
    invalid_shares = Column(Integer)
    round_share_percent = Column(Float)
    effective_hashrate = Column(Float)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Miner(Base):
    __tablename__ = "miner"

    id = Column(UNIQUEIDENTIFIER,
                primary_key=True,
                default=uuid.uuid4())
    wallet_addr = Column(String(42),
                         ForeignKey("user.wallet_addr",
                                    ondelete="CASCADE"))
    user = relationship("User", back_populates="miners")

    gpus = relationship("Gpu",
                        back_populates="miner",
                        cascade="all, delete-orphan")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Gpu(Base):
    __tablename__ = "gpu"

    miner_id = Column(UNIQUEIDENTIFIER,
                      ForeignKey("miner.id",
                                 ondelete="CASCADE"),
                      primary_key=True)
    miner = relationship("Miner", back_populates="gpus")
    gpu_no = Column(Integer, primary_key=True)

    healths = relationship("Health",
                           cascade="all, delete-orphan")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Health(Base):
    __tablename__ = "health"
    __table_args__ = (
        ForeignKeyConstraint(
            ["miner_id", "gpu_no"], ["gpu.miner_id", "gpu.gpu_no"],
            ondelete="CASCADE"
        ),
    )

    # don't need backpopulates because we only ever insert into this table
    miner_id = Column(UNIQUEIDENTIFIER, primary_key=True)
    gpu_no = Column(Integer, primary_key=True)

    time = Column(DateTime, default=datetime.now(), primary_key=True)

    temperature = Column(Integer)
    power = Column(Integer)
    hashrate = Column(Float)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

#Base.metadata.create_all(engine)
