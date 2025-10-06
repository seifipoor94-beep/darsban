import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from fpdf import FPDF
import jdatetime

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
            نام_کاربری TEXT,
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

# افزودن کاربر اولیه
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
    today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")

    st.markdown(f"""
    🏫 مدرسه: {school}
    👧 دانش‌آموز: {student_name}
    📚 کلاس: {student_class}
    📅 تاریخ صدور: {today_shamsi}
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
def show_superadmin_panel():
    st.header("🛠 پنل مدیر سامانه")

    # ثبت کاربر جدید با نقش
    with st.form("register_teacher_form"):
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

    # لیست کاربران قابل ویرایش
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
                st.success("✅ اطلاعات کاربر با موفقیت به‌روزرسانی شد.")

        with col2:
            if st.button("🗑 حذف کاربر"):
                cursor.execute("DELETE FROM users WHERE نام_کاربر = ?", (selected_user,))
                conn.commit()
                st.warning(f"❌ کاربر {selected_user} حذف شد.")

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

def show_school_admin_panel(school):
    st.header("🏫 پنل مدیر مدرسه")
    st.write(f"مدرسه: {school}")
    st.info("🔧 این بخش در حال توسعه است.")

def show_assistant_panel(school):
    st.header("📋 پنل معاون")
    st.write(f"مدرسه: {school}")
    st.info("🔧 این بخش در حال توسعه است.")
def show_teacher_panel(username):
    st.header("🎓 پنل آموزگار")
    st.write(f"خوش آمدید، {username}!")

    teacher_action = st.radio("لطفاً انتخاب کنید:", [
        "➕ ثبت دانش‌آموز جدید",
        "📌 ثبت نمره",
        "📊 گزارش عملکرد کلاس",
        "👤 گزارش فردی دانش‌آموز",
        "✏️ ویرایش یا حذف نمره"
    ])

    if teacher_action == "➕ ثبت دانش‌آموز جدید":
        register_student_form(username)

    elif teacher_action == "📌 ثبت نمره":
        show_score_entry_panel(username)

    elif teacher_action == "📊 گزارش عملکرد کلاس":
        show_class_report_panel(username)

    elif teacher_action == "👤 گزارش فردی دانش‌آموز":
        show_individual_report_panel(username)

    elif teacher_action == "✏️ ویرایش یا حذف نمره":
        show_score_edit_panel(username)
def register_student_form(username):
    with st.form("register_student_form"):
        st.subheader("➕ ثبت دانش‌آموز جدید")
        student_name = st.text_input("نام دانش‌آموز")
        student_username = st.text_input("نام کاربری دانش‌آموز")
        student_class = st.text_input("کلاس")
        student_password = st.text_input("رمز ورود دانش‌آموز", type="password")
        register_date = jdatetime.date.today().strftime("%Y/%m/%d")
        submitted = st.form_submit_button("ثبت دانش‌آموز")

        if submitted:
            cursor.execute("""
                INSERT INTO students (آموزگار, نام_دانش‌آموز, نام_کاربری, رمز_دانش‌آموز, کلاس, تاریخ_ثبت)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, student_name, student_username, student_password, student_class, register_date))
            conn.commit()
            st.success(f"✅ دانش‌آموز {student_name} با نام کاربری {student_username} ثبت شد.")
