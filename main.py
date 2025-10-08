# main.py
import os
from datetime import datetime
import sqlite3

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from fpdf import FPDF
import jdatetime

# -------------------------
# تنظیمات صفحه
# -------------------------
st.set_page_config(page_title="سامانه نمرات", layout="wide")
# سبک ساده با Markdown برای هِدر
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:12px">
      <h1 style="margin:0">🎓 سامانه مدیریت نمرات</h1>
      <div style="color:gray">نسخه اصلاح‌شده و مرتب</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# مسیر دیتابیس و اتصال
# -------------------------
DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "school.db")
os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()


# -------------------------
# توابع کمکی پایگاه‌داده
# -------------------------
def init_database():
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            نام_کاربر TEXT PRIMARY KEY,
            رمز_عبور TEXT,
            نقش TEXT,
            مدرسه TEXT,
            وضعیت TEXT,
            تاریخ_انقضا TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            آموزگار TEXT,
            نام_دانش‌آموز TEXT,
            نام_کاربری TEXT,
            رمز_دانش‌آموز TEXT,
            کلاس TEXT,
            تاریخ_ثبت TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            آموزگار TEXT,
            نام_دانش‌آموز TEXT,
            درس TEXT,
            نمره_شماره TEXT,
            نمره INTEGER,
            تاریخ TEXT
        )
        """
    )
    conn.commit()

    # درج کاربر admin اگر وجود ندارد
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("admin", "1234", "مدیر سامانه", "مدرسه نمونه", "فعال", "2099/12/31"),
    )
    conn.commit()


# -------------------------
# منطق وضعیت نمره و متن وضعیت
# -------------------------
def وضعیت_نمره‌ای(student_avg, class_avg):
    try:
        if student_avg < class_avg * 0.6:
            return 1  # نیاز به تلاش بیشتر
        elif student_avg < class_avg * 0.85:
            return 2  # قابل قبول
        elif student_avg < class_avg * 1.15:
            return 3  # خوب
        else:
            return 4  # خیلی خوب
    except Exception:
        return 0


def متن_وضعیت(status_num):
    وضعیت‌ها = {
        1: "نیاز به تلاش بیشتر",
        2: "قابل قبول",
        3: "خوب",
        4: "خیلی خوب",
    }
    return وضعیت‌ها.get(status_num, "نامشخص")


# -------------------------
# توابع نمایش پنل‌ها و امکانات
# توجه: همه توابع قبل از استفاده تعریف شدند
# -------------------------

# ----- پنل مدیر سامانه -----
def show_superadmin_panel():
    st.header("🛠 پنل مدیر سامانه")
    st.write("این بخش برای مدیریت کاربران سامانه است.")

    with st.expander("➕ ثبت کاربر جدید"):
        with st.form("register_user_form"):
            username = st.text_input("نام کاربری", key="reg_username")
            password = st.text_input("رمز عبور", type="password", key="reg_password")
            school = st.text_input("نام مدرسه", key="reg_school")
            role = st.selectbox(
                "نقش کاربر", ["آموزگار", "معاون", "مدیر مدرسه", "مدیر سامانه"], key="reg_role"
            )
            expiry_date = st.date_input("تاریخ انقضا", key="reg_expiry")
            submitted = st.form_submit_button("ثبت کاربر")

            if submitted:
                if not username or not password:
                    st.error("نام کاربری و رمز عبور را وارد کنید.")
                else:
                    expiry_str = expiry_date.strftime("%Y/%m/%d")
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO users
                        (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
                        VALUES (?, ?, ?, ?, 'فعال', ?)
                        """,
                        (username, password, role, school, expiry_str),
                    )
                    conn.commit()
                    st.success(f"✅ کاربر {username} با نقش {role} ثبت شد.")

    st.markdown("---")
    st.subheader("🧑‍🏫 مدیریت کاربران ثبت‌شده")
    df = pd.read_sql_query("SELECT * FROM users", conn)
    st.dataframe(df)

    if not df.empty:
        selected_user = st.selectbox("انتخاب کاربر برای ویرایش یا حذف", df["نام_کاربر"], key="sel_user")
        user_row = df[df["نام_کاربر"] == selected_user].iloc[0]

        new_password = st.text_input("رمز جدید", value=user_row["رمز_عبور"], key="edit_pwd")
        roles_list = ["آموزگار", "معاون", "مدیر مدرسه", "مدیر سامانه"]
        new_role = st.selectbox("نقش جدید", roles_list, index=roles_list.index(user_row["نقش"]), key="edit_role")
        new_school = st.text_input("مدرسه جدید", value=user_row["مدرسه"], key="edit_school")
        new_status = st.radio("وضعیت جدید", ["فعال", "مسدود"], index=["فعال", "مسدود"].index(user_row["وضعیت"]), key="edit_status")
        try:
            new_expiry = st.date_input("تاریخ جدید انقضا", value=datetime.strptime(user_row["تاریخ_انقضا"], "%Y/%m/%d"), key="edit_expiry")
        except Exception:
            new_expiry = st.date_input("تاریخ جدید انقضا", key="edit_expiry_fallback")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 ثبت تغییرات", key="save_user_changes"):
                expiry_str = new_expiry.strftime("%Y/%m/%d")
                cursor.execute(
                    """
                    UPDATE users
                    SET رمز_عبور = ?, نقش = ?, مدرسه = ?, وضعیت = ?, تاریخ_انقضا = ?
                    WHERE نام_کاربر = ?
                    """,
                    (new_password, new_role, new_school, new_status, expiry_str, selected_user),
                )
                conn.commit()
                st.success("✅ اطلاعات کاربر به‌روزرسانی شد.")
                st.experimental_rerun()

        with col2:
            if st.button("🗑 حذف کاربر", key="delete_user_btn"):
                cursor.execute("DELETE FROM users WHERE نام_کاربر = ?", (selected_user,))
                conn.commit()
                st.warning(f"❌ کاربر {selected_user} حذف شد.")
                st.experimental_rerun()

    st.markdown("---")
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


