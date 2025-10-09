# main_part1.py
# بخش ۱: واردات، تنظیمات صفحه، ثبت فونت (Vazir.ttf)، مسیرها و مقداردهی اولیه دیتابیس


import os
import sqlite3
from datetime import datetime
import io
import traceback

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib import font_manager
from fpdf import FPDF
import jdatetime

# -------------------------
# تنظیم صفحه Streamlit
# -------------------------
st.set_page_config(page_title="سامانه نمرات", layout="wide")
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:12px">
      <h1 style="margin:0">🎓 سامانه مدیریت نمرات</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# مسیرها
# -------------------------
# اگر روی Render/Heroku/... اجرا می‌کنی و متغیر DATA_DIR را تنظیم کردی، از آن استفاده شود.
DATA_DIR = os.environ.get("DATA_DIR", "/tmp/app_data")
os.makedirs(DATA_DIR, exist_ok=True)

FONTS_DIR = os.path.join(os.getcwd(), "fonts")  # انتظار میره Vazir.ttf اینجا باشه
os.makedirs(FONTS_DIR, exist_ok=True)

PREFERRED_FONT_FILENAME = "Vazir.ttf"   # لطفاً این فایل را در پوشه fonts/ قرار بده
PREFERRED_FONT_FAMILY = "Vazir"

# -------------------------
# تابع ثبت و تنظیم فونت برای matplotlib و fpdf
# - اگر Vazir.ttf در fonts/ باشد از آن استفاده می‌کنیم (نمودارها و PDF)
# - در غیر اینصورت سعی می‌کنیم از DejaVuSans یا Noto استفاده کنیم
# -------------------------
def register_fonts_and_configure_matplotlib():
    font_path = os.path.join(FONTS_DIR, PREFERRED_FONT_FILENAME)
    pdf_font_path = None
    matplotlib_ok = False

    # تلاش برای ثبت فونت دلخواه در matplotlib
    try:
        if os.path.isfile(font_path):
            font_manager.fontManager.addfont(font_path)
            # به matplotlib اسم فونت را بده
            plt.rcParams["font.family"] = PREFERRED_FONT_FAMILY
            plt.rcParams["font.sans-serif"] = [PREFERRED_FONT_FAMILY]
            plt.rcParams["axes.unicode_minus"] = False
            matplotlib_ok = True
            pdf_font_path = font_path
        else:
            # جستجوی فونت‌های نصب‌شده
            sys_fonts = [f.name for f in font_manager.fontManager.ttflist]
            for candidate in ["DejaVu Sans", "Noto Sans", "Tahoma"]:
                if candidate in sys_fonts:
                    plt.rcParams["font.family"] = candidate
                    plt.rcParams["font.sans-serif"] = [candidate]
                    plt.rcParams["axes.unicode_minus"] = False
                    matplotlib_ok = True
                    # مسیر احتمالی برای PDF را نیز بررسی می‌کنیم
                    break
    except Exception:
        matplotlib_ok = False

    # تلاش برای پیدا کردن مسیر فونت مناسب برای FPDF (برای تولید PDF فارسی)
    if pdf_font_path is None:
        # مسیرهای معمول برای DejaVu/Noto در لینوکس
        common_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf",
        ]
        for p in common_paths:
            if os.path.isfile(p):
                pdf_font_path = p
                break

    # تنظیمات ویژه برای راست‌چین بودن متن در نمودارها
    # (توضیح: matplotlib پشتیبانی کامل RTL نداره؛ ما با معکوس کردن محور x و تنظیم align تا حدی به نتیجه دست می‌یابیم)
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.titlepad"] = 6
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"

    return matplotlib_ok, pdf_font_path

_MATPLOTLIB_FONT_OK, _PDF_FONT_PATH = register_fonts_and_configure_matplotlib()

