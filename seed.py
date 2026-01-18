"""
Seed script to populate the database with test data.
Run with: python seed.py
"""
import asyncio
import bcrypt
from database import db


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def seed():
    await db.connect()
    
    print("🌱 Seeding database...")
    
    # Clear existing data
    print("🗑️  Clearing existing data...")
    await db.expenseparticipant.delete_many()
    await db.expense.delete_many()
    await db.receipt.delete_many()
    await db.groupmember.delete_many()
    await db.group.delete_many()
    await db.user.delete_many()
    
    # Create users
    print("👤 Creating users...")
    users = []
    user_data = [
        {"username": "demo", "password": "demo123", "displayName": "Demo User"},
        {"username": "tuan", "password": "123456", "displayName": "Tuấn"},
        {"username": "linh", "password": "123456", "displayName": "Linh"},
        {"username": "minh", "password": "123456", "displayName": "Minh"},
    ]
    
    for data in user_data:
        user = await db.user.create(
            data={
                "username": data["username"],
                "password": hash_password(data["password"]),
                "displayName": data["displayName"],
            }
        )
        users.append(user)
        print(f"   ✓ Created user: {user.username}")
    
    demo, tuan, linh, minh = users
    
    # Create groups
    print("👥 Creating groups...")
    
    group1 = await db.group.create(
        data={
            "name": "Nhóm đi ăn",
            "emoji": "🍜",
            "description": "Nhóm để chia tiền đi ăn uống",
            "createdById": demo.id,
            "members": {
                "create": [
                    {"userId": demo.id},
                    {"userId": tuan.id},
                    {"userId": linh.id},
                ]
            }
        }
    )
    print(f"   ✓ Created group: {group1.name}")
    
    group2 = await db.group.create(
        data={
            "name": "Du lịch Đà Lạt",
            "emoji": "🏔️",
            "description": "Chuyến du lịch cuối năm",
            "createdById": tuan.id,
            "members": {
                "create": [
                    {"userId": demo.id},
                    {"userId": tuan.id},
                    {"userId": linh.id},
                    {"userId": minh.id},
                ]
            }
        }
    )
    print(f"   ✓ Created group: {group2.name}")
    
    # Create expenses
    print("💰 Creating expenses...")
    
    expense1 = await db.expense.create(
        data={
            "groupId": group1.id,
            "amount": 450000,
            "description": "Ăn phở sáng",
            "paidById": demo.id,
            "participants": {
                "create": [
                    {"userId": demo.id, "amount": 150000, "settled": True},
                    {"userId": tuan.id, "amount": 150000, "settled": False},
                    {"userId": linh.id, "amount": 150000, "settled": False},
                ]
            }
        }
    )
    print(f"   ✓ Created expense: {expense1.description} - {expense1.amount:,}đ")
    
    expense2 = await db.expense.create(
        data={
            "groupId": group1.id,
            "amount": 320000,
            "description": "Cà phê chiều",
            "paidById": tuan.id,
            "participants": {
                "create": [
                    {"userId": demo.id, "amount": 160000, "settled": False},
                    {"userId": tuan.id, "amount": 160000, "settled": True},
                ]
            }
        }
    )
    print(f"   ✓ Created expense: {expense2.description} - {expense2.amount:,}đ")
    
    expense3 = await db.expense.create(
        data={
            "groupId": group2.id,
            "amount": 2400000,
            "description": "Thuê khách sạn 2 đêm",
            "paidById": tuan.id,
            "participants": {
                "create": [
                    {"userId": demo.id, "amount": 600000, "settled": False},
                    {"userId": tuan.id, "amount": 600000, "settled": True},
                    {"userId": linh.id, "amount": 600000, "settled": True},
                    {"userId": minh.id, "amount": 600000, "settled": False},
                ]
            }
        }
    )
    print(f"   ✓ Created expense: {expense3.description} - {expense3.amount:,}đ")
    
    expense4 = await db.expense.create(
        data={
            "groupId": group2.id,
            "amount": 800000,
            "description": "Ăn tối BBQ",
            "paidById": linh.id,
            "participants": {
                "create": [
                    {"userId": demo.id, "amount": 200000, "settled": False},
                    {"userId": tuan.id, "amount": 200000, "settled": False},
                    {"userId": linh.id, "amount": 200000, "settled": True},
                    {"userId": minh.id, "amount": 200000, "settled": False},
                ]
            }
        }
    )
    print(f"   ✓ Created expense: {expense4.description} - {expense4.amount:,}đ")
    
    await db.disconnect()
    
    print("\n✅ Database seeded successfully!")
    print("\n📋 Test accounts:")
    print("   Username: demo    Password: demo123")
    print("   Username: tuan    Password: 123456")
    print("   Username: linh    Password: 123456")
    print("   Username: minh    Password: 123456")


if __name__ == "__main__":
    asyncio.run(seed())