# ----- پنل آموزگار -----
def register_student_form(username):
    st.subheader("➕ ثبت دانش‌آموز جدید")
    name = st.text_input("نام دانش‌آموز", key=f"std_name_{username}")
    username_std = st.text_input("نام کاربری دانش‌آموز", key=f"std_user_{username}")
    password_std = st.text_input("رمز دانش‌آموز", type="password", key=f"std_pwd_{username}")
    class_name = st.text_input("کلاس", key=f"std_class_{username}")
    if st.button("ثبت", key=f"register_student_{username}"):
        if not name or not username_std:
            st.error("نام و نام کاربری دانش‌آموز را وارد کنید.")
            return
        today = datetime.today().strftime("%Y/%m/%d")
        cursor.execute(
            """
            INSERT INTO students (آموزگار, نام_دانش‌آموز, نام_کاربری, رمز_دانش‌آموز, کلاس, تاریخ_ثبت)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, name, username_std, password_std, class_name, today),
        )
        conn.commit()
        st.success("✅ دانش‌آموز با موفقیت ثبت شد.")


def show_score_entry_panel(username):
    st.subheader("📌 ثبت نمره")
    student_df = pd.read_sql_query("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique(), key=f"score_student_{username}")
    lesson = st.text_input("نام درس", key=f"score_lesson_{username}")
    score_number = st.text_input("شماره نمره (مثلاً نمره اول، دوم...)", key=f"score_num_{username}")
    score_value = st.number_input("نمره", min_value=0, max_value=20, step=1, key=f"score_value_{username}")
    if st.button("ثبت نمره", key=f"submit_score_{username}"):
        if not lesson or not score_number:
            st.error("نام درس و شماره نمره را وارد کنید.")
            return
        today = datetime.today().strftime("%Y/%m/%d")
        cursor.execute(
            """
            INSERT INTO scores (آموزگار, نام_دانش‌آموز, درس, نمره_شماره, نمره, تاریخ)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, student_name, lesson, score_number, score_value, today),
        )
        conn.commit()
        st.success("✅ نمره ثبت شد.")


def show_class_statistics_panel(username):
    st.subheader("📊 آمار کلی کلاس")
    df = pd.read_sql_query("SELECT نام_دانش‌آموز, درس, AVG(نمره) as میانگین_نمره FROM scores WHERE آموزگار = ? GROUP BY نام_دانش‌آموز, درس", conn, params=(username,))
    if df.empty:
        st.info("هیچ نمره‌ای ثبت نشده است.")
        return
    st.dataframe(df)


