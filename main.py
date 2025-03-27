import asyncio
import argparse
import db.database as db
from src.bot.bot import TelegramBot
from src.loggers import logger
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy()) 

async def main(init_db=False, run_bot=False):

    if init_db:
        try:
            logger.info("Initialization db")
            db.init_engine()
            await db.init_db()
            logger.info("Successfully initializated")
        except Exception as e:
            logger.error(f"Error while initializated: {e}")
            return

    if run_bot:
        logger.info("🚀 Start Telegram Bot...")
        bot = TelegramBot()
        await bot.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database/TelegramBot Start Params")
    parser.add_argument("--init-db", action="store_true", help="Initialize Database")
    parser.add_argument("--run-bot", action="store_true", help="Start Telegram-bot")

    args = parser.parse_args()

    if not any([args.init_db, args.run_bot]):
        args.init_db = True
        args.run_bot = True

    asyncio.run(main(init_db=args.init_db, run_bot=args.run_bot))
