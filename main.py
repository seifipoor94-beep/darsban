# main_part1.py  -- بخش ۱: واردات، تنظیمات صفحه، دیتابیس، فونت و توابع کمکی عمومی

import os
import sqlite3
from datetime import datetime
import io

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib import font_manager
from fpdf import FPDF
import jdatetime

# -------------------------
# تنظیمات صفحه
# -------------------------
st.set_page_config(page_title="سامانه نمرات", layout="wide")

# -------------------------
# مسیرها و constantes
# -------------------------
DATA_DIR = "data"
FONTS_DIR = "fonts"
DB_PATH = os.path.join(DATA_DIR, "school.db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

# نام پیشنهادی فونت فارسی (اگر فایل ttf در پوشه fonts قرار بگیره)
PREFERRED_FONT_FILENAME = "Vazir.ttf"  # اگر این فایل رو بذاری در fonts/ بهتره
PREFERRED_FONT_FAMILY = "Vazir"  # اسمی که در matplotlib و PDF می‌شناسیم

# -------------------------
# اتصال به دیتابیس
# -------------------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# -------------------------
# توابع: دیتابیس اولیه
# -------------------------
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

    # درج کاربر admin پیش‌فرض
    cursor.execute("""
        INSERT OR IGNORE INTO users
        (نام_کاربر, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("admin", "1234", "مدیر سامانه", "مدرسه نمونه", "فعال", "2099/12/31"))
    conn.commit()

# -------------------------
# تنظیم فونت برای matplotlib و FPDF
# توضیح: اگر فایل فونت (TTF) داخل پوشه fonts/ باشه آن را بارگذاری می‌کنیم.
# در غیر اینصورت از فونت پیشفرض matplotlib استفاده می‌کنیم ولی ممکنه فونت فارسی درست نشان داده نشود.
# -------------------------
def register_fonts():
    # مسیر احتمالی فایل فونت
    font_path = os.path.join(FONTS_DIR, PREFERRED_FONT_FILENAME)
    registered = False

    # 1) تلاش برای ثبت فونت برای matplotlib
    try:
        if os.path.isfile(font_path):
            font_manager.fontManager.addfont(font_path)
            plt.rcParams["font.family"] = PREFERRED_FONT_FAMILY
            plt.rcParams["axes.unicode_minus"] = False
            registered = True
        else:
            # جستجوی فونت‌های نصب‌شده برای یک فونت فارسی قابل استفاده (DejaVu یا Noto یا Vazir)
            sys_fonts = [f.name for f in font_manager.fontManager.ttflist]
            for candidate in ["DejaVu Sans", "Noto Sans", "Vazir", "IRANSans", "Tahoma"]:
                if candidate in sys_fonts:
                    plt.rcParams["font.family"] = candidate
                    plt.rcParams["axes.unicode_minus"] = False
                    registered = True
                    break
    except Exception:
        # اگر هر مشکلی پیش آمد، به فونت پیشفرض برمی‌گردیم
        registered = False

    # 2) تنظیم فونت برای FPDF (برای تولید PDF فارسی)
    # fpdf (pyFPDF) نیاز به add_font با uni=True دارد تا متن‌های یونیکد (مثل فارسی) کار کنند.
    pdf_font_registered = False
    try:
        if os.path.isfile(font_path):
            # در صورتی که فایل فونت وجود دارد، آن را به fpdf اضافه می‌کنیم
            # توجه: در بعضی ورژن‌ها نام سبک باید '' یا 'B' یا 'I' و غیره باشد؛ ما سبک '' را اضافه می‌کنیم.
            FPDF.add_font(FPDF, PREFERRED_FONT_FAMILY, "", font_path, uni=True)
            pdf_font_registered = True
        else:
            # تلاش برای استفاده از DejaVuSans (اگر نصب شده در سیستم)
            # مسیرهای معمول برای DejaVu
            common_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            ]
            for p in common_paths:
                if os.path.isfile(p):
                    FPDF.add_font(FPDF, "DejaVuSans", "", p, uni=True)
                    pdf_font_registered = True
                    break
    except Exception:
        pdf_font_registered = False

    return registered, pdf_font_registered, font_path

# اجرا و اطلاعات ثبت فونت
_fonts_ok_matplotlib, _fonts_ok_pdf, _font_path_used = register_fonts()

# -------------------------
# توابع کمکی وضعیت و متن
# -------------------------
def وضعیت_نمره‌ای(student_avg, class_avg):
    try:
        if student_avg < class_avg * 0.6:
            return 1
        elif student_avg < class_avg * 0.85:
            return 2
        elif student_avg < class_avg * 1.15:
            return 3
        else:
            return 4
    except Exception:
        return 0

def متن_وضعیت(status_num):
    وضعیت‌ها = {
        1: "نیاز به تلاش بیشتر",
        2: "قابل قبول",
        3: "خوب",
        4: "خیلی خوب"
    }
    return وضعیت‌ها.get(status_num, "نامشخص")

# -------------------------
# تابع کمکی برای تولید PDF با پشتیبانی از فونت فارسی
# خروجی: بایت‌های PDF (bytes) که می‌توانند توسط st.download_button ارائه شوند.
# -------------------------
def build_student_report_pdf(student_name, rows, school="", student_class="", issuer_date_str=None):
    """
    student_name: str
    rows: list of dicts with keys: 'درس', 'میانگین دانش‌آموز', 'میانگین کلاس', 'وضعیت'
    school, student_class: strings
    issuer_date_str: str تاریخ به شمسی (مثلاً jdatetime.date.today().strftime("%Y/%m/%d"))
    """
    if issuer_date_str is None:
        issuer_date_str = jdatetime.date.today().strftime("%Y/%m/%d")

    pdf = FPDF()
    pdf.add_page()

    # تلاش برای استفاده از فونت فارسی ثبت‌شده
    try:
        if os.path.isfile(_font_path_used):
            # اگر فونت Vazir ثبت شده، از آن استفاده کن
            pdf.set_font(_fonts_ok_pdf and PREFERRED_FONT_FAMILY or "Arial", size=12)
        else:
            # اگر فونتی ثبت نشده، تلاش برای DejaVuSans یا fallback به Arial
            if _fonts_ok_pdf:
                pdf.set_font("DejaVuSans", size=12)
            else:
                pdf.set_font("Arial", size=12)
    except Exception:
        pdf.set_font("Arial", size=12)

    # عنوان و اطلاعات پایه
    pdf.cell(0, 8, txt=f"کارنامه دانش‌آموز: {student_name}", ln=True, align="C")
    pdf.cell(0, 8, txt=f"تاریخ صدور: {issuer_date_str}", ln=True, align="C")
    pdf.ln(4)
    if school:
        pdf.cell(0, 6, txt=f"مدرسه: {school}", ln=True)
    if student_class:
        pdf.cell(0, 6, txt=f"کلاس: {student_class}", ln=True)
    pdf.ln(4)

    # جدول خلاصه
    for row in rows:
        lesson = str(row.get("درس", ""))
        s_avg = str(row.get("میانگین دانش‌آموز", ""))
        c_avg = str(row.get("میانگین کلاس", ""))
        status = str(row.get("وضعیت", ""))
        line = f"{lesson}: میانگین دانش‌آموز {s_avg}، میانگین کلاس {c_avg}، وضعیت: {status}"
        pdf.multi_cell(0, 7, txt=line)

    # خروجی بایت‌ها
    try:
        pdf_bytes = pdf.output(dest="S").encode("latin1")
    except Exception:
        # اگر encoding لاتین مشکل داشت (برای فارسی)، از بایت خام خروجی استفاده می‌کنیم (py3k)
        try:
            pdf_bytes = pdf.output(dest="S").encode("utf-8", errors="ignore")
        except Exception:
            # آخرین حربه: خروجی بدون encode (ممکنه نوع str باشد)، آن را به bytes تبدیل می‌کنیم
            out = pdf.output(dest="S")
            if isinstance(out, bytes):
                pdf_bytes = out
            else:
                pdf_bytes = out.encode("latin1", errors="ignore")
    return pdf_bytes

# -------------------------
# مقداردهی اولیه دیتابیس
# -------------------------
init_database()
# ------------------------------
# بخش ۲: پنل آموزگار — ثبت/ویرایش دانش‌آموز، ثبت/ویرایش نمرات، نمودارها، رتبه‌بندی
# ------------------------------

# ثبت دانش‌آموز جدید (قابل استفاده در پنل آموزگار)
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
        cursor.execute("""
            INSERT INTO students (آموزگار, نام_دانش‌آموز, نام_کاربری, رمز_دانش‌آموز, کلاس, تاریخ_ثبت)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, name, username_std, password_std, class_name, today))
        conn.commit()
        st.success("✅ دانش‌آموز با موفقیت ثبت شد.")
        st.rerun()

