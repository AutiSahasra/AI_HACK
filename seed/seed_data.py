import asyncio
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import DatabaseManager
from app.core.seeder import seed_all_data

async def main():
    print("Connecting to database...")
    await DatabaseManager.connect()
    print("Running seeds...")
    await seed_all_data()
    print("Done!")
    await DatabaseManager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
