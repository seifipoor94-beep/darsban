import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from fpdf import FPDF
import jdatetime
import os

# تنظیمات صفحه
st.set_page_config(page_title="سامانه نمرات", layout="wide")
st.title("🎓 سامانه مدیریت نمرات")

# اتصال به دیتابیس
db_path = "data/school.db"
os.makedirs("data", exist_ok=True)
conn = sqlite3.connect(db_path, check_same_thread=False)
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            آموزگار TEXT,
            نام_دانش‌آموز TEXT,
            نام_کاربری TEXT,
            رمز_دانش‌آموز TEXT,
            کلاس TEXT,
            تاریخ_ثبت TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

# افزودن کاربر اولیه
cursor.execute("""
    INSERT OR IGNORE INTO users (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
    VALUES (?, ?, ?, ?, ?, ?)
""", ("admin", "1234", "مدیر سامانه", "مدرسه نمونه", "فعال", "2099/12/31"))
conn.commit()
# تعریف وضعیت ورود در session_state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "school" not in st.session_state:
    st.session_state.school = ""

# فرم ورود
if not st.session_state.logged_in:
    st.subheader("🔐 ورود به سامانه")
    col1, col2 = st.columns([1, 2])
    with col2:
        username_input = st.text_input("نام کاربری")
        password_input = st.text_input("رمز عبور", type="password")
        login_btn = st.button("ورود")

        if login_btn:
            # بررسی کاربران رسمی
            user_df = pd.read_sql_query("SELECT * FROM users", conn)
            user_row = user_df[
                (user_df["نام_کاربر"] == username_input) &
                (user_df["رمز_عبور"] == password_input)
            ]

            # بررسی دانش‌آموزان
            student_df = pd.read_sql_query("SELECT * FROM students", conn)
            if "نام_کاربری" in student_df.columns:
                student_row = student_df[
                    (student_df["نام_کاربری"] == username_input) &
                    (student_df["رمز_دانش‌آموز"] == password_input)
                ]
            else:
                student_row = pd.DataFrame()

            if not user_row.empty:
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
                    st.session_state.username = username_input
                    st.session_state.role = roles[0] if len(roles) == 1 else st.radio("🎭 انتخاب نقش:", roles)
                    st.session_state.school = school
                    st.success("✅ ورود موفقیت‌آمیز")

            elif not student_row.empty:
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.role = "دانش‌آموز"
                st.session_state.school = ""
                st.success("✅ ورود دانش‌آموز موفقیت‌آمیز")

            else:
                st.error("❌ نام کاربری یا رمز اشتباه است.")
