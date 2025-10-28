import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
from supabase_utils import supabase
import uuid
import matplotlib.font_manager as fm  # برای فونت فارسی در نمودارها
import arabic_reshaper
from bidi.algorithm import get_display
def fix_rtl(text):
    """اعمال الگوریتم BiDi برای تصحیح راست‌چین شدن متون فارسی/عربی."""
    if not isinstance(text, str) or not text.strip():
        return text
    
    # ۱. اصلاح شکل حروف
    reshaped_text = arabic_reshaper.reshape(text)
    # ۲. اعمال جهت‌دهی راست‌چین
    return get_display(reshaped_text)
# 🎯 تنظیم صفحه Streamlit
st.set_page_config(page_title="سامانه مدیریت مدرسه", layout="wide")

# 🎨 تنظیم فونت فارسی برای نمودارها
font_path = "fonts/Vazir.ttf"  # مسیر به فونت فارسی در پروژه
font_prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = font_prop.get_name()
plt.rcParams["axes.unicode_minus"] = False

# 📐 تنظیم راست‌چین برای کل صفحه
# 📌 نوار کناری کشویی در Streamlit
with st.sidebar:
    show_sidebar = st.toggle("📂 نمایش منوی اصلی", value=True)

if show_sidebar:
    st.sidebar.title("منوی اصلی")
    st.sidebar.markdown(f"👋 خوش آمدی، **{user.get('نام_کامل', user.get('student', 'کاربر'))}**")

    if st.sidebar.button("🚪 خروج از سامانه"):
        st.session_state.pop("user", None)
        st.success("با موفقیت خارج شدید ✅")
        st.rerun()

# 🎨 استایل RTL و فونت فارسی برای کل صفحه و نوار کناری
st.markdown("""
<style>
/* تنظیمات کلی برای فونت و راست‌چین */
body, div, p, h1, h2, h3, h4, h5, h6, label, span, input, select, textarea, button {
  direction: rtl !important;
  text-align: right !important;
  font-family: 'Vazir', sans-serif !important;
  word-break: keep-all;
}

/* نوار کناری Streamlit */
section[data-testid="stSidebar"] {
  direction: rtl !important;
  text-align: right !important;
  font-family: 'Vazir', sans-serif !important;
  padding: 1rem;
  overflow-wrap: break-word;
  word-break: break-word;
}

/* جلوگیری از شکستن حروف فارسی */
section[data-testid="stSidebar"] * {
  white-space: normal !important;
  word-spacing: normal !important;
  letter-spacing: normal !important;
}

/* موبایل: نوار کناری تمام‌عرض و بدون سایه */
@media screen and (max-width: 768px) {
  section[data-testid="stSidebar"] {
    width: 100% !important;
    position: relative !important;
    box-shadow: none !important;
    border: none !important;
  }
}
</style>
""", unsafe_allow_html=True)

def apply_farsi_style(ax, title=None, xlabel=None, ylabel=None):
    """تنظیم فونت فارسی و راست‌چین برای نمودارهای Matplotlib"""
    from matplotlib import font_manager
    font_path = "fonts/Vazir.ttf"
    font_prop = font_manager.FontProperties(fname=font_path)

    if title:
        ax.set_title(title, fontproperties=font_prop, horizontalalignment='right')
    if xlabel:
        ax.set_xlabel(xlabel, fontproperties=font_prop, horizontalalignment='right')
    if ylabel:
        ax.set_ylabel(ylabel, fontproperties=font_prop, horizontalalignment='right')

    # تنظیم فونت برای تیک‌های محور
    ax.tick_params(axis='x', labelrotation=0)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(font_prop)
        label.set_horizontalalignment('right')

    # تنظیم شبکه
    ax.grid(True, linestyle="--", alpha=0.5)

# -------------------------------
# توابع کمکی Supabase
# -------------------------------

def get_users():
    response = supabase.table("users").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

def get_students():
    response = supabase.table("students").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

def get_scores():
    response = supabase.table("scores").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

def add_user(data):
    supabase.table("users").insert(data).execute()

def add_student(data):
    supabase.table("students").insert(data).execute()

def add_score(data):
    supabase.table("scores").insert(data).execute()

def update_score(student_name, lesson, new_score):
    supabase.table("scores").update({"نمره": new_score}).eq("student", student_name).eq("درس", lesson).execute()

def delete_student(student_name):
    supabase.table("students").delete().eq("نام", student_name).execute()

# -------------------------------
# احراز هویت کاربر
# -------------------------------
def authenticate(username, password):
    # 👑 جستجو در جدول users (مدیر، معاون، آموزگار)
    response = supabase.table("users").select("*").eq("نام_کاربر", username).eq("رمز_عبور", password).execute()
    if response.data:
        return response.data[0]

    # 🎓 جستجو در جدول students (دانش‌آموز)
    response2 = supabase.table("students").select("*").eq("نام_کاربر", username).eq("رمز_عبور", password).execute()
    if response2.data:
        student = response2.data[0]
        student["نقش"] = "دانش‌آموز"
        return student

    return None


# -------------------------------
# ثبت‌نام مدیر یا کاربر جدید
# -------------------------------

def register_user(username, password, role, fullname, school=None):
    data = {
        "نام_کاربر": username,
        "رمز": password,
        "نقش": role,
        "نام_کامل": fullname,
        "مدرسه": school or "",
    }
    supabase.table("users").insert(data).execute()
    st.success("کاربر جدید با موفقیت ثبت شد ✅")

# -------------------------------
# داشبورد اصلی بعد از ورود
# -------------------------------

def main_dashboard(user):
    role = user["نقش"]
    username = user["نام_کاربر"]

    st.sidebar.title("منوی اصلی")
    st.sidebar.markdown(f"👋 خوش آمدی، **{user.get('نام_کامل', user.get('student', 'کاربر'))}**")


    # 🚪 دکمه خروج از سامانه
    if st.sidebar.button("🚪 خروج از سامانه"):
        st.session_state.pop("user", None)
        st.success("با موفقیت خارج شدید ✅")
        st.rerun()

    # 📌 نمایش پنل مناسب بر اساس نقش
    if role == "مدیر سامانه":
        show_superadmin_panel(username)
    elif role == "مدیر مدرسه":
        show_school_admin_panel(username)
    elif role == "معاون":
        show_assistant_panel(username)
    elif role == "آموزگار":
        show_teacher_panel(username)
    elif role == "دانش‌آموز":
        show_student_panel(username)
    else:
        st.error("نقش کاربر نامعتبر است!")

# -------------------------------
# صفحه ورود
# -------------------------------

def login_page():
    st.title("ورود به سامانه مدیریت مدرسه")

    username = st.text_input("نام کاربری:")
    password = st.text_input("رمز عبور:", type="password")

    if st.button("ورود"):
        user = authenticate(username, password)
        if user:
            st.session_state["user"] = user
            st.success("ورود موفقیت‌آمیز ✅")
            st.rerun()
        else:
            st.error("نام کاربری یا رمز اشتباه است.")

    st.markdown("---")
    st.info("اگر حساب ندارید، برای ثبت‌نام با مدیر سامانه تماس بگیرید.")

