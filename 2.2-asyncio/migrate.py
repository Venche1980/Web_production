import asyncio
from models import init_orm, close_orm


async def main():
    await init_orm()
    print("Таблица создана")
    await close_orm()


if __name__ == "__main__":
    asyncio.run(main())