# دکمه خروج در نوار کناری
if st.session_state.logged_in:
    if st.sidebar.button("🚪 خروج"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.school = ""
        st.experimental_rerun()

# نمایش پنل‌ها بر اساس نقش کاربر
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
def show_superadmin_panel():
    st.header("🛠 پنل مدیر سامانه")
    st.write("به پنل مدیر سامانه خوش آمدید.")

    # ثبت کاربر جدید
    with st.form("register_user_form"):
        st.subheader("➕ ثبت کاربر جدید")
        username = st.text_input("نام کاربری")
        password = st.text_input("رمز عبور", type="password")
        school = st.text_input("نام مدرسه")
        role = st.selectbox("نقش کاربر", ["آموزگار", "معاون", "مدیر مدرسه", "مدیر سامانه"])
        expiry_date = st.date_input("تاریخ انقضا")
        submitted = st.form_submit_button("ثبت کاربر")

        if submitted:
            expiry_str = expiry_date.strftime("%Y/%m/%d")
            cursor.execute("""
                INSERT INTO users (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
                VALUES (?, ?, ?, ?, 'فعال', ?)
            """, (username, password, role, school, expiry_str))
            conn.commit()
            st.success(f"✅ کاربر {username} با نقش {role} ثبت شد.")

    # لیست کاربران ثبت‌شده
    st.subheader("🧑‍🏫 مدیریت کاربران ثبت‌شده")
    df = pd.read_sql_query("SELECT * FROM users", conn)
    st.dataframe(df)

    if not df.empty:
        selected_user = st.selectbox("انتخاب کاربر برای ویرایش یا حذف", df["نام_کاربر"])
        user_row = df[df["نام_کاربر"] == selected_user].iloc[0]

        new_password = st.text_input("رمز جدید", value=user_row["رمز_عبور"])
        new_role = st.selectbox("نقش جدید", ["آموزگار", "معاون", "مدیر مدرسه", "مدیر سامانه"],
                                index=["آموزگار", "معاون", "مدیر مدرسه", "مدیر سامانه"].index(user_row["نقش"]))
        new_school = st.text_input("مدرسه جدید", value=user_row["مدرسه"])
        new_status = st.radio("وضعیت جدید", ["فعال", "مسدود"],
                              index=["فعال", "مسدود"].index(user_row["وضعیت"]))
        new_expiry = st.date_input("تاریخ جدید انقضا",
                                   value=datetime.strptime(user_row["تاریخ_انقضا"], "%Y/%m/%d"))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 ثبت تغییرات"):
                expiry_str = new_expiry.strftime("%Y/%m/%d")
                cursor.execute("""
                    UPDATE users
                    SET رمز_عبور = ?, نقش = ?, مدرسه = ?, وضعیت = ?, تاریخ_انقضا = ?
                    WHERE نام_کاربر = ?
                """, (new_password, new_role, new_school, new_status, expiry_str, selected_user))
                conn.commit()
                st.success("✅ اطلاعات کاربر به‌روزرسانی شد.")
                st.experimental_rerun()

        with col2:
            if st.button("🗑 حذف کاربر"):
                cursor.execute("DELETE FROM users WHERE نام_کاربر = ?", (selected_user,))
                conn.commit()
                st.warning(f"❌ کاربر {selected_user} حذف شد.")
                st.experimental_rerun()

    # تغییر رمز مدیر سامانه
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
# پنل آموزگار
def show_teacher_panel(username):
    st.header("🎓 پنل آموزگار")
    st.write(f"خوش آمدید، {username}!")

    teacher_action = st.radio("لطفاً انتخاب کنید:", [
        "➕ ثبت دانش‌آموز جدید",
        "✏️ ویرایش یا حذف دانش‌آموز",
        "📌 ثبت نمره",
        "📊 آمار کلی کلاس",
        "👤 گزارش فردی دانش‌آموز",
        "📄 دانلود کارنامه PDF"
    ])

    if teacher_action == "➕ ثبت دانش‌آموز جدید":
        register_student_form(username)
    elif teacher_action == "✏️ ویرایش یا حذف دانش‌آموز":
        edit_or_delete_student(username)
    elif teacher_action == "📌 ثبت نمره":
        show_score_entry_panel(username)
    elif teacher_action == "📊 آمار کلی کلاس":
        show_class_statistics_panel(username)
    elif teacher_action == "👤 گزارش فردی دانش‌آموز":
        show_individual_report_panel(username)
    elif teacher_action == "📄 دانلود کارنامه PDF":
        download_student_report(username)

# پنل مدیر مدرسه
def show_school_admin_panel(school):
    st.header("🏫 پنل مدیر مدرسه")
    st.write(f"مدرسه: {school}")
    show_teacher_statistics_by_admin(school)

# پنل معاون
def show_assistant_panel(school):
    st.header("📋 پنل معاون")
    st.write(f"مدرسه: {school}")
    show_teacher_statistics_by_admin(school)

# پنل دانش‌آموز
def show_student_panel(username):
    st.header("👧 پنل دانش‌آموز")
    st.write(f"خوش آمدی، {username} عزیز!")

    student_info = pd.read_sql_query("SELECT * FROM students WHERE نام_کاربری = ?", conn, params=(username,))
    if student_info.empty:
        st.error("اطلاعات شما پیدا نشد.")
        return

    student_name = student_info.iloc[0]["نام_دانش‌آموز"]

    lessons_df = pd.read_sql_query("SELECT DISTINCT درس FROM scores WHERE نام_دانش‌آموز = ?", conn, params=(student_name,))
    if lessons_df.empty:
        st.info("هنوز نمره‌ای برای شما ثبت نشده.")
        return

    selected_lesson = st.selectbox("انتخاب درس:", lessons_df["درس"].unique())

    st.markdown("### 📈 نمودار خطی پیشرفت")
    df_line = pd.read_sql_query("""
        SELECT نمره_شماره, نمره FROM scores
        WHERE نام_دانش‌آموز = ? AND درس = ?
        ORDER BY نمره_شماره
    """, conn, params=(student_name, selected_lesson))

    if not df_line.empty:
        fig, ax = plt.subplots()
        ax.plot(df_line["نمره_شماره"], df_line["نمره"], marker="o")
        ax.set_title(f"روند نمرات درس {selected_lesson}")
        ax.set_xlabel("شماره نمره")
        ax.set_ylabel("نمره")
        st.pyplot(fig)

    st.markdown("### 🟢 نمودار دایره‌ای میانگین نمرات")
    draw_pie_chart(student_name)

    st.markdown("### 📄 جدول کارنامه")
    download_student_report_direct(student_name)
# گزارش فردی دانش‌آموز برای آموزگار
def download_student_report(username):
    st.subheader("📄 دانلود کارنامه PDF")

    student_df = pd.read_sql_query("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique())
    student_info = pd.read_sql_query("SELECT * FROM students WHERE نام_دانش‌آموز = ?", conn, params=(student_name,)).iloc[0]
    student_class = student_info["کلاس"]
    school = pd.read_sql_query("SELECT مدرسه FROM users WHERE نام_کاربر = ?", conn, params=(username,)).iloc[0]["مدرسه"]
    today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")

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
        """, conn, params=(username, lesson)).iloc[0]["میانگین_کلاس"]

        status_num = وضعیت_نمره‌ای(student_avg, class_avg)
        status_text = متن_وضعیت(status_num)

        rows.append({
            "درس": lesson,
            "میانگین دانش‌آموز": round(student_avg, 2),
            "میانگین کلاس": round(class_avg, 2),
            "وضعیت": status_text
        })

    st.markdown(f"""
    🏫 مدرسه: {school}  
    👧 دانش‌آموز: {student_name}  
    📚 کلاس: {student_class}  
    📅 تاریخ صدور: {today_shamsi}
    """)
    st.table(pd.DataFrame(rows))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"کارنامه دانش‌آموز: {student_name}", ln=True, align="C")
    pdf.cell(200, 10, txt=f"تاریخ صدور: {today_shamsi}", ln=True, align="C")
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
# تعیین وضعیت نمره‌ای بر اساس میانگین فرد و کلاس
def وضعیت_نمره‌ای(student_avg, class_avg):
    if student_avg < class_avg * 0.6:
        return 1  # نیاز به تلاش بیشتر
    elif student_avg < class_avg * 0.85:
        return 2  # قابل قبول
    elif student_avg < class_avg * 1.15:
        return 3  # خوب
    else:
        return 4  # خیلی خوب

# تبدیل عدد وضعیت به متن فارسی
def متن_وضعیت(status_num):
    وضعیت‌ها = {
        1: "نیاز به تلاش بیشتر",
        2: "قابل قبول",
        3: "خوب",
        4: "خیلی خوب"
    }
    return وضعیت‌ها.get(status_num, "نامشخص")

# رسم نمودار دایره‌ای وضعیت نمرات دانش‌آموز
def draw_pie_chart(student_name):
    df = pd.read_sql_query("""
        SELECT درس, AVG(نمره) as میانگین_دانش‌آموز
        FROM scores
        WHERE نام_دانش‌آموز = ?
        GROUP BY درس
    """, conn, params=(student_name,))

    if df.empty:
        st.info("هیچ نمره‌ای برای رسم نمودار وجود ندارد.")
        return

    status_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for _, row in df.iterrows():
        lesson = row["درس"]
        student_avg = row["میانگین_دانش‌آموز"]
        teacher = pd.read_sql_query("SELECT آموزگار FROM students WHERE نام_دانش‌آموز = ?", conn, params=(student_name,)).iloc[0]["آموزگار"]
        class_avg = pd.read_sql_query("""
            SELECT AVG(نمره) as میانگین_کلاس
            FROM scores
            WHERE آموزگار = ? AND درس = ?
        """, conn, params=(teacher, lesson)).iloc[0]["میانگین_کلاس"]

        status = وضعیت_نمره‌ای(student_avg, class_avg)
        status_counts[status] += 1

    labels = ["نیاز به تلاش بیشتر", "قابل قبول", "خوب", "خیلی خوب"]
    colors = ["#e74c3c", "#f39c12", "#3498db", "#2ecc71"]
    sizes = [status_counts[i] for i in range(1, 5)]

    fig, ax = plt.subplots()
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
    for text in texts + autotexts:
        text.set_fontsize(12)
        text.set_horizontalalignment("right")
    ax.set_title("📊 توزیع وضعیت نمرات", fontsize=14)
    st.pyplot(fig)
# ثبت دانش‌آموز جدید
def register_student_form(username):
    st.subheader("➕ ثبت دانش‌آموز جدید")
    name = st.text_input("نام دانش‌آموز")
    username_std = st.text_input("نام کاربری دانش‌آموز")
    password_std = st.text_input("رمز دانش‌آموز", type="password")
    class_name = st.text_input("کلاس")
    if st.button("ثبت"):
        today = datetime.today().strftime("%Y/%m/%d")
        cursor.execute("""
            INSERT INTO students (آموزگار, نام_دانش‌آموز, نام_کاربری, رمز_دانش‌آموز, کلاس, تاریخ_ثبت)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, name, username_std, password_std, class_name, today))
        conn.commit()
        st.success("✅ دانش‌آموز با موفقیت ثبت شد.")