# -------------------------------
# پنل مدیر سامانه
# -------------------------------
import uuid
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

def show_superadmin_panel(username):
    st.title("🏫 پنل مدیر سامانه")
    st.markdown(f"👤 مدیر: {username}")

    tabs = st.tabs(["مدیریت مدارس", "مدیریت کاربران", "گزارش‌ها"])

    # --- تب مدیریت مدارس ---
    with tabs[0]:
        st.subheader("افزودن یا مشاهده مدارس")

        new_school = st.text_input("نام مدرسه جدید:")
        if st.button("افزودن مدرسه"):
            if new_school.strip():
                school_code = str(uuid.uuid4())[:8]
                supabase.table("schools").insert({
                    "نام_مدرسه": new_school,
                    "کد_مدرسه": school_code
                }).execute()
                st.success("✅ مدرسه با موفقیت افزوده شد.")
                st.rerun()
            else:
                st.warning("لطفاً نام مدرسه را وارد کنید.")

        schools_response = supabase.table("schools").select("*").execute()
        if schools_response.data:
            schools_df = pd.DataFrame(schools_response.data)
            st.markdown("### لیست مدارس ثبت‌شده")
            selected_school = st.selectbox("انتخاب مدرسه برای ویرایش یا حذف:", schools_df["نام_مدرسه"].tolist())
            new_name = st.text_input("نام جدید برای مدرسه:")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("ویرایش نام مدرسه"):
                    if new_name.strip():
                        supabase.table("schools").update({"نام_مدرسه": new_name}).eq("نام_مدرسه", selected_school).execute()
                        st.success("✅ نام مدرسه ویرایش شد.")
                        st.rerun()
                    else:
                        st.warning("نام جدید نمی‌تواند خالی باشد.")
            with col2:
                if st.button("🗑️ حذف مدرسه"):
                    supabase.table("schools").delete().eq("نام_مدرسه", selected_school).execute()
                    st.success("✅ مدرسه حذف شد.")
                    st.rerun()
            st.dataframe(schools_df[["نام_مدرسه", "کد_مدرسه"]])
        else:
            st.info("هیچ مدرسه‌ای ثبت نشده است.")

    # --- تب مدیریت کاربران ---
    with tabs[1]:
        st.subheader("مدیریت کاربران سیستم")

        users_response = supabase.table("users").select("*").execute()
        users_df = pd.DataFrame(users_response.data) if users_response.data else pd.DataFrame()

        if not users_df.empty:
            st.dataframe(users_df[["نام_کاربر", "نام_کامل", "نقش", "مدرسه"]])
            selected_user = st.selectbox("انتخاب کاربر برای ویرایش یا حذف:", users_df["نام_کاربر"].tolist())
            new_fullname = st.text_input("نام کامل جدید:")
            new_password = st.text_input("رمز عبور جدید:", type="password")
            new_role = st.selectbox("نقش جدید:", ["آموزگار", "مدیر مدرسه", "معاون"])
            school_list = supabase.table("schools").select("نام_مدرسه").execute()
            school_names = [row["نام_مدرسه"] for row in school_list.data] if school_list.data else []
            new_school = st.selectbox("مدرسه جدید:", school_names)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("ویرایش اطلاعات کاربر"):
                    supabase.table("users").update({
                        "نام_کامل": new_fullname,
                        "رمز_عبور": new_password,
                        "نقش": new_role,
                        "مدرسه": new_school
                    }).eq("نام_کاربر", selected_user).execute()
                    st.success("✅ اطلاعات کاربر ویرایش شد.")
                    st.rerun()
            with col2:
                if st.button("🗑️ حذف کاربر"):
                    supabase.table("users").delete().eq("نام_کاربر", selected_user).execute()
                    st.success("✅ کاربر حذف شد.")
                    st.rerun()

        st.markdown("### افزودن کاربر جدید")
        col1, col2, col3 = st.columns(3)
        with col1:
            username = st.text_input("نام کاربری:")
        with col2:
            password = st.text_input("رمز عبور:", type="password")
        with col3:
            fullname = st.text_input("نام کامل:")

        role = st.selectbox("نقش کاربر:", ["آموزگار", "مدیر مدرسه", "معاون"])
        school = st.selectbox("مدرسه:", school_names)

        if st.button("افزودن کاربر"):
            if username and password and fullname:
                supabase.table("users").insert({
                    "نام_کاربر": username,
                    "رمز_عبور": password,
                    "نام_کامل": fullname,
                    "نقش": role,
                    "مدرسه": school
                }).execute()
                st.success("✅ کاربر با موفقیت افزوده شد.")
                st.rerun()
            else:
                st.warning("لطفاً تمام فیلدها را پر کنید.")

    # --- تب گزارش‌ها ---
    with tabs[2]:
        st.subheader("گزارش کلی کاربران و مدارس")

        school_count = supabase.table("schools").select("*", count="exact").execute().count or 0
        user_count = supabase.table("users").select("*", count="exact").execute().count or 0

        st.markdown(f"""
        - 🏫 تعداد مدارس: **{school_count}**
        - 👩‍🏫 تعداد کاربران: **{user_count}**
        """)

        


# پنل مدیر مدرسه
# -------------------------------

import streamlit as st
import pandas as pd
# ... (سایر ایمپورت‌ها: plt, supabase, fix_rtl, categorize, show_individual_reports, show_overall_statistics)