def draw_pie_chart(student_name):
    df = pd.read_sql_query(
        """
        SELECT درس, AVG(نمره) as میانگین_دانش‌آموز
        FROM scores
        WHERE نام_دانش‌آموز = ?
        GROUP BY درس
        """,
        conn,
        params=(student_name,),
    )

    if df.empty:
        st.info("هیچ نمره‌ای برای رسم نمودار وجود ندارد.")
        return

    # جمع کردن وضعیت‌ها
    status_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for _, row in df.iterrows():
        lesson = row["درس"]
        student_avg = row["میانگین_دانش‌آموز"]
        # واکشی آموزگار برای محاسبه میانگین کلاس
        teacher_row = pd.read_sql_query("SELECT آموزگار FROM students WHERE نام_دانش‌آموز = ?", conn, params=(student_name,))
        if teacher_row.empty:
            continue
        teacher = teacher_row.iloc[0]["آموزگار"]
        class_avg_row = pd.read_sql_query(
            """
            SELECT AVG(نمره) as میانگین_کلاس
            FROM scores
            WHERE آموزگار = ? AND درس = ?
            """,
            conn,
            params=(teacher, lesson),
        )
        class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
        status = وضعیت_نمره‌ای(student_avg, class_avg)
        if status in status_counts:
            status_counts[status] += 1

    labels = ["نیاز به تلاش بیشتر", "قابل قبول", "خوب", "خیلی خوب"]
    sizes = [status_counts[i] for i in range(1, 5)]

    # اگر همه صفر بودند پیغام بده
    if sum(sizes) == 0:
        st.info("داده کافی برای نمودار وجود ندارد.")
        return

    fig, ax = plt.subplots()
    # بدون تعیین رنگ خاص (قابل تنظیم توسط تو) — اما چون درخواست کردی زیباتر کنم، از پالت ساده استفاده می‌کنم
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title("📊 توزیع وضعیت نمرات")
    st.pyplot(fig)


def show_individual_report_panel(username):
    st.subheader("👤 گزارش فردی دانش‌آموز")
    student_df = pd.read_sql_query("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return
    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique(), key=f"ind_rep_{username}")
    draw_pie_chart(student_name)


def download_student_report(username):
    st.subheader("📄 دانلود کارنامه PDF")
    student_df = pd.read_sql_query("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique(), key=f"dl_rep_select_{username}")
    student_info = pd.read_sql_query("SELECT * FROM students WHERE نام_دانش‌آموز = ?", conn, params=(student_name,)).iloc[0]
    student_class = student_info["کلاس"]
    school = pd.read_sql_query("SELECT مدرسه FROM users WHERE نام_کاربر = ?", conn, params=(username,)).iloc[0]["مدرسه"]
    today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")

    df = pd.read_sql_query(
        """
        SELECT درس, AVG(نمره) as میانگین_دانش‌آموز
        FROM scores
        WHERE نام_دانش‌آموز = ?
        GROUP BY درس
        """,
        conn,
        params=(student_name,),
    )

    rows = []
    for _, row in df.iterrows():
        lesson = row["درس"]
        student_avg = row["میانگین_دانش‌آموز"]
        class_avg_row = pd.read_sql_query(
            """
            SELECT AVG(نمره) as میانگین_کلاس
            FROM scores
            WHERE آموزگار = ? AND درس = ?
            """,
            conn,
            params=(username, lesson),
        )
        class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
        status_num = وضعیت_نمره‌ای(student_avg, class_avg)
        status_text = متن_وضعیت(status_num)
        rows.append(
            {
                "درس": lesson,
                "میانگین دانش‌آموز": round(student_avg, 2),
                "میانگین کلاس": round(class_avg, 2),
                "وضعیت": status_text,
            }
        )

    st.markdown(
        f"""
    🏫 مدرسه: {school}  
    👧 دانش‌آموز: {student_name}  
    📚 کلاس: {student_class}  
    📅 تاریخ صدور: {today_shamsi}
    """
    )
    st.table(pd.DataFrame(rows))

    # ساخت PDF
    pdf = FPDF()
    pdf.add_page()
    # اگر فونت Arial نصب نیست، FPDF از فونت پیشفرض استفاده می‌کند
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"کارنامه دانش‌آموز: {student_name}", ln=True, align="C")
    pdf.cell(200, 10, txt=f"تاریخ صدور: {today_shamsi}", ln=True, align="C")
    pdf.ln(10)

    for row in rows:
        pdf.cell(0, 8, txt=f"{row['درس']}: میانگین دانش‌آموز {row['میانگین دانش‌آموز']}، میانگین کلاس {row['میانگین کلاس']}، وضعیت: {row['وضعیت']}", ln=True)

    pdf_output = pdf.output(dest="S").encode("latin1")
    st.download_button(label="📥 دانلود کارنامه PDF", data=pdf_output, file_name=f"report_{student_name}.pdf", mime="application/pdf")


