# main.py (نسخه اصلاح‌شده — جایگزین کد قبلی)
import os
import sqlite3
from datetime import datetime
import io
import traceback
import tempfile
import uuid  # برای تولید کلید منحصربه‌فرد در ویجت‌ها

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib import font_manager
from fpdf import FPDF
import jdatetime

# برای راست‌چین و reshaping متن فارسی در matplotlib
import arabic_reshaper
from bidi.algorithm import get_display
import streamlit as st
from supabase_utils import supabase  # اتصال به Supabase از فایل جدا

# تست اتصال: دریافت لیست کاربران
response = supabase.table("users").select("*").execute()
users = response.data

# نمایش در Streamlit
st.title("لیست کاربران")
for user in users:
    st.write(f"{user['نام_کاربر']} - نقش: {user['نقش']}")

# -------------------------
# تابع reshape برای متن‌های فارسی
def reshape(text):
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)

# -------------------------
# تنظیم صفحه
st.set_page_config(page_title="📊 درس‌بان | داشبورد تحلیلی کلاس", layout="wide")

# -------------------------
# مسیرها و فونت
DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

FONTS_DIR = os.path.join(os.getcwd(), "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

PREFERRED_FONT_FILENAME = "Vazir.ttf"
PREFERRED_FONT_FAMILY = "Vazir"

# ثبت فونت برای matplotlib و پیدا کردن مسیر فونت برای FPDF
def register_fonts_and_configure_matplotlib():
    font_path = os.path.join(FONTS_DIR, PREFERRED_FONT_FILENAME)
    pdf_font_path = None
    matplotlib_ok = False
    try:
        if os.path.isfile(font_path):
            font_manager.fontManager.addfont(font_path)
            plt.rcParams["font.family"] = PREFERRED_FONT_FAMILY
            plt.rcParams["font.sans-serif"] = [PREFERRED_FONT_FAMILY]
            plt.rcParams["axes.unicode_minus"] = False
            matplotlib_ok = True
            pdf_font_path = font_path
        else:
            sys_fonts = [f.name for f in font_manager.fontManager.ttflist]
            for candidate in ["DejaVu Sans", "Noto Sans", "Tahoma"]:
                if candidate in sys_fonts:
                    plt.rcParams["font.family"] = candidate
                    plt.rcParams["font.sans-serif"] = [candidate]
                    plt.rcParams["axes.unicode_minus"] = False
                    matplotlib_ok = True
                    break
    except Exception:
        matplotlib_ok = False

    # مسیرهای معمول برای PDF fallback
    if pdf_font_path is None:
        common_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        ]
        for p in common_paths:
            if os.path.isfile(p):
                pdf_font_path = p
                break

    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.titlepad"] = 6
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"

    return matplotlib_ok, pdf_font_path

_MATPLOTLIB_FONT_OK, _PDF_FONT_PATH = register_fonts_and_configure_matplotlib()

