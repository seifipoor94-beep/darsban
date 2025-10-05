import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

# اتصال به دیتابیس
conn = sqlite3.connect("school.db", check_same_thread=False)
cursor = conn.cursor()

# ساخت جدول‌ها در صورت نیاز
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

# تنظیمات صفحه
st.set_page_config(page_title="سامانه نمرات", layout="wide")
st.title("🎓 سامانه مدیریت نمرات")
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
def show_teacher_panel(username):
    st.header(f"👩‍🏫 پنل آموزگار ({username})")

    with st.form("register_student_form"):
        st.subheader("➕ ثبت دانش‌آموز")
        student_name = st.text_input("نام دانش‌آموز")
        student_password = st.text_input("رمز دانش‌آموز", type="password")
        student_class = st.text_input("کلاس")
        submitted = st.form_submit_button("ثبت دانش‌آموز")
        if submitted:
            today = datetime.today().strftime("%Y/%m/%d")
            cursor.execute("""
                INSERT INTO students (آموزگار, نام_دانش‌آموز, رمز_دانش‌آموز, کلاس, تاریخ_ثبت)
                VALUES (?, ?, ?, ?, ?)
            """, (username, student_name, student_password, student_class, today))
            conn.commit()
            st.success("✅ دانش‌آموز ثبت شد.")

    st.subheader("📝 ثبت نمره")
    student_list = pd.read_sql_query(
        "SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,)
    )["نام_دانش‌آموز"].tolist()
    if student_list:
        selected_student = st.selectbox("نام دانش‌آموز", student_list)
        lesson = st.selectbox("درس", ["ریاضی", "فارسی", "علوم", "هدیه"])
        score_number = st.selectbox("شماره نمره", ["نمره ۱", "نمره ۲", "نمره ۳", "نمره ۴"])
        score = st.number_input("نمره", min_value=0, max_value=20, step=1)
        if st.button("ثبت نمره"):
            today = datetime.today().strftime("%Y/%m/%d")
            cursor.execute("""
                INSERT INTO scores (آموزگار, نام_دانش‌آموز, درس, نمره_شماره, نمره, تاریخ)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, selected_student, lesson, score_number, int(score), today))
            conn.commit()
            st.success("✅ نمره ثبت شد.")
    else:
        st.warning("⛔️ هنوز دانش‌آموزی ثبت نشده.")

    st.subheader("🔐 تغییر رمز")
    current_password = st.text_input("رمز فعلی", type="password")
    new_password = st.text_input("رمز جدید", type="password")
    confirm_password = st.text_input("تکرار رمز جدید", type="password")
    if st.button("ثبت تغییر رمز"):
        cursor.execute("SELECT * FROM users WHERE نام_کاربر = ? AND رمز_عبور = ?", (username, current_password))
        result = cursor.fetchone()
        if not result:
            st.error("❌ رمز فعلی اشتباه است.")
        elif new_password != confirm_password:
            st.error("❌ رمز جدید با تکرار آن مطابقت ندارد.")
        elif len(new_password) < 4:
            st.warning("⚠️ رمز جدید باید حداقل ۴ حرف باشد.")
        else:
            cursor.execute("UPDATE users SET رمز_عبور = ? WHERE نام_کاربر = ?", (new_password, username))
            conn.commit()
            st.success("✅ رمز ورود تغییر یافت.")
def show_student_panel(student_name):
    st.header(f"👧 پنل دانش‌آموز ({student_name})")

    df = pd.read_sql_query("""
        SELECT درس, نمره_شماره, نمره, تاریخ
        FROM scores
        WHERE نام_دانش‌آموز = ?
        ORDER BY تاریخ DESC
    """, conn, params=(student_name,))
    if df.empty:
        st.warning("هنوز نمره‌ای ثبت نشده.")
        return

    st.subheader("📄 نمرات شما")
    st.dataframe(df)

    draw_line_chart(student_name)
    draw_pie_chart(student_name)

    if st.button("📥 مشاهده کارنامه"):
        generate_report(student_name)
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
def show_assistant_panel(school):
    st.header(f"📚 پنل معاون ({school})")

    df = pd.read_sql_query("""
        SELECT s.نام_دانش‌آموز, s.کلاس, u.نام_کاربر as آموزگار
        FROM students s
        JOIN users u ON s.آموزگار = u.نام_کاربر
        WHERE u.مدرسه = ?
    """, conn, params=(school,))
    
    if df.empty:
        st.warning("❌ هنوز دانش‌آموزی ثبت نشده.")
    else:
        st.subheader("👧 لیست دانش‌آموزان مدرسه")
        st.dataframe(df)
def show_school_admin_panel(school):
    st.header(f"🏫 پنل مدیر مدرسه ({school})")

    df = pd.read_sql_query("SELECT * FROM users WHERE مدرسه = ?", conn, params=(school,))
    if df.empty:
        st.warning("❌ هنوز کاربری برای این مدرسه ثبت نشده.")
    else:
        st.subheader("👩‍🏫 کاربران مدرسه")
        st.dataframe(df)

    if not df.empty:
        selected_user = st.selectbox("انتخاب کاربر برای مدیریت", df["نام_کاربر"])
        new_status = st.radio("وضعیت جدید", ["فعال", "مسدود"])
        if st.button("ثبت تغییرات"):
            cursor.execute("UPDATE users SET وضعیت = ? WHERE نام_کاربر = ?", (new_status, selected_user))
            conn.commit()
            st.success("✅ تغییرات ثبت شد.")
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
            st.success("✅ ورود موفقیت‌آمیز")

            if len(roles) == 1:
                selected_role = roles[0]
            else:
                selected_role = st.radio("🎭 انتخاب نقش:", roles)

            if selected_role == "مدیر سامانه":
                show_superadmin_panel()
            elif selected_role == "مدیر مدرسه":
                show_school_admin_panel(school)
            elif selected_role == "معاون":
                show_assistant_panel(school)
            elif selected_role == "آموزگار":
                show_teacher_panel(username)
            elif selected_role == "دانش‌آموز":
                show_student_panel(username)
            else:
                st.warning("⚠️ نقش انتخاب‌شده پشتیبانی نمی‌شود.")
from fpdf import FPDF
import base64

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
    b64_pdf = base64.b64encode(pdf_output).decode()

    st.download_button(
        label="📥 دانلود کارنامه PDF",
        data=pdf_output,
        file_name=f"report_{student_name}.pdf",
        mime="application/pdf"
    )
