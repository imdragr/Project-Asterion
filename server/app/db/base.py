from datetime import datetime
from typing import Annotated, Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

tz_aware_datetime = Annotated[datetime, mapped_column(DateTime(timezone=True))]
jsonb = Annotated[dict[str, Any], mapped_column()]
jsonb_list = Annotated[list[dict[str, Any]], mapped_column()]


class Base(DeclarativeBase): ...


class Entity(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[tz_aware_datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[tz_aware_datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