# ویرایش یا حذف دانش‌آموزان (برای آموزگار)
def edit_or_delete_student(username):
    st.subheader("✏️ ویرایش / حذف دانش‌آموز")
    students_df = pd.read_sql_query("SELECT * FROM students WHERE آموزگار = ?", conn, params=(username,))
    if students_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    selected = st.selectbox("انتخاب دانش‌آموز برای ویرایش:", students_df["نام_دانش‌آموز"].unique(), key=f"edit_std_select_{username}")
    row = students_df[students_df["نام_دانش‌آموز"] == selected].iloc[0]

    new_name = st.text_input("نام دانش‌آموز", value=row["نام_دانش‌آموز"], key=f"edit_name_{username}")
    new_username = st.text_input("نام کاربری دانش‌آموز", value=row["نام_کاربری"], key=f"edit_usr_{username}")
    new_pwd = st.text_input("رمز دانش‌آموز", value=row["رمز_دانش‌آموز"], key=f"edit_pwd_std_{username}")
    new_class = st.text_input("کلاس", value=row["کلاس"], key=f"edit_class_{username}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 ذخیره تغییرات دانش‌آموز", key=f"save_std_{username}"):
            cursor.execute("""
                UPDATE students
                SET نام_دانش‌آموز = ?, نام_کاربری = ?, رمز_دانش‌آموز = ?, کلاس = ?
                WHERE id = ?
            """, (new_name, new_username, new_pwd, new_class, row["id"]))
            conn.commit()
            st.success("✅ اطلاعات دانش‌آموز به‌روزرسانی شد.")
            st.rerun()
    with col2:
        if st.button("🗑 حذف دانش‌آموز", key=f"del_std_{username}"):
            # حذف همه نمرات مرتبط نیز
            cursor.execute("DELETE FROM scores WHERE نام_دانش‌آموز = ?", (row["نام_دانش‌آموز"],))
            cursor.execute("DELETE FROM students WHERE id = ?", (row["id"],))
            conn.commit()
            st.warning("❌ دانش‌آموز و نمرات مربوطه حذف شدند.")
            st.rerun()

