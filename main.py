import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
from supabase_utils import supabase
import uuid

st.set_page_config(page_title="سامانه مدیریت مدرسه", layout="wide")

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
    response = supabase.table("users").select("*").eq("نام_کاربر", username).eq("رمز_عبور", password).execute()

    if response.data:
        return response.data[0]
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

def show_superadmin_panel(username):
    st.title("🏫 پنل مدیر سامانه")
    st.markdown(f"👤 مدیر: {username}")

    tabs = st.tabs(["مدیریت کاربران", "گزارش‌ها"])


    # --- تب مدیریت مدارس ---
   
    # --- تب مدیریت کاربران ---
    with tabs[1]:
        st.subheader("مدیریت کاربران سیستم")

        users_response = supabase.table("users").select("*").execute()
        users_df = pd.DataFrame(users_response.data) if users_response.data else pd.DataFrame()

        if not users_df.empty:
            st.dataframe(users_df[["نام_کاربر", "نام_کامل", "نقش", "مدرسه"]])

        st.markdown("### افزودن کاربر جدید")
        col1, col2, col3 = st.columns(3)
        with col1:
            username = st.text_input("نام کاربری:")
        with col2:
            password = st.text_input("رمز عبور:", type="password")
        with col3:
            fullname = st.text_input("نام کامل:")

        role = st.selectbox("نقش کاربر:", ["آموزگار", "مدیر مدرسه", "معاون"])
        school_list = supabase.table("schools").select("نام_مدرسه").execute()
        school_names = [row["نام_مدرسه"] for row in school_list.data] if school_list.data else []
        school = st.selectbox("مدرسه:", school_names)

        if st.button("افزودن کاربر"):
            if username and password and fullname:
                supabase.table("users").insert({
                    "نام_کاربر": username,
                    "رمز": password,
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
# -------------------------------
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
                    "رمز": password,
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

def show_teacher_panel(username):
    st.title("👩‍🏫 پنل آموزگار")
    st.markdown(f"👤 آموزگار: {username}")

    st.subheader("📚 مدیریت دانش‌آموزان")

    students_response = supabase.table("students").select("*").eq("آموزگار", username).execute()
    students_df = pd.DataFrame(students_response.data) if students_response.data else pd.DataFrame()

    if not students_df.empty:
        st.dataframe(students_df)
    else:
        st.info("هنوز دانش‌آموزی برای شما ثبت نشده است.")

    st.markdown("### ➕ افزودن دانش‌آموز جدید")
    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("نام دانش‌آموز:")
    with col2:
        grade = st.selectbox("پایه:", ["چهارم", "پنجم", "ششم"])

    if st.button("افزودن دانش‌آموز"):
        if student_name:
            supabase.table("students").insert({
                "نام": student_name,
                "پایه": grade,
                "آموزگار": username
            }).execute()
            st.success("✅ دانش‌آموز با موفقیت افزوده شد.")
            st.rerun()
        else:
            st.warning("لطفاً نام دانش‌آموز را وارد کنید.")

    # ثبت نمره برای دانش‌آموزان
    st.subheader("✏️ ثبت نمرات دانش‌آموزان")

    if not students_df.empty:
        selected_student = st.selectbox("انتخاب دانش‌آموز:", students_df["نام"].tolist())
        lesson = st.text_input("نام درس:")
        score = st.number_input("نمره:", min_value=0, max_value=20, step=1)

        if st.button("ثبت نمره"):
            supabase.table("scores").insert({
                "نام_دانش‌آموز": selected_student,
                "درس": lesson,
                "نمره": score,
                "آموزگار": username
            }).execute()
            st.success("✅ نمره ثبت شد.")
            st.rerun()

    # نمایش میانگین نمرات
    st.subheader("📈 میانگین نمرات دانش‌آموزان")
    scores_response = supabase.table("scores").select("نام_دانش‌آموز", "نمره").eq("آموزگار", username).execute()
    if scores_response.data:
        df_scores = pd.DataFrame(scores_response.data)
        avg_scores = df_scores.groupby("نام_دانش‌آموز")["نمره"].mean().sort_values(ascending=False)
        st.bar_chart(avg_scores)
    else:
        st.info("هنوز نمره‌ای ثبت نشده است.")

# -------------------------------
# پنل دانش‌آموز + PDF کارنامه
# -------------------------------

def show_student_panel(username):
    st.title("🎓 پنل دانش‌آموز")
    st.markdown(f"👤 دانش‌آموز: {username}")

    student_row = supabase.table("students").select("*").eq("نام", username).execute()
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






