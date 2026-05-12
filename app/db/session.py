from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
	AsyncSession,
	async_sessionmaker,
	create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
	str(settings.DATABASE_URL),
	echo=False,
	pool_size=20,
	max_overflow=10,
	pool_recycle=3600,
	pool_pre_ping=True,
	connect_args={
		"timeout": 10,
		"server_settings": {"jit": "off"},
	},
)

AsyncSessionLocal = async_sessionmaker(
	engine,
	class_=AsyncSession,
	expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
	async with AsyncSessionLocal() as session:
		yield session