def show_school_admin_panel(username):
    global font_prop

    st.title("🏫 پنل مدیر مدرسه")
    st.markdown(f"👤 مدیر مدرسه: {username}")

    # دریافت نام مدرسه
    try:
        user_row = supabase.table("users").select("مدرسه, نام_کامل").eq("نام_کاربر", username).execute()
        if not user_row.data:
            st.error("مدرسه‌ای برای این مدیر ثبت نشده است.")
            return
        school = user_row.data[0]["مدرسه"]
    except Exception as e:
        st.error(f"❌ خطا در دریافت اطلاعات مدرسه: {e}")
        return

    tabs = st.tabs(["مدیریت آموزگاران", "📊 گزارش عملکرد آموزگاران", "📈 آمار کلی مدرسه"])

    # --- تب مدیریت آموزگاران (بدون تغییر) ---
    with tabs[0]:
        st.subheader("👩‍🏫 مدیریت آموزگاران مدرسه")

        try:
            teachers = supabase.table("users").select("*").eq("مدرسه", school).eq("نقش", "آموزگار").execute()
            df_teachers = pd.DataFrame(teachers.data) if teachers.data else pd.DataFrame()
            if not df_teachers.empty:
                st.dataframe(df_teachers[["نام_کاربر", "نام_کامل"]].rename(columns={"نام_کاربر": "نام کاربری", "نام_کامل": "نام کامل"}))
            else:
                st.info("هیچ آموزگاری در این مدرسه ثبت نشده است.")
        except Exception as e:
             st.error(f"❌ خطا در دریافت لیست آموزگاران: {e}")
             df_teachers = pd.DataFrame() 

        st.markdown("### ➕ افزودن آموزگار جدید")
        col1, col2 = st.columns(2)
        with col1:
            new_teacher_username = st.text_input("نام کاربری آموزگار:")
        with col2:
            new_teacher_password = st.text_input("رمز عبور آموزگار:", type="password")
        new_teacher_fullname = st.text_input("نام کامل آموزگار:")

        if st.button("افزودن آموزگار"):
            if new_teacher_username and new_teacher_password and new_teacher_fullname:
                try:
                    supabase.table("users").insert({
                        "نام_کاربر": new_teacher_username,
                        "رمز_عبور": new_teacher_password, 
                        "نام_کامل": new_teacher_fullname,
                        "نقش": "آموزگار",
                        "مدرسه": school
                    }).execute()
                    st.success("✅ آموزگار با موفقیت افزوده شد.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطایی در افزودن آموزگار رخ داد: {e}")

            else:
                st.warning("لطفاً اطلاعات را کامل وارد کنید.")

    # -------------------------------------------------------------------------
    # --- تب گزارش عملکرد آموزگاران (بهینه‌سازی شده برای تشخیص خطا) ---
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.subheader("📊 گزارش عملکرد آموزگاران")

        if df_teachers.empty:
            st.info("هیچ آموزگاری در این مدرسه برای نمایش گزارش وجود ندارد.")
        else:
            teacher_fullnames = sorted(df_teachers["نام_کامل"].tolist())
            selected_teacher_fullname = st.selectbox("انتخاب آموزگار برای مشاهده گزارش:", teacher_fullnames, key="admin_report_teacher_select")

            st.markdown(f"**🔍 سیستم در حال جستجوی نمرات ثبت شده با نام آموزگار:** `{selected_teacher_fullname}`")

            # دریافت نمرات مربوط به آموزگار انتخاب شده
            try:
                # کوئری دقیق بر اساس نام کامل آموزگار
                scores_response = supabase.table("scores").select("*").eq("آموزگار", selected_teacher_fullname).execute()
                scores_df_teacher = pd.DataFrame(scores_response.data) if scores_response.data else pd.DataFrame()
            except Exception as e:
                st.error(f"❌ خطا در اجرای کوئری نمرات: {e}")
                scores_df_teacher = pd.DataFrame() 

            if scores_df_teacher.empty:
                st.error("⚠️ **هیچ نمره‌ای با این نام آموزگار پیدا نشد!**")
                # نمایش پیام عیب‌یابی واضح
                st.warning(
                    f"""
                    **تعداد نمرات پیدا شده: 0**
                    
                    اگر نمره ثبت شده، تنها دلیل عدم نمایش **ناهماهنگی نام آموزگار** در دو جدول است.
                    لطفاً نام آموزگار را در جدول `users` با نام ثبت شده در ستون `آموزگار` در جدول `scores` **دقیقاً یکسان کنید.**
                    """
                )
            else:
                st.success(f"✅ **{len(scores_df_teacher)}** نمره از آموزگار **{selected_teacher_fullname}** پیدا شد. آمار در زیر نمایش داده می‌شود.")
                st.divider()
                
                # نمایش گزارش‌ها (حذف کشوی مدیریت نمرات)
                report_option = st.radio(
                    "انتخاب نوع گزارش:",
                    ["📊 گزارش‌های فردی دانش‌آموزان", "📈 آمار کلی کلاس"],
                    horizontal=True,
                    key="admin_report_type"
                )

                if report_option == "📊 گزارش‌های فردی دانش‌آموزان":
                    # توجه: توابع show_individual_reports باید در دسترس باشد.
                    show_individual_reports(scores_df_teacher)
                else:
                    # توجه: توابع show_overall_statistics باید در دسترس باشد.
                    show_overall_statistics(scores_df_teacher)


    # --- تب آمار کلی مدرسه (بدون تغییر) ---
    with tabs[2]:
        st.subheader("📈 آمار کلی مدرسه")
        try:
            total_students = supabase.table("students").select("id", count="exact").eq("مدرسه", school).execute().count or 0
            total_teachers = supabase.table("users").select("id", count="exact").eq("مدرسه", school).eq("نقش", "آموزگار").execute().count or 0

            st.markdown(f"""
            - 👩‍🏫 تعداد آموزگاران: **{total_teachers}**
            - 👨‍🎓 تعداد دانش‌آموزان: **{total_students}**
            """)
        except Exception as e:
            st.error(f"❌ خطا در دریافت آمار کلی مدرسه: {e}")

# -------------------------------
# پنل معاون مدرسه
# -------------------------------

import streamlit as st
import pandas as pd
# ... (سایر ایمپورت‌ها مانند: plt, supabase, fix_rtl, categorize, show_individual_reports, show_overall_statistics باید در دسترس باشند)

def show_assistant_panel(username):
    global font_prop

    st.title("🧾 پنل معاون مدرسه")
    st.markdown(f"👤 معاون: {username}")

    # 1. دریافت نام مدرسه
    try:
        user_row = supabase.table("users").select("مدرسه").eq("نام_کاربر", username).execute()
        if not user_row.data:
            st.error("مدرسه‌ای برای این معاون ثبت نشده است.")
            return
        school = user_row.data[0]["مدرسه"]
    except Exception as e:
        st.error(f"❌ خطا در دریافت اطلاعات مدرسه: {e}")
        return

    # 2. دریافت لیست آموزگاران
    try:
        teachers = supabase.table("users").select("نام_کامل").eq("مدرسه", school).eq("نقش", "آموزگار").execute()
        df_teachers = pd.DataFrame(teachers.data) if teachers.data else pd.DataFrame()
    except Exception as e:
         st.error(f"❌ خطا در دریافت لیست آموزگاران: {e}")
         df_teachers = pd.DataFrame() 

    # 3. تعریف تب‌ها (بدون مدیریت آموزگاران)
    tabs = st.tabs(["📊 گزارش عملکرد آموزگاران", "📈 آمار کلی مدرسه"])

    # -------------------------------------------------------------------------
    # --- تب گزارش عملکرد آموزگاران (مشابه مدیر مدرسه) ---
    # -------------------------------------------------------------------------
    with tabs[0]:
        st.subheader("📊 گزارش عملکرد آموزگاران")

        if df_teachers.empty:
            st.info("هیچ آموزگاری در این مدرسه برای نمایش گزارش وجود ندارد.")
        else:
            teacher_fullnames = sorted(df_teachers["نام_کامل"].tolist())
            selected_teacher_fullname = st.selectbox("انتخاب آموزگار برای مشاهده گزارش:", teacher_fullnames, key="assistant_report_teacher_select")

            st.markdown(f"**🔍 سیستم در حال جستجوی نمرات ثبت شده با نام آموزگار:** `{selected_teacher_fullname}`")

            # دریافت نمرات مربوط به آموزگار انتخاب شده
            try:
                # کوئری دقیق بر اساس نام کامل آموزگار (این کلید حل مشکل است)
                scores_response = supabase.table("scores").select("*").eq("آموزگار", selected_teacher_fullname).execute()
                scores_df_teacher = pd.DataFrame(scores_response.data) if scores_response.data else pd.DataFrame()
            except Exception as e:
                st.error(f"❌ خطا در اجرای کوئری نمرات: {e}")
                scores_df_teacher = pd.DataFrame() 

            if scores_df_teacher.empty:
                st.error("⚠️ **هیچ نمره‌ای با این نام آموزگار پیدا نشد!**")
                st.warning(
                    """
                    **تعداد نمرات پیدا شده: 0**
                    دلیل عدم نمایش آمار، ناهماهنگی نام آموزگار در جدول کاربران و جدول نمرات است.
                    """
                )
            else:
                st.success(f"✅ **{len(scores_df_teacher)}** نمره از آموزگار **{selected_teacher_fullname}** پیدا شد.")
                st.divider()
                
                # نمایش گزارش‌ها (استفاده مجدد از توابع پنل آموزگار)
                report_option = st.radio(
                    "انتخاب نوع گزارش:",
                    ["📊 گزارش‌های فردی دانش‌آموزان", "📈 آمار کلی کلاس"],
                    horizontal=True,
                    key="assistant_report_type"
                )

                if report_option == "📊 گزارش‌های فردی دانش‌آموزان":
                    show_individual_reports(scores_df_teacher)
                else:
                    show_overall_statistics(scores_df_teacher)


    # -------------------------------------------------------------------------
    # --- تب آمار کلی مدرسه (مشابه مدیر مدرسه) ---
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.subheader("📈 آمار کلی مدرسه")
        try:
            total_students = supabase.table("students").select("id", count="exact").eq("مدرسه", school).execute().count or 0
            # تعداد آموزگاران
            total_teachers = len(df_teachers)

            st.markdown(f"""
            - 👩‍🏫 تعداد آموزگاران: **{total_teachers}**
            - 👨‍🎓 تعداد دانش‌آموزان: **{total_students}**
            """)
        except Exception as e:
            st.error(f"❌ خطا در دریافت آمار کلی مدرسه: {e}")
