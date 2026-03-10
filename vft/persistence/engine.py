import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


def load_env():
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


load_env()


@dataclass(frozen=True)
class DBConfig:
    database_url: str


_engine: Optional[Engine] = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")

    _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


def ping_db() -> bool:
    try:
        eng = get_engine()
        with eng.begin() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False