# ----- پنل مدیر مدرسه و معاون -----
def show_teacher_statistics_by_admin(school):
    st.subheader("📈 آمار آموزگاران مدرسه")
    teachers_df = pd.read_sql_query("SELECT نام_کاربر, مدرسه, نقش FROM users WHERE مدرسه = ? AND نقش = 'آموزگار'", conn, params=(school,))
    if teachers_df.empty:
        st.info("هیچ آموزگاری برای این مدرسه ثبت نشده است.")
        return
    st.dataframe(teachers_df)


def show_school_admin_panel(school):
    st.header("🏫 پنل مدیر مدرسه")
    st.write(f"مدرسه: {school}")
    show_teacher_statistics_by_admin(school)


def show_assistant_panel(school):
    st.header("📋 پنل معاون")
    st.write(f"مدرسه: {school}")
    show_teacher_statistics_by_admin(school)


# ----- پنل دانش‌آموز -----
def download_student_report_direct(student_name):
    student_info = pd.read_sql_query("SELECT * FROM students WHERE نام_دانش‌آموز = ?", conn, params=(student_name,))
    if student_info.empty:
        st.error("اطلاعات دانش‌آموز پیدا نشد.")
        return
    student_info = student_info.iloc[0]
    teacher = student_info["آموزگار"]
    student_class = student_info["کلاس"]
    school_row = pd.read_sql_query("SELECT مدرسه FROM users WHERE نام_کاربر = ?", conn, params=(teacher,))
    school = school_row.iloc[0]["مدرسه"] if not school_row.empty else ""
    today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")

    df = pd.read_sql_query(
        """
        SELECT درس, AVG(نمره) as میانگین_دانش‌آموز
        FROM scores
        WHERE نام_دانش‌آموز = ?
        GROUP BY درس
        """,
        conn,
        params=(student_name,),
    )

    rows = []
    for _, row in df.iterrows():
        lesson = row["درس"]
        student_avg = row["میانگین_دانش‌آموز"]
        class_avg_row = pd.read_sql_query(
            """
            SELECT AVG(نمره) as میانگین_کلاس
            FROM scores
            WHERE آموزگار = ? AND درس = ?
            """,
            conn,
            params=(teacher, lesson),
        )
        class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
        status_num = وضعیت_نمره‌ای(student_avg, class_avg)
        status_text = متن_وضعیت(status_num)
        rows.append(
            {
                "درس": lesson,
                "میانگین دانش‌آموز": round(student_avg, 2),
                "میانگین کلاس": round(class_avg, 2),
                "وضعیت": status_text,
            }
        )

    st.table(pd.DataFrame(rows))

    # PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"کارنامه دانش‌آموز: {student_name}", ln=True, align="C")
    pdf.cell(200, 10, txt=f"تاریخ صدور: {today_shamsi}", ln=True, align="C")
    pdf.ln(10)
    for row in rows:
        pdf.cell(0, 8, txt=f"{row['درس']}: میانگین دانش‌آموز {row['میانگین دانش‌آموز']}، میانگین کلاس {row['میانگین کلاس']}، وضعیت: {row['وضعیت']}", ln=True)
    pdf_output = pdf.output(dest="S").encode("latin1")
    st.download_button(label="📥 دانلود کارنامه PDF", data=pdf_output, file_name=f"report_{student_name}.pdf", mime="application/pdf")


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
    else:
        selected_lesson = st.selectbox("انتخاب درس:", lessons_df["درس"].unique(), key=f"stud_lesson_{username}")

        st.markdown("### 📈 نمودار خطی پیشرفت")
        df_line = pd.read_sql_query(
            """
            SELECT نمره_شماره, نمره FROM scores
            WHERE نام_دانش‌آموز = ? AND درس = ?
            ORDER BY نمره_شماره
            """,
            conn,
            params=(student_name, selected_lesson),
        )

        if not df_line.empty:
            fig, ax = plt.subplots()
            ax.plot(df_line["نمره_شماره"], df_line["نمره"], marker="o")
            ax.set_title(f"روند نمرات درس {selected_lesson}")
            ax.set_xlabel("شماره نمره")
            ax.set_ylabel("نمره")
            st.pyplot(fig)
        else:
            st.info("برای این درس هنوز نمره‌ای ثبت نشده است.")

    st.markdown("### 🟢 نمودار دایره‌ای میانگین نمرات")
    draw_pie_chart(student_name)

    st.markdown("### 📄 جدول کارنامه")
    download_student_report_direct(student_name)


