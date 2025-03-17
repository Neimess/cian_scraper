from sqlalchemy.ext.asyncio import AsyncSession
from db.models import User, UserConfig
from sqlalchemy.future import select


async def get_or_create_user(db: AsyncSession, tg_id: str) -> User:
    """
    Retrieves an existing user by Telegram ID, or creates a new one if doesn't exist.
    Updates username/full_name if they changed.
    """
    stmt = select(User).where(User.tg_id == tg_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        user = User(tg_id=tg_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user

async def get_user_config(db: AsyncSession, user_id: int) -> UserConfig:
    """
    Get the user's search preferences from the database.
    """
    smtp = select(UserConfig).filter_by(user_id=user_id)
    result = await db.execute(smtp)
    config = result.scalars().first()
    if not config:
        config = UserConfig(user_id=user_id)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


async def update_user_config(db: AsyncSession, user_id: int, field: str, value: str):
    """
    Update the user's search preferences in the database.
    """
    config = await get_user_config(db, user_id)
    setattr(config, field, value)
    await db.commit()
