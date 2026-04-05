import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import os
import sqlite3
from datetime import datetime
import urllib.parse
import httpx

# Ensure we use the exact same DB path as main.py
def get_db_path():
    db_path = os.environ.get('DATABASE_PATH', 'echomind_notes.db')
    db_dir = os.path.dirname(db_path)
    if db_dir and db_dir.strip():
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception:
                db_path = os.path.basename(db_path)
    return db_path

def init_user_db():
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                auth_provider TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing user database: {e}")

def get_or_create_user(email, name=None, auth_provider="otp"):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT id, email, name FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        
        if not user:
            c.execute('''
                INSERT INTO users (email, name, auth_provider, created_at)
                VALUES (?, ?, ?, ?)
            ''', (email, name, auth_provider, datetime.now()))
            conn.commit()
            user_id = c.lastrowid
            user = (user_id, email, name)
            
        conn.close()
        return user
    except Exception as e:
        print(f"Error with user db: {e}")
        return None

def send_otp_email(to_email, otp):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_email = os.environ.get("SMTP_EMAIL", os.environ.get("EMAIL_SENDER", ""))
    smtp_password = os.environ.get("SMTP_PASSWORD", os.environ.get("EMAIL_PASSWORD", ""))
    
    if not smtp_email or not smtp_password:
        return False, "SMTP credentials missing in environment variables (.env)."
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = to_email
        msg['Subject'] = "Your EchoMind Login OTP"
        
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5dc; padding: 20px;">
                <div style="background-color: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-top: 5px solid #0066cc;">
                    <h2 style="color: #0066cc; text-align: center;">EchoMind Platform</h2>
                    <p style="color: #333; font-size: 16px;">Hello,</p>
                    <p style="color: #333; font-size: 16px;">Your One-Time Password (OTP) for secure platform access is:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #000; background-color: #f0f8ff; padding: 15px 30px; border-radius: 8px; border: 1px dashed #0066cc;">{otp}</span>
                    </div>
                    <p style="color: #666; font-size: 14px; text-align: center;">This code is valid for 10 minutes. Please do not share it with anyone.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px; text-align: center;">© 2025 EchoMind | MIT ADT University</p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        return True, "OTP Sent successfully!"
    except Exception as e:
        return False, str(e)

def render_google_login():
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    
    if not client_id:
        st.warning("⚠️ Google OAuth credentials missing. Setup `.env` with GOOGLE_CLIENT_ID and GOOGLE_REDIRECT_URI.")
        return
        
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"access_type=offline"
    )
    
    st.markdown(f'''
        <a href="{auth_url}" target="_self" style="text-decoration: none;">
            <div style="display: flex; align-items: center; justify-content: center; background-color: transparent; border: 1px solid #3b3b4f; border-radius: 0px; padding: 12px; cursor: pointer; transition: 0.3s; margin-top: 10px;">
                <img src="https://developers.google.com/identity/images/g-logo.png" width="20" height="20" style="margin-right: 15px;">
                <span style="color: #ffffff; font-weight: 600; font-size: 16px; text-transform: uppercase; letter-spacing: 1px;">Continue with Google</span>
            </div>
        </a>
        ''', unsafe_allow_html=True)

def check_google_callback():
    if "code" in st.query_params:
        code = st.query_params["code"]
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")
        
        if not client_id or not client_secret:
            st.error("Google OAuth Secret is missing in environment variables.")
            return False
            
        try:
            # Exchange code for token
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            r = httpx.post(token_url, data=data)
            r.raise_for_status()
            access_token = r.json().get("access_token")
            
            # Get user info
            user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            user_r = httpx.get(user_info_url, headers=headers)
            user_r.raise_for_status()
            user_data = user_r.json()
            
            email = user_data.get("email")
            name = user_data.get("name")
            
            if email:
                user = get_or_create_user(email, name, "google")
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.user_name = name
                # Clean up query params
                st.query_params.clear()
                return True
        except Exception as e:
            st.error(f"Failed to authenticate with Google: {str(e)}")
            st.query_params.clear()
    return False

def show_login_page():
    # Attempt to handle Google Callback first
    if check_google_callback():
        st.rerun()
        return

    st.markdown("""
    <style>
        /* Full-page dark gradient */
        .stApp {
            background: linear-gradient(135deg, #0a0a23 0%, #0d1b2a 40%, #1b2838 100%) !important;
        }
        
        /* Login card with glassmorphism */
        .login-card {
            background: rgba(27, 27, 50, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(25, 135, 84, 0.3);
            border-radius: 16px;
            padding: 48px 40px 36px;
            max-width: 440px;
            margin: 40px auto;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 60px rgba(25, 135, 84, 0.08);
        }
        
        /* Logo area */
        .login-logo {
            text-align: center;
            margin-bottom: 8px;
        }
        .login-logo-icon {
            font-size: 48px;
            display: block;
            margin-bottom: 4px;
        }
        .login-brand {
            font-size: 36px;
            font-weight: 800;
            background: linear-gradient(135deg, #198754, #20c997);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        .login-tagline {
            text-align: center;
            color: #8b8ca7;
            font-size: 14px;
            margin-bottom: 32px;
            letter-spacing: 0.5px;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(255,255,255,0.03) !important;
            border-radius: 8px;
            padding: 4px;
            gap: 0 !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #8b8ca7 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            padding: 8px 16px !important;
            border-radius: 6px !important;
        }
        .stTabs [aria-selected="true"] {
            color: #ffffff !important;
            background: rgba(25, 135, 84, 0.2) !important;
            border-bottom: 2px solid #198754 !important;
        }
        
        /* Input fields */
        .stTextInput > div > div > input {
            background: rgba(255,255,255,0.05) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 8px !important;
            color: #ffffff !important;
            padding: 12px 16px !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #198754 !important;
            box-shadow: 0 0 0 1px #198754 !important;
        }
        
        /* Buttons */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #198754, #20c997) !important;
            color: white !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 12px !important;
            font-size: 15px !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s ease !important;
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 16px rgba(25, 135, 84, 0.4) !important;
        }
        
        /* Footer */
        .login-footer {
            text-align: center;
            color: #5c5d78;
            font-size: 11px;
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.05);
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown("""
        <div class="login-logo">
            <span class="login-logo-icon">🧠</span>
            <span class="login-brand">EchoMind</span>
        </div>
        <div class="login-tagline">Transform lectures into intelligent notes</div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🔑 Password", "📧 Email OTP", "🌐 Google"])
    
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        login_user = st.text_input("Username", key="login_user", placeholder="Enter username")
        login_pass = st.text_input("Password", type="password", key="login_pass", placeholder="Enter password")
        if st.button("Sign In", use_container_width=True, type="primary"):
            if login_user == "sushant" and login_pass == "9090":
                user = get_or_create_user(f"{login_user}@echomind.local", name=login_user, auth_provider="password")
                st.session_state.authenticated = True
                st.session_state.user_email = f"{login_user}@echomind.local"
                st.session_state.user_name = login_user
                st.success(f"Welcome {login_user.capitalize()}!")
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        if 'otp_sent' not in st.session_state:
            st.session_state.otp_sent = False
            
        email = st.text_input("Email Address", placeholder="name@example.com")
        
        if not st.session_state.otp_sent:
            if st.button("Send Access Code", use_container_width=True, type="primary"):
                if email and "@" in email:
                    with st.spinner("Sending OTP..."):
                        otp = str(random.randint(100000, 999999))
                        success, req_msg = send_otp_email(email, otp)
                        if success:
                            st.session_state.otp = otp
                            st.session_state.otp_email = email
                            st.session_state.otp_sent = True
                            st.rerun()
                        else:
                            st.error(req_msg)
                else:
                    st.warning("Please enter a valid email address.")
        else:
            otp_input = st.text_input("Enter 6-digit OTP", type="password", key="otp_input", placeholder="000000")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Verify", use_container_width=True, type="primary"):
                    if otp_input == st.session_state.otp and email == st.session_state.otp_email:
                        user = get_or_create_user(email, auth_provider="otp")
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.success("Verification successful!")
                        st.rerun()
                    else:
                        st.error("Invalid or expired OTP.")
            with col2:
                if st.button("Resend", use_container_width=True):
                    st.session_state.otp_sent = False
                    st.rerun()
                    
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#8b8ca7; font-size: 13px;'>Sign in securely with your Google account</p>", unsafe_allow_html=True)
        render_google_login()
    
    st.markdown("""
        <div class="login-footer">
            MIT ADT University, Pune &middot; &copy; 2025 EchoMind
        </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

