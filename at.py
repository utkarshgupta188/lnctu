from fastapi import FastAPI, HTTPException, BackgroundTasks
from bs4 import BeautifulSoup
import requests
import urllib3
from datetime import datetime, timedelta
import logging
import asyncio
import threading
import time
import json
import os
from functools import wraps
from typing import Dict, Any, Optional
import hashlib

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="LNCT Attendance API - Automated", version="2.0.0")

# Automation configurations
CACHE_TTL = 300  # 5 minutes cache
SESSION_TTL = 1800  # 30 minutes session
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2
BACKGROUND_FETCH_INTERVAL = 60  # Background fetch every minute
MAX_CONCURRENT_USERS = 50

# Storage
user_sessions = {}
attendance_cache = {}
failed_requests = {}
background_tasks_running = False

class LNCTAttendance:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive'
        })
        self.base_url = "https://accsoft2.lnctu.ac.in"
        self.login_url = f"{self.base_url}/Accsoft2/studentLogin.aspx"
        self.attendance_url = f"{self.base_url}/AccSoft2/Parents/StuAttendanceStatus.aspx"
        self.session.verify = False
        self.last_activity = datetime.now()

    def get_form_data(self, soup):
        form_data = {}
        for inp in soup.find_all('input', {'type': 'hidden'}):
            if inp.get('name'):
                form_data[inp.get('name')] = inp.get('value', '')
        return form_data

    def retry_on_failure(self, func, *args, **kwargs):
        """Automatic retry mechanism with exponential backoff"""
        for attempt in range(RETRY_ATTEMPTS):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}, retrying in {wait_time}s")
                if attempt < RETRY_ATTEMPTS - 1:
                    time.sleep(wait_time)
                else:
                    raise e

    def login(self, username, password):
        def _login():
            logger.info(f"Attempting login for user: {username}")
            r = self.session.get(self.login_url, timeout=15)
            r.raise_for_status()

            soup = BeautifulSoup(r.content, 'html.parser')
            form_data = self.get_form_data(soup)

            # Try detecting input fields by known names
            username_field = next((f for f in ['txtUserName', 'txtUsername', 'UserId', 'txtUserId'] if soup.find('input', {'name': f})), None)
            password_field = next((f for f in ['txtPassword', 'Password', 'txtPass'] if soup.find('input', {'name': f})), None)

            # Fallback detection by input type
            if not username_field:
                user_input = soup.find('input', {'type': 'text'})
                username_field = user_input.get('name') if user_input else None

            if not password_field:
                pass_input = soup.find('input', {'type': 'password'})
                password_field = pass_input.get('name') if pass_input else None

            if not username_field or not password_field:
                return False, "Login form fields not found"

            form_data[username_field] = username
            form_data[password_field] = password

            # Include submit button if needed
            submit_btn = soup.find('input', {'type': 'submit'}) or soup.find('input', {'type': 'button'})
            if submit_btn and submit_btn.get('name'):
                form_data[submit_btn.get('name')] = submit_btn.get('value', 'Login')

            res = self.session.post(self.login_url, data=form_data, timeout=15, allow_redirects=True)
            res.raise_for_status()

            if "studentLogin.aspx" in res.url:
                return False, "Invalid credentials"

            success_indicators = ['dashboard', 'attendance', 'logout', 'welcome', 'student']
            if any(word in res.text.lower() for word in success_indicators):
                self.last_activity = datetime.now()
                return True, "Login successful"

            return False, "Login verification failed"

        try:
            return self.retry_on_failure(_login)
        except Exception as e:
            logger.error(f"Login error after all retries: {e}")
            return False, f"Login error: {e}"

    def extract_value(self, soup, element_id, convert_type=str):
        try:
            el = soup.find('span', {'id': element_id}) or soup.find('label', {'id': element_id})
            if not el:
                return convert_type() if convert_type != int else 0
            text = el.text.strip()
            if ':' in text:
                text = text.split(':')[-1].strip()
            if convert_type == int:
                digits = ''.join(filter(str.isdigit, text))
                return int(digits) if digits else 0
            return convert_type(text)
        except:
            return convert_type() if convert_type != int else 0

    def get_attendance(self):
        def _get_attendance():
            r = self.session.get(self.attendance_url, timeout=15)
            if "studentLogin.aspx" in r.url:
                return None, "Session expired"
            soup = BeautifulSoup(r.content, 'html.parser')

            ids = {
                'total_classes': ['ctl00_ctl00_ContentPlaceHolder1_cp2_lbltotperiod111'],
                'present': ['ctl00_ctl00_ContentPlaceHolder1_cp2_lbltotalp11'],
                'absent': ['ctl00_ctl00_ContentPlaceHolder1_cp2_lbltotala11']
            }

            data = {}
            for key, id_list in ids.items():
                for _id in id_list:
                    val = self.extract_value(soup, _id, int)
                    if val > 0:
                        data[key] = val
                        break
                else:
                    data[key] = 0

            if data['total_classes'] > 0:
                percentage = round((data['present'] / data['total_classes']) * 100, 2)
            else:
                percentage = 0.0

            self.last_activity = datetime.now()
            return {
                **data,
                'percentage': percentage,
                'overall_percentage': percentage,
                'attended_classes': data['present'],
                'timestamp': datetime.now().isoformat(),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, "Success"

        try:
            return self.retry_on_failure(_get_attendance)
        except Exception as e:
            logger.error(f"Attendance error after all retries: {e}")
            return None, f"Attendance error: {e}"

    def is_session_expired(self):
        """Check if session has expired based on last activity"""
        return datetime.now() - self.last_activity > timedelta(seconds=SESSION_TTL)

# Automation Helper Functions

def get_user_hash(username: str, password: str) -> str:
    """Generate a hash for user credentials"""
    return hashlib.md5(f"{username}:{password}".encode()).hexdigest()

def get_cached_session(username: str, password: str) -> Optional[LNCTAttendance]:
    """Get cached session or create new one with automatic cleanup"""
    user_hash = get_user_hash(username, password)
    now = datetime.now()
    
    # Check if session exists and is not expired
    if user_hash in user_sessions:
        session_data = user_sessions[user_hash]
        lnct = session_data['lnct']
        
        if not lnct.is_session_expired():
            logger.info(f"Using cached session for user: {username}")
            return lnct
        else:
            logger.info(f"Session expired for user: {username}, creating new session")
            del user_sessions[user_hash]
    
    # Create new session
    lnct = LNCTAttendance()
    success, msg = lnct.login(username, password)
    
    if success:
        user_sessions[user_hash] = {
            'lnct': lnct,
            'username': username,
            'created_at': now,
            'last_used': now
        }
        logger.info(f"Created new session for user: {username}")
        return lnct
    else:
        logger.error(f"Failed to create session for user: {username} - {msg}")
        return None

def get_cached_attendance(username: str) -> Optional[Dict[str, Any]]:
    """Get cached attendance data if available and fresh"""
    user_hash = get_user_hash(username, "")  # Cache by username only
    if user_hash in attendance_cache:
        cache_data = attendance_cache[user_hash]
        cache_time = datetime.fromisoformat(cache_data['cached_at'])
        
        if datetime.now() - cache_time < timedelta(seconds=CACHE_TTL):
            logger.info(f"Using cached attendance for user: {username}")
            return cache_data['data']
    
    return None

def cache_attendance(username: str, data: Dict[str, Any]):
    """Cache attendance data"""
    user_hash = get_user_hash(username, "")
    attendance_cache[user_hash] = {
        'data': data,
        'cached_at': datetime.now().isoformat()
    }
    logger.info(f"Cached attendance data for user: {username}")

def cleanup_expired_sessions():
    """Automatic cleanup of expired sessions and cache"""
    now = datetime.now()
    expired_sessions = []
    expired_cache = []
    
    # Cleanup sessions
    for user_hash, session_data in user_sessions.items():
        if session_data['lnct'].is_session_expired():
            expired_sessions.append(user_hash)
    
    for user_hash in expired_sessions:
        del user_sessions[user_hash]
        logger.info(f"Cleaned up expired session: {user_hash[:8]}...")
    
    # Cleanup cache
    for user_hash, cache_data in attendance_cache.items():
        cache_time = datetime.fromisoformat(cache_data['cached_at'])
        if now - cache_time > timedelta(seconds=CACHE_TTL):
            expired_cache.append(user_hash)
    
    for user_hash in expired_cache:
        del attendance_cache[user_hash]
        logger.info(f"Cleaned up expired cache: {user_hash[:8]}...")

async def background_fetch_attendance():
    """Background task to pre-fetch attendance for active users"""
    while background_tasks_running:
        try:
            active_users = []
            now = datetime.now()
            
            # Find recently active users
            for user_hash, session_data in list(user_sessions.items()):
                last_used = session_data['last_used']
                if now - last_used < timedelta(minutes=10):  # Active in last 10 minutes
                    active_users.append((user_hash, session_data))
            
            # Pre-fetch attendance for active users
            for user_hash, session_data in active_users:
                try:
                    lnct = session_data['lnct']
                    username = session_data['username']
                    
                    # Check if cache is stale
                    cached_data = get_cached_attendance(username)
                    if not cached_data:
                        data, msg = lnct.get_attendance()
                        if data:
                            cache_attendance(username, data)
                            logger.info(f"Pre-fetched attendance for user: {username}")
                        
                        session_data['last_used'] = now
                except Exception as e:
                    logger.error(f"Background fetch error for user {user_hash[:8]}...: {e}")
            
            # Cleanup expired data
            cleanup_expired_sessions()
            
        except Exception as e:
            logger.error(f"Background task error: {e}")
        
        await asyncio.sleep(BACKGROUND_FETCH_INTERVAL)

def start_background_tasks():
    """Start background automation tasks"""
    global background_tasks_running
    if not background_tasks_running:
        background_tasks_running = True
        loop = asyncio.new_event_loop()
        threading.Thread(target=lambda: loop.run_until_complete(background_fetch_attendance()), daemon=True).start()
        logger.info("Background automation tasks started")

def rate_limit_decorator(max_calls_per_minute: int = 30):
    """Rate limiting decorator"""
    calls = {}
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            minute = int(now // 60)
            
            if minute not in calls:
                calls[minute] = 0
            
            if calls[minute] >= max_calls_per_minute:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
            
            calls[minute] += 1
            
            # Cleanup old entries
            old_minutes = [m for m in calls.keys() if m < minute - 1]
            for old_minute in old_minutes:
                del calls[old_minute]
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@app.on_event("startup")
async def startup_event():
    """Initialize automation on startup"""
    logger.info("Starting LNCT Attendance API with automation features...")
    start_background_tasks()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global background_tasks_running
    background_tasks_running = False
    logger.info("Shutting down automation tasks...")

@app.get("/attendance")
@rate_limit_decorator(max_calls_per_minute=60)
async def attendance(username: str = "", password: str = "", background_tasks: BackgroundTasks = None):
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    # Check cache first for faster response
    cached_data = get_cached_attendance(username)
    if cached_data:
        return {
            "success": True, 
            "message": "Retrieved from cache (fast response)", 
            "data": cached_data,
            "cached": True
        }

    # Get or create session
    lnct = get_cached_session(username, password)
    if not lnct:
        raise HTTPException(status_code=401, detail="Authentication failed")

    # Fetch attendance data
    data, msg = lnct.get_attendance()
    if not data:
        # Track failed requests for analysis
        user_hash = get_user_hash(username, password)
        failed_requests[user_hash] = {
            'timestamp': datetime.now().isoformat(),
            'error': msg
        }
        raise HTTPException(status_code=500, detail=msg)

    # Cache the data
    cache_attendance(username, data)
    
    # Update session last used time
    user_hash = get_user_hash(username, password)
    if user_hash in user_sessions:
        user_sessions[user_hash]['last_used'] = datetime.now()

    return {
        "success": True, 
        "message": "Data fetched and cached", 
        "data": data,
        "cached": False
    }

@app.post("/attendance")
@rate_limit_decorator(max_calls_per_minute=30)
async def attendance_post(credentials: dict, background_tasks: BackgroundTasks = None):
    """Secure POST endpoint for attendance"""
    username = credentials.get("username")
    password = credentials.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    # Use the same logic as GET endpoint
    return await attendance(username, password, background_tasks)

@app.get("/batch-attendance")
@rate_limit_decorator(max_calls_per_minute=10)
async def batch_attendance(users: str):
    """Batch processing for multiple users (format: user1:pass1,user2:pass2)"""
    try:
        user_pairs = []
        for pair in users.split(','):
            if ':' in pair:
                username, password = pair.strip().split(':', 1)
                user_pairs.append((username, password))
        
        if len(user_pairs) > 10:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximum 10 users per batch request")
        
        results = {}
        for username, password in user_pairs:
            try:
                # Check cache first
                cached_data = get_cached_attendance(username)
                if cached_data:
                    results[username] = {"success": True, "data": cached_data, "cached": True}
                    continue
                
                # Get session and fetch data
                lnct = get_cached_session(username, password)
                if lnct:
                    data, msg = lnct.get_attendance()
                    if data:
                        cache_attendance(username, data)
                        results[username] = {"success": True, "data": data, "cached": False}
                    else:
                        results[username] = {"success": False, "error": msg}
                else:
                    results[username] = {"success": False, "error": "Authentication failed"}
            except Exception as e:
                results[username] = {"success": False, "error": str(e)}
        
        return {"success": True, "results": results}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Batch processing error: {str(e)}")

@app.get("/")
def root():
    active_sessions = len(user_sessions)
    cached_data = len(attendance_cache)
    
    return {
        "message": "LNCT Attendance API - Automated Version",
        "version": "2.0.0",
        "features": [
            "Session caching with auto-cleanup",
            "Automatic retry mechanisms", 
            "Background data pre-fetching",
            "Rate limiting protection",
            "Batch processing support",
            "Health monitoring"
        ],
        "usage": {
            "single": "/attendance?username=YOUR_ID&password=YOUR_PASS",
            "batch": "/batch-attendance?users=user1:pass1,user2:pass2",
            "secure": "POST /attendance with JSON {username, password}"
        },
        "status": {
            "active_sessions": active_sessions,
            "cached_data_count": cached_data,
            "background_tasks": background_tasks_running
        }
    }

@app.get("/health")
def health():
    """Health check endpoint with detailed status"""
    now = datetime.now()
    active_sessions = len(user_sessions)
    cached_data = len(attendance_cache)
    failed_count = len(failed_requests)
    
    # Calculate average response time (simplified)
    health_status = "healthy" if active_sessions < MAX_CONCURRENT_USERS else "degraded"
    
    return {
        "status": health_status,
        "timestamp": now.isoformat(),
        "uptime": "running",
        "metrics": {
            "active_sessions": active_sessions,
            "cached_data_count": cached_data,
            "failed_requests": failed_count,
            "background_tasks_running": background_tasks_running,
            "max_concurrent_users": MAX_CONCURRENT_USERS
        },
        "cache_settings": {
            "cache_ttl_seconds": CACHE_TTL,
            "session_ttl_seconds": SESSION_TTL,
            "background_fetch_interval": BACKGROUND_FETCH_INTERVAL
        }
    }

@app.get("/status/{username}")
@rate_limit_decorator(max_calls_per_minute=20)
async def user_status(username: str):
    """Get status for a specific user"""
    user_hash = get_user_hash(username, "")
    
    status = {
        "username": username,
        "session_active": False,
        "cached_data_available": False,
        "last_activity": None
    }
    
    # Check session status
    for hash_key, session_data in user_sessions.items():
        if session_data['username'] == username:
            status["session_active"] = True
            status["last_activity"] = session_data['last_used'].isoformat()
            break
    
    # Check cache status
    if user_hash in attendance_cache:
        cache_data = attendance_cache[user_hash]
        cache_time = datetime.fromisoformat(cache_data['cached_at'])
        time_since_cache = datetime.now() - cache_time
        
        if time_since_cache < timedelta(seconds=CACHE_TTL):
            status["cached_data_available"] = True
            status["cache_age_seconds"] = time_since_cache.total_seconds()
    
    return status

@app.post("/refresh-cache/{username}")
@rate_limit_decorator(max_calls_per_minute=10)
async def refresh_cache(username: str, credentials: dict):
    """Force refresh cache for a user"""
    password = credentials.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="Password required")
    
    lnct = get_cached_session(username, password)
    if not lnct:
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    data, msg = lnct.get_attendance()
    if not data:
        raise HTTPException(status_code=500, detail=msg)
    
    cache_attendance(username, data)
    
    return {
        "success": True,
        "message": "Cache refreshed successfully",
        "data": data
    }

@app.get("/cleanup")
@rate_limit_decorator(max_calls_per_minute=5)
async def manual_cleanup():
    """Manual cleanup endpoint for maintenance"""
    initial_sessions = len(user_sessions)
    initial_cache = len(attendance_cache)
    
    cleanup_expired_sessions()
    
    final_sessions = len(user_sessions)
    final_cache = len(attendance_cache)
    
    return {
        "success": True,
        "message": "Cleanup completed",
        "cleaned": {
            "sessions": initial_sessions - final_sessions,
            "cache_entries": initial_cache - final_cache
        },
        "remaining": {
            "sessions": final_sessions,
            "cache_entries": final_cache
        }
    }
