import sqlite3

conn = sqlite3.connect("school.db")
cursor = conn.cursor()

# مدیر سامانه (دسترسی کامل)
cursor.execute("""
INSERT OR IGNORE INTO users (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
VALUES ('fatemeh', '1234', 'آموزگار,مدیر سامانه', 'مرکزی', 'فعال', NULL)
""")

# معاون مدرسه شهید بهشتی
cursor.execute("""
INSERT OR IGNORE INTO users (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
VALUES ('moaven1', '4321', 'معاون', 'شهید بهشتی', 'فعال', '1404/07/30')
""")

# آموزگار تستی برای مدرسه شهید بهشتی
cursor.execute("""
INSERT OR IGNORE INTO users (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
VALUES ('teacher1', '1111', 'آموزگار', 'شهید بهشتی', 'فعال', '1404/07/30')
""")

conn.commit()
conn.close()