# -------------------------------
# پنل آموزگار
# -------------------------------
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from matplotlib import font_manager
# فرض بر این است که فایل اتصال به دیتابیس (supabase_utils) و متغیر supabase در دسترس هستند
from supabase_utils import supabase 
import os
from io import BytesIO # برای توابع PDF (اگر دارید)
import base64 # برای توابع PDF (اگر دارید)

# -------------------- ایمپورت‌های جدید برای اصلاح راست‌چین (BiDi) --------------------
import arabic_reshaper
from bidi.algorithm import get_display

# -------------------------------------------------------------------------------------
# 🛠️ تنظیمات فونت سراسری و RTL
# -------------------------------------------------------------------------------------

# مسیر فونت فارسی
font_path = "fonts/Vazir.ttf" 
absolute_font_path = os.path.abspath(font_path)

# 🎨 تنظیم فونت فارسی (مخصوص نمودارها)
try:
    font_prop = font_manager.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = font_prop.get_name()
    plt.rcParams["axes.unicode_minus"] = False
except FileNotFoundError:
    st.error("فایل فونت Vazir.ttf پیدا نشد. لطفاً آن را در پوشه 'fonts' قرار دهید.")
    font_prop = None

# 📐 تنظیم راست‌چین سراسری برای کل صفحه (حل مشکل بهم ریختگی متن Streamlit)
st.markdown("""
    <style>
    /* تنظیم فونت و جهت برای تمام عناصر Streamlit */
    body, div, p, h1, h2, h3, h4, h5, h6, label, span, input, select, textarea, button, th, td {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Vazir', sans-serif !important; 
    }
    /* راست‌چین کردن متن و هدرهای ستون‌های جدول Streamlit */
    .stDataFrame, .stDataFrame .header {
        direction: rtl !important;
        text-align: right !important;
    }
    /* اجزای فرم (ورودی‌ها، کشوها) */
    .stSelectbox, .stTextInput, .stButton, .stTextarea {
        direction: rtl;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------
# توابع کمکی (برای RTL و دسته‌بندی)
# -------------------------------

def fix_rtl(text):
    """(فقط برای Matplotlib) اعمال BiDi برای تصحیح راست‌چین شدن متون فارسی/عربی."""
    if not isinstance(text, str) or not text.strip():
        return text
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def categorize(score):
    """دسته‌بندی سطح عملکرد بر اساس نمره (فرض بر اساس نمره 1 تا 4)."""
    try:
        score = float(score)
    except:
        return "نامشخص" # متن عادی، نه fix_rtl

    if score >= 3.5:
        return "خیلی خوب"
    elif score >= 2.5:
        return "خوب"
    elif score >= 1.5:
        return "قابل قبول"
    else:
        return "نیاز به تلاش بیشتر"

# -------------------------------
# 1. ماژول مدیریت و ثبت نمره
# -------------------------------

def show_management_panel(full_name, school_name, students_df):
    """شامل لیست دانش‌آموزان، افزودن دانش‌آموز، تغییر رمز، ثبت نمره و مدیریت نمرات."""
    
    # 📚 لیست دانش‌آموزان
    st.subheader("📚 لیست دانش‌آموزان شما")
    if not students_df.empty:
        # ✅ FIX: حذف fix_rtl از نام ستون‌ها
        st.dataframe(students_df[["student", "پایه", "کلاس", "مدرسه"]].rename(
            columns={
                "student": "دانش‌آموز",
                "پایه": "پایه",
                "کلاس": "کلاس",
                "مدرسه": "مدرسه"
            }
        ))
    else:
        st.info("هنوز دانش‌آموزی برای شما ثبت نشده است.")

    # ➕ افزودن دانش‌آموز
    st.subheader("➕ افزودن دانش‌آموز جدید")
    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("نام کامل دانش‌آموز:")
        student_username = st.text_input("نام کاربری دانش‌آموز:")
    with col2:
        grade = st.selectbox("پایه:", ["اول", "دوم", "سوم", "چهارم", "پنجم", "ششم"], key="grade_new")
        class_name = st.text_input("کلاس:")
    school_name_input = st.text_input("نام مدرسه:", value=school_name, disabled=True)
    student_password = st.text_input("رمز ورود دانش‌آموز:", type="password")

    if st.button("ثبت دانش‌آموز"):
        if student_name and student_username and student_password and class_name:
            try:
                supabase.table("students").insert({
                    "student": student_name,
                    "نام_کاربر": student_username,
                    "رمز_عبور": student_password, 
                    "پایه": grade,
                    "کلاس": class_name,
                    "مدرسه": school_name_input,
                    "آموزگار": full_name,
                    "تاریخ_ثبت": datetime.date.today().isoformat()
                }).execute()
                st.success("✅ دانش‌آموز با موفقیت ثبت شد.")
                st.rerun()
            except Exception as e:
                 st.error("❌ خطایی در ثبت دانش‌آموز رخ داد. (نام کاربری تکراری یا مشکل پایگاه داده)")
        else:
            st.warning("لطفاً تمام فیلدهای ضروری را پر کنید.")

    # 🔐 تغییر رمز ورود دانش‌آموز
    st.subheader("🔐 تغییر رمز ورود دانش‌آموز")
    if not students_df.empty:
        student_usernames = students_df["نام_کاربر"].dropna().tolist()
        selected_user = st.selectbox("انتخاب دانش‌آموز برای تغییر رمز:", student_usernames, key="change_pass_user")
        new_password = st.text_input("رمز جدید:", type="password", key="new_student_pass")
        if st.button("ثبت رمز جدید", key="btn_change_pass"):
            if new_password:
                supabase.table("students").update({"رمز_عبور": new_password}).eq("نام_کاربر", selected_user).execute() 
                st.success("✅ رمز جدید با موفقیت ثبت شد.")
                st.rerun()
            else:
                st.warning("رمز جدید نمی‌تواند خالی باشد.")
    else:
        st.info("هیچ دانش‌آموزی برای شما ثبت نشده است.")

    # ✏️ ثبت نمره برای دانش‌آموز
    st.subheader("✏️ ثبت نمره برای دانش‌آموز")
    if not students_df.empty:
        selected_student_score = st.selectbox("انتخاب دانش‌آموز:", students_df["student"].tolist(), key="submit_score_student")
        lesson = st.text_input("نام درس:")
        score = st.selectbox("نمره (۱ تا ۴):", [1, 2, 3, 4]) 
        if st.button("ثبت نمره", key="btn_add_score"):
            if lesson:
                supabase.table("scores").insert({
                    "student": selected_student_score,
                    "درس": lesson,
                    "نمره": score,
                    "آموزگار": full_name,
                    "تاریخ": datetime.date.today().isoformat()
                }).execute()
                st.success("✅ نمره ثبت شد.")
                st.rerun()
            else:
                st.warning("لطفاً نام درس را وارد کنید.")
    else:
        st.info("برای ثبت نمره ابتدا باید دانش‌آموزی ثبت کنید.")
        
    # ----------------------------------------------------
    # مدیریت نمرات ثبت شده (جدول نمرات حذف شد)
    # ----------------------------------------------------
    st.subheader("🛠️ مدیریت نمرات ثبت‌شده")
    scores_response = supabase.table("scores").select("*").eq("آموزگار", full_name).execute()
    scores_df = pd.DataFrame(scores_response.data) if scores_response.data else pd.DataFrame()

    if not scores_df.empty:
        selected_row = st.selectbox(
            "انتخاب نمره برای ویرایش یا حذف (دانش‌آموز - درس - نمره):",
            scores_df.apply(lambda r: f"{r['student']} - {r['درس']} - {r['نمره']} ({r['id']})", axis=1).tolist(),
            key="select_edit_delete"
        )
        
        selected_id = int(selected_row.split('(')[-1].strip(')'))
        selected_score = scores_df.loc[scores_df["id"] == selected_id].iloc[0]

        new_score = st.selectbox("نمره جدید:", [1, 2, 3, 4], index=int(selected_score["نمره"]) - 1, key="edit_new_score")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("ویرایش نمره", key="btn_edit_score"):
                supabase.table("scores").update({"نمره": new_score}).eq("id", selected_id).execute()
                st.success("✅ نمره ویرایش شد.")
                st.rerun()
        with col2:
            if st.button("🗑️ حذف نمره", key="btn_delete_score"):
                supabase.table("scores").delete().eq("id", selected_id).execute()
                st.success("✅ نمره حذف شد.")
                st.rerun()
    else:
        st.info("هنوز نمره‌ای برای شما ثبت نشده است.")


# -------------------------------
# 2. ماژول گزارش‌های فردی
# -------------------------------

def show_individual_reports(df):
    """بخش گزارش فردی: انتخاب دانش‌آموز، درس، نمایش نمودار خطی، دایره‌ای و جدول نمرات."""
    
    global font_prop

    st.info("دانش‌آموز و درس مورد نظر را انتخاب کنید تا گزارش عملکرد او را مشاهده نمایید.")

    all_students = sorted(df['student'].unique().tolist())
    selected_student = st.selectbox("دانش‌آموز مورد نظر را انتخاب کنید:", all_students, key="rep_student")
    
    student_df = df[df['student'] == selected_student].copy()
    available_lessons = sorted(student_df['درس'].unique().tolist())
    
    if not available_lessons:
        st.warning("برای این دانش‌آموز هنوز نمره‌ای ثبت نشده است.")
        return
        
    selected_lesson = st.selectbox("درس مورد نظر را انتخاب کنید:", available_lessons, key="rep_lesson")
    
    lesson_df = student_df[student_df["درس"] == selected_lesson].sort_values("تاریخ", ascending=True).reset_index(drop=True)
    lesson_df["شماره نمره"] = lesson_df.index + 1

    st.divider()
    
    # --- 1. Score Table (جدول نمرات ثبت شده آن درس) ---
    st.subheader(f"جدول نمرات ثبت شده {selected_student} در درس {selected_lesson}")
    st.dataframe(lesson_df[["شماره نمره", "نمره", "تاریخ"]].rename(
        columns={
            "شماره نمره": "شماره نمره",
            "نمره": "نمره",
            "تاریخ": "تاریخ ثبت"
        }
    ))

    # --- 2. Line Chart (روند پیشرفت) ---
    st.subheader(f"📈 نمودار خطی روند پیشرفت {selected_student} در درس {selected_lesson}")
    fig_line, ax_line = plt.subplots(figsize=(7, 4)) 
    ax_line.plot(lesson_df["شماره نمره"], lesson_df["نمره"], marker="o", linewidth=2, color="#007ACC")
    
    # ✅ FIX: اعمال font_prop و fix_rtl (فقط برای Matplotlib)
    ax_line.set_title(fix_rtl(f"روند نمرات {selected_lesson}"), fontproperties=font_prop, fontsize=14)
    ax_line.set_xlabel(fix_rtl("شماره نمره"), fontproperties=font_prop)
    ax_line.set_ylabel(fix_rtl("نمره"), fontproperties=font_prop)
    ax_line.tick_params(axis='x', rotation=0)
    ax_line.set_ylim(0.5, 4.5) 
    st.pyplot(fig_line)

    # --- 3. Pie Chart (سطح عملکرد) ---
    st.subheader(f"🎯 نمودار دایره‌ای توزیع نمرات ثبت شده در درس {selected_lesson}") 
    
    def categorize_single_score(score):
        return {1: "نیاز به تلاش بیشتر", 2: "قابل قبول", 3: "خوب", 4: "خیلی خوب"}.get(score, "نامشخص")
        
    lesson_df["سطح عملکرد"] = lesson_df["نمره"].apply(categorize_single_score)
    performance_counts = lesson_df["سطح عملکرد"].value_counts()
    
    # ✅ FIX: اعمال font_prop و fix_rtl (فقط برای Matplotlib)
    labels_bidi = [fix_rtl(label) for label in performance_counts.index]
    
    fig_pie, ax_pie = plt.subplots(figsize=(5.5, 5.5)) 
    ax_pie.axis('equal') 
    
    ax_pie.pie(
        performance_counts,
        labels=labels_bidi, 
        autopct=lambda pct: f"{pct:.1f}%",
        startangle=140,
        colors=["#FF9999", "#FFD580", "#90EE90", "#66B2FF"],
        wedgeprops={'linewidth': 1, 'edgecolor': 'white'}, 
        pctdistance=0.7, 
        labeldistance=1.1,
        textprops={'fontproperties': font_prop} 
    )
    
    ax_pie.set_title(fix_rtl(f"توزیع نمرات ثبت شده"), fontproperties=font_prop, fontsize=12)
    st.pyplot(fig_pie)
    avg_score = lesson_df["نمره"].mean()
    st.success(f"میانگین نمره این دانش‌آموز در این درس: {round(avg_score, 2)} ({categorize(avg_score)})")


# -------------------------------
# 3. ماژول آمار کلی (رتبه‌بندی کلی اضافه شد)
# -------------------------------

def show_overall_statistics(df):
    """بخش آمار کلی کلاس: شامل رتبه‌بندی کلی و آمار درسی."""
    
    global font_prop

    # -------------------------------------------
    # 🏆 رتبه‌بندی کلی دانش‌آموزان (جدید)
    # -------------------------------------------
    st.subheader("🏆 رتبه‌بندی کلی دانش‌آموزان (تمام دروس)")
    
    overall_avg_all = df.groupby("student")["نمره"].mean().reset_index()
    overall_avg_all["سطح عملکرد"] = overall_avg_all["نمره"].apply(categorize)
    
    st.dataframe(overall_avg_all.sort_values("نمره", ascending=False).rename(
        columns={
            "student": "نام دانش‌آموز",
            "نمره": "میانگین کلی نمره",
            "سطح عملکرد": "سطح عملکرد"
        }
    ))
    
    st.markdown("---")
    
    # -------------------------------------------
    # 📈 آمار درسی (نمودار دایره‌ای)
    # -------------------------------------------
    st.info("درس مورد نظر را انتخاب کنید تا توزیع سطح عملکرد دانش‌آموزان کلاس در آن درس را مشاهده نمایید.")

    available_lessons = sorted(df['درس'].unique().tolist())
    selected_lesson = st.selectbox("درس مورد نظر را انتخاب کنید:", available_lessons, key="overall_lesson")

    lesson_df_all = df[df["درس"] == selected_lesson].copy()
    avg_per_student = lesson_df_all.groupby("student")["نمره"].mean().reset_index()
    avg_per_student["سطح عملکرد"] = avg_per_student["نمره"].apply(categorize)
    performance_counts = avg_per_student["سطح عملکرد"].value_counts()

    st.divider()
    
    # --- Overall Class Pie Chart ---
    st.subheader(f"📈 نمودار دایره‌ای توزیع عملکرد دانش‌آموزان در درس {selected_lesson}") 
    
    # ✅ FIX: اعمال font_prop و fix_rtl (فقط برای Matplotlib)
    labels_bidi = [fix_rtl(label) for label in performance_counts.index]
    
    fig_pie, ax_pie = plt.subplots(figsize=(6, 6)) 
    ax_pie.axis('equal') 
    
    ax_pie.pie(
        performance_counts,
        labels=labels_bidi, 
        autopct=lambda pct: f"{pct:.1f}%",
        startangle=140,
        colors=["#FF9999", "#FFD580", "#90EE90", "#66B2FF"],
        wedgeprops={'linewidth': 1, 'edgecolor': 'white'}, 
        pctdistance=0.7, 
        labeldistance=1.1,
        textprops={'fontproperties': font_prop}
    )
    
    ax_pie.set_title(fix_rtl(f"توزیع سطح عملکرد کلاس"), fontproperties=font_prop, fontsize=14)
    st.pyplot(fig_pie)
    
    class_avg = round(avg_per_student["نمره"].mean(), 2)
    st.success(f"میانگین کلی نمرات دانش‌آموزان شما در این درس: {class_avg}")
    
    # نمایش جدول میانگین نمرات (رتبه‌بندی درسی)
    st.markdown("---")
    st.subheader("🏆 رتبه‌بندی دانش‌آموزان در این درس")
    st.dataframe(avg_per_student.sort_values("نمره", ascending=False).rename(
        columns={
            "student": "نام دانش‌آموز",
            "نمره": "میانگین نمره",
            "سطح عملکرد": "سطح عملکرد"
        }
    ))


# -------------------------------
# تابع اصلی (Router) - ماژولار شده
# -------------------------------

def show_teacher_panel(username):
    # تنظیمات کلی صفحه 
    if 'layout' not in st.session_state:
         st.set_page_config(layout="wide")
         st.session_state['layout'] = 'wide'

    st.title("👩‍🏫 پنل آموزگار")

    # 📌 دریافت اطلاعات آموزگار و هندل کردن خطای اتصال به دیتابیس
    try:
        teacher_info = supabase.table("users").select("نام_کامل, مدرسه").eq("نام_کاربر", username).limit(1).execute()
    except Exception as e:
        st.error(f"❌ خطا در اتصال به پایگاه داده (users): {e}")
        full_name = username
        school_name = "نامشخص"
        students_df = pd.DataFrame()
        scores_df = pd.DataFrame()
        
    else:
        full_name = teacher_info.data[0]["نام_کامل"] if teacher_info.data else username
        school_name = teacher_info.data[0]["مدرسه"] if teacher_info.data else "نامشخص"

        try:
            # 📚 دریافت لیست دانش‌آموزان و نمرات 
            students_response = supabase.table("students").select("*").eq("آموزگار", full_name).execute()
            students_df = pd.DataFrame(students_response.data) if students_response.data else pd.DataFrame()
            
            scores_response = supabase.table("scores").select("*").eq("آموزگار", full_name).execute()
            scores_df = pd.DataFrame(scores_response.data) if scores_response.data else pd.DataFrame()
        except Exception as e:
            st.error(f"❌ خطا در اتصال به پایگاه داده (students/scores): {e}")
            students_df = pd.DataFrame()
            scores_df = pd.DataFrame()


    # نمایش اطلاعات آموزگار
    st.markdown(f'<div style="text-align: right; direction: rtl;"><b>👤 آموزگار:</b> {full_name} | <b>🏫 مدرسه:</b> {school_name}</div>', unsafe_allow_html=True)
    st.divider()

    # --- Navigation Selectbox (ماژولار کردن بخش‌ها در سایدبار) ---
    st.sidebar.title("بخش‌های پنل")
    menu_options_display = {
        "management": "📝 مدیریت نمره و دانش‌آموز",
        "reports": "📊 گزارش‌های فردی (دانش‌آموز - درس)",
        "overall": "📈 آمار کلی کلاس",
    }
    menu_options_keys = list(menu_options_display.keys())
    
    selected_option_key = st.sidebar.selectbox(
        "انتخاب بخش:", 
        menu_options_keys, 
        format_func=lambda x: menu_options_display[x] 
    )

    st.header(menu_options_display[selected_option_key])

    # --- نمایش محتوای بخش انتخاب شده ---
    if selected_option_key == "management":
        show_management_panel(full_name, school_name, students_df)
    
    elif selected_option_key == "reports":
        if scores_df.empty:
            st.warning("برای مشاهده گزارش‌ها، ابتدا باید نمره‌ای ثبت کنید.")
        else:
            show_individual_reports(scores_df)
            
    elif selected_option_key == "overall":
        if scores_df.empty:
            st.warning("برای مشاهده آمار کلی، ابتدا باید نمره‌ای ثبت کنید.")
        else:
            show_overall_statistics(scores_df)

# -------------------------------------------------------------------------------------
# **توجه: کد زیر مربوط به سایر بخش‌های برنامه شما (مانند پنل دانش‌آموز، مدیر و...) است**
# **لطفاً این بخش‌ها را از فایل اصلی خودتان کپی کنید و در اینجا قرار دهید.**
# -------------------------------------------------------------------------------------

# def show_student_panel(username):
#     # ... (کد پنل دانش‌آموز که قبلاً داشتید) ...
#     pass

# def show_superadmin_panel(username):
#     # ... (کد پنل مدیر سامانه) ...
#     pass

# ... (سایر توابع پنل‌ها) ...

# def main_dashboard(user):
#     # ... (تابع مسیریاب شما) ...
#     pass

# def login_page():
#     # ... (تابع ورود شما) ...
#     pass

# def app():
#     # ... (تابع اصلی اجرای برنامه) ...
#     pass

# if __name__ == "__main__":
#     app()
# پنل دانش‌آموز + PDF کارنامه
# -------------------------------
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from io import BytesIO # ✅ تصحیح شده
import os
import base64
from weasyprint import HTML
# اگر از supabase استفاده می‌کنید، این خط را حفظ کنید
# from supabase_utils import supabase 

# -------------------- ایمپورت‌های جدید برای اصلاح راست‌چین (BiDi) --------------------
import arabic_reshaper
from bidi.algorithm import get_display

# 🛠️ تابع اصلی برای تصحیح راست‌چین متون در نمودارها (برای Matplotlib)
def fix_rtl(text):
    """اعمال الگوریتم BiDi برای تصحیح راست‌چین شدن متون فارسی/عربی در محیط Matplotlib."""
    if not isinstance(text, str) or not text.strip():
        return text
    
    # ۱. اصلاح شکل حروف
    reshaped_text = arabic_reshaper.reshape(text)
    # ۲. اعمال جهت‌دهی راست‌چین
    return get_display(reshaped_text)
# -------------------------------------------------------------------------------------

# مسیر فونت فارسی
font_path = "fonts/Vazir.ttf"
absolute_font_path = os.path.abspath(font_path)

# تابع کمکی تبدیل نمودار به Base64
def convert_image_to_base64(fig):
    # ✅ FIX: اصلاح Bytes瓯 به BytesIO
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=300)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

# تابع دسته‌بندی سطح عملکرد
def categorize(score):
    try:
        score = float(score)
    except:
        return "نامشخص"

    if score >= 3.5:
        return "خیلی خوب"
    elif score >= 2.5:
        return "خوب"
    elif score >= 1.5:
        return "قابل قبول"
    else:
        return "نیاز به تلاش بیشتر"
        
# -------------------------------------------------------------------------------------

def show_student_panel(username):
    font_prop = font_manager.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = font_prop.get_name()
    plt.rcParams["axes.unicode_minus"] = False

    st.title("🎓 پنل دانش‌آموز") 

    student_response = supabase.table("students").select("*").eq("نام_کاربر", username).execute()
    if not student_response.data:
        st.error("❌ اطلاعات دانش‌آموز پیدا نشد.") 
        return
    student_info = student_response.data[0]
    full_name = student_info["student"]
    school_name = student_info.get("مدرسه", "نامشخص")
    class_name = student_info.get("کلاس", "نامشخص")
    grade = student_info.get("پایه", "نامشخص")

    st.markdown(
        f"""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:15px; text-align: right; direction: rtl;">
        <b>👤 نام دانش‌آموز:</b> {full_name}<br>
        <b>🏫 مدرسه:</b> {school_name}<br>
        <b>📘 پایه:</b> {grade}<br>
        <b>🧩 کلاس:</b> {class_name}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    scores_response = supabase.table("scores").select("درس, نمره").eq("student", full_name).execute()
    if not scores_response.data:
        st.info("هنوز نمره‌ای برای شما ثبت نشده است.") 
        return
    scores_df = pd.DataFrame(scores_response.data)

    lessons = scores_df["درس"].unique().tolist()
    
    lesson_options = ["📊 آمار کلی"] + lessons
    selected_lesson = st.selectbox("درس مورد نظر خود را انتخاب کنید:", lesson_options) 
    
    selected_lesson_display = selected_lesson

    if selected_lesson != "📊 آمار کلی":
        lesson_df = scores_df[scores_df["درس"] == selected_lesson].reset_index(drop=True)
        lesson_df["شماره نمره"] = lesson_df.index + 1

        # --- نمودار خطی (Line Chart) ---
        st.subheader(f"📈 روند پیشرفت در درس {selected_lesson_display}") 
        # FIX: اندازه نمودار
        fig_line, ax_line = plt.subplots(figsize=(6, 3.5)) 
        ax_line.plot(
            lesson_df["شماره نمره"],
            lesson_df["نمره"],
            marker="o",
            linewidth=2,
            color="#007ACC"
        )
        
        ax_line.set_title(fix_rtl(f"نمودار پیشرفت در درس {selected_lesson_display}"), fontproperties=font_prop)
        ax_line.set_xlabel(fix_rtl("شماره نمره"), fontproperties=font_prop)
        ax_line.set_ylabel(fix_rtl("نمره"), fontproperties=font_prop)
        ax_line.tick_params(axis='x', rotation=0)
        st.pyplot(fig_line)

        # --- نمودار دایره‌ای (Pie Chart) ---
        st.subheader(f"🎯 سطح عملکرد در درس {selected_lesson_display}") 
        lesson_df["سطح عملکرد"] = lesson_df["نمره"].apply(categorize)
        performance_counts = lesson_df["سطح عملکرد"].value_counts()
        
        labels_bidi = [fix_rtl(label) for label in performance_counts.index]
        
        # FIX: اندازه نمودار
        fig_pie, ax_pie = plt.subplots(figsize=(4.5, 4.5)) 
        ax_pie.axis('equal') 
        
        wedges, texts, autotexts = ax_pie.pie(
            performance_counts,
            labels=labels_bidi, 
            autopct=lambda pct: f"{pct:.1f}%",
            startangle=140,
            colors=["#FF9999", "#FFD580", "#90EE90", "#66B2FF"],
            wedgeprops={'linewidth': 1, 'edgecolor': 'white', 'width': 0.4}, 
            pctdistance=0.7, 
            labeldistance=1.1
        )
        
        for t in texts:
            t.set_fontproperties(font_prop)
            t.set_fontsize(10)
            x, y = t.get_position()
            if x > 0:
                t.set_horizontalalignment('right') 
            else:
                t.set_horizontalalignment('left') 
                
        for autotext in autotexts:
            autotext.set_fontproperties(font_prop)
            autotext.set_fontsize(10)
            
        ax_pie.set_title(fix_rtl(f"توزیع سطح عملکرد - {selected_lesson_display}"), fontproperties=font_prop, fontsize=12)
        st.pyplot(fig_pie)

    else:
        # --- آمار کلی ---
        st.subheader("📋 کارنامه کلی شما") 
        avg_per_lesson = scores_df.groupby("درس")["نمره"].mean().reset_index()
        avg_per_lesson["سطح عملکرد"] = avg_per_lesson["نمره"].apply(categorize)

        class_data = supabase.table("scores").select("درس, نمره").execute().data
        class_df = pd.DataFrame(class_data)
        class_avg = class_df.groupby("درس")["نمره"].mean().reset_index().rename(columns={"نمره": "میانگین کلاس"})
        report_df = pd.merge(avg_per_lesson, class_avg, on="درس", how="left")
        report_df["مقایسه با کلاس"] = report_df.apply(
            lambda x: "⬆️ بالاتر از میانگین" if x["نمره"] > x["میانگین کلاس"]
            else "⬇️ پایین‌تر از میانگین" if x["نمره"] < x["میانگین کلاس"]
            else "⚖️ برابر با میانگین", axis=1
        )
        
        st.table(report_df[["درس", "نمره", "سطح عملکرد", "میانگین کلاس", "مقایسه با کلاس"]].rename(
            columns={
                "درس": "درس", 
                "نمره": "نمره", 
                "سطح عملکرد": "سطح عملکرد", 
                "میانگین کلاس": "میانگین کلاس", 
                "مقایسه با کلاس": "مقایسه با کلاس"
            }
        ))

        # --- نمودار پیشرفت کلی دروس (Line Chart) ---
        st.subheader("📊 روند پیشرفت کلی دروس") 
        fig_all, ax_all = plt.subplots(figsize=(6, 3.5))
        colors = plt.cm.tab10.colors
        for i, lesson in enumerate(scores_df["درس"].unique()):
            lesson_df = scores_df[scores_df["درس"] == lesson].reset_index(drop=True)
            lesson_df["شماره نمره"] = lesson_df.index + 1
            ax_all.plot(
                lesson_df["شماره نمره"],
                lesson_df["نمره"],
                marker="o",
                linewidth=2,
                color=colors[i % len(colors)],
                label=fix_rtl(lesson), 
            )
            
        ax_all.set_title(fix_rtl("نمودار پیشرفت نمرات در تمام دروس"), fontproperties=font_prop)
        ax_all.set_xlabel(fix_rtl("شماره نمره"), fontproperties=font_prop)
        ax_all.set_ylabel(fix_rtl("نمره"), fontproperties=font_prop)
        ax_all.legend(prop=font_prop, loc="best")
        st.pyplot(fig_all)

        # --- بخش کارنامه PDF ---
        base64_image = convert_image_to_base64(fig_all)
        
        # FIX: حذف fix_rtl از نام ستون‌ها برای PDF و استفاده از متن خام
        report_df_pdf = report_df[["درس", "نمره", "سطح عملکرد", "میانگین کلاس", "مقایسه با کلاس"]].rename(
            columns={
                "درس": "درس", 
                "نمره": "نمره", 
                "سطح عملکرد": "سطح عملکرد", 
                "میانگین کلاس": "میانگین کلاس", 
                "مقایسه با کلاس": "مقایسه با کلاس"
            }
        )
        
        html_table = report_df_pdf.to_html(index=False, classes="report-table")
        
        html_content = f"""
        <html lang="fa" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>کارنامه تحصیلی</title>
            <style>
                @font-face {{
                    font-family: 'Vazir';
                    src: url('file:///{absolute_font_path}') format('truetype');
                }}
                body {{
                    font-family: 'Vazir', sans-serif;
                    direction: rtl;
                    text-align: right;
                    margin: 40px;
                    color: #333;
                    line-height: 1.6;
                }}
                h1 {{
                    color: #004d99; text-align: center; border-bottom: 2px solid #eee;
                }}
                table {{
                    width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12pt;
                }}
                /* FIX نهایی: اعمال قوی جهت‌دهی بر روی سرستون‌ها و سلول‌ها */
                th {{
                    border: 2px solid #333; 
                    padding: 10px; 
                    text-align: right; 
                    direction: rtl; 
                    unicode-bidi: normal; 
                    background-color: #cceeff;
                }}
                td {{
                    border: 2px solid #333; 
                    padding: 10px; 
                    text-align: right; 
                    direction: rtl; 
                    unicode-bidi: normal; 
                }}
            </style>
        </head>
        <body>
            <h1>📘 کارنامه تحصیلی</h1>
            <p><b>نام دانش‌آموز:</b> {full_name}</p>
            <p><b>مدرسه:</b> {school_name} | <b>پایه:</b> {grade} | <b>کلاس:</b> {class_name}</p>
            {html_table}
            <img src="data:image/png;base64,{base64_image}" style="width:100%;max-width:600px;display:block;margin:auto;">
        </body>
        </html>
        """
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        st.download_button(
            label="📥 دانلود کارنامه PDF",
            data=pdf_bytes,
            file_name=f"کارنامه_{full_name}.pdf",
            mime="application/pdf",
        )
        st.success("✅ کارنامه شما آماده دانلود است.")
# تابع آمار آموزگار برای مدیر/معاون
# -------------------------------

def show_teacher_statistics_by_admin(school, selected_teacher):
    st.subheader(f"📊 آمار آموزگار: {selected_teacher}")

    scores = supabase.table("scores").select("*").eq("آموزگار", selected_teacher).execute()
    if not scores.data:
        st.info("هنوز نمره‌ای برای این آموزگار ثبت نشده است.")
        return

    df = pd.DataFrame(scores.data)
    avg_per_student = df.groupby("student")["نمره"].mean().reset_index()
    avg_per_student = avg_per_student.sort_values("نمره", ascending=False)
    st.dataframe(avg_per_student)

    st.subheader("نمودار میانگین نمرات دانش‌آموزان")
    fig, ax = plt.subplots()
    ax.bar(avg_per_student["student"], avg_per_student["نمره"])
    ax.set_xticklabels(avg_per_student["student"], rotation=45, ha="right")
    st.pyplot(fig)

    class_avg = round(avg_per_student["نمره"].mean(), 2)
    st.success(f"میانگین کلی کلاس: {class_avg}")

    st.subheader("نمودار دایره‌ای وضعیت کلی دانش‌آموزان")
    bins = [0, 10, 14, 17, 20]
    labels = ["ضعیف", "قابل قبول", "خوب", "عالی"]
    avg_per_student["وضعیت"] = pd.cut(avg_per_student["نمره"], bins=bins, labels=labels, include_lowest=True)

    pie_data = avg_per_student["وضعیت"].value_counts()
    fig2, ax2 = plt.subplots()
    ax2.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%", startangle=90)
    ax2.set_title("توزیع سطح عملکرد دانش‌آموزان")
    st.pyplot(fig2)

# -------------------------------
# تابع اصلی برنامه
# -------------------------------

def app():
    if "user" not in st.session_state:
        login_page()
    else:
        main_dashboard(st.session_state["user"])

if __name__ == "__main__":
    app()

































