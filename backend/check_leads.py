import asyncio
from app.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT id FROM zl_users WHERE email = 'demo@gmail.com'"))
        user = r.fetchone()
        if not user:
            print("demo@gmail.com not found")
            return
        user_id = user[0]
        print(f"User ID: {user_id}")

        r = await conn.execute(text(f"SELECT COUNT(*) FROM zl_leads WHERE user_id = '{user_id}'"))
        count = r.scalar()
        print(f"Total leads: {count}")

        if count > 0:
            r = await conn.execute(text(f"""
                SELECT lead_score, lead_tier, status, source, created_at
                FROM zl_leads WHERE user_id = '{user_id}' ORDER BY lead_score DESC
            """))
            print("\nLeads:")
            for row in r.fetchall():
                print(f"  Score {row[0]:>2} {row[1]:>8} | {row[2]:>10} | {row[3]:>15} | {row[4]}")

asyncio.run(check())
