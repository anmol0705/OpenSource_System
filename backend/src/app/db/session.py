from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.debug)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Every database table (SQLAlchemy 'model') we define will inherit
    from this. It's just a shared starting point SQLAlchemy needs.
    """


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Hands a fresh database session to whichever endpoint asks for one
    (via Depends(get_db)), and guarantees it gets closed afterward —
    even if the endpoint raises an error.
    """
    async with async_session_factory() as session:
        yield session
