import streamlit as st
import uuid
from datetime import datetime, timedelta
import time
from auth import login_page, logout
from database import (
    db, get_clubs, join_club_request, create_chat, send_message, 
    get_chat_messages, get_user_chats, create_call, get_user_calls,
    update_call_status, get_active_calls, get_call_by_id,
    create_confession, get_confessions_for_students, get_confessions_for_admin,
    create_announcement, get_announcements, get_all_students,
    get_user_notifications, mark_notification_read, mark_all_notifications_read,
    get_unread_count, create_notification
)

# Page configuration
st.set_page_config(
    page_title="Campus Connect",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Home"
    if 'current_chat' not in st.session_state:
        st.session_state.current_chat = None
    if 'start_call_with' not in st.session_state:
        st.session_state.start_call_with = None
    if 'active_call_id' not in st.session_state:
        st.session_state.active_call_id = None
    if 'call_type' not in st.session_state:
        st.session_state.call_type = "voice"
    if 'last_notification_check' not in st.session_state:
        st.session_state.last_notification_check = datetime.now()
    if 'show_notifications' not in st.session_state:
        st.session_state.show_notifications = False
    
    # Show login if not authenticated
    if not st.session_state.user:
        login_page()
    else:
        show_main_app()

def show_main_app():
    """Show the main application with sidebar navigation"""
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("# 🎓 Campus Connect")
        st.write(f"**Welcome, {st.session_state.user.get('name', 'User')}**")
        st.write(f"**Role:** {st.session_state.role.title()}")
        
        # Notification badge
        unread_count = get_unread_count(st.session_state.user['email'])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if unread_count > 0:
                st.markdown(f"**🔔 Notifications ({unread_count})**")
            else:
                st.markdown("**🔔 Notifications**")
        
        with col2:
            if st.button("📨", help="View notifications"):
                st.session_state.show_notifications = True
        
        if st.session_state.show_notifications:
            show_notifications_sidebar()
        
        if st.session_state.role == 'student':
            st.write(f"**Major:** {st.session_state.user.get('major', 'Student')}")
            st.write(f"**Year:** {st.session_state.user.get('year', '')}")
            
            # Student navigation
            st.markdown("---")
            st.subheader("Navigation")
            pages = [
                "🏠 Home", "👤 Profile", "📢 Announcements", 
                "👥 Clubs", "💬 Chat", "📞 Calls", "🗣️ Confessions"
            ]
            
            selected_page = st.radio("Go to:", pages, key="student_nav")
            st.session_state.current_page = selected_page
            
        else:  # Admin
            st.write("⚡ Administrator")
            
            # Admin navigation
            st.markdown("---")
            st.subheader("Admin Tools")
            pages = [
                "📊 Dashboard", "👥 User Management", "📢 Announcements", 
                "👥 Club Management", "🗣️ Confessions", "💬 Chat", "📞 Calls"
            ]
            
            selected_page = st.radio("Go to:", pages, key="admin_nav")
            st.session_state.current_page = selected_page
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
    
    # Check for incoming calls automatically
    check_incoming_calls()
    
    # Main content area
    display_current_page()

def show_notifications_sidebar():
    """Show notifications in sidebar"""
    st.divider()
    st.subheader("Your Notifications")
    
    notifications = get_user_notifications(st.session_state.user['email'])
    
    if not notifications:
        st.info("No notifications")
        return
    
    # Mark as read button
    if st.button("Mark all as read", use_container_width=True):
        mark_all_notifications_read(st.session_state.user['email'])
        st.success("All notifications marked as read!")
        st.rerun()
    
    st.divider()
    
    for notification in notifications[:10]:  # Show last 10
        is_read = notification.get("read", False)
        bg_color = "#f0f2f6" if is_read else "#e3f2fd"
        
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Notification content
                emoji = {
                    "call": "📞",
                    "message": "💬",
                    "club": "👥",
                    "confession": "🗣️",
                    "announcement": "📢",
                    "user": "👤"
                }.get(notification.get("type", ""), "🔔")
                
                st.markdown(f"{emoji} **{notification.get('title', 'Notification')}**")
                st.write(notification.get("message", ""))
                
                # Time ago
                created_at = datetime.fromisoformat(notification.get("created_at", datetime.now().isoformat()))
                time_ago = get_time_ago(created_at)
                st.caption(time_ago)
            
            with col2:
                if not is_read:
                    if st.button("✓", key=f"read_{notification['id']}", help="Mark as read"):
                        mark_notification_read(notification['id'], st.session_state.user['email'])
                        st.rerun()
            
            # Add action buttons based on notification type
            data = notification.get("data", {})
            action = data.get("action", "")
            
            if action == "open_chat":
                if st.button("Open Chat", key=f"action_{notification['id']}", use_container_width=True):
                    chat_id = data.get("chat_id")
                    if chat_id:
                        st.session_state.current_chat = chat_id
                        st.session_state.current_page = "💬 Chat"
                        mark_notification_read(notification['id'], st.session_state.user['email'])
                        st.rerun()
            
            elif action == "manage_clubs":
                if st.button("Manage Clubs", key=f"action_{notification['id']}", use_container_width=True):
                    st.session_state.current_page = "👥 Club Management"
                    mark_notification_read(notification['id'], st.session_state.user['email'])
                    st.rerun()
            
            st.divider()
    
    if len(notifications) > 10:
        st.info(f"Showing 10 of {len(notifications)} notifications")

def get_time_ago(dt):
    """Convert datetime to time ago string"""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutes ago"
    else:
        return "Just now"

def check_incoming_calls():
    """Check for incoming calls and show popup"""
    # Check for new incoming call notifications
    notifications = get_user_notifications(st.session_state.user['email'], unread_only=True)
    
    for notification in notifications:
        if notification.get("type") == "call" and notification.get("data", {}).get("action") == "call_incoming":
            # Show incoming call popup
            data = notification.get("data", {})
            call_id = data.get("call_id")
            initiator = data.get("initiator")
            call_type = data.get("call_type", "voice")
            
            # Get initiator name
            initiator_user = get_user_by_email(initiator)
            initiator_name = initiator_user.get('name', 'Someone') if initiator_user else 'Someone'
            
            # Show call popup
            show_incoming_call_popup(call_id, initiator_name, initiator, call_type)
            break

def show_incoming_call_popup(call_id, caller_name, caller_email, call_type):
    """Show incoming call popup"""
    st.markdown("""
    <style>
    .incoming-call {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        z-index: 1000;
        text-align: center;
        min-width: 300px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown(f"<div class='incoming-call'>", unsafe_allow_html=True)
        
        call_type_emoji = "📹" if call_type == "video" else "📞"
        st.markdown(f"# {call_type_emoji}")
        st.markdown(f"## Incoming Call")
        st.markdown(f"**{caller_name}** is calling you")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Answer", use_container_width=True, type="primary"):
                # Answer the call
                st.session_state.active_call_id = call_id
                st.session_state.current_page = "📞 Calls"
                st.rerun()
        
        with col2:
            if st.button("❌ Decline", use_container_width=True):
                # Decline the call
                update_call_status(call_id, 'declined')
                st.success("Call declined")
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

# ========== REST OF THE APP.PY FUNCTIONS ==========
# [Keep all the existing functions from the previous app.py, but update these key sections:]

def show_calls_page():
    st.title("📞 Campus Calls")
    
    # Check for active calls
    active_calls = get_active_calls()
    user_email = st.session_state.user['email']
    
    # Find if user has any active calls
    user_active_call = None
    for call in active_calls:
        if user_email in call.get('participants', []):
            user_active_call = call
            break
    
    if user_active_call:
        st.session_state.active_call_id = user_active_call['id']
        show_active_call()
    elif st.session_state.active_call_id:
        show_active_call()
    elif st.session_state.start_call_with:
        show_call_interface()
    else:
        show_call_dashboard()

def show_call_interface():
    """Interface to start a call"""
    target_email = st.session_state.start_call_with
    
    # Get target user info
    if target_email == "MES.edu":
        target_name = "👑 Campus Administrator"
    else:
        students = get_all_students()
        target_name = students.get(target_email, {}).get('name', 'User')
    
    st.title(f"📞 Calling {target_name}")
    
    # Check if target is already in a call
    active_calls = get_active_calls()
    target_in_call = False
    
    for call in active_calls:
        if target_email in call.get('participants', []):
            target_in_call = True
            break
    
    if target_in_call:
        st.warning(f"{target_name} is currently on another call.")
        if st.button("← Back"):
            st.session_state.start_call_with = None
            st.rerun()
        return
    
    # Call type selection
    call_type = st.radio("Select Call Type:", 
                        ["📞 Voice Call", "📹 Video Call"], 
                        key="call_type_select")
    
    st.divider()
    
    # Call purpose (optional for admin)
    if st.session_state.role == 'admin':
        call_purpose = st.text_area("Purpose of Call (Optional):", 
                                   placeholder="Briefly describe the purpose of this call...")
    else:
        call_purpose = ""
    
    # Call controls
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎤 Start Call", use_container_width=True, type="primary"):
            # Create call record
            call_id = str(uuid.uuid4())
            call_data = {
                "id": call_id,
                "participants": [st.session_state.user['email'], target_email],
                "type": "video" if "Video" in call_type else "voice",
                "start_time": datetime.now().isoformat(),
                "status": "active",
                "initiator": st.session_state.user['email'],
                "purpose": call_purpose
            }
            
            create_call(call_data)
            st.session_state.active_call_id = call_id
            st.session_state.start_call_with = None
            st.success(f"Calling {target_name}...")
            st.rerun()
    
    with col2:
        if st.button("← Cancel", use_container_width=True):
            st.session_state.start_call_with = None
            st.rerun()

def show_active_call():
    """Display active call interface"""
    call = get_call_by_id(st.session_state.active_call_id)
    
    if not call:
        st.error("Call not found")
        st.session_state.active_call_id = None
        st.rerun()
        return
    
    # Get other participant info
    participants = call.get('participants', [])
    other_email = [p for p in participants if p != st.session_state.user['email']][0]
    
    if other_email == "MES.edu":
        other_name = "👑 Campus Administrator"
    else:
        students = get_all_students()
        other_name = students.get(other_email, {}).get('name', 'User')
    
    # Call header with notification
    st.toast(f"In call with {other_name}", icon="📞")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        call_type = call.get('type', 'voice')
        type_emoji = "📹" if call_type == 'video' else "📞"
        st.title(f"{type_emoji} In Call with {other_name}")
    
    with col2:
        # Calculate call duration
        start_time = datetime.fromisoformat(call.get('start_time', datetime.now().isoformat()))
        duration = datetime.now() - start_time
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)
        st.metric("Duration", f"{minutes}:{seconds:02d}")
    
    st.divider()
    
    # Rest of the active call function remains the same...
    # [Keep the existing active call interface code]

def show_chat_page():
    st.title("💬 Campus Chat")
    
    if st.session_state.current_chat:
        show_chat_messages()
    else:
        show_chat_list()

def show_chat_messages():
    """Show chat messages"""
    chat_id = st.session_state.current_chat
    
    # Mark chat notifications as read when opening
    notifications = get_user_notifications(st.session_state.user['email'], unread_only=True)
    for notification in notifications:
        if notification.get("data", {}).get("chat_id") == chat_id:
            mark_notification_read(notification['id'], st.session_state.user['email'])
    
    # Rest of the chat messages function remains the same...
    # [Keep the existing chat messages code]

# [Keep all other existing functions: display_current_page, show_student_home, etc.]

if __name__ == "__main__":
    main()