# -------------------------
# مقداردهی اولیه و state
# -------------------------
init_database()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "school" not in st.session_state:
    st.session_state.school = ""

# -------------------------
# نوار کناری: نمایش وضعیت کاربر و خروج
# -------------------------
with st.sidebar:
    st.markdown("### وضعیت ورود")
    if st.session_state.logged_in:
        st.write(f"👤 کاربر: **{st.session_state.username}**")
        st.write(f"🔖 نقش: **{st.session_state.role}**")
        st.write(f"🏫 مدرسه: **{st.session_state.school}**")
        if st.button("🚪 خروج"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.session_state.school = ""
            st.experimental_rerun()
    else:
        st.write("شما وارد نشده‌اید.")

# -------------------------
# فرم ورود
# -------------------------
if not st.session_state.logged_in:
    st.subheader("🔐 ورود به سامانه")
    col1, col2 = st.columns([1, 2])
    with col2:
        username_input = st.text_input("نام کاربری", key="login_user")
        password_input = st.text_input("رمز عبور", type="password", key="login_pwd")
        login_btn = st.button("ورود", key="login_btn")

        if login_btn:
            # بررسی کاربران رسمی
            user_df = pd.read_sql_query("SELECT * FROM users", conn)
            user_row = user_df[(user_df["نام_کاربر"] == username_input) & (user_df["رمز_عبور"] == password_input)]

            # بررسی دانش‌آموزان
            student_df = pd.read_sql_query("SELECT * FROM students", conn)
            if "نام_کاربری" in student_df.columns:
                student_row = student_df[(student_df["نام_کاربری"] == username_input) & (student_df["رمز_دانش‌آموز"] == password_input)]
            else:
                student_row = pd.DataFrame()

            if not user_row.empty:
                roles = str(user_row.iloc[0]["نقش"]).split(",")
                status = user_row.iloc[0]["وضعیت"]
                expiry = user_row.iloc[0]["تاریخ_انقضا"]
                school = user_row.iloc[0]["مدرسه"]

                # بررسی وضعیت و انقضا
                if status != "فعال":
                    st.error("⛔️ حساب شما مسدود شده است.")
                else:
                    try:
                        if expiry and datetime.today().date() > datetime.strptime(expiry, "%Y/%m/%d").date():
                            st.error("⛔️ حساب شما منقضی شده است.")
                            raise Exception("expired")
                    except Exception:
                        # اگر فرمت تاریخ مشکل داشت، از ادامه جلوگیری نکن
                        pass

                    # ورود موفق
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    if len(roles) == 1:
                        st.session_state.role = roles[0]
                    else:
                        # اگر نقش چندگانه است، از کاربر انتخاب بگیر
                        st.session_state.role = st.radio("🎭 انتخاب نقش:", roles, key="multi_role_choice")
                    st.session_state.school = school
                    st.success("✅ ورود موفقیت‌آمیز")
                    st.experimental_rerun()

            elif not student_row.empty:
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.role = "دانش‌آموز"
                st.session_state.school = ""
                st.success("✅ ورود دانش‌آموز موفقیت‌آمیز")
                st.experimental_rerun()
            else:
                st.error("❌ نام کاربری یا رمز اشتباه است.")

# -------------------------
# نمایش پنل‌ها بر اساس نقش
# -------------------------
if st.session_state.logged_in:
    role = st.session_state.role
    username = st.session_state.username
    school = st.session_state.school

    # نقشه نقش به پنل‌ها
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
    else:
        st.info("نقش کاربری شناسایی نشد. لطفاً با مدیر سامانه تماس بگیرید.")


# -------------------------
# کمک / نسخه برنامه
# -------------------------
st.markdown("---")
st.caption("نسخه اصلاح‌شده توسط فافو — در صورت نیاز به تغییرات ظاهری بیشتر یا اضافه کردن قابلیت دو‌زبانه، اطلاع بده 😊")