# -------------------------
# اتصال به دیتابیس
DB_PATH = os.path.join(DATA_DIR, "school.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

def init_database():
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
    # درج admin پیش‌فرض در صورت نبودن
    cursor.execute("""
        INSERT OR IGNORE INTO users
        (نام_کاربر, نام_کامل, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("admin", "مدیر سامانه", "1234", "مدیر سامانه", "مدرسه نمونه", "فعال", "2099/12/31"))
    conn.commit()

init_database()

# -------------------------
# توابع کمکی DB
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
# وضعیت/متن وضعیت (ایمن‌تر)
def وضعیت_نمره‌ای(student_avg, class_avg):
    try:
        if class_avg is None or class_avg == 0:
            class_avg = 10.0
        ratio = float(student_avg) / float(class_avg)
        if ratio < 0.8:
            return 1
        elif ratio < 1.0:
            return 2
        elif ratio < 1.2:
            return 3
        else:
            return 4
    except Exception:
        return 2

def متن_وضعیت(status_code):
    return {1: "نیاز به تلاش بیشتر", 2: "قابل قبول", 3: "خوب", 4: "خیلی خوب"}.get(status_code, "نامشخص")

# -------------------------
# تابع رسم پی‌چارت با legend و فونت فارسی
def pie_chart_with_legend(status_counts, title="نمودار وضعیت"):
    try:
        filtered = {k: v for k, v in status_counts.items() if v > 0}
        if not filtered:
            return None, None

        labels_raw = {1: "نیاز به تلاش بیشتر", 2: "قابل قبول", 3: "خوب", 4: "خیلی خوب"}
        colors = {1: "#e74c3c", 2: "#e67e22", 3: "#2ecc71", 4: "#3498db"}

        keys = list(filtered.keys())
        labels = [reshape(labels_raw[k]) for k in keys]
        values = [filtered[k] for k in keys]
        color_list = [colors[k] for k in keys]

        fig, ax = plt.subplots(figsize=(5, 4))
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.0f%%", startangle=90, colors=color_list, textprops={"fontsize": 10}
        )
        # عنوان با reshape
        ax.set_title(reshape(title), fontsize=12)
        # تلاش برای ست فونت Vazir روی برچسب‌ها
        try:
            for t in texts + autotexts:
                if _MATPLOTLIB_FONT_OK:
                    t.set_fontname(PREFERRED_FONT_FAMILY)
        except Exception:
            pass
        ax.axis("equal")
        plt.tight_layout()
        return fig, ax
    except Exception as e:
        print("خطا در رسم نمودار:", e)
        print(traceback.format_exc())
        return None, None

# -------------------------
# اصلاح شده: draw_class_pie_chart (حذف رندر تکراری)
def draw_class_pie_chart(teacher, selected_lesson=None, title="توزیع وضعیت کلاس"):
    # خواندن میانگین‌ها
    if selected_lesson and selected_lesson != "همه دروس":
        df = read_sql(
            "SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_درس FROM scores WHERE آموزگار = ? AND درس = ? GROUP BY نام_دانش‌آموز",
            params=(teacher, selected_lesson)
        )
    else:
        df = read_sql(
            "SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_دانش‌آموز FROM scores WHERE آموزگار = ? GROUP BY نام_دانش‌آموز",
            params=(teacher,)
        )

    if df.empty:
        st.info("اطلاعات نمرات موجود نیست.")
        return

    status_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    if selected_lesson and selected_lesson != "همه دروس":
        for _, row in df.iterrows():
            student_avg = row["میانگین_درس"]
            class_avg_row = read_sql(
                "SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?",
                params=(teacher, selected_lesson)
            )
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

    # فیلتر و رسم تنها یک بار
    filtered = {k: v for k, v in status_counts.items() if v > 0}
    if not filtered:
        st.warning("داده کافی برای نمایش نمودار وجود ندارد.")
        return

    fig, ax = pie_chart_with_legend(filtered, title=title)
    if fig is None:
        st.warning("خطا در رسم نمودار.")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        st.pyplot(fig)
    with col2:
        st.markdown("### 🎨 راهنمای رنگ")
        st.markdown(
            """
            <div style='display:flex;flex-direction:column;gap:6px;font-size:14px;text-align:right;'>
                <div><span style='display:inline-block;width:14px;height:14px;background:#e74c3c;margin-left:6px;border-radius:3px;'></span> ۱ - نیاز به تلاش بیشتر</div>
                <div><span style='display:inline-block;width:14px;height:14px;background:#e67e22;margin-left:6px;border-radius:3px;'></span> ۲ - قابل قبول</div>
                <div><span style='display:inline-block;width:14px;height:14px;background:#2ecc71;margin-left:6px;border-radius:3px;'></span> ۳ - خوب</div>
                <div><span style='display:inline-block;width:14px;height:14px;background:#3498db;margin-left:6px;border-radius:3px;'></span> ۴ - خیلی خوب</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# -------------------------
# نمودار خطی دانش‌آموز و کلاس (با reshape برچسب‌ها)
def show_student_line_chart(student_name, lesson):
    df_line = read_sql("SELECT id, نمره_شماره, نمره FROM scores WHERE نام_دانش‌آموز = ? AND درس = ? ORDER BY id", params=(student_name, lesson))
    if df_line.empty:
        st.info("برای این درس هنوز نمره‌ای ثبت نشده است.")
        return
    x_labels = df_line["نمره_شماره"].astype(str).tolist()
    y_values = df_line["نمره"].tolist()
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(x_labels, y_values, marker="o", linewidth=2)
    ax.set_title(reshape(f"روند نمرات {student_name} - درس {lesson}"))
    ax.set_xlabel(reshape("شماره نمره"))
    ax.set_ylabel(reshape("نمره"))
    try:
        if _MATPLOTLIB_FONT_OK:
            for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] + ax.get_xticklabels() + ax.get_yticklabels()):
                item.set_fontname(PREFERRED_FONT_FAMILY)
    except Exception:
        pass
    ax.set_xticklabels([reshape(lbl) for lbl in x_labels])
    plt.tight_layout()
    st.pyplot(fig)

