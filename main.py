import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from fpdf import FPDF

# اتصال به دیتابیس
conn = sqlite3.connect("school.db", check_same_thread=False)
cursor = conn.cursor()

# ساخت جدول‌ها
def init_database():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            نام_کاربر TEXT PRIMARY KEY,
            رمز_عبور TEXT,
            نقش TEXT,
            مدرسه TEXT,
            وضعیت TEXT,
            تاریخ_انقضا TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            آموزگار TEXT,
            نام_دانش‌آموز TEXT,
            رمز_دانش‌آموز TEXT,
            کلاس TEXT,
            تاریخ_ثبت TEXT
        )
    """)
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

init_database()

# افزودن کاربر اولیه (فقط یک‌بار اجرا می‌شود)
cursor.execute("""
    INSERT OR IGNORE INTO users (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
    VALUES (?, ?, ?, ?, ?, ?)
""", ("admin", "1234", "مدیر سامانه", "مدرسه نمونه", "فعال", "2099/12/31"))
conn.commit()

# تنظیمات صفحه
st.set_page_config(page_title="سامانه نمرات", layout="wide")
st.title("🎓 سامانه مدیریت نمرات")

# وضعیت ورود
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "school" not in st.session_state:
    st.session_state.school = ""
def وضعیت_نمره‌ای(میانگین_دانش‌آموز, میانگین_کلاس):
    اختلاف = میانگین_دانش‌آموز - میانگین_کلاس
    if اختلاف < -2:
        return 1
    elif اختلاف < -1:
        return 2
    elif اختلاف <= 1:
        return 3
    else:
        return 4

def متن_وضعیت(عدد):
    return {
        1: "نیاز به تلاش بیشتر",
        2: "قابل قبول",
        3: "خوب",
        4: "خیلی خوب"
    }.get(عدد, "نامشخص")

def draw_line_chart(student_name):
    df = pd.read_sql_query("""
        SELECT درس, نمره_شماره, نمره
        FROM scores
        WHERE نام_دانش‌آموز = ?
    """, conn, params=(student_name,))
    if df.empty:
        return
    fig, ax = plt.subplots()
    for lesson in df["درس"].unique():
        sub_df = df[df["درس"] == lesson]
        ax.plot(sub_df["نمره_شماره"], sub_df["نمره"], label=lesson)
    ax.set_title("📈 روند نمرات")
    ax.set_xlabel("شماره نمره")
    ax.set_ylabel("نمره")
    ax.legend()
    st.pyplot(fig)

def draw_pie_chart(student_name):
    df = pd.read_sql_query("""
        SELECT درس, نمره
        FROM scores
        WHERE نام_دانش‌آموز = ?
    """, conn, params=(student_name,))
    if df.empty:
        return
    avg_df = df.groupby("درس")["نمره"].mean()
    fig, ax = plt.subplots()
    ax.pie(avg_df, labels=avg_df.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("🟢 سهم میانگین نمرات هر درس")
    st.pyplot(fig)

def generate_report(student_name):
    st.subheader("📄 کارنامه دانش‌آموز")

    student_info = pd.read_sql_query(
        "SELECT * FROM students WHERE نام_دانش‌آموز = ?", conn, params=(student_name,)
    ).iloc[0]
    teacher = student_info["آموزگار"]
    student_class = student_info["کلاس"]

    school = pd.read_sql_query(
        "SELECT مدرسه FROM users WHERE نام_کاربر = ?", conn, params=(teacher,)
    ).iloc[0]["مدرسه"]

    st.markdown(f"""
    🏫 مدرسه: {school}  
    👧 دانش‌آموز: {student_name}  
    📚 کلاس: {student_class}  
    📅 تاریخ صدور: {datetime.today().strftime("%Y/%m/%d")}
    """)

    df = pd.read_sql_query("""
        SELECT درس, AVG(نمره) as میانگین_دانش‌آموز
        FROM scores
        WHERE نام_دانش‌آموز = ?
        GROUP BY درس
    """, conn, params=(student_name,))

    rows = []
    for _, row in df.iterrows():
        lesson = row["درس"]
        student_avg = row["میانگین_دانش‌آموز"]

        class_avg = pd.read_sql_query("""
            SELECT AVG(نمره) as میانگین_کلاس
            FROM scores
            WHERE آموزگار = ? AND درس = ?
        """, conn, params=(teacher, lesson)).iloc[0]["میانگین_کلاس"]

        status_num = وضعیت_نمره‌ای(student_avg, class_avg)
        status_text = متن_وضعیت(status_num)

        rows.append({
            "درس": lesson,
            "میانگین دانش‌آموز": round(student_avg, 2),
            "میانگین کلاس": round(class_avg, 2),
            "وضعیت": status_text
        })

    st.table(pd.DataFrame(rows))

    total_avg = df["میانگین_دانش‌آموز"].mean()
    st.markdown(f"📊 میانگین کل: **{round(total_avg, 2)}**")

    if total_avg >= 18:
        st.success("🌟 آفرین! پیشرفتت عالی بوده.")
    elif total_avg >= 15:
        st.info("👍 عملکردت خوبه، ادامه بده!")
    else:
        st.warning("💡 تلاش بیشتری لازم داری. من بهت ایمان دارم!")

    # ساخت فایل PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"کارنامه دانش‌آموز: {student_name}", ln=True, align="C")
    pdf.cell(200, 10, txt=f"تاریخ صدور: {datetime.today().strftime('%Y/%m/%d')}", ln=True, align="C")
    pdf.ln(10)

    for row in rows:
        pdf.cell(200, 10, txt=f"{row['درس']}: میانگین دانش‌آموز {row['میانگین دانش‌آموز']}، میانگین کلاس {row['میانگین کلاس']}، وضعیت: {row['وضعیت']}", ln=True)

    pdf_output = pdf.output(dest="S").encode("latin1")

    st.download_button(
        label="📥 دانلود کارنامه PDF",
        data=pdf_output,
        file_name=f"report_{student_name}.pdf",
        mime="application/pdf"
    )
def show_superadmin_panel():
    st.header("🛠 پنل مدیر سامانه")

    with st.form("register_teacher_form"):
        st.subheader("➕ ثبت آموزگار جدید")
        username = st.text_input("نام کاربری آموزگار")
        password = st.text_input("رمز عبور", type="password")
        school = st.text_input("نام مدرسه")
        expiry_date = st.date_input("تاریخ انقضا")
        submitted = st.form_submit_button("ثبت آموزگار")
        if submitted:
            expiry_str = expiry_date.strftime("%Y/%m/%d")
            cursor.execute("""
                INSERT INTO users (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
                VALUES (?, ?, 'آموزگار', ?, 'فعال', ?)
            """, (username, password, school, expiry_str))
            conn.commit()
            st.success(f"✅ آموزگار {username} ثبت شد.")

    st.subheader("👩‍🏫 لیست آموزگارها")
    df = pd.read_sql_query("SELECT * FROM users WHERE نقش LIKE '%آموزگار%'", conn)
    st.dataframe(df)

    if not df.empty:
        selected_teacher = st.selectbox("انتخاب آموزگار برای مدیریت", df["نام_کاربر"])
        new_status = st.radio("وضعیت جدید", ["فعال", "مسدود"])
        new_expiry = st.date_input("تاریخ جدید انقضا")
        if st.button("ثبت تغییرات"):
            expiry_str = new_expiry.strftime("%Y/%m/%d")
            cursor.execute("UPDATE users SET وضعیت = ?, تاریخ_انقضا = ? WHERE نام_کاربر = ?",
                           (new_status, expiry_str, selected_teacher))
            conn.commit()
            st.success("✅ تغییرات ثبت شد.")

    st.subheader("🔐 تغییر رمز مدیر سامانه")
    current_password = st.text_input("رمز فعلی", type="password", key="admin_current")
    new_password = st.text_input("رمز جدید", type="password", key="admin_new")
    confirm_password = st.text_input("تکرار رمز جدید", type="password", key="admin_confirm")

    if st.button("ثبت تغییر رمز", key="admin_change_btn"):
        cursor.execute("SELECT * FROM users WHERE نام_کاربر = ? AND رمز_عبور = ?", ("admin", current_password))
        result = cursor.fetchone()
        if not result:
            st.error("❌ رمز فعلی اشتباه است.")
        elif new_password != confirm_password:
            st.error("❌ رمز جدید با تکرار آن مطابقت ندارد.")
        elif len(new_password) < 4:
            st.warning("⚠️ رمز جدید باید حداقل ۴ حرف باشد.")
        else:
            cursor.execute("UPDATE users SET رمز_عبور = ? WHERE نام_کاربر = ?", (new_password, "admin"))
            conn.commit()
            st.success("✅ رمز ورود تغییر یافت.")
def show_teacher_panel(username):
    st.header("🎓 پنل آموزگار")
    st.write(f"خوش آمدید، {username}!")

def show_student_panel(username):
    st.header("👧 پنل دانش‌آموز")
    st.write(f"سلام {username} عزیز!")
    generate_report(username)
    draw_line_chart(username)
    draw_pie_chart(username)

def show_assistant_panel(school):
    st.header("📋 پنل معاون")
    st.write(f"مدرسه: {school}")

def show_school_admin_panel(school):
    st.header("🏫 پنل مدیر مدرسه")
    st.write(f"مدرسه: {school}")

# فرم ورود
if not st.session_state.logged_in:
    st.subheader("🔐 ورود به سامانه")
    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")
    login_btn = st.button("ورود")

    if login_btn:
        user_df = pd.read_sql_query("SELECT * FROM users", conn)
        user_row = user_df[
            (user_df["نام_کاربر"] == username) &
            (user_df["رمز_عبور"] == password)
        ]

        if user_row.empty:
            st.error("❌ نام کاربری یا رمز اشتباه است.")
        else:
            roles = user_row.iloc[0]["نقش"].split(",")
            status = user_row.iloc[0]["وضعیت"]
            expiry = user_row.iloc[0]["تاریخ_انقضا"]
            school = user_row.iloc[0]["مدرسه"]

            if status != "فعال":
                st.error("⛔️ حساب شما مسدود شده است.")
            elif expiry and datetime.today().date() > datetime.strptime(expiry, "%Y/%m/%d").date():
                st.error("⛔️ حساب شما منقضی شده است.")
            else:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = roles[0] if len(roles) == 1 else st.radio("🎭 انتخاب نقش:", roles)
                st.session_state.school = school
                st.success("✅ ورود موفقیت‌آمیز")

# نمایش پنل‌ها
if st.session_state.logged_in:
    role = st.session_state.role
    username = st.session_state.username
    school = st.session_state.school

    if role == "مدیر سامانه":
        show_superadmin_panel()
    elif role == "مدیر مدرسه":
        show_school_admin_panel(school)
    elif role == "معاون":
        show_assistant_panel(school)
    elif role == "آموزگار":
        show_teacher_panel(username)
    elif role == "دانش‌آموز":
        show_student_panel(username)
# دکمهٔ خروج از سامانه
if st.session_state.logged_in:
    if st.button("🚪 خروج از سامانه"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.school = ""
        st.experimental_rerun()