# -------------------------
# تابع ساخت PDF مقاوم (استفاده از فونت فارسی اگر موجود)
# خروجی: bytes قابل استفاده در st.download_button
# -------------------------
def build_student_report_pdf(student_name, rows, school="", student_class="", issuer_date_str=None):
    """
    student_name: str
    rows: list of dicts with keys: 'درس', 'میانگین دانش‌آموز', 'میانگین کلاس', 'وضعیت'
    school, student_class: optional strings
    issuer_date_str: تاریخ به فرمت دلخواه (مثلاً شمسی)
    """
    if issuer_date_str is None:
        issuer_date_str = jdatetime.date.today().strftime("%Y/%m/%d")

    pdf = FPDF()
    pdf.add_page()

    # تلاش برای اضافه کردن فونت یونیکد (اگر مسیر موجود باشد)
    try:
        if _PDF_FONT_PATH and os.path.isfile(_PDF_FONT_PATH):
            try:
                pdf.add_font(PREFERRED_FONT_FAMILY, "", _PDF_FONT_PATH, uni=True)
                pdf.set_font(PREFERRED_FONT_FAMILY, size=12)
            except Exception:
                # fallback
                try:
                    pdf.add_font("DejaVuSans", "", _PDF_FONT_PATH, uni=True)
                    pdf.set_font("DejaVuSans", size=12)
                except Exception:
                    pdf.set_font("Arial", size=12)
        else:
            pdf.set_font("Arial", size=12)
    except Exception:
        pdf.set_font("Arial", size=12)

    # عنوان و اطلاعات پایه (حاشیه‌ها راست چین نزدیک باشند)
    try:
        pdf.cell(0, 8, txt=f"کارنامه دانش‌آموز: {student_name}", ln=True, align="C")
        pdf.cell(0, 8, txt=f"تاریخ صدور: {issuer_date_str}", ln=True, align="C")
        pdf.ln(4)
        if school:
            pdf.cell(0, 6, txt=f"مدرسه: {school}", ln=True, align="L")
        if student_class:
            pdf.cell(0, 6, txt=f"کلاس: {student_class}", ln=True, align="L")
        pdf.ln(4)
    except Exception:
        # در صورت خطا در رندر متن (یونیکد) از نسخه ساده‌تر استفاده کن
        pass

    # جدول خلاصه
    for row in rows:
        lesson = str(row.get("درس", ""))
        s_avg = str(row.get("میانگین دانش‌آموز", ""))
        c_avg = str(row.get("میانگین کلاس", ""))
        status = str(row.get("وضعیت", ""))
        line = f"{lesson}: میانگین دانش‌آموز {s_avg}، میانگین کلاس {c_avg}، وضعیت: {status}"
        try:
            pdf.multi_cell(0, 7, txt=line)
        except Exception:
            # اگر مشکلی در یونیکد بود، کاراکترهای نامشخص را جایگزین می‌کنیم
            safe_line = line.encode("latin-1", errors="replace").decode("latin-1", errors="ignore")
            pdf.multi_cell(0, 7, txt=safe_line)

    # خروجی بایت‌ها با مدیریت encoding
    try:
        out = pdf.output(dest="S")
        if isinstance(out, bytes):
            pdf_bytes = out
        else:
            pdf_bytes = out.encode("latin-1", errors="replace")
    except Exception:
        try:
            out = pdf.output(dest="S")
            pdf_bytes = out.encode("utf-8", errors="ignore") if isinstance(out, str) else out
        except Exception:
            # خروجی ساده (انگلیسی) در بدترین حالت
            pdf2 = FPDF()
            pdf2.add_page()
            pdf2.set_font("Arial", size=12)
            pdf2.cell(0, 8, txt=f"Report for {student_name}", ln=True)
            out2 = pdf2.output(dest="S")
            pdf_bytes = out2.encode("latin-1", errors="replace") if isinstance(out2, str) else out2

    return pdf_bytes

