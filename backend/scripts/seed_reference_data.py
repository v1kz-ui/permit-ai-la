"""Seed reference data into the database.

Usage: cd backend && python -m scripts.seed_reference_data
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Load clearance taxonomy
    taxonomy_path = Path(__file__).parent.parent.parent / "shared" / "clearance_types.json"
    with open(taxonomy_path) as f:
        taxonomy = json.load(f)

    async with session_factory() as session:
        # Ensure PostGIS extension exists
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

        # Log the loaded taxonomy for verification
        departments = [dept["department"] for dept in taxonomy["clearance_taxonomy"]]
        total_clearances = sum(
            len(dept["clearances"]) for dept in taxonomy["clearance_taxonomy"]
        )
        total_inspections = len(taxonomy["inspection_types"])

        print(f"Loaded clearance taxonomy:")
        print(f"  Departments: {', '.join(departments)}")
        print(f"  Clearance types: {total_clearances}")
        print(f"  Inspection types: {total_inspections}")

        # Create a sample admin user for development
        await session.execute(
            text("""
                INSERT INTO users (id, email, name, role, language)
                VALUES (
                    '00000000-0000-0000-0000-000000000001',
                    'dev@permitai.la',
                    'Dev Admin',
                    'admin',
                    'en'
                )
                ON CONFLICT (id) DO NOTHING
            """)
        )

        await session.commit()
        print("Seed data loaded successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
