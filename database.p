import json
import os
import bcrypt
import uuid
from datetime import datetime, timedelta

class SimpleDB:
    def __init__(self):
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        self.init_default_data()
    
    def init_default_data(self):
        """Initialize with default admin and sample data"""
        # Admin account
        admin_data = {
            "MES.edu": {
                "password": bcrypt.hashpw("education".encode(), bcrypt.gensalt()).decode(),
                "role": "admin",
                "name": "Admin User"
            }
        }
        
        # Sample clubs
        sample_clubs = {
            "club_cs": {
                "id": "club_cs",
                "name": "Computer Science Club",
                "category": "technology",
                "description": "Weekly coding sessions, hackathon preparation, and tech workshops. Open to all skill levels!",
                "members": [],
                "pending_requests": [],
                "admins": ["MES.edu"],
                "meeting_schedule": "Wednesdays 6-8 PM",
                "location": "Tech Building 301",
                "created_date": datetime.now().isoformat()
            }
        }
        
        # Sample announcements
        sample_announcements = [
            {
                "id": str(uuid.uuid4()),
                "title": "Welcome to Campus Connect!",
                "message": "Welcome to our new campus social platform! Connect with fellow students, join clubs, and stay updated with campus events.",
                "category": "general",
                "priority": "high",
                "author": "Admin User",
                "created_date": datetime.now().isoformat(),
                "expiry_date": None
            }
        ]
        
        # Ensure files exist with default data
        default_data = {
            "users.json": admin_data,
            "students.json": {},
            "announcements.json": sample_announcements,
            "clubs.json": sample_clubs,
            "club_requests.json": [],
            "chats.json": {},
            "calls.json": [],
            "confessions.json": [],
            "notifications.json": {}  # Add notifications file
        }
        
        for filename, data in default_data.items():
            if not os.path.exists(os.path.join(self.data_dir, filename)):
                self.save_data(filename, data)
    
    def load_data(self, filename):
        """Load data from JSON file"""
        try:
            with open(os.path.join(self.data_dir, filename), 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            if filename == "announcements.json":
                return []
            elif filename in ["club_requests.json", "calls.json", "confessions.json"]:
                return []
            elif filename in ["chats.json", "notifications.json"]:
                return {}
            else:
                return {}
    
    def save_data(self, filename, data):
        """Save data to JSON file"""
        with open(os.path.join(self.data_dir, filename), 'w') as f:
            json.dump(data, f, indent=2)

# Global database instance
db = SimpleDB()

# ========== NOTIFICATION FUNCTIONS ==========
def create_notification(user_email, notification_type, title, message, data=None):
    """Create a notification for a user"""
    notifications = db.load_data("notifications.json")
    
    if user_email not in notifications:
        notifications[user_email] = []
    
    notification = {
        "id": str(uuid.uuid4()),
        "type": notification_type,  # "call", "message", "club", "confession", "announcement"
        "title": title,
        "message": message,
        "data": data or {},
        "created_at": datetime.now().isoformat(),
        "read": False,
        "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
    }
    
    notifications[user_email].append(notification)
    
    # Keep only last 50 notifications per user
    notifications[user_email] = notifications[user_email][-50:]
    
    db.save_data("notifications.json", notifications)
    return notification["id"]

def get_user_notifications(user_email, unread_only=False):
    """Get notifications for a user"""
    notifications = db.load_data("notifications.json")
    user_notifications = notifications.get(user_email, [])
    
    # Filter expired notifications
    now = datetime.now()
    valid_notifications = []
    
    for notification in user_notifications:
        expires_at = datetime.fromisoformat(notification.get("expires_at", now.isoformat()))
        if expires_at > now:
            valid_notifications.append(notification)
    
    # Filter unread if requested
    if unread_only:
        valid_notifications = [n for n in valid_notifications if not n.get("read", False)]
    
    # Sort by creation time, newest first
    valid_notifications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Save filtered list
    notifications[user_email] = valid_notifications
    db.save_data("notifications.json", notifications)
    
    return valid_notifications

def mark_notification_read(notification_id, user_email):
    """Mark a notification as read"""
    notifications = db.load_data("notifications.json")
    
    if user_email in notifications:
        for notification in notifications[user_email]:
            if notification.get("id") == notification_id:
                notification["read"] = True
                break
        
        db.save_data("notifications.json", notifications)
        return True
    return False

def mark_all_notifications_read(user_email):
    """Mark all notifications as read for a user"""
    notifications = db.load_data("notifications.json")
    
    if user_email in notifications:
        for notification in notifications[user_email]:
            notification["read"] = True
        
        db.save_data("notifications.json", notifications)
        return True
    return False

def get_unread_count(user_email):
    """Get count of unread notifications for a user"""
    notifications = get_user_notifications(user_email, unread_only=True)
    return len(notifications)

# ========== CALL FUNCTIONS WITH NOTIFICATIONS ==========
def create_call(call_data):
    """Create a new call record and send notification"""
    calls = db.load_data("calls.json")
    calls.append(call_data)
    db.save_data("calls.json", calls)
    
    # Send notification to the other participant
    participants = call_data.get('participants', [])
    initiator = call_data.get('initiator', '')
    
    for participant in participants:
        if participant != initiator:
            # Get initiator name
            initiator_user = get_user_by_email(initiator)
            initiator_name = initiator_user.get('name', 'Someone') if initiator_user else 'Someone'
            
            # Create notification
            call_type = call_data.get('type', 'voice')
            call_type_text = "video call" if call_type == 'video' else "voice call"
            
            create_notification(
                user_email=participant,
                notification_type="call",
                title="📞 Incoming Call",
                message=f"{initiator_name} is calling you for a {call_type_text}",
                data={
                    "call_id": call_data.get('id'),
                    "initiator": initiator,
                    "call_type": call_type,
                    "action": "call_incoming"
                }
            )
    
    return True

def update_call_status(call_id, status, duration_minutes=None):
    """Update call status and send completion notification"""
    calls = db.load_data("calls.json")
    call_found = None
    
    for call in calls:
        if call.get('id') == call_id:
            call['status'] = status
            call['end_time'] = datetime.now().isoformat()
            
            if duration_minutes:
                call['duration'] = f"{duration_minutes} min"
            else:
                start_time = datetime.fromisoformat(call.get('start_time', datetime.now().isoformat()))
                end_time = datetime.now()
                duration = end_time - start_time
                minutes = int(duration.total_seconds() / 60)
                call['duration'] = f"{minutes} min" if minutes > 0 else "Just started"
            
            call_found = call
            break
    
    if call_found and status == 'ended':
        # Send missed call notification if call was never answered
        participants = call_found.get('participants', [])
        initiator = call_found.get('initiator', '')
        
        for participant in participants:
            if participant != initiator:
                initiator_user = get_user_by_email(initiator)
                initiator_name = initiator_user.get('name', 'Someone') if initiator_user else 'Someone'
                
                # Check if call was answered (should have call records)
                call_type = call_found.get('type', 'voice')
                call_type_text = "video call" if call_type == 'video' else "voice call"
                
                create_notification(
                    user_email=participant,
                    notification_type="call",
                    title="📞 Missed Call",
                    message=f"You missed a {call_type_text} from {initiator_name}",
                    data={
                        "call_id": call_id,
                        "initiator": initiator,
                        "call_type": call_type,
                        "action": "call_missed"
                    }
                )
    
    if call_found:
        db.save_data("calls.json", calls)
        return True
    return False

# ========== CHAT FUNCTIONS WITH NOTIFICATIONS ==========
def send_message(chat_id, sender, message_text):
    """Send a message in a chat and notify other participant"""
    chats = db.load_data("chats.json")
    
    if chat_id in chats:
        message = {
            "id": str(uuid.uuid4()),
            "sender": sender,
            "message": message_text,
            "timestamp": datetime.now().isoformat(),
            "read": False
        }
        
        chats[chat_id]["messages"].append(message)
        chats[chat_id]["last_updated"] = datetime.now().isoformat()
        db.save_data("chats.json", chats)
        
        # Send notification to other participant
        participants = chats[chat_id].get("participants", [])
        for participant in participants:
            if participant != sender:
                sender_user = get_user_by_email(sender)
                sender_name = sender_user.get('name', 'Someone') if sender_user else 'Someone'
                
                # Truncate message for notification
                preview = message_text[:50] + "..." if len(message_text) > 50 else message_text
                
                create_notification(
                    user_email=participant,
                    notification_type="message",
                    title=f"💬 New message from {sender_name}",
                    message=preview,
                    data={
                        "chat_id": chat_id,
                        "sender": sender,
                        "message_id": message["id"],
                        "action": "open_chat"
                    }
                )
        
        return True
    return False

# ========== OTHER FUNCTIONS WITH NOTIFICATIONS ==========
def create_announcement(announcement_data):
    """Create announcement and notify all students"""
    announcements = db.load_data("announcements.json")
    announcements.append(announcement_data)
    db.save_data("announcements.json", announcements)
    
    # Notify all students
    students = db.load_data("students.json")
    for student_email in students.keys():
        create_notification(
            user_email=student_email,
            notification_type="announcement",
            title="📢 New Announcement",
            message=announcement_data.get('title', 'New announcement'),
            data={
                "announcement_id": announcement_data.get('id'),
                "action": "view_announcements"
            }
        )
    
    return True

def join_club_request(student_email, club_id):
    """Send club join request and notify admin"""
    clubs = db.load_data("clubs.json")
    if club_id in clubs:
        if student_email not in clubs[club_id]["pending_requests"]:
            clubs[club_id]["pending_requests"].append(student_email)
            db.save_data("clubs.json", clubs)
            
            # Notify admin
            student = get_user_by_email(student_email)
            student_name = student.get('name', 'A student') if student else 'A student'
            club_name = clubs[club_id].get('name', 'a club')
            
            create_notification(
                user_email="MES.edu",  # Admin
                notification_type="club",
                title="👥 Club Join Request",
                message=f"{student_name} wants to join {club_name}",
                data={
                    "student_email": student_email,
                    "club_id": club_id,
                    "action": "manage_clubs"
                }
            )
            
            return True
    return False

# ========== USER MANAGEMENT ==========
def get_user_by_email(email):
    users = db.load_data("users.json")
    students = db.load_data("students.json")
    return users.get(email) or students.get(email)

def create_student(student_data):
    students = db.load_data("students.json")
    students[student_data['email']] = student_data
    db.save_data("students.json", students)
    
    # Notify admin about new student
    create_notification(
        user_email="MES.edu",
        notification_type="user",
        title="🎓 New Student Registered",
        message=f"{student_data['name']} has joined Campus Connect",
        data={
            "student_email": student_data['email'],
            "action": "view_users"
        }
    )
    
    return True

def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

def get_all_students():
    """Get all student emails and names"""
    students = db.load_data("students.json")
    return students

# ========== CHAT FUNCTIONS ==========
def create_chat(user1, user2):
    """Create a new chat between two users"""
    chats = db.load_data("chats.json")
    
    participants = sorted([user1, user2])
    chat_id = f"chat_{participants[0]}_{participants[1]}"
    
    if chat_id not in chats:
        chats[chat_id] = {
            "id": chat_id,
            "participants": participants,
            "messages": [],
            "created_date": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        db.save_data("chats.json", chats)
    return chat_id

def get_chat_messages(chat_id):
    """Get all messages in a chat"""
    chats = db.load_data("chats.json")
    return chats.get(chat_id, {}).get("messages", [])

def get_user_chats(user_email):
    """Get all chats for a user"""
    chats = db.load_data("chats.json")
    user_chats = []
    
    for chat_id, chat in chats.items():
        if user_email in chat.get("participants", []):
            messages = chat.get("messages", [])
            last_message = messages[-1] if messages else None
            
            participants = chat.get("participants", [])
            other_participant = [p for p in participants if p != user_email][0] if participants else ""
            
            user_chats.append({
                "chat_id": chat_id,
                "other_participant": other_participant,
                "last_message": last_message.get("message", "No messages yet") if last_message else "No messages yet",
                "last_timestamp": last_message.get("timestamp", chat.get("created_date")) if last_message else chat.get("created_date"),
                "unread_count": sum(1 for msg in messages if not msg.get("read", False) and msg.get("sender") != user_email)
            })
    
    user_chats.sort(key=lambda x: x["last_timestamp"], reverse=True)
    return user_chats

# ========== OTHER FUNCTIONS ==========
def get_announcements():
    return db.load_data("announcements.json")

def get_clubs():
    return db.load_data("clubs.json")

def create_confession(confession_data):
    confessions = db.load_data("confessions.json")
    confession_data['anonymous_id'] = f"anon_{str(uuid.uuid4())[:8]}"
    confessions.append(confession_data)
    db.save_data("confessions.json", confessions)
    
    # Notify admin about new confession
    create_notification(
        user_email="MES.edu",
        notification_type="confession",
        title="🗣️ New Confession",
        message="A new confession needs approval",
        data={
            "confession_id": confession_data.get('id'),
            "action": "manage_confessions"
        }
    )
    
    return True

def get_confessions_for_students():
    confessions = db.load_data("confessions.json")
    student_view = []
    for confession in confessions:
        if confession.get('is_approved', True):
            student_confession = confession.copy()
            student_confession.pop('user_email', None)
            student_view.append(student_confession)
    return student_view

def get_confessions_for_admin():
    return db.load_data("confessions.json")

def get_user_calls(user_email):
    """Get all calls for a specific user"""
    calls = db.load_data("calls.json")
    user_calls = []
    
    for call in calls:
        if user_email in call.get('participants', []):
            user_calls.append(call)
    
    user_calls.sort(key=lambda x: x.get('start_time', ''), reverse=True)
    return user_calls

def get_call_by_id(call_id):
    """Get a specific call by ID"""
    calls = db.load_data("calls.json")
    for call in calls:
        if call.get('id') == call_id:
            return call
    return None

def get_active_calls():
    """Get currently active calls"""
    calls = db.load_data("calls.json")
    active_calls = [call for call in calls if call.get('status') == 'active']
    return active_calls
