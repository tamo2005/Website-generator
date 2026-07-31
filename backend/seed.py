"""
seed.py — Database seeding script for development and testing

Creates default verified user and admin accounts if they do not already exist.
Usage:
    python seed.py
"""
import asyncio
import sys

from core.security import hash_password
from db.session import AsyncSessionLocal
from models.user import UserRole
from repositories.user_repo import user_repo


SEED_USERS = [
    {
        "email": "admin@example.com",
        "username": "admin",
        "password": "Password123!",
        "role": UserRole.ADMIN,
        "is_verified": True,
    },
    {
        "email": "user@example.com",
        "username": "testuser",
        "password": "Password123!",
        "role": UserRole.USER,
        "is_verified": True,
    },
]


async def seed_database():
    print("[INFO] Starting database seeding...")
    async with AsyncSessionLocal() as db:
        created_count = 0
        for user_data in SEED_USERS:
            existing = await user_repo.get_by_email(db, user_data["email"])
            if existing:
                print(f"  - User '{user_data['email']}' already exists (ID: {existing.id})")
                if not existing.is_verified or not existing.is_active:
                    await user_repo.update(db, existing, is_verified=True, is_active=True)
                    print(f"    Updated '{user_data['email']}' to verified & active.")
                continue

            hashed = hash_password(user_data["password"])
            user = await user_repo.create(
                db,
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=hashed,
                role=user_data["role"],
                is_verified=user_data["is_verified"],
            )
            created_count += 1
            print(f"  + Created {user_data['role'].value} user: {user.email} (Username: {user.username})")

        await db.commit()
        print(f"[SUCCESS] Seeding complete! {created_count} user(s) created.")


if __name__ == "__main__":
    asyncio.run(seed_database())