def show_class_line_chart(teacher, lesson):
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
    ax.set_title(reshape(f"روند میانگین کلاس - درس {lesson}"))
    ax.set_xlabel(reshape("شماره نمره"))
    ax.set_ylabel(reshape("میانگین نمره"))
    try:
        if _MATPLOTLIB_FONT_OK:
            for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] + ax.get_xticklabels() + ax.get_yticklabels()):
                item.set_fontname(PREFERRED_FONT_FAMILY)
    except Exception:
        pass
    ax.set_xticklabels([reshape(lbl) for lbl in x_labels])
    plt.tight_layout()
    st.pyplot(fig)

# -------------------------
# تولید PDF پیشرفته: اضافه کردن جدول و نمودارها (ذخیره تصاویر موقت و embed در PDF)
def build_student_report_pdf(student_name, rows, school="", student_class="", issuer_date_str=None):
    if issuer_date_str is None:
        issuer_date_str = jdatetime.date.today().strftime("%Y/%m/%d")
    pdf = FPDF()
    pdf.add_page()
    # فونت PDF
    try:
        if _PDF_FONT_PATH and os.path.isfile(_PDF_FONT_PATH):
            pdf.add_font(PREFERRED_FONT_FAMILY, "", _PDF_FONT_PATH, uni=True)
            pdf.set_font(PREFERRED_FONT_FAMILY, size=12)
        else:
            pdf.set_font("Arial", size=12)
    except Exception:
        pdf.set_font("Arial", size=12)

    # هدر
    pdf.cell(0, 8, txt=f"کارنامه دانش‌آموز: {student_name}", ln=True, align="C")
    pdf.cell(0, 8, txt=f"تاریخ صدور: {issuer_date_str}", ln=True, align="C")
    pdf.ln(4)
    if school:
        pdf.cell(0, 6, txt=f"مدرسه: {school}", ln=True)
    if student_class:
        pdf.cell(0, 6, txt=f"کلاس: {student_class}", ln=True)
    pdf.ln(6)

    # جدول خلاصه (سطرها)
    # ستون‌ها: درس | میانگین دانش‌آموز | میانگین کلاس | وضعیت
    col_w = [60, 45, 45, 40]
    # عنوان جدول
    try:
        pdf.set_font(PREFERRED_FONT_FAMILY, size=11)
    except Exception:
        pdf.set_font("Arial", size=11)
    pdf.cell(col_w[0], 8, txt="درس", border=1)
    pdf.cell(col_w[1], 8, txt="میانگین دانش‌آموز", border=1)
    pdf.cell(col_w[2], 8, txt="میانگین کلاس", border=1)
    pdf.cell(col_w[3], 8, txt="وضعیت", border=1, ln=True)
    # محتویات جدول
    for r in rows:
        lesson = str(r.get("درس", ""))
        s_avg = str(r.get("میانگین دانش‌آموز", ""))
        c_avg = str(r.get("میانگین کلاس", ""))
        status = str(r.get("وضعیت", ""))
        pdf.cell(col_w[0], 7, txt=lesson[:30], border=1)
        pdf.cell(col_w[1], 7, txt=str(s_avg), border=1)
        pdf.cell(col_w[2], 7, txt=str(c_avg), border=1)
        pdf.cell(col_w[3], 7, txt=status[:20], border=1, ln=True)

    pdf.ln(6)

    # اگر داده‌ کمتری هست، اضافه کردن نمودارها (در صورت وجود)
    try:
        # ساخت نمودار دایره‌ای از rows
        status_counts = {1:0,2:0,3:0,4:0}
        for r in rows:
            # سعی کن وضعیت را به شماره تبدیل کنی اگر متن است
            stt = r.get("وضعیت", "")
            # map text to code
            code = None
            for k,v in {1:"نیاز به تلاش بیشتر",2:"قابل قبول",3:"خوب",4:"خیلی خوب"}.items():
                if v in str(stt):
                    code = k
                    break
            if code is None:
                # fallback: guess based on words
                if "نیاز" in str(stt):
                    code = 1
                elif "قابل" in str(stt):
                    code = 2
                elif "خیلی" in str(stt):
                    code = 4
                else:
                    code = 3
            status_counts[code] += 1

        # نمودار دایره‌ای
        fig1, ax1 = plt.subplots(figsize=(4,3))
        labels_map = {1:"نیاز به تلاش بیشتر",2:"قابل قبول",3:"خوب",4:"خیلی خوب"}
        keys = [k for k,v in status_counts.items() if v>0]
        vals = [status_counts[k] for k in keys]
        labs = [reshape(labels_map[k]) for k in keys]
        cols = [ "#e74c3c" if k==1 else ("#e67e22" if k==2 else ("#2ecc71" if k==3 else "#3498db")) for k in keys ]
        if sum(vals)>0:
            ax1.pie(vals, labels=labs, autopct="%1.0f%%", startangle=90, colors=cols, textprops={"fontsize":9})
            ax1.set_title(reshape("توزیع وضعیت"))
            ax1.axis("equal")
            tmp_pie = os.path.join(DATA_DIR, f"tmp_pie_{student_name}.png")
            fig1.tight_layout()
            fig1.savefig(tmp_pie, dpi=150)
            plt.close(fig1)
            try:
                pdf.image(tmp_pie, w=90)
            except Exception:
                pass
            # remove temp file
            if os.path.exists(tmp_pie):
                os.remove(tmp_pie)

        # نمودار خطی — اگر حداقل یک درس داشته باشیم، رسم میانگین کلاس برای اولین درس
        if rows:
            first_lesson = rows[0].get("درس")
            # خواندن نمرات برای دانش‌آموز در آن درس جهت رسم خطی
            student_scores = read_sql("SELECT نمره_شماره, نمره FROM scores WHERE نام_دانش‌آموز = ? AND درس = ? ORDER BY id", params=(student_name, first_lesson))
            if not student_scores.empty:
                fig2, ax2 = plt.subplots(figsize=(6,2.5))
                x = student_scores["نمره_شماره"].astype(str).tolist()
                y = student_scores["نمره"].tolist()
                ax2.plot(x, y, marker="o", linewidth=2)
                ax2.set_title(reshape(f"روند نمرات دانش‌آموز - درس {first_lesson}"))
                ax2.set_xlabel(reshape("شماره نمره"))
                ax2.set_ylabel(reshape("نمره"))
                fig2.tight_layout()
                tmp_line = os.path.join(DATA_DIR, f"tmp_line_{student_name}.png")
                fig2.savefig(tmp_line, dpi=150)
                plt.close(fig2)
                try:
                    pdf.image(tmp_line, w=170)
                except Exception:
                    pass
                if os.path.exists(tmp_line):
                    os.remove(tmp_line)

    except Exception as e:
        print("خطا هنگام ساخت نمودارهای PDF:", e)
        print(traceback.format_exc())

    # خروجی PDF bytes
    try:
        out = pdf.output(dest="S")
        if isinstance(out, bytes):
            return out
        else:
            return out.encode("latin-1", errors="replace")
    except Exception:
        try:
            return pdf.output(dest="S").encode("utf-8", errors="ignore")
        except Exception:
            # fallback
            pdf2 = FPDF()
            pdf2.add_page()
            pdf2.set_font("Arial", size=12)
            pdf2.cell(0, 8, txt=f"Report for {student_name}", ln=True)
            out2 = pdf2.output(dest="S")
            return out2 if isinstance(out2, bytes) else out2.encode("latin-1", errors="replace")

