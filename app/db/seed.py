import asyncio
from datetime import date
from app.db.repository import init_db, AsyncSessionLocal
from app.db.models import Author, Book, PlatformIdentifier

async def seed_data():
    await init_db()
    async with AsyncSessionLocal() as session:
        a1 = Author(
            email="sara.johnson@xyz.com", name="Sara Johnson",
            phone="+919876543210", instagram="@sarapoetry23",
        )
        a2 = Author(email="john.doe@example.com", name="John Doe", phone="+1234567890")
        session.add_all([a1, a2])
        await session.commit()

        session.add_all([
            PlatformIdentifier(author_id=a1.id, platform="email",
                               identifier="sara.johnson@xyz.com", confidence=1.0),
            PlatformIdentifier(author_id=a1.id, platform="instagram",
                               identifier="@sarapoetry23", confidence=1.0),
            PlatformIdentifier(author_id=a1.id, platform="whatsapp",
                               identifier="+91 9876543210", confidence=1.0),
            PlatformIdentifier(author_id=a2.id, platform="email",
                               identifier="john.doe@example.com", confidence=1.0),
            PlatformIdentifier(author_id=a2.id, platform="whatsapp",
                               identifier="+1234567890", confidence=1.0),
        ])

        session.add_all([
            Book(
                author_id=a1.id, book_title="The Silent Garden",
                isbn="978-3-16-148410-0",
                final_submission_date=date(2025, 2, 10),
                book_live_date=date(2025, 4, 20),
                royalty_status="PROCESSING",
                author_copy_status="DISPATCHED",
                add_on_services=["PR", "Bestseller Package"],
            ),
            Book(
                author_id=a2.id, book_title="Mystery of the Old House",
                isbn="978-1-23-456789-0",
                final_submission_date=date(2024, 11, 5),
                book_live_date=date(2025, 1, 15),
                royalty_status="PAID",
                author_copy_status="DELIVERED",
                add_on_services=[],
            ),
        ])
        await session.commit()
        print("Seed data created successfully.")

if __name__ == "__main__":
    asyncio.run(seed_data())
