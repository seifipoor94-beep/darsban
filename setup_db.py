import sqlite3

conn = sqlite3.connect("school.db")
cursor = conn.cursor()

# جدول کاربران
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    نام_کاربر TEXT PRIMARY KEY,
    رمز_عبور TEXT,
    نقش TEXT,
    مدرسه TEXT,
    وضعیت TEXT DEFAULT 'فعال',
    تاریخ_انقضا TEXT
)
""")

# جدول دانش‌آموزها
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    آموزگار TEXT,
    نام_دانش‌آموز TEXT,
    رمز_دانش‌آموز TEXT,
    کلاس TEXT,
    تاریخ_ثبت TEXT
)
""")

# جدول نمرات
cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    آموزگار TEXT,
    نام_دانش‌آموز TEXT,
    درس TEXT,
    نمره_شماره TEXT,
    نمره INTEGER,
    تاریخ TEXT
)
""")

conn.commit()
conn.close()