# -------------------------
# پنل‌ها و توابع قبلی (ثابت نگه داشته شده، تنها بهبود ظاهری در پنل دانش‌آموز)
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

# -------------------------
# پنل آمار کلاس (با یک بار نمایش دایره‌ای)
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

    # فقط یکبار نمودار دایره‌ای نمایش داده شود
    if selected_lesson == "همه دروس":
        draw_class_pie_chart(username, selected_lesson=None, title="توزیع وضعیت (همه دروس)")
    else:
        draw_class_pie_chart(username, selected_lesson=selected_lesson, title=f"توزیع وضعیت درس {selected_lesson}")

    # نمودار خطی میانگین کلاس برای درس انتخابی (درصورت وجود)
    if selected_lesson != "همه دروس":
        if st.button("نمایش نمودار روند میانگین کلاس برای این درس"):
            show_class_line_chart(username, selected_lesson)

# -------------------------
# رتبه‌بندی و دانلود (بدون تغییر اساسی)
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

    if st.button("📥 دانلود کارنامه یک دانش‌آموز (PDF)"):
        students = read_sql("SELECT DISTINCT نام_دانش‌آموز FROM students WHERE آموزگار = ?", params=(selected_teacher,))
        if students.empty:
            st.info("هیچ دانش‌آموزی برای این آموزگار ثبت نشده است.")
        else:
            student_choice = st.selectbox("انتخاب دانش‌آموز برای دانلود کارنامه:", students["نام_دانش‌آموز"].unique(), key=f"dl_choice_for_{selected_teacher}")
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
                pdf_bytes = build_student_report_pdf(student_choice, rows, school="", student_class="")
                st.download_button(label=f"📥 دانلود کارنامه {student_choice}.pdf", data=pdf_bytes, file_name=f"report_{student_choice}.pdf", mime="application/pdf")
            except Exception as e:
                st.error("خطا در تولید PDF:")
                st.text(str(e))
                st.text(traceback.format_exc())