def show_score_entry_panel(username):
    st.subheader("📝 ثبت نمرات جدید")

    lesson = st.text_input("نام درس")
    score_label = st.text_input("شماره یا عنوان نمره (مثلاً نمره اول، آزمون مهر)")
    score_date = jdatetime.date.today().strftime("%Y/%m/%d")

    student_df = pd.read_sql_query("SELECT * FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    st.markdown("👧 لیست دانش‌آموزان برای ثبت نمره:")
    score_inputs = {}

    for i, row in student_df.iterrows():
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"{row['نام_دانش‌آموز']} - کلاس {row['کلاس']}")
        with col2:
            score_inputs[row["نام_دانش‌آموز"]] = st.number_input(
                f"نمره {row['نام_دانش‌آموز']}", min_value=0, max_value=20, step=1, key=f"score_{i}"
            )

    if st.button("ثبت همه نمرات"):
        for student_name, score in score_inputs.items():
            cursor.execute("""
                INSERT INTO scores (آموزگار, نام_دانش‌آموز, درس, نمره_شماره, نمره, تاریخ)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, student_name, lesson, score_label, score, score_date))
        conn.commit()
        st.success("✅ همه نمرات با موفقیت ثبت شدند.")
def show_class_report_panel(username):
    st.subheader("📊 گزارش عملکرد کلاس")

    report_df = pd.read_sql_query("""
        SELECT نام_دانش‌آموز, درس, AVG(نمره) as میانگین
        FROM scores
        WHERE آموزگار = ?
        GROUP BY نام_دانش‌آموز, درس
    """, conn, params=(username,))

    if report_df.empty:
        st.info("هنوز نمره‌ای ثبت نشده است.")
    else:
        st.dataframe(report_df)
        avg_df = report_df.groupby("نام_دانش‌آموز")["میانگین"].mean().reset_index()
        st.bar_chart(avg_df.set_index("نام_دانش‌آموز"))
def show_individual_report_panel(username):
    st.subheader("👤 گزارش فردی دانش‌آموز")

    student_df = pd.read_sql_query("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique())
    lessons_df = pd.read_sql_query("SELECT DISTINCT درس FROM scores WHERE نام_دانش‌آموز = ?", conn, params=(student_name,))
    if lessons_df.empty:
        st.info("برای این دانش‌آموز هنوز نمره‌ای ثبت نشده.")
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
def show_score_edit_panel(username):
    st.subheader("✏️ ویرایش یا حذف نمره")

    df = pd.read_sql_query("SELECT rowid, * FROM scores WHERE آموزگار = ?", conn, params=(username,))
    if df.empty:
        st.info("هیچ نمره‌ای برای ویرایش یا حذف وجود ندارد.")
        return

    selected_row = st.selectbox("انتخاب ردیف:", df.index)
    selected_score = df.loc[selected_row]

    st.write(f"دانش‌آموز: {selected_score['نام_دانش‌آموز']}")
    st.write(f"درس: {selected_score['درس']}")
    st.write(f"شماره نمره: {selected_score['نمره_شماره']}")
    st.write(f"نمره فعلی: {selected_score['نمره']}")

    new_score = st.number_input("نمره جدید:", value=selected_score["نمره"], min_value=0, max_value=20)
    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ ویرایش نمره"):
            cursor.execute("UPDATE scores SET نمره = ? WHERE rowid = ?", (new_score, selected_score["rowid"]))
            conn.commit()
            st.success("نمره با موفقیت ویرایش شد.")
with col2:  # فرم ورود
   if not st.session_state.logged_in:
    st.subheader("🔐 ورود به سامانه")

    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")
    login_btn = st.button("ورود")

    if login_btn:
        # بررسی کاربران رسمی
        user_df = pd.read_sql_query("SELECT * FROM users", conn)
        user_row = user_df[
            (user_df["نام_کاربر"] == username) &
            (user_df["رمز_عبور"] == password)
        ]

        # بررسی دانش‌آموزان
        student_df = pd.read_sql_query("SELECT * FROM students", conn)
        if "نام_کاربری" in student_df.columns:
            student_row = student_df[
                (student_df["نام_کاربری"] == username) &
                (student_df["رمز_دانش‌آموز"] == password)
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
                st.session_state.username = username
                st.session_state.role = roles[0] if len(roles) == 1 else st.radio("🎭 انتخاب نقش:", roles)
                st.session_state.school = school
                st.success("✅ ورود موفقیت‌آمیز")

        elif not student_row.empty:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = "دانش‌آموز"
            st.session_state.school = ""
            st.success("✅ ورود دانش‌آموز موفقیت‌آمیز")

        else:
            st.error("❌ نام کاربری یا رمز اشتباه است.")

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

    # دکمه خروج
    if st.button("🚪 خروج از سامانه"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.school = ""
        st.experimental_rerun()

        if st.button("🗑 حذف نمره"):
            cursor.execute("DELETE FROM scores WHERE rowid = ?", (selected_score["rowid"],))
            conn.commit()
            st.warning("نمره حذف شد.")


