import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
from supabase_utils import supabase
import uuid
import matplotlib.font_manager as fm  # برای فونت فارسی در نمودارها

# 🎯 تنظیم صفحه Streamlit
st.set_page_config(page_title="سامانه مدیریت مدرسه", layout="wide")

# 🎨 تنظیم فونت فارسی برای نمودارها
font_path = "fonts/Vazir.ttf"  # مسیر به فونت فارسی در پروژه
font_prop = fm.FontProperties(fname=font_path)
plt.rcParams["font.family"] = font_prop.get_name()
plt.rcParams["axes.unicode_minus"] = False

# 📐 تنظیم راست‌چین برای کل صفحه
st.markdown("""
    <style>
    body, div, p, h1, h2, h3, h4, h5, h6 {
        direction: rtl;
        text-align: right;
        font-family: 'Vazir', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)


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
    supabase.table("scores").update({"نمره": new_score}).eq("نام_دانش‌آموز", student_name).eq("درس", lesson).execute()

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
    st.sidebar.markdown(f"👋 خوش آمدی، **{user['نام_کامل']}**")
    if st.sidebar.button("🚪 خروج از سامانه"):
    st.session_state.pop("user", None)
    st.success("با موفقیت خارج شدید ✅")
    st.rerun()

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

        users_chart = supabase.table("users").select("نقش").execute()
        if users_chart.data:
            df_chart = pd.DataFrame(users_chart.data)
            role_counts = df_chart["نقش"].value_counts()
            fig, ax = plt.subplots()
            ax.pie(role_counts, labels=role_counts.index, autopct="%1.1f%%", startangle=140)
            ax.set_title("توزیع نقش کاربران در سامانه")
            st.pyplot(fig)
        else:
            st.info("داده کافی برای نمایش نمودار وجود ندارد.")


# پنل مدیر مدرسه
# -------------------------------

def show_school_admin_panel(username):
    st.title("🏫 پنل مدیر مدرسه")
    st.markdown(f"👤 مدیر مدرسه: {username}")

    # دریافت نام مدرسه
    user_row = supabase.table("users").select("مدرسه").eq("نام_کاربر", username).execute()
    if not user_row.data:
        st.error("مدرسه‌ای برای این مدیر ثبت نشده است.")
        return
    school = user_row.data[0]["مدرسه"]

    tabs = st.tabs(["مدیریت آموزگاران", "گزارش کلاس‌ها", "آمار کلی"])

    # --- تب مدیریت آموزگاران ---
    with tabs[0]:
        st.subheader("👩‍🏫 مدیریت آموزگاران مدرسه")

        teachers = supabase.table("users").select("*").eq("مدرسه", school).eq("نقش", "آموزگار").execute()
        df_teachers = pd.DataFrame(teachers.data) if teachers.data else pd.DataFrame()
        if not df_teachers.empty:
            st.dataframe(df_teachers[["نام_کاربر", "نام_کامل"]])
        else:
            st.info("هیچ آموزگاری در این مدرسه ثبت نشده است.")

        st.markdown("### ➕ افزودن آموزگار جدید")
        col1, col2 = st.columns(2)
        with col1:
            new_teacher = st.text_input("نام کاربری آموزگار:")
        with col2:
            password = st.text_input("رمز عبور آموزگار:", type="password")
        fullname = st.text_input("نام کامل آموزگار:")

        if st.button("افزودن آموزگار"):
            if new_teacher and password:
                supabase.table("users").insert({
                    "نام_کاربر": new_teacher,
                    "رمز_عبور": password,
                    "نام_کامل": fullname,
                    "نقش": "آموزگار",
                    "مدرسه": school
                }).execute()
                st.success("✅ آموزگار با موفقیت افزوده شد.")
                st.rerun()
            else:
                st.warning("لطفاً اطلاعات را کامل وارد کنید.")

    # --- تب گزارش کلاس‌ها ---
    with tabs[1]:
        st.subheader("📊 گزارش عملکرد آموزگاران")

        teachers = supabase.table("users").select("نام_کاربر", "نام_کامل").eq("مدرسه", school).eq("نقش", "آموزگار").execute()
        if teachers.data:
            teacher_names = [t["نام_کاربر"] for t in teachers.data]
            selected_teacher = st.selectbox("انتخاب آموزگار:", teacher_names)
            show_teacher_statistics_by_admin(school, selected_teacher)
        else:
            st.info("هیچ آموزگاری در این مدرسه وجود ندارد.")

    # --- تب آمار کلی ---
    with tabs[2]:
        st.subheader("📈 آمار کلی مدرسه")

        total_students = supabase.table("students").select("*", count="exact").eq("مدرسه", school).execute().count or 0

        total_teachers = supabase.table("users").select("*", count="exact").eq("مدرسه", school).eq("نقش", "آموزگار").execute().count or 0

        st.markdown(f"""
        - 👩‍🏫 تعداد آموزگاران: **{total_teachers}**
        - 👨‍🎓 تعداد دانش‌آموزان: **{total_students}**
        """)

# -------------------------------
# پنل معاون مدرسه
# -------------------------------

def show_assistant_panel(username):
    st.title("🧾 پنل معاون مدرسه")
    st.markdown(f"👤 معاون: {username}")

    user_row = supabase.table("users").select("مدرسه").eq("نام_کاربر", username).execute()
    if not user_row.data:
        st.error("مدرسه‌ای برای این معاون ثبت نشده است.")
        return
    school = user_row.data[0]["مدرسه"]

    st.subheader("📊 مشاهده وضعیت آموزگاران")
    teachers = supabase.table("users").select("نام_کاربر").eq("مدرسه", school).eq("نقش", "آموزگار").execute()
    if teachers.data:
        teacher_names = [t["نام_کاربر"] for t in teachers.data]
        selected_teacher = st.selectbox("انتخاب آموزگار:", teacher_names)
        show_teacher_statistics_by_admin(school, selected_teacher)
    else:
        st.info("هیچ آموزگاری در این مدرسه وجود ندارد.")

# -------------------------------
# پنل آموزگار
# -------------------------------
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from matplotlib import font_manager
from supabase_utils import supabase

# 🎨 تنظیم فونت فارسی
font_path = "fonts/Vazir.ttf"  # یا fonts/IRANSans.ttf اگر داری
font_prop = font_manager.FontProperties(fname=font_path)
plt.rcParams["font.family"] = font_prop.get_name()
plt.rcParams["axes.unicode_minus"] = False

def show_teacher_panel(username):
    st.set_page_config(layout="wide")
    st.title("👩‍🏫 پنل آموزگار")

    # 📌 دریافت اطلاعات آموزگار
    teacher_info = supabase.table("users").select("نام_کامل, مدرسه").eq("نام_کاربر", username).limit(1).execute()
    full_name = teacher_info.data[0]["نام_کامل"] if teacher_info.data else username
    school_name = teacher_info.data[0]["مدرسه"] if teacher_info.data else "نامشخص"

    col_left, col_right = st.columns([4, 1])
    with col_right:
        st.markdown(f"**👤 آموزگار:** {full_name}")
        st.markdown(f"**🏫 مدرسه:** {school_name}")

    # 📚 لیست دانش‌آموزان
    st.subheader("📚 لیست دانش‌آموزان شما")
    students_response = supabase.table("students").select("*").eq("آموزگار", full_name).execute()
    students_df = pd.DataFrame(students_response.data) if students_response.data else pd.DataFrame()

    if not students_df.empty:
        st.dataframe(students_df[["نام_دانش‌آموز", "پایه", "کلاس", "مدرسه"]])
    else:
        st.info("هنوز دانش‌آموزی برای شما ثبت نشده است.")

    # ➕ افزودن دانش‌آموز
    st.subheader("➕ افزودن دانش‌آموز جدید")
    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("نام کامل دانش‌آموز:")
        student_username = st.text_input("نام کاربری دانش‌آموز:")
    with col2:
        grade = st.selectbox("پایه:", ["اول", "دوم", "سوم", "چهارم", "پنجم", "ششم"])
        class_name = st.text_input("کلاس:")
    school_name_input = st.text_input("نام مدرسه:", value=school_name)
    student_password = st.text_input("رمز ورود دانش‌آموز:", type="password")

    if st.button("ثبت دانش‌آموز"):
        if student_name and student_username and student_password and class_name:
            supabase.table("students").insert({
                "نام_دانش‌آموز": student_name,
                "نام_کاربری": student_username,
                "رمز_دانش‌آموز": student_password,
                "پایه": grade,
                "کلاس": class_name,
                "مدرسه": school_name_input,
                "آموزگار": full_name,
                "تاریخ_ثبت": datetime.date.today().isoformat()
            }).execute()
            st.success("✅ دانش‌آموز با موفقیت ثبت شد.")
            st.rerun()
        else:
            st.warning("لطفاً تمام فیلدهای ضروری را پر کنید.")

    # 🔐 تغییر رمز ورود دانش‌آموز
    st.subheader("🔐 تغییر رمز ورود دانش‌آموز")
    if not students_df.empty:
        student_usernames = students_df["نام_کاربر"].dropna().tolist()
        selected_user = st.selectbox("انتخاب دانش‌آموز برای تغییر رمز:", student_usernames)
        new_password = st.text_input("رمز جدید:", type="password")

        if st.button("ثبت رمز جدید"):
            if new_password:
                supabase.table("students").update({"رمز_دانش‌آموز": new_password}).eq("نام_کاربری", selected_user).execute()
                st.success("✅ رمز جدید با موفقیت ثبت شد.")
            else:
                st.warning("رمز جدید نمی‌تواند خالی باشد.")
    else:
        st.info("هیچ دانش‌آموزی برای شما ثبت نشده است.")

    # ✏️ ثبت نمره برای دانش‌آموز
    st.subheader("✏️ ثبت نمره برای دانش‌آموز")
    if not students_df.empty:
        selected_student = st.selectbox("انتخاب دانش‌آموز:", students_df["نام_دانش‌آموز"].tolist())
        lesson = st.text_input("نام درس:")
        score = st.selectbox("نمره (۱ تا ۴):", [1, 2, 3, 4])

        if st.button("ثبت نمره"):
            if lesson:
                supabase.table("scores").insert({
                    "نام_دانش‌آموز": selected_student,
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

    # 🛠️ مدیریت نمرات ثبت‌شده
    st.subheader("🛠️ مدیریت نمرات ثبت‌شده")
    scores_response = supabase.table("scores").select("*").eq("آموزگار", full_name).execute()
    scores_df = pd.DataFrame(scores_response.data) if scores_response.data else pd.DataFrame()

    if not scores_df.empty:
        st.dataframe(scores_df[["نام_دانش‌آموز", "درس", "نمره"]])

        selected_row = st.selectbox(
            "انتخاب ردیف نمره برای ویرایش یا حذف:",
            scores_df.apply(lambda r: f"{r['نام_دانش‌آموز']} - {r['درس']} - {r['نمره']}", axis=1).tolist()
        )
        selected_index = scores_df.index[
            scores_df.apply(lambda r: f"{r['نام_دانش‌آموز']} - {r['درس']} - {r['نمره']}", axis=1) == selected_row
        ][0]
        selected_score = scores_df.loc[selected_index]
        new_score = st.selectbox("نمره جدید:", [1, 2, 3, 4], index=int(selected_score["نمره"]) - 1)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("ویرایش نمره"):
                supabase.table("scores").update({"نمره": new_score}).eq("id", selected_score["id"]).execute()
                st.success("✅ نمره ویرایش شد.")
                st.rerun()
        with col2:
            if st.button("🗑️ حذف نمره"):
                supabase.table("scores").delete().eq("id", selected_score["id"]).execute()
                st.success("✅ نمره حذف شد.")
                st.rerun()
    else:
        st.info("هنوز نمره‌ای برای شما ثبت نشده است.")

    # 🏆 رتبه‌بندی کلی دانش‌آموزان
    st.subheader("🏆 رتبه‌بندی کلی دانش‌آموزان")
    if not scores_df.empty:
        avg_all = scores_df.groupby("نام_دانش‌آموز")["نمره"].mean().sort_values(ascending=False)
        st.dataframe(avg_all.reset_index().rename(columns={"نمره": "میانگین نمرات"}))
    else:
        st.info("داده‌ای برای رتبه‌بندی کلی وجود ندارد.")

    # 📚 رتبه‌بندی در یک درس خاص
    st.subheader("📚 رتبه‌بندی دانش‌آموزان در یک درس")
    if not scores_df.empty:
        selected_lesson_rank = st.selectbox("انتخاب درس برای رتبه‌بندی:", scores_df["درس"].unique())
        lesson_df_rank = scores_df[scores_df["درس"] == selected_lesson_rank]
        avg_lesson = lesson_df_rank.groupby("نام_دانش‌آموز")["نمره"].mean().sort_values(ascending=False)
        st.dataframe(avg_lesson.reset_index().rename(columns={"نمره": f"میانگین نمره ({selected_lesson_rank})"}))
    else:
        st.info("داده‌ای برای رتبه‌بندی درسی وجود ندارد.")

    # 📊 نمودار دایره‌ای سطح عملکرد دانش‌آموزان در یک درس
    st.subheader("📊 سطح عملکرد دانش‌آموزان در یک درس")
    if not scores_df.empty:
        selected_lesson = st.selectbox("انتخاب درس برای نمودار:", scores_df["درس"].unique())
        lesson_df = scores_df[scores_df["درس"] == selected_lesson]

        def categorize(score):
            return {
                1: "نیاز به تلاش بیشتر",
                2: "قابل قبول",
                3: "خوب",
                4: "خیلی خوب"
            }.get(score, "نامشخص")

        lesson_df["سطح عملکرد"] = lesson_df["نمره"].apply(categorize)
        performance_counts = lesson_df["سطح عملکرد"].value_counts()

        fig, ax = plt.subplots()
        wedges, texts, autotexts = ax.pie(
            performance_counts,
            labels=performance_counts.index,
            autopct="%1.1f%%",
            startangle=140,
            textprops={"fontproperties": font_prop}
        )
        for text in texts + autotexts:
            text.set_fontproperties(font_prop)

        ax.set_title(f"سطح عملکرد در درس {selected_lesson}", fontproperties=font_prop)
        st.pyplot(fig)
    else:
        st.info("هنوز نمره‌ای برای رسم نمودار وجود ندارد.")

# پنل دانش‌آموز + PDF کارنامه
# -------------------------------

def show_student_panel(username):
    st.title("🎓 پنل دانش‌آموز")
    st.markdown(f"👤 دانش‌آموز: {username}")

    student_row = supabase.table("students").select("*").eq("نام_کامل", username).execute()

    if not student_row.data:
        st.error("اطلاعات دانش‌آموز یافت نشد.")
        return

    teacher = student_row.data[0].get("آموزگار", "")
    grade = student_row.data[0].get("پایه", "")
    st.markdown(f"🏫 پایه: **{grade}**  |  👩‍🏫 آموزگار: **{teacher}**")

    scores_response = supabase.table("scores").select("درس", "نمره").eq("نام_دانش‌آموز", username).execute()
    if not scores_response.data:
        st.info("هنوز نمره‌ای برای شما ثبت نشده است.")
        return

    df_scores = pd.DataFrame(scores_response.data)
    st.subheader("📋 نمرات ثبت‌شده شما")
    st.dataframe(df_scores)

    avg = df_scores["نمره"].mean()
    st.success(f"🎯 میانگین کل شما: {round(avg, 2)}")

    fig1, ax1 = plt.subplots()
    ax1.pie(df_scores["نمره"], labels=df_scores["درس"], autopct="%1.1f%%", startangle=90)
    ax1.set_title("درصد نمرات هر درس")
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots()
    ax2.plot(df_scores["درس"], df_scores["نمره"], marker="o", linestyle="-")
    ax2.set_xlabel("درس")
    ax2.set_ylabel("نمره")
    ax2.set_title("نمودار پیشرفت تحصیلی")
    st.pyplot(fig2)

    if st.button("📄 دانلود کارنامه به صورت PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("Vazir", "", "Vazir.ttf", uni=True)
        pdf.set_font("Vazir", "", 14)
        pdf.cell(200, 10, txt=f"کارنامه {username}", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Vazir", "", 12)
        for index, row in df_scores.iterrows():
            pdf.cell(90, 10, txt=row["درس"], border=1)
            pdf.cell(30, 10, txt=str(row["نمره"]), border=1, ln=True)

        pdf.ln(10)
        pdf.cell(200, 10, txt=f"میانگین کل: {round(avg, 2)}", ln=True, align="R")

        pdf_output = BytesIO()
        pdf.output(pdf_output)
        st.download_button(
            label="دانلود PDF",
            data=pdf_output.getvalue(),
            file_name=f"Report_{username}.pdf",
            mime="application/pdf"
        )

# -------------------------------
# تابع آمار آموزگار برای مدیر/معاون
# -------------------------------

def show_teacher_statistics_by_admin(school, selected_teacher):
    st.subheader(f"📊 آمار آموزگار: {selected_teacher}")

    scores = supabase.table("scores").select("*").eq("آموزگار", selected_teacher).execute()
    if not scores.data:
        st.info("هنوز نمره‌ای برای این آموزگار ثبت نشده است.")
        return

    df = pd.DataFrame(scores.data)
    avg_per_student = df.groupby("نام_دانش‌آموز")["نمره"].mean().reset_index()
    avg_per_student = avg_per_student.sort_values("نمره", ascending=False)
    st.dataframe(avg_per_student)

    st.subheader("نمودار میانگین نمرات دانش‌آموزان")
    fig, ax = plt.subplots()
    ax.bar(avg_per_student["نام_دانش‌آموز"], avg_per_student["نمره"])
    ax.set_xticklabels(avg_per_student["نام_دانش‌آموز"], rotation=45, ha="right")
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

