# -------------------------
# گزارش فردی دانش‌آموز (آموزگار)
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
    # نمودار خطی
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
    if st.button("📥 دانلود کارنامه این دانش‌آموز"):
        try:
            pdf_bytes = build_student_report_pdf(student_name, rows, school="", student_class="")
            st.download_button(label=f"📥 دانلود کارنامه {student_name}.pdf", data=pdf_bytes, file_name=f"report_{student_name}.pdf", mime="application/pdf")
        except Exception as e:
            st.error("خطا در تولید PDF:")
            st.text(str(e))
            st.text(traceback.format_exc())

# -------------------------
# پنل‌های اصلی (بدون تغییر ساختار، فقط پنل دانش‌آموز کامل‌تر شد)
def show_superadmin_panel():
    st.header("🛠 پنل مدیر سامانه")
    st.write("در این بخش می‌توانید کاربران سامانه را مدیریت کنید.")
    with st.expander("➕ ثبت کاربر جدید"):
        with st.form("register_user_form"):
            username = st.text_input("نام کاربری", key="reg_username")
            full_name = st.text_input("نام کامل", key="reg_fullname")
            password = st.text_input("رمز عبور", type="password", key="reg_password")
            school = st.text_input("نام مدرسه", key="reg_school")
            role = st.selectbox("نقش کاربر", ["آموزگار", "معاون", "مدیر مدرسه", "مدیر سامانه"], key="reg_role")
            expiry_date = st.date_input("تاریخ انقضا", key="reg_expiry")
            submitted = st.form_submit_button("ثبت کاربر")
            if submitted:
                if not username or not password:
                    st.error("نام کاربری و رمز عبور را وارد کنید.")
                else:
                    expiry_str = expiry_date.strftime("%Y/%m/%d")
                    cursor.execute("""
                        INSERT OR REPLACE INTO users
                        (نام_کاربر, نام_کامل, رمز_عبور, نقش, مدرسه, وضعیت, تاریخ_انقضا)
                        VALUES (?, ?, ?, ?, ?, 'فعال', ?)
                    """, (username, full_name, password, role, school, expiry_str))
                    conn.commit()
                    st.success(f"✅ کاربر {username} با نقش {role} ثبت شد.")
                    st.rerun()
    st.subheader("🧑‍🏫 فهرست کاربران")
    df = pd.read_sql_query("SELECT * FROM users", conn)
    if df.empty:
        st.info("هنوز هیچ کاربری ثبت نشده است.")
        return
    st.dataframe(df)
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
            cursor.execute("""
                UPDATE users
                SET رمز_عبور = ?, نقش = ?, مدرسه = ?, وضعیت = ?, تاریخ_انقضا = ?
                WHERE نام_کاربر = ?
            """, (new_password, new_role, new_school, new_status, expiry_str, selected_user))
            conn.commit()
            st.success("✅ اطلاعات کاربر به‌روزرسانی شد.")
            st.rerun()
    with col2:
        if st.button("🗑 حذف کاربر", key="delete_user_btn"):
            cursor.execute("DELETE FROM users WHERE نام_کاربر = ?", (selected_user,))
            conn.commit()
            st.warning(f"❌ کاربر {selected_user} حذف شد.")
            st.rerun()
    st.subheader("🔐 تغییر رمز مدیر سامانه")
    current_password = st.text_input("رمز فعلی", type="password", key="admin_current")
    new_password_admin = st.text_input("رمز جدید", type="password", key="admin_new")
    confirm_password = st.text_input("تکرار رمز جدید", type="password", key="admin_confirm")
    if st.button("ثبت تغییر رمز", key="admin_change_btn"):
        cursor.execute("SELECT * FROM users WHERE نام_کاربر = ? AND رمز_عبور = ?", ("admin", current_password))
        result = cursor.fetchone()
        if not result:
            st.error("❌ رمز فعلی اشتباه است.")
        elif new_password_admin != confirm_password:
            st.error("❌ رمز جدید با تکرار آن مطابقت ندارد.")
        elif len(new_password_admin) < 4:
            st.warning("⚠️ رمز جدید باید حداقل ۴ حرف باشد.")
        else:
            cursor.execute("UPDATE users SET رمز_عبور = ? WHERE نام_کاربر = ?", (new_password_admin, "admin"))
            conn.commit()
            st.success("✅ رمز مدیر سامانه تغییر یافت.")