# -------------------------
# اتصال به دیتابیس (ویرایش: اضافه شدن ستون نام_کامل در users)
# -------------------------
DB_PATH = os.path.join(DATA_DIR, "school.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

def init_database():
    # جدول users با فیلد جدید نام_کامل
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            نام_کاربر TEXT PRIMARY KEY,
            نام_کامل TEXT,
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

    # درج admin پیش‌فرض (در صورت عدم وجود) — توجه: نام_کامل خالی است ولی می‌توان آن را تغییر داد
    cursor.execute("""
        INSERT OR IGNORE INTO users
        (نام_کاربر, نام_کامل, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("admin", "مدیر سامانه", "1234", "مدیر سامانه", "مدرسه نمونه", "فعال", "2099/12/31"))
    conn.commit()

# فراخوانی اولیه ایجاد جداول
init_database()

# -------------------------
# توابع کمکی ساده برای کار با دیتابیس (خواندن با pandas و اجرای کوئری)
# این توابع را می‌توان در بخش‌های بعدی استفاده کرد بدون تغییر
# -------------------------
def read_sql(query, params=None):
    try:
        return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        st.error("خطا در اجرای پرس‌وجوی خواندن SQL:")
        st.text(str(e))
        st.text(traceback.format_exc())
        return pd.DataFrame()

def execute_sql(query, params=None):
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
    except Exception as e:
        st.error("خطا در اجرای پرس‌وجوی نوشتن SQL:")
        st.text(str(e))
        st.text(traceback.format_exc())

# -------------------------
# تابع کمکی برای رسم نمودار دایره‌ای با legend رنگ‌ها (برای استفاده در بخش‌های بعدی)
# رنگ‌بندی مطابق چهار سطح: قرمز، نارنجی، سبز، آبی
# برمی‌گرداند: (fig, ax) برای نمایش با st.pyplot
# -------------------------
def pie_chart_with_legend(status_counts, title="توزیع وضعیت"):
    """
    status_counts: dict keyed by 1..4 => count
    returns matplotlib fig, ax
    """
    labels = ["نیاز به تلاش بیشتر", "قابل قبول", "خوب", "خیلی خوب"]
    colors = ["#e74c3c", "#e67e22", "#2ecc71", "#3498db"]  # قرمز، نارنجی، سبز، آبی
    sizes = [status_counts.get(i, 0) for i in range(1, 5)]
    if sum(sizes) == 0:
        return None, None
    fig, ax = plt.subplots(figsize=(5, 4))
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors, textprops={'fontsize': 10})
    ax.set_title(title)
    # Legend کنار نمودار (راست)
    ax.legend(wedges, labels, title="وضعیت", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    plt.tight_layout()
    return fig, ax

# -------------------------
# آماده: بخش ۱ کامل شد.
# بخش‌های بعدی (توابع کامل پنل آموزگار/مدیر/معاون، نمودار خطی کلاس، و UI ورود) را جداگانه می‌فرستم.
# -------------------------
# ------------------------------
# بخش ۲: توابع پنل آموزگار/مدیر/معاون — ثبت/ویرایش/نمودار/PDF
# ------------------------------

# ثبت دانش‌آموز جدید (پنل آموزگار)
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
        try:
            execute_sql("INSERT INTO students (آموزگار, نام_دانش‌آموز, نام_کاربری, رمز_دانش‌آموز, کلاس, تاریخ_ثبت) VALUES (?, ?, ?, ?, ?, ?)",
                        (username, name, username_std, password_std, class_name, today))
            st.success("✅ دانش‌آموز با موفقیت ثبت شد.")
            st.rerun()
        except Exception as e:
            st.error("خطا در ثبت دانش‌آموز:")
            st.text(str(e))

# ویرایش یا حذف دانش‌آموز (پنل آموزگار)
def edit_or_delete_student(username):
    st.subheader("✏️ ویرایش / حذف دانش‌آموز")
    student_df = read_sql("SELECT * FROM students WHERE آموزگار = ?", params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    selected = st.selectbox("انتخاب دانش‌آموز برای ویرایش:", student_df["نام_دانش‌آموز"].unique(), key=f"edit_std_select_{username}")
    row = student_df[student_df["نام_دانش‌آموز"] == selected].iloc[0]

    new_name = st.text_input("نام دانش‌آموز", value=row["نام_دانش‌آموز"], key=f"edit_name_{username}")
    new_username = st.text_input("نام کاربری دانش‌آموز", value=row["نام_کاربری"], key=f"edit_usr_{username}")
    new_pwd = st.text_input("رمز دانش‌آموز", value=row["رمز_دانش‌آموز"], key=f"edit_pwd_std_{username}")
    new_class = st.text_input("کلاس", value=row["کلاس"], key=f"edit_class_{username}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 ذخیره تغییرات دانش‌آموز", key=f"save_std_{username}"):
            try:
                execute_sql("UPDATE students SET نام_دانش‌آموز = ?, نام_کاربری = ?, رمز_دانش‌آموز = ?, کلاس = ? WHERE id = ?",
                            (new_name, new_username, new_pwd, new_class, row["id"]))
                st.success("✅ اطلاعات دانش‌آموز به‌روزرسانی شد.")
                st.rerun()
            except Exception as e:
                st.error("خطا در ذخیره تغییرات:")
                st.text(str(e))
    with col2:
        if st.button("🗑 حذف دانش‌آموز", key=f"del_std_{username}"):
            try:
                execute_sql("DELETE FROM scores WHERE نام_دانش‌آموز = ?", (row["نام_دانش‌آموز"],))
                execute_sql("DELETE FROM students WHERE id = ?", (row["id"],))
                st.warning("❌ دانش‌آموز و نمرات مربوطه حذف شدند.")
                st.rerun()
            except Exception as e:
                st.error("خطا در حذف دانش‌آموز:")
                st.text(str(e))

# ثبت نمره (پنل آموزگار)
def show_score_entry_panel(username):
    st.subheader("📌 ثبت نمره جدید")
    student_df = read_sql("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", params=(username,))
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
        try:
            execute_sql("INSERT INTO scores (آموزگار, نام_دانش‌آموز, درس, نمره_شماره, نمره, تاریخ) VALUES (?, ?, ?, ?, ?, ?)",
                        (username, student_name, lesson, score_number, score_value, today))
            st.success("✅ نمره ثبت شد.")
            st.rerun()
        except Exception as e:
            st.error("خطا در ثبت نمره:")
            st.text(str(e))

# ویرایش / حذف نمرات دانش‌آموز (پنل آموزگار)
def edit_scores_for_student(username):
    st.subheader("✏️ ویرایش / حذف نمرات دانش‌آموز")
    student_df = read_sql("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return

    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique(), key=f"edit_score_student_{username}")
    scores_df = read_sql("SELECT * FROM scores WHERE نام_دانش‌آموز = ? AND آموزگار = ?", params=(student_name, username))
    if scores_df.empty:
        st.info("برای این دانش‌آموز هنوز نمره‌ای ثبت نشده است.")
        return

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
            try:
                execute_sql("UPDATE scores SET درس = ?, نمره_شماره = ?, نمره = ? WHERE id = ?", (new_lesson, new_num, new_val, selected_id))
                st.success("✅ نمره به‌روزرسانی شد.")
                st.rerun()
            except Exception as e:
                st.error("خطا در به‌روزرسانی نمره:")
                st.text(str(e))
    with col2:
        if st.button("🗑 حذف نمره", key=f"del_score_{username}"):
            try:
                execute_sql("DELETE FROM scores WHERE id = ?", (selected_id,))
                st.warning("❌ نمره حذف شد.")
                st.rerun()
            except Exception as e:
                st.error("خطا در حذف نمره:")
                st.text(str(e))

# نمودار خطی پیشرفت برای یک دانش‌آموز و درس مشخص (با محور x راست‌چین شده)
def show_student_line_chart(student_name, lesson):
    df_line = read_sql("SELECT id, نمره_شماره, نمره FROM scores WHERE نام_دانش‌آموز = ? AND درس = ? ORDER BY id", params=(student_name, lesson))
    if df_line.empty:
        st.info("برای این درس هنوز نمره‌ای ثبت نشده است.")
        return

    # تبدیل نمره_شماره به لیبل‌های قابل نمایش و حفظ ترتیب
    x_labels = df_line["نمره_شماره"].astype(str).tolist()
    y_values = df_line["نمره"].tolist()

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(x_labels, y_values, marker="o", linewidth=2)
    ax.set_title(f"روند نمرات {student_name} - درس {lesson}")
    ax.set_xlabel("شماره نمره")
    ax.set_ylabel("نمره")

    # معکوس محور x برای القای سمت راست شروع (RTL-like)
    try:
        ax.invert_xaxis()
    except Exception:
        pass

    # تنظیم فونت (اگر Vazir ثبت شده باشد matplotlib آن را می‌شناسد)
    try:
        if _MATPLOTLIB_FONT_OK:
            for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] + ax.get_xticklabels() + ax.get_yticklabels()):
                item.set_fontname(PREFERRED_FONT_FAMILY)
    except Exception:
        pass

    plt.tight_layout()
    st.pyplot(fig)

# نمودار خطی میانگین کلاس برای یک درس (تاریخ/شماره نمره -> میانگین)
def show_class_line_chart(teacher, lesson):
    # خواندن همه نمرات برای آن درس و گروه‌بندی براساس نمره_شماره (ترتیب بر اساس min(id) برای هر شماره)
    df = read_sql("""
        SELECT نمره_شماره, AVG(نمره) as میانگین
        FROM scores
        WHERE آموزگار = ? AND درس = ?
        GROUP BY نمره_شماره
        ORDER BY MIN(id)
    """, params=(teacher, lesson))
    if df.empty:
        st.info("برای این درس هنوز نمره‌ای ثبت نشده است.")
        return

    x_labels = df["نمره_شماره"].astype(str).tolist()
    y_values = df["میانگین"].tolist()

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(x_labels, y_values, marker="o", linewidth=2)
    ax.set_title(f"روند میانگین کلاس - درس {lesson}")
    ax.set_xlabel("شماره نمره")
    ax.set_ylabel("میانگین نمره")
    try:
        ax.invert_xaxis()
    except Exception:
        pass

    try:
        if _MATPLOTLIB_FONT_OK:
            for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] + ax.get_xticklabels() + ax.get_yticklabels()):
                item.set_fontname(PREFERRED_FONT_FAMILY)
    except Exception:
        pass

    plt.tight_layout()
    st.pyplot(fig)

# رسم نمودار دایره‌ای وضعیت کلاس با legend (رنگ‌بندی بر اساس چهار سطح)
def draw_class_pie_chart(teacher, selected_lesson=None, title="توزیع وضعیت کلاس"):
    # استفاده از توابع کمکی: خواندن میانگین‌ها و تعیین وضعیت
    if selected_lesson:
        df = read_sql("SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_درس FROM scores WHERE آموزگار = ? AND درس = ? GROUP BY نام_دانش‌آموز", params=(teacher, selected_lesson))
    else:
        df = read_sql("SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_دانش‌آموز FROM scores WHERE آموزگار = ? GROUP BY نام_دانش‌آموز", params=(teacher,))
    if df.empty:
        st.info("اطلاعات نمرات موجود نیست.")
        return

    # جمع‌بندی وضعیت‌ها
    status_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    if selected_lesson:
        for _, row in df.iterrows():
            student_avg = row["میانگین_درس"]
            class_avg_row = read_sql("SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?", params=(teacher, selected_lesson))
            class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
            status = وضعیت_نمره‌ای(student_avg, class_avg)
            status_counts[status] = status_counts.get(status, 0) + 1
    else:
        grouped = df.groupby("نام_دانش‌آموز")["میانگین_دانش‌آموز"].mean().reset_index()
        for _, row in grouped.iterrows():
            student_avg = row["میانگین_دانش‌آموز"]
            class_avg_row = read_sql("SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ?", params=(teacher,))
            class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
            status = وضعیت_نمره‌ای(student_avg, class_avg)
            status_counts[status] = status_counts.get(status, 0) + 1

    fig, ax = pie_chart_with_legend(status_counts, title=title)
    if fig is None:
        st.info("داده کافی برای نمودار وجود ندارد.")
        return

    # نمایش نمودار و راهنمای رنگ به صورت خوانا
    col1, col2 = st.columns([3, 1])
    with col1:
        st.pyplot(fig)
    with col2:
        st.markdown("### راهنمای رنگ")
        st.markdown("<div style='display:flex;flex-direction:column;gap:6px'>"
                    "<div><span style='display:inline-block;width:16px;height:16px;background:#e74c3c;margin-left:6px;'></span> نیاز به تلاش بیشتر</div>"
                    "<div><span style='display:inline-block;width:16px;height:16px;background:#e67e22;margin-left:6px;'></span> قابل قبول</div>"
                    "<div><span style='display:inline-block;width:16px;height:16px;background:#2ecc71;margin-left:6px;'></span> خوب</div>"
                    "<div><span style='display:inline-block;width:16px;height:16px;background:#3498db;margin-left:6px;'></span> خیلی خوب</div>"
                    "</div>", unsafe_allow_html=True)

# آمار کلی کلاس با انتخاب درس برای آموزگار (شامل نمودار دایره‌ای و امکان دیدن نمودار خطی کلاس)
def show_class_statistics_panel(username):
    st.subheader("📊 آمار کلی کلاس")
    lessons = read_sql("SELECT DISTINCT درس FROM scores WHERE آموزگار = ?", params=(username,))
    lesson_options = ["همه دروس"] + lessons["درس"].tolist() if not lessons.empty else ["همه دروس"]
    selected_lesson = st.selectbox("انتخاب درس برای نمایش آمار:", lesson_options, key=f"class_stats_lesson_{username}")

    if selected_lesson == "همه دروس":
        df = read_sql("SELECT نام_دانش‌آموز, درس, AVG(نمره) as میانگین_نمره FROM scores WHERE آموزگار = ? GROUP BY نام_دانش‌آموز, درس", params=(username,))
    else:
        df = read_sql("SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_درس FROM scores WHERE آموزگار = ? AND درس = ? GROUP BY نام_دانش‌آموز", params=(username, selected_lesson))

    if df.empty:
        st.info("هیچ نمره‌ای ثبت نشده است.")
    else:
        st.dataframe(df)

    # نمودار دایره‌ای
    if selected_lesson == "همه دروس":
        draw_class_pie_chart(username, selected_lesson=None, title="توزیع وضعیت (همه دروس)")
    else:
        draw_class_pie_chart(username, selected_lesson=selected_lesson, title=f"توزیع وضعیت درس {selected_lesson}")

    # امکان نمایش نمودار خطی میانگین کلاس برای درس انتخابی
    if selected_lesson != "همه دروس":
        if st.button("نمایش نمودار روند میانگین کلاس برای این درس"):
            show_class_line_chart(username, selected_lesson)

# رتبه‌بندی کلی و هر درس (برای آموزگار/مدیر/معاون)
def show_class_ranking_panel(username_or_school_admin, role="آموزگار"):
    st.subheader("🏅 رتبه‌بندی کلاس")
    if role in ["مدیر مدرسه", "معاون"]:
        teachers_df = read_sql("SELECT نام_کاربر FROM users WHERE نقش = 'آموزگار' AND مدرسه = ?", params=(username_or_school_admin,))
        if teachers_df.empty:
            st.info("هیچ آموزگاری برای این مدرسه ثبت نشده است.")
            return
        selected_teacher = st.selectbox("انتخاب آموزگار:", teachers_df["نام_کاربر"].unique(), key=f"rank_select_teacher_{username_or_school_admin}")
    else:
        selected_teacher = username_or_school_admin

    lessons_df = read_sql("SELECT DISTINCT درس FROM scores WHERE آموزگار = ?", params=(selected_teacher,))
    lesson_options = ["کل دروس"] + lessons_df["درس"].tolist() if not lessons_df.empty else ["کل دروس"]
    selected_lesson = st.selectbox("انتخاب درس برای رتبه‌بندی:", lesson_options, key=f"rank_lesson_{selected_teacher}")

    if selected_lesson == "کل دروس":
        total_df = read_sql("SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_کل FROM scores WHERE آموزگار = ? GROUP BY نام_دانش‌آموز ORDER BY میانگین_کل DESC", params=(selected_teacher,))
        st.markdown("### 📊 رتبه‌بندی کلی کلاس")
        st.dataframe(total_df)
    else:
        lesson_df = read_sql("SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_درس FROM scores WHERE آموزگار = ? AND درس = ? GROUP BY نام_دانش‌آموز ORDER BY میانگین_درس DESC", params=(selected_teacher, selected_lesson))
        st.markdown(f"### 📘 رتبه‌بندی درس {selected_lesson}")
        st.dataframe(lesson_df)

    # امکان دانلود کارنامه کلی یا کارنامه هر دانش‌آموز از همینجا (برای مدیر/معاون/آموزگار)
    if st.button("📥 دانلود کارنامه یک دانش‌آموز (PDF)"):
        # بازکردن دیالوگ انتخاب دانش‌آموز
        students = read_sql("SELECT DISTINCT نام_دانش‌آموز FROM students WHERE آموزگار = ?", params=(selected_teacher,))
        if students.empty:
            st.info("هیچ دانش‌آموزی برای این آموزگار ثبت نشده است.")
        else:
            student_choice = st.selectbox("انتخاب دانش‌آموز برای دانلود کارنامه:", students["نام_دانش‌آموز"].unique(), key=f"dl_choice_for_{selected_teacher}")
            # تولید rows مشابه بخش دانلود
            df = read_sql("SELECT درس, AVG(نمره) as میانگین_دانش‌آموز FROM scores WHERE نام_دانش‌آموز = ? GROUP BY درس", params=(student_choice,))
            rows = []
            for _, row in df.iterrows():
                lesson = row["درس"]
                student_avg = row["میانگین_دانش‌آموز"]
                class_avg_row = read_sql("SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?", params=(selected_teacher, lesson))
                class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
                status_num = وضعیت_نمره‌ای(student_avg, class_avg)
                status_text = متن_وضعیت(status_num)
                rows.append({"درس": lesson, "میانگین دانش‌آموز": round(student_avg, 2), "میانگین کلاس": round(class_avg, 2), "وضعیت": status_text})
            try:
                pdf_bytes = build_student_report_pdf(student_choice, rows, school="", student_class="")
                st.download_button(label=f"📥 دانلود کارنامه {student_choice}.pdf", data=pdf_bytes, file_name=f"report_{student_choice}.pdf", mime="application/pdf")
            except Exception as e:
                st.error("خطا در تولید PDF:")
                st.text(str(e))
                st.text(traceback.format_exc())

# گزارش فردی دانش‌آموز (برای آموزگار) — شامل نمودار خطی برای درس انتخابی و جدول خلاصه
def show_individual_report_panel(username):
    st.subheader("👤 گزارش فردی دانش‌آموز")
    student_df = read_sql("SELECT نام_دانش‌آموز FROM students WHERE آموزگار = ?", params=(username,))
    if student_df.empty:
        st.info("هیچ دانش‌آموزی ثبت نشده است.")
        return
    student_name = st.selectbox("انتخاب دانش‌آموز:", student_df["نام_دانش‌آموز"].unique(), key=f"ind_rep_{username}")

    lessons_df = read_sql("SELECT DISTINCT درس FROM scores WHERE نام_دانش‌آموز = ? AND آموزگار = ?", params=(student_name, username))
    if lessons_df.empty:
        st.info("برای این دانش‌آموز هنوز نمره‌ای ثبت نشده است.")
        return
    lesson_choice = st.selectbox("انتخاب درس برای نمایش نمودار:", lessons_df["درس"].unique(), key=f"ind_less_{username}_{student_name}")

    # نمودار خطی دانش‌آموز
    show_student_line_chart(student_name, lesson_choice)

    st.markdown("### 📄 جدول خلاصه نمرات")
    df = read_sql("SELECT درس, AVG(نمره) as میانگین_دانش‌آموز FROM scores WHERE نام_دانش‌آموز = ? GROUP BY درس", params=(student_name,))
    rows = []
    for _, row in df.iterrows():
        lesson = row["درس"]
        student_avg = row["میانگین_دانش‌آموز"]
        class_avg_row = read_sql("SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?", params=(username, lesson))
        class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
        status_num = وضعیت_نمره‌ای(student_avg, class_avg)
        status_text = متن_وضعیت(status_num)
        rows.append({"درس": lesson, "میانگین دانش‌آموز": round(student_avg,2), "میانگین کلاس": round(class_avg,2), "وضعیت": status_text})
    st.table(pd.DataFrame(rows))

    # دانلود PDF از همین پنل
    if st.button("📥 دانلود کارنامه این دانش‌آموز"):
        try:
            pdf_bytes = build_student_report_pdf(student_name, rows, school="", student_class="")
            st.download_button(label=f"📥 دانلود کارنامه {student_name}.pdf", data=pdf_bytes, file_name=f"report_{student_name}.pdf", mime="application/pdf")
        except Exception as e:
            st.error("خطا در تولید PDF:")
            st.text(str(e))
            st.text(traceback.format_exc())

# --------------
# توابع تکمیلی جهت استفاده مدیر/معاون: مشاهده همه آمار آموزگاران و دانلود گزارش‌ها
# --------------
def show_teacher_statistics_by_admin(school):
    st.subheader("📈 آمار آموزگاران مدرسه")
    teachers_df = read_sql("SELECT نام_کاربر, نام_کامل, نقش FROM users WHERE مدرسه = ? AND نقش = 'آموزگار'", params=(school,))
    if teachers_df.empty:
        st.info("هیچ آموزگاری در این مدرسه ثبت نشده است.")
        return
    st.dataframe(teachers_df)

    # انتخاب آموزگار برای دیدن جزئیات
    selected_teacher = st.selectbox("انتخاب آموزگار برای نمایش آمار:", teachers_df["نام_کاربر"].unique(), key=f"admin_sel_teacher_{school}")
    st.markdown("### آمار انتخاب‌شده")
    show_class_statistics_panel(selected_teacher)
    st.markdown("### رتبه‌بندی")
    show_class_ranking_panel(selected_teacher, role="مدیر مدرسه")

    # دانلود کارنامه از این پنل
    if st.button("📥 دانلود کارنامه دانش‌آموز از مدرسه"):
        students = read_sql("SELECT DISTINCT نام_دانش‌آموز FROM students WHERE آموزگار = ?", params=(selected_teacher,))
        if students.empty:
            st.info("هیچ دانش‌آموزی برای این آموزگار ثبت نشده است.")
        else:
            student_choice = st.selectbox("انتخاب دانش‌آموز برای دانلود:", students["نام_دانش‌آموز"].unique(), key=f"admin_dl_choice_{selected_teacher}")
            df = read_sql("SELECT درس, AVG(نمره) as میانگین_دانش‌آموز FROM scores WHERE نام_دانش‌آموز = ? GROUP BY درس", params=(student_choice,))
            rows = []
            for _, row in df.iterrows():
                lesson = row["درس"]
                student_avg = row["میانگین_دانش‌آموز"]
                class_avg_row = read_sql("SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?", params=(selected_teacher, lesson))
                class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
                status_num = وضعیت_نمره‌ای(student_avg, class_avg)
                status_text = متن_وضعیت(status_num)
                rows.append({"درس": lesson, "میانگین دانش‌آموز": round(student_avg,2), "میانگین کلاس": round(class_avg,2), "وضعیت": status_text})
            try:
                pdf_bytes = build_student_report_pdf(student_choice, rows, school=school, student_class="")
                st.download_button(label=f"📥 دانلود کارنامه {student_choice}.pdf", data=pdf_bytes, file_name=f"report_{student_choice}.pdf", mime="application/pdf")
            except Exception as e:
                st.error("خطا در تولید PDF:")
                st.text(str(e))
                st.text(traceback.format_exc())

# ------------------------------
# پایان بخش ۲
# ------------------------------
# ------------------------------
# بخش ۳: ورود کاربران و اجرای نهایی پنل‌ها
# ------------------------------

# پنل مدیر سامانه (Super Admin)
def show_superadmin_panel():
    st.title("🛠️ پنل مدیر سامانه")
    st.markdown("در این بخش می‌توانید کاربران جدید ایجاد کنید و اطلاعات مدارس را مدیریت نمایید.")

    # ثبت کاربر جدید
    with st.expander("➕ ثبت کاربر جدید"):
        username = st.text_input("نام کاربری", key="super_user_username")
        full_name = st.text_input("نام کامل کاربر", key="super_user_fullname")
        password = st.text_input("رمز عبور", type="password", key="super_user_pwd")
        role = st.selectbox("نقش کاربر", ["مدیر مدرسه", "معاون", "آموزگار"], key="super_user_role")
        school = st.text_input("نام مدرسه", key="super_user_school")
        if st.button("ثبت کاربر جدید", key="super_user_submit"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور الزامی است.")
            else:
                try:
                    execute_sql("INSERT INTO users (نام_کاربر, نام_کامل, رمز, نقش, مدرسه) VALUES (?, ?, ?, ?, ?)",
                                (username, full_name, password, role, school))
                    st.success("✅ کاربر جدید با موفقیت ثبت شد.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error("خطا در ثبت کاربر:")
                    st.text(str(e))

    # نمایش فهرست کاربران موجود
    st.markdown("### 👥 فهرست کاربران")
    df = read_sql(" نام_کاربر, نام_کامل, نقش, مدرسه FROM users")
    if df.empty:
        st.info("هیچ کاربری ثبت نشده است.")
    else:
        st.dataframe(df)

    # حذف کاربر
    with st.expander("🗑 حذف کاربر"):
        selected = st.selectbox("انتخاب کاربر برای حذف", df["نام_کاربر"].tolist() if not df.empty else [], key="super_user_delete_select")
        if st.button("حذف کاربر", key="super_user_delete_btn"):
            try:
                execute_sql("DELETE FROM users WHERE نام_کاربر = ?", (selected,))
                st.warning(f"❌ کاربر {selected} حذف شد.")
                st.experimental_rerun()
            except Exception as e:
                st.error("خطا در حذف کاربر:")
                st.text(str(e))


# پنل مدیر مدرسه
def show_school_admin_panel(username):
    st.title("🏫 پنل مدیر مدرسه")
    df_user = read_sql("SELECT مدرسه FROM users WHERE نام_کاربر = ?", params=(username,))
    school = df_user.iloc[0]["مدرسه"] if not df_user.empty else "نامشخص"

    tab1, tab2, tab3 = st.tabs(["👥 آموزگاران و آمار", "🏅 رتبه‌بندی کلاس‌ها", "📥 گزارش‌ها"])
    with tab1:
        show_teacher_statistics_by_admin(school)
    with tab2:
        show_class_ranking_panel(username, role="مدیر مدرسه")
    with tab3:
        show_teacher_statistics_by_admin(school)


# پنل معاون مدرسه
def show_assistant_panel(username):
    st.title("🎓 پنل معاون مدرسه")
    df_user = read_sql("SELECT مدرسه FROM users WHERE نام_کاربر = ?", params=(username,))
    school = df_user.iloc[0]["مدرسه"] if not df_user.empty else "نامشخص"

    tab1, tab2 = st.tabs(["📈 آمار آموزگاران", "🏅 رتبه‌بندی"])
    with tab1:
        show_teacher_statistics_by_admin(school)
    with tab2:
        show_class_ranking_panel(username, role="معاون")


# پنل آموزگار
def show_teacher_panel(username):
    st.title("🍎 پنل آموزگار")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "➕ ثبت دانش‌آموز",
        "✏️ ویرایش دانش‌آموز",
        "📘 ثبت نمره",
        "✏️ ویرایش نمره",
        "📊 آمار کلاس",
        "👤 گزارش فردی"
    ])

    with tab1:
        register_student_form(username)
    with tab2:
        edit_or_delete_student(username)
    with tab3:
        show_score_entry_panel(username)
    with tab4:
        edit_scores_for_student(username)
    with tab5:
        show_class_statistics_panel(username)
    with tab6:
        show_individual_report_panel(username)


# پنل دانش‌آموز
def show_student_panel(username):
    st.title("🎒 پنل دانش‌آموز")

    df_student = read_sql("SELECT * FROM students WHERE نام_کاربری = ?", params=(username,))
    if df_student.empty:
        st.warning("مشخصات شما در سامانه یافت نشد.")
        return

    student_row = df_student.iloc[0]
    student_name = student_row["نام_دانش‌آموز"]
    teacher = student_row["آموزگار"]

    st.markdown(f"👤 نام دانش‌آموز: {student_name}")
    st.markdown(f"🍎 آموزگار: {teacher}")
    st.markdown(f"🏫 کلاس: {student_row['کلاس']}")

    df = read_sql("SELECT درس, AVG(نمره) as میانگین FROM scores WHERE نام_دانش‌آموز = ? GROUP BY درس", params=(student_name,))
    if df.empty:
        st.info("هیچ نمره‌ای برای شما ثبت نشده است.")
        return

    st.dataframe(df)

    # نمودار دایره‌ای سطح عملکرد دانش‌آموز
    rows = []
    for _, row in df.iterrows():
        lesson = row["درس"]
        student_avg = row["میانگین"]
        class_avg_row = read_sql("SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?", params=(teacher, lesson))
        class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
        status_num = وضعیت_نمره‌ای(student_avg, class_avg)
        rows.append(status_num)
    fig, ax = pie_chart_with_legend({i: rows.count(i) for i in range(1, 5)}, title="توزیع عملکرد شما")
    st.pyplot(fig)

    # امکان دانلود کارنامه خودش
    if st.button("📥 دانلود کارنامه من"):
        try:
            report_rows = []
            for _, row in df.iterrows():
                lesson = row["درس"]
                student_avg = row["میانگین"]
                class_avg_row = read_sql("SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?", params=(teacher, lesson))
                class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
                status_num = وضعیت_نمره‌ای(student_avg, class_avg)
                status_text = متن_وضعیت(status_num)
                report_rows.append({
                    "درس": lesson,
                    "میانگین دانش‌آموز": round(student_avg, 2),
                    "میانگین کلاس": round(class_avg, 2),
                    "وضعیت": status_text
                })
            pdf_bytes = build_student_report_pdf(student_name, report_rows, school="", student_class=student_row["کلاس"])
            st.download_button(label=f"📥 دانلود کارنامه {student_name}.pdf", data=pdf_bytes, file_name=f"report_{student_name}.pdf", mime="application/pdf")
        except Exception as e:
            st.error("خطا در تولید PDF:")
            st.text(str(e))
            st.text(traceback.format_exc())


# ------------------------------
# صفحه ورود اصلی
# ------------------------------
st.title("📘 سامانه مدیریت نمرات مدارس")
st.markdown("به سامانه خوش آمدید. لطفاً وارد شوید:")

username = st.text_input("نام کاربری", key="login_user")
password = st.text_input("رمز عبور", type="password", key="login_pass")

if st.button("ورود"):
    user = read_sql("SELECT * FROM users WHERE نام_کاربر = ? AND رمز_عبور = ?", params=(username, password))
    if not user.empty:
        role = user.iloc[0]["نقش"]
        st.success(f"ورود موفقیت‌آمیز به عنوان {role}")

        if role == "مدیر سامانه":
            show_superadmin_panel()
        elif role == "مدیر مدرسه":
            show_school_admin_panel(username)
        elif role == "معاون":
            show_assistant_panel(username)
        elif role == "آموزگار":
            show_teacher_panel(username)
        else:
            show_student_panel(username)
    else:
        student = read_sql("SELECT * FROM students WHERE نام_کاربری = ? AND رمز_دانش‌آموز = ?", params=(username, password))
        if not student.empty:
            st.success("ورود موفقیت‌آمیز به عنوان دانش‌آموز 🎒")
            show_student_panel(username)
        else:
            st.error("❌ نام کاربری یا رمز عبور نادرست است.")


# ------------------------------
# پایان فایل main.py
# ------------------------------






