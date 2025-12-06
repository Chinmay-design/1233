import streamlit as st
import bcrypt
from datetime import datetime
from database import get_user_by_email, create_student, db, verify_password

def login_page():
    st.title("🎓 Campus Connect")
    st.subheader("Learn. Collaborate. Grow Together.")
    
    # Initialize session state for forgot password
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    
    # Forgot password link
    if st.button("🔐 Forgot Password?"):
        st.session_state.show_forgot_password = True
    
    if st.session_state.get('show_forgot_password'):
        forgot_password()
        return
    
    tab1, tab2, tab3 = st.tabs(["🎓 Student Login", "⚡ Admin Login", "📝 Student Sign Up"])
    
    with tab1:
        student_login()
    
    with tab2:
        admin_login()
    
    with tab3:
        student_signup()

def student_login():
    with st.form("student_login"):
        email = st.text_input("📧 College Email")
        password = st.text_input("🔑 Password", type="password")
        
        if st.form_submit_button("Student Login", use_container_width=True):
            if email and password:
                user = get_user_by_email(email)
                if user and verify_password(password, user.get('password', '')) and user.get('role') == 'student':
                    st.session_state.user = user
                    st.session_state.user['email'] = email
                    st.session_state.role = 'student'
                    st.success("Welcome back! 🎉")
                    st.rerun()
                else:
                    st.error("Invalid student credentials")
            else:
                st.error("Please enter both email and password")

def admin_login():
    with st.form("admin_login"):
        username = st.text_input("👑 Admin Username")
        password = st.text_input("🔑 Admin Password", type="password")
        
        if st.form_submit_button("Admin Login", use_container_width=True):
            if username == "MES.edu" and password == "education":
                admin_user = {
                    "username": "MES.edu",
                    "email": "MES.edu",
                    "name": "Campus Administrator",
                    "role": "admin"
                }
                st.session_state.user = admin_user
                st.session_state.role = 'admin'
                st.success("Admin access granted! ⚡")
                st.rerun()
            else:
                st.error("Invalid admin credentials")

def student_signup():
    with st.form("student_signup"):
        name = st.text_input("Full Name")
        email = st.text_input("📧 College Email")
        year = st.selectbox("Year", ["Freshman", "Sophomore", "Junior", "Senior"])
        major = st.text_input("Major")
        password = st.text_input("🔑 Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        security_question = st.selectbox("Security Question", 
                                       ["What is your favorite color?", 
                                        "What is your favorite place?"])
        security_answer = st.text_input("Security Answer")
        
        if st.form_submit_button("Create Student Account", use_container_width=True):
            if not all([name, email, major, password, security_answer]):
                st.error("Please fill all required fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif not any(domain in email for domain in [".edu", ".ac."]):
                st.error("Please use a college email address")
            elif get_user_by_email(email):
                st.error("An account with this email already exists")
            else:
                student_data = {
                    "name": name,
                    "email": email,
                    "year": year,
                    "major": major,
                    "password": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                    "security_question": security_question,
                    "security_answer": bcrypt.hashpw(security_answer.encode(), bcrypt.gensalt()).decode(),
                    "role": "student",
                    "joined_date": datetime.now().isoformat()
                }
                
                if create_student(student_data):
                    st.session_state.user = student_data
                    st.session_state.role = 'student'
                    st.success("Student account created! 🎉")
                    st.balloons()
                    st.rerun()

def forgot_password():
    st.title("🔐 Forgot Password")
    
    with st.form("forgot_password"):
        email = st.text_input("📧 Enter your college email")
        
        if st.form_submit_button("Reset Password"):
            if email:
                user = get_user_by_email(email)
                if user and user.get('role') == 'student':
                    st.session_state.reset_email = email
                    st.session_state.show_security_question = True
                    st.rerun()
                else:
                    st.error("Student account not found")
            else:
                st.error("Please enter your email")
    
    if st.session_state.get('show_security_question'):
        user = get_user_by_email(st.session_state.reset_email)
        security_question = user.get('security_question', '')
        
        st.write(f"**Security Question:** {security_question}")
        answer = st.text_input("Your answer")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.button("Reset Password"):
            if answer and new_password and confirm_password:
                if verify_password(answer, user.get('security_answer', '')):
                    if new_password == confirm_password:
                        students = db.load_data("students.json")
                        if st.session_state.reset_email in students:
                            students[st.session_state.reset_email]['password'] = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                            db.save_data("students.json", students)
                            st.success("Password reset successfully! You can now login.")
                            st.session_state.show_security_question = False
                            st.session_state.reset_email = None
                            st.session_state.show_forgot_password = False
                            st.rerun()
                    else:
                        st.error("Passwords do not match")
                else:
                    st.error("Incorrect security answer")
            else:
                st.error("Please fill all fields")
    
    if st.button("← Back to Login"):
        st.session_state.show_forgot_password = False
        st.rerun()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