# ثبت نمره (اضافه)
def show_score_entry_panel(username):
    st.subheader("📌 ثبت نمره جدید")
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
        cursor.execute("""
            INSERT INTO scores (آموزگار, نام_دانش‌آموز, درس, نمره_شماره, نمره, تاریخ)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, student_name, lesson, score_number, score_value, today))
        conn.commit()
        st.success("✅ نمره ثبت شد.")
        st.rerun()

# ویرایش یا حذف نمرات ثبت‌شده برای یک دانش‌آموز (پنل آموزگار)
def edit_scores_for_student(username):
    st.subheader("✏️ ویرایش / حذف نمرات دانش‌آموز")
    student_df = pd.read_sql_query("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique(), key=f"edit_score_student_{username}")
    scores_df = pd.read_sql_query("SELECT * FROM scores WHERE نام_دانش‌آموز = ? AND آموزگار = ?", conn, params=(student_name, username))
    if scores_df.empty:
        st.info("برای این دانش‌آموز هنوز نمره‌ای ثبت نشده است.")
        return

    # نمایش جدول نمرات
    st.markdown("### فهرست نمرات")
    st.dataframe(scores_df[["id", "درس", "نمره_شماره", "نمره", "تاریخ"]].set_index("id"))

    selected_id = st.selectbox("انتخاب ردیف (id) برای ویرایش/حذف:", scores_df["id"].tolist(), key=f"sel_score_id_{username}")
    sel_row = scores_df[scores_df["id"] == selected_id].iloc[0]

    new_lesson = st.text_input("درس", value=sel_row["درس"], key=f"edit_score_lesson_{username}")
    new_num = st.text_input("شماره نمره", value=sel_row["نمره_شماره"], key=f"edit_score_num_{username}")
    new_val = st.number_input("نمره", min_value=0, max_value=20, value=int(sel_row["نمره"]), key=f"edit_score_val_{username}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 ذخیره تغییرات نمره", key=f"save_score_{username}"):
            cursor.execute("""
                UPDATE scores
                SET درس = ?, نمره_شماره = ?, نمره = ?
                WHERE id = ?
            """, (new_lesson, new_num, new_val, selected_id))
            conn.commit()
            st.success("✅ نمره به‌روزرسانی شد.")
            st.rerun()
    with col2:
        if st.button("🗑 حذف نمره", key=f"del_score_{username}"):
            cursor.execute("DELETE FROM scores WHERE id = ?", (selected_id,))
            conn.commit()
            st.warning("❌ نمره حذف شد.")
            st.rerun()

# نمودار خطی پیشرفت برای یک دانش‌آموز و درس مشخص
def show_student_line_chart(student_name, lesson):
    df_line = pd.read_sql_query("""
        SELECT id, نمره_شماره, نمره FROM scores
        WHERE نام_دانش‌آموز = ? AND درس = ?
        ORDER BY id
    """, conn, params=(student_name, lesson))

    if df_line.empty:
        st.info("برای این درس هنوز نمره‌ای ثبت نشده است.")
        return

    # رسم نمودار خطی
    fig, ax = plt.subplots(figsize=(6, 3))
    # x labels = نمره_شماره (متن) ; y = نمره
    ax.plot(df_line["نمره_شماره"], df_line["نمره"], marker="o", linewidth=2)
    ax.set_title(f"روند نمرات {student_name} - درس {lesson}")
    ax.set_xlabel("شماره نمره")
    ax.set_ylabel("نمره")
    # برای راست‌چین شدن جهت زمان/شماره، محور x را معکوس می‌کنیم تا نمودار از راست به چپ باشد
    try:
        ax.invert_xaxis()
    except Exception:
        pass
    plt.tight_layout()
    st.pyplot(fig)

# رسم نمودار دایره‌ای وضعیت کلی (کلاسی یا برای یک درس خاص)
def draw_class_pie_chart(teacher, selected_lesson=None):
    # اگر درس مشخص نشده، برای هر درس میانگین دانش‌آموز را محاسبه و وضعیت کلی (تعداد درس‌ها در هر وضعیت) را جمع می‌کنیم
    if selected_lesson:
        df = pd.read_sql_query("""
            SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_درس
            FROM scores
            WHERE آموزگار = ? AND درس = ?
            GROUP BY نام_دانش‌آموز
        """, conn, params=(teacher, selected_lesson))
    else:
        df = pd.read_sql_query("""
            SELECT نام_دانش‌آموز, درس, AVG(نمره) as میانگین_دانش‌آموز
            FROM scores
            WHERE آموزگار = ?
            GROUP BY نام_دانش‌آموز, درس
        """, conn, params=(teacher,))

    if df.empty:
        st.info("اطلاعات نمرات موجود نیست.")
        return

    # اگر selected_lesson نیست، باید ابتدا میانگین هر دانش‌آموز در همه دروس را حساب کنیم
    if selected_lesson:
        # برای هر دانش‌آموز وضعیت تعیین کن
        status_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for _, row in df.iterrows():
            student_avg = row["میانگین_درس"]
            # برای محاسبه میانگین کلاس روی آن درس
            class_avg_row = pd.read_sql_query("""
                SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?
            """, conn, params=(teacher, selected_lesson))
            class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
            status = وضعیت_نمره‌ای(student_avg, class_avg)
            if status in status_counts:
                status_counts[status] += 1
    else:
        # df شامل ردیف به ردیف (هر دانش‌آموز-درس). ابتدا میانگین دانش‌آموز در همه دروس را محاسبه می‌کنیم
        grouped = df.groupby("نام_دانش‌آموز")["میانگین_دانش‌آموز"].mean().reset_index()
        status_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for _, row in grouped.iterrows():
            student_avg = row["میانگین_دانش‌آموز"]
            # میانگین کلی کلاس (میانگین همه نمرات برای آموزگار)
            class_avg_row = pd.read_sql_query("""
                SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ?
            """, conn, params=(teacher,))
            class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
            status = وضعیت_نمره‌ای(student_avg, class_avg)
            if status in status_counts:
                status_counts[status] += 1

    labels = ["نیاز به تلاش بیشتر", "قابل قبول", "خوب", "خیلی خوب"]
    sizes = [status_counts[i] for i in range(1, 5)]
    if sum(sizes) == 0:
        st.info("داده کافی برای نمودار وجود ندارد.")
        return

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title("توزیع وضعیت کلاس")
    st.pyplot(fig)

# آمار کلی کلاس با انتخاب درس (برای آموزگار)
def show_class_statistics_panel(username):
    st.subheader("📊 آمار کلی کلاس")
    # امکان انتخاب درس برای فیلتر
    lessons = pd.read_sql_query("SELECT DISTINCT درس FROM scores WHERE آموزگار = ?", conn, params=(username,))
    lesson_options = ["همه دروس"] + lessons["درس"].tolist() if not lessons.empty else ["همه دروس"]
    selected_lesson = st.selectbox("انتخاب درس برای نمایش آمار:", lesson_options, key=f"class_stats_lesson_{username}")

    if selected_lesson == "همه دروس":
        df = pd.read_sql_query("""
            SELECT نام_دانش‌آموز, درس, AVG(نمره) as میانگین_نمره
            FROM scores
            WHERE آموزگار = ?
            GROUP BY نام_دانش‌آموز, درس
        """, conn, params=(username,))
    else:
        df = pd.read_sql_query("""
            SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_درس
            FROM scores
            WHERE آموزگار = ? AND درس = ?
            GROUP BY نام_دانش‌آموز
        """, conn, params=(username, selected_lesson))

    if df.empty:
        st.info("هیچ نمره‌ای ثبت نشده است.")
    else:
        st.dataframe(df)

    # نمودار دایره‌ای وضعیت کل کلاس (براساس انتخاب درس یا همه دروس)
    if selected_lesson == "همه دروس":
        draw_class_pie_chart(username, selected_lesson=None)
    else:
        draw_class_pie_chart(username, selected_lesson=selected_lesson)

# رتبه‌بندی کلی کلاس و رتبه‌بندی در هر درس (برای آموزگار/مدیر/معاون)
def show_class_ranking_panel(username_or_school_admin, role="آموزگار"):
    """
    اگر role == 'آموزگار' آنگاه username_or_school_admin باید نام آموزگار باشه،
    اگر role در ['مدیر مدرسه','معاون'] آنگاه username_or_school_admin باید نام مدرسه باشد.
    """
    st.subheader("🏅 رتبه‌بندی کلاس")
    if role in ["مدیر مدرسه", "معاون"]:
        teachers_df = pd.read_sql_query("SELECT نام_کاربر FROM users WHERE نقش = 'آموزگار' AND مدرسه = ?", conn, params=(username_or_school_admin,))
        if teachers_df.empty:
            st.info("هیچ آموزگاری برای این مدرسه ثبت نشده است.")
            return
        selected_teacher = st.selectbox("انتخاب آموزگار:", teachers_df["نام_کاربر"].unique(), key=f"rank_select_teacher_{username_or_school_admin}")
    else:
        selected_teacher = username_or_school_admin

    lessons_df = pd.read_sql_query("SELECT DISTINCT درس FROM scores WHERE آموزگار = ?", conn, params=(selected_teacher,))
    lesson_options = ["کل دروس"] + lessons_df["درس"].tolist() if not lessons_df.empty else ["کل دروس"]
    selected_lesson = st.selectbox("انتخاب درس برای رتبه‌بندی:", lesson_options, key=f"rank_lesson_{selected_teacher}")

    if selected_lesson == "کل دروس":
        total_df = pd.read_sql_query("""
            SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_کل
            FROM scores
            WHERE آموزگار = ?
            GROUP BY نام_دانش‌آموز
            ORDER BY میانگین_کل DESC
        """, conn, params=(selected_teacher,))
        st.markdown("### 📊 رتبه‌بندی کلی کلاس")
        st.dataframe(total_df)
    else:
        lesson_df = pd.read_sql_query("""
            SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_درس
            FROM scores
            WHERE آموزگار = ? AND درس = ?
            GROUP BY نام_دانش‌آموز
            ORDER BY میانگین_درس DESC
        """, conn, params=(selected_teacher, selected_lesson))
        st.markdown(f"### 📘 رتبه‌بندی درس {selected_lesson}")
        st.dataframe(lesson_df)

# نمایش گزارش فردی دانش‌آموز (برای آموزگار) — شامل نمودار خطی برای درس انتخابی
def show_individual_report_panel(username):
    st.subheader("👤 گزارش فردی دانش‌آموز")
    student_df = pd.read_sql_query("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", conn, params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return
    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique(), key=f"ind_rep_{username}")

    # انتخاب درس خاص برای نمایش نمودار خطی
    lessons_df = pd.read_sql_query("SELECT DISTINCT درس FROM scores WHERE نام_دانش‌آموز = ? AND آموزگار = ?", conn, params=(student_name, username))
    if lessons_df.empty:
        st.info("برای این دانش‌آموز هنوز نمره‌ای ثبت نشده است.")
        return
    lesson_choice = st.selectbox("انتخاب درس برای نمایش نمودار:", lessons_df["درس"].unique(), key=f"ind_less_{username}_{student_name}")

    # نمایش نمودار خطی
    show_student_line_chart(student_name, lesson_choice)

    # همچنین نمایش نمودار دایره‌ای وضعیت آن دانش‌آموز (خلاصه)
    # ساختار برای یک دانش‌آموز: میانگین هر درس -> سپس تعیین وضعیت نسبت به میانگین کلاس آن درس
    df = pd.read_sql_query("""
        SELECT درس, AVG(نمره) as میانگین_دانش‌آموز
        FROM scores
        WHERE نام_دانش‌آموز = ?
        GROUP BY درس
    """, conn, params=(student_name,))
    if not df.empty:
        rows = []
        for _, row in df.iterrows():
            lesson = row["درس"]
            student_avg = row["میانگین_دانش‌آموز"]
            class_avg_row = pd.read_sql_query("""
                SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?
            """, conn, params=(username, lesson))
            class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
            status_num = وضعیت_نمره‌ای(student_avg, class_avg)
            status_text = متن_وضعیت(status_num)
            rows.append({"درس": lesson, "میانگین دانش‌آموز": round(student_avg,2), "میانگین کلاس": round(class_avg,2), "وضعیت": status_text})
        st.markdown("### 📄 جدول خلاصه نمرات")
        st.table(pd.DataFrame(rows))
# ------------------------------
# بخش ۳: پنل مدیر مدرسه، معاون، و دانش‌آموز + دانلود PDF
# ------------------------------

# دانلود PDF کارنامه برای آموزگار
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
        class_avg_row = pd.read_sql_query("""
            SELECT AVG(نمره) as میانگین_کلاس
            FROM scores
            WHERE آموزگار = ? AND درس = ?
        """, conn, params=(username, lesson))
        class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
        status_num = وضعیت_نمره‌ای(student_avg, class_avg)
        status_text = متن_وضعیت(status_num)
        rows.append({
            "درس": lesson,
            "میانگین دانش‌آموز": round(student_avg, 2),
            "میانگین کلاس": round(class_avg, 2),
            "وضعیت": status_text
        })

    st.markdown(
        f"""
        🏫 مدرسه: {school}  
        👧 دانش‌آموز: {student_name}  
        📚 کلاس: {student_class}  
        📅 تاریخ صدور: {today_shamsi}
        """
    )
    st.table(pd.DataFrame(rows))

    pdf_bytes = build_student_report_pdf(student_name, rows, school, student_class, today_shamsi)
    st.download_button(label="📥 دانلود کارنامه PDF", data=pdf_bytes, file_name=f"report_{student_name}.pdf", mime="application/pdf")

# ------------------------------
# پنل مدیر مدرسه
# ------------------------------
def show_school_admin_panel(school):
    st.header("🏫 پنل مدیر مدرسه")
    st.write(f"مدرسه: {school}")

    # آمار آموزگاران مدرسه
    st.markdown("### 📋 فهرست آموزگاران")
    teachers_df = pd.read_sql_query("SELECT نام_کاربر, نقش FROM users WHERE مدرسه = ? AND نقش = 'آموزگار'", conn, params=(school,))
    st.dataframe(teachers_df)

    st.markdown("### 📊 آمار و رتبه‌بندی")
    show_class_ranking_panel(school, role="مدیر مدرسه")

# ------------------------------
# پنل معاون
# ------------------------------
def show_assistant_panel(school):
    st.header("📚 پنل معاون")
    st.write(f"مدرسه: {school}")
    show_class_ranking_panel(school, role="معاون")

# ------------------------------
# پنل دانش‌آموز
# ------------------------------
def show_student_panel(username):
    st.header("👧 پنل دانش‌آموز")
    st.write(f"خوش آمدی، {username}!")

    student_info = pd.read_sql_query("SELECT * FROM students WHERE نام_کاربری = ?", conn, params=(username,))
    if student_info.empty:
        st.error("اطلاعات شما پیدا نشد.")
        return
    student_name = student_info.iloc[0]["نام_دانش‌آموز"]
    student_class = student_info.iloc[0]["کلاس"]
    teacher = student_info.iloc[0]["آموزگار"]

    # درس‌ها
    lessons_df = pd.read_sql_query("SELECT DISTINCT درس FROM scores WHERE نام_دانش‌آموز = ?", conn, params=(student_name,))
    if lessons_df.empty:
        st.info("هنوز نمره‌ای برای شما ثبت نشده است.")
        return

    selected_lesson = st.selectbox("انتخاب درس:", lessons_df["درس"].unique(), key=f"stud_lesson_{username}")

    st.markdown("### 📈 نمودار خطی پیشرفت در این درس")
    df_line = pd.read_sql_query("""
        SELECT نمره_شماره, نمره FROM scores
        WHERE نام_دانش‌آموز = ? AND درس = ?
        ORDER BY id
    """, conn, params=(student_name, selected_lesson))
    if not df_line.empty:
        fig, ax = plt.subplots()
        ax.plot(df_line["نمره_شماره"], df_line["نمره"], marker="o", linewidth=2)
        ax.set_title(f"روند نمرات درس {selected_lesson}")
        ax.set_xlabel("شماره نمره")
        ax.set_ylabel("نمره")
        try:
            ax.invert_xaxis()
        except Exception:
            pass
        st.pyplot(fig)
    else:
        st.info("برای این درس هنوز نمره‌ای ثبت نشده است.")

    st.markdown("### 🟢 نمودار دایره‌ای میانگین نمرات")
    draw_class_pie_chart(teacher)

    # جدول کارنامه شخصی
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
        class_avg_row = pd.read_sql_query("""
            SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?
        """, conn, params=(teacher, lesson))
        class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
        status_num = وضعیت_نمره‌ای(student_avg, class_avg)
        status_text = متن_وضعیت(status_num)
        rows.append({
            "درس": lesson,
            "میانگین دانش‌آموز": round(student_avg, 2),
            "میانگین کلاس": round(class_avg, 2),
            "وضعیت": status_text
        })

    st.markdown("### 📄 جدول کارنامه")
    st.table(pd.DataFrame(rows))

    pdf_bytes = build_student_report_pdf(student_name, rows, student_class=student_class)
    st.download_button(label="📥 دانلود PDF کارنامه", data=pdf_bytes, file_name=f"student_report_{student_name}.pdf", mime="application/pdf")
# ------------------------------
# بخش ۴ (پایانی): ورود، سشن و نقشه نقش‌ها
# ------------------------------

# مقداردهی اولیه state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "school" not in st.session_state:
    st.session_state.school = ""

# نوار کناری: وضعیت و خروج
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
            st.rerun()
    else:
        st.write("شما وارد نشده‌اید.")

# فرم ورود
if not st.session_state.logged_in:
    st.subheader("🔐 ورود به سامانه")
    col1, col2 = st.columns([1, 2])
    with col2:
        username_input = st.text_input("نام کاربری", key="login_user")
        password_input = st.text_input("رمز عبور", type="password", key="login_pwd")
        login_btn = st.button("ورود", key="login_btn")

        if login_btn:
            # خواندن کاربران و دانش‌آموزان
            user_df = pd.read_sql_query("SELECT * FROM users", conn)
            user_row = user_df[
                (user_df["نام_کاربر"] == username_input) &
                (user_df["رمز_عبور"] == password_input)
            ]

            student_df = pd.read_sql_query("SELECT * FROM students", conn)
            if "نام_کاربری" in student_df.columns:
                student_row = student_df[
                    (student_df["نام_کاربری"] == username_input) &
                    (student_df["رمز_دانش‌آموز"] == password_input)
                ]
            else:
                student_row = pd.DataFrame()

            if not user_row.empty:
                roles = str(user_row.iloc[0]["نقش"]).split(",")
                status = user_row.iloc[0]["وضعیت"]
                expiry = user_row.iloc[0]["تاریخ_انقضا"]
                school = user_row.iloc[0]["مدرسه"]

                if status != "فعال":
                    st.error("⛔️ حساب شما مسدود شده است.")
                else:
                    try:
                        if expiry and datetime.today().date() > datetime.strptime(expiry, "%Y/%m/%d").date():
                            st.error("⛔️ حساب شما منقضی شده است.")
                            raise Exception("expired")
                    except Exception:
                        pass

                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    if len(roles) == 1:
                        st.session_state.role = roles[0]
                    else:
                        st.session_state.role = st.radio("🎭 انتخاب نقش:", roles, key="multi_role_choice")
                    st.session_state.school = school
                    st.success("✅ ورود موفقیت‌آمیز")
                    st.rerun()

            elif not student_row.empty:
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.role = "دانش‌آموز"
                st.session_state.school = ""
                st.success("✅ ورود دانش‌آموز موفقیت‌آمیز")
                st.rerun()
            else:
                st.error("❌ نام کاربری یا رمز اشتباه است.")

# نمایش پنل‌ها بر اساس نقش
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
        # منوی آموزگار (امکانات ثبت/ویرایش دانش‌آموز و نمره و آمار)
        teacher_action = st.radio("لطفاً انتخاب کنید:", [
            "➕ ثبت دانش‌آموز جدید",
            "✏️ ویرایش / حذف اطلاعات دانش‌آموزان",
            "✏️ ویرایش / حذف نمرات دانش‌آموز",
            "📌 ثبت نمره",
            "📊 آمار کلی کلاس",
            "👤 گزارش فردی دانش‌آموز",
            "📄 دانلود کارنامه PDF",
            "🏅 رتبه‌بندی کلاس"
        ], key="teacher_main_menu")
        if teacher_action == "➕ ثبت دانش‌آموز جدید":
            register_student_form(username)
        elif teacher_action == "✏️ ویرایش / حذف اطلاعات دانش‌آموزان":
            edit_or_delete_student(username)
        elif teacher_action == "✏️ ویرایش / حذف نمرات دانش‌آموز":
            edit_scores_for_student(username)
        elif teacher_action == "📌 ثبت نمره":
            show_score_entry_panel(username)
        elif teacher_action == "📊 آمار کلی کلاس":
            show_class_statistics_panel(username)
        elif teacher_action == "👤 گزارش فردی دانش‌آموز":
            show_individual_report_panel(username)
        elif teacher_action == "📄 دانلود کارنامه PDF":
            download_student_report(username)
        elif teacher_action == "🏅 رتبه‌بندی کلاس":
            show_class_ranking_panel(username, role="آموزگار")

    elif role == "دانش‌آموز":
        show_student_panel(username)
    else:
        st.info("نقش کاربری شناسایی نشد. لطفاً با مدیر سامانه تماس بگیرید.")