# اضافه کن: نمایش آمار آموزگاران برای مدیر/معاون (مقاوم و هماهنگ با ساختار جدید)
def show_teacher_statistics_by_admin(school):
    """نمایش آمار آموزگاران برای مدیر یا معاون مدرسه"""
    st.subheader(f"📊 آمار آموزگاران مدرسه: {school}")

    # گرفتن لیست آموزگاران
    teachers_df = read_sql("SELECT نام_کاربر, نام_کامل FROM users WHERE نقش = 'آموزگار' AND مدرسه = ?", params=(school,))
    if teachers_df.empty:
        st.info("هیچ آموزگاری در این مدرسه ثبت نشده است.")
        return

    # نمایش جدول آموزگاران
    st.markdown("### 👥 فهرست آموزگاران")
    try:
        st.dataframe(teachers_df)
    except Exception:
        st.write(teachers_df.head())

    # انتخاب آموزگار برای جزئیات
    unique_key = f"teach_stat_{school}_{uuid.uuid4().hex[:6]}"
    selected_teacher = st.selectbox(
        "انتخاب آموزگار برای مشاهده آمار:",
        teachers_df["نام_کاربر"].unique(),
        key=unique_key
    )

    # تعداد دانش‌آموزان آن آموزگار
    student_count_df = read_sql(
        "SELECT COUNT(*) as تعداد FROM students WHERE آموزگار = ?",
        params=(selected_teacher,)
    )
    total_students = int(student_count_df.iloc[0]["تعداد"]) if not student_count_df.empty else 0
    st.markdown(f"**👥 تعداد دانش‌آموزان:** {total_students}")

    # دروس آن آموزگار
    lessons_df = read_sql("SELECT DISTINCT درس FROM scores WHERE آموزگار = ?", params=(selected_teacher,))
    if lessons_df.empty:
        st.info("هنوز نمره‌ای برای این آموزگار ثبت نشده است.")
        return

   unique_key = f"teach_lesson_{selected_teacher}_{uuid.uuid4().hex[:6]}"
   selected_lesson = st.selectbox(
    "انتخاب درس برای مشاهده وضعیت:",
    lesson_options,
    key=unique_key
)
    # نمودار دایره‌ای
    if selected_lesson == "همه دروس":
        draw_class_pie_chart(selected_teacher, selected_lesson=None, title=f"توزیع وضعیت - همه دروس ({selected_teacher})")
    else:
        draw_class_pie_chart(selected_teacher, selected_lesson=selected_lesson, title=f"توزیع وضعیت درس {selected_lesson} ({selected_teacher})")

    # نمایش جدول میانگین‌ها
    if selected_lesson == "همه دروس":
        df_avg = read_sql("SELECT درس, AVG(نمره) as میانگین_نمره FROM scores WHERE آموزگار = ? GROUP BY درس", params=(selected_teacher,))
        if not df_avg.empty:
            st.markdown("### 📋 میانگین نمرات به ازای هر درس")
            st.dataframe(df_avg)
    else:
        df_avg = read_sql("SELECT نام_دانش‌آموز, AVG(نمره) as میانگین_دانش‌آموز FROM scores WHERE آموزگار = ? AND درس = ? GROUP BY نام_دانش‌آموز", params=(selected_teacher, selected_lesson))
        if not df_avg.empty:
            st.markdown(f"### 📋 میانگین نمرات درس {selected_lesson}")
            st.dataframe(df_avg)


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