# ثبت نمره
def show_score_entry_panel(username):
    st.subheader("📌 ثبت نمره")
    student_df = pd.read_sql_query("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique())
    lesson = st.text_input("نام درس")
    score_number = st.text_input("شماره نمره (مثلاً نمره اول، دوم...)")
    score_value = st.number_input("نمره", min_value=0, max_value=20)
    if st.button("ثبت نمره"):
        today = datetime.today().strftime("%Y/%m/%d")
        cursor.execute("""
            INSERT INTO scores (آموزگار, نام_دانش‌آموز, درس, نمره_شماره, نمره, تاریخ)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, student_name, lesson, score_number, score_value, today))
        conn.commit()
        st.success("✅ نمره ثبت شد.")

# گزارش فردی دانش‌آموز
def show_individual_report_panel(username):
    st.subheader("👤 گزارش فردی دانش‌آموز")
    student_df = pd.read_sql_query("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique())
    draw_pie_chart(student_name)

# رتبه‌بندی کلاس
def show_class_ranking_panel(username, role):
    st.subheader("🏅 رتبه‌بندی کلاس")
    if role in ["مدیر مدرسه", "معاون"]:
        teacher_df = pd.read_sql_query("SELECT نام_کاربر FROM users WHERE نقش = 'آموزگار' AND مدرسه = ?", conn, params=(st.session_state.school,))
        if teacher_df.empty:
            st.info("هیچ آموزگاری برای این مدرسه ثبت نشده.")
            return
        selected_teacher = st.selectbox("انتخاب آموزگار:", teacher_df["نام_کاربر"].unique())
    else:
        selected_teacher = username

    lessons_df = pd.read_sql_query("SELECT DISTINCT درس FROM scores WHERE آموزگار = ?", conn, params=(selected_teacher,))
    if lessons_df.empty:
        st.info("هیچ نمره‌ای ثبت نشده است.")
        return

    selected_lesson = st.selectbox("انتخاب درس برای رتبه‌بندی:", lessons_df["درس"].unique())

    total_df = pd.read_sql_query("""
        SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_کل
        FROM scores
        WHERE آموزگار = ?
        GROUP BY نام_دانش‌آموز
        ORDER BY میانگین_کل DESC
    """, conn, params=(selected_teacher,))
    st.markdown("### 📊 رتبه‌بندی کلی کلاس")
    st.dataframe(total_df)

    lesson_df = pd.read_sql_query("""
        SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_درس
        FROM scores
        WHERE آموزگار = ? AND درس = ?
        GROUP BY نام_دانش‌آموز
        ORDER BY میانگین_درس DESC
    """, conn, params=(selected_teacher, selected_lesson))
    st.markdown(f"### 📘 رتبه‌بندی درس {selected_lesson}")
    st.dataframe(lesson_df)

# خروجی PDF برای دانش‌آموز
def download_student_report_direct(student_name):
    student_info = pd.read_sql_query("SELECT * FROM students WHERE نام_دانش‌آموز = ?", conn, params=(student_name,)).iloc[0]
    teacher = student_info["آموزگار"]
    student_class = student_info["کلاس"]
    school = pd.read_sql_query("SELECT مدرسه FROM users WHERE نام_کاربر = ?", conn, params=(teacher,)).iloc[0]["مدرسه"]
    today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")

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

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"کارنامه دانش‌آموز: {student_name}", ln=True, align="C")
    pdf.cell(200, 10, txt=f"تاریخ صدور: {today_shamsi}", ln=True, align="C")
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