def show_assistant_panel(username):
    st.title("🎓 پنل معاون مدرسه")
    df_user = read_sql("SELECT مدرسه FROM users WHERE نام_کاربر = ?", params=(username,))
    school = df_user.iloc[0]["مدرسه"] if not df_user.empty else "نامشخص"
    tab1, tab2 = st.tabs(["📈 آمار آموزگاران", "🏅 رتبه‌بندی"])
    with tab1:
        show_teacher_statistics_by_admin(school)
    with tab2:
        show_class_ranking_panel(username, role="معاون")

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

def show_student_panel(username):
    st.title("🎒 پنل دانش‌آموز")
    df_student = read_sql("SELECT * FROM students WHERE نام_کاربری = ?", params=(username,))
    if df_student.empty:
        st.warning("مشخصات شما در سامانه یافت نشد.")
        return
    student_row = df_student.iloc[0]
    student_name = student_row["نام_دانش‌آموز"]
    teacher = student_row["آموزگار"]
    st.markdown(f"**👤 نام دانش‌آموز:** {student_name}")
    st.markdown(f"**🍎 آموزگار:** {teacher}")
    st.markdown(f"**🏫 کلاس:** {student_row['کلاس']}")
    # خلاصه در یک کارت
    df = read_sql("SELECT درس, AVG(نمره) as میانگین FROM scores WHERE نام_دانش‌آموز = ? GROUP BY درس", params=(student_name,))
    if df.empty:
        st.info("هیچ نمره‌ای برای شما ثبت نشده است.")
        return
    # جدول خلاصه
    st.markdown("### 📄 خلاصه نمرات شما")
    st.dataframe(df)
    # نمودار دایره‌ای عملکرد (یک بار)
    rows = []
    for _, row in df.iterrows():
        lesson = row["درس"]
        student_avg = row["میانگین"]
        class_avg_row = read_sql("SELECT AVG(نمره) as میانگین_کلاس FROM scores WHERE آموزگار = ? AND درس = ?", params=(teacher, lesson))
        class_avg = class_avg_row.iloc[0]["میانگین_کلاس"] if not class_avg_row.empty else student_avg
        status_num = وضعیت_نمره‌ای(student_avg, class_avg)
        rows.append(status_num)
    fig, ax = pie_chart_with_legend({i: rows.count(i) for i in range(1,5)}, title="توزیع عملکرد شما")
    if fig is not None:
        st.pyplot(fig)
    # نمودار خطی برای هر درس (آیکن یا انتخاب درس)
    st.markdown("### 📈 نمودار پیشرفت برای درس")
    lesson_choice = st.selectbox("انتخاب درس:", df["درس"].unique(), key=f"stud_lesson_{username}")
    if lesson_choice:
        show_student_line_chart(student_name, lesson_choice)
    # دانلود کارنامه با نمودارها
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

# -------------------------
# نوار کناری و ورود
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None
if "school" not in st.session_state:
    st.session_state.school = ""

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

if not st.session_state.logged_in:
    st.title("📘 سامانه مدیریت نمرات مدارس")
    st.markdown("به سامانه خوش آمدید. لطفاً وارد شوید:")
    username = st.text_input("نام کاربری", key="login_user")
    password = st.text_input("رمز عبور", type="password", key="login_pass")
    if st.button("ورود"):
        user = read_sql("SELECT * FROM users WHERE نام_کاربر = ? AND رمز_عبور = ?", params=(username, password))
        if not user.empty:
            role = user.iloc[0]["نقش"]
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.session_state.school = user.iloc[0]["مدرسه"] if "مدرسه" in user.columns else ""
            st.success(f"ورود موفقیت‌آمیز به عنوان {role}")
            st.rerun()
        else:
            student = read_sql("SELECT * FROM students WHERE نام_کاربری = ? AND رمز_دانش‌آموز = ?", params=(username, password))
            if not student.empty:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = "دانش‌آموز"
                st.success("ورود موفقیت‌آمیز به عنوان دانش‌آموز 🎒")
                st.rerun()
            else:
                st.error("❌ نام کاربری یا رمز عبور نادرست است.")
else:
    role = st.session_state.role
    username = st.session_state.username
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










