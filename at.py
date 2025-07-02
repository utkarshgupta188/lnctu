from fastapi import FastAPI, Request, HTTPException
from bs4 import BeautifulSoup
import requests
import urllib3
from datetime import datetime, timedelta
import logging

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
user_sessions = {}

class LNCTAttendance:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.base_url = "https://accsoft2.lnctu.ac.in"
        self.login_url = f"{self.base_url}/Accsoft2/studentLogin.aspx"
        self.attendance_url = f"{self.base_url}/AccSoft2/Parents/StuAttendanceStatus.aspx"
        self.session.verify = False

    def get_form_data(self, soup):
        """Extract all hidden form fields"""
        form_data = {}
        for inp in soup.find_all('input', {'type': 'hidden'}):
            name = inp.get('name')
            value = inp.get('value', '')
            if name:
                form_data[name] = value
        return form_data

    def login(self, username, password):
        """Login to LNCT portal"""
        try:
            logger.info(f"Attempting login for user: {username}")
            
            # Get login page
            response = self.session.get(self.login_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form_data = self.get_form_data(soup)

            # Find username and password fields
            username_field = None
            password_field = None
            
            for field_name in ['txtUserName', 'txtUsername', 'UserId', 'txtUserId']:
                if soup.find('input', {'name': field_name}):
                    username_field = field_name
                    break
                    
            for field_name in ['txtPassword', 'Password', 'txtPass']:
                if soup.find('input', {'name': field_name}):
                    password_field = field_name
                    break

            if not username_field or not password_field:
                logger.error("Login fields not found on page")
                return False, "Login form fields not found"

            # Fill login data
            form_data[username_field] = username
            form_data[password_field] = password

            # Find submit button
            submit_btn = soup.find('input', {'type': 'submit'}) or soup.find('input', {'type': 'button'})
            if submit_btn and submit_btn.get('name'):
                form_data[submit_btn.get('name')] = submit_btn.get('value', 'Login')

            # Submit login
            login_response = self.session.post(
                self.login_url, 
                data=form_data, 
                timeout=15,
                allow_redirects=True
            )
            login_response.raise_for_status()

            # Check if login was successful
            if "studentLogin.aspx" in login_response.url:
                logger.warning("Login failed - redirected back to login page")
                return False, "Invalid username or password"
            
            # Check for success indicators in response
            response_text = login_response.text.lower()
            success_indicators = ['dashboard', 'attendance', 'logout', 'welcome', 'student']
            
            if any(indicator in response_text for indicator in success_indicators):
                logger.info("Login successful")
                return True, "Login successful"
            
            logger.warning("Login status uncertain")
            return False, "Login verification failed"

        except requests.RequestException as e:
            logger.error(f"Network error during login: {str(e)}")
            return False, f"Network error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            return False, f"Login error: {str(e)}"

    def extract_value(self, soup, element_id, convert_type=str):
        """Extract value from HTML element"""
        try:
            element = soup.find('span', {'id': element_id})
            if not element:
                # Try alternative selectors
                element = soup.find('label', {'id': element_id})
            
            if not element:
                logger.warning(f"Element not found: {element_id}")
                return convert_type() if convert_type != int else 0
            
            text = element.get_text(strip=True)
            if not text:
                return convert_type() if convert_type != int else 0
            
            # Handle cases where text contains labels like "Total: 50"
            if ':' in text:
                value = text.split(':')[-1].strip()
            else:
                value = text
            
            # Remove any non-numeric characters for int conversion
            if convert_type == int:
                value = ''.join(filter(str.isdigit, value))
                return int(value) if value else 0
            
            return convert_type(value) if value else convert_type()
            
        except Exception as e:
            logger.error(f"Error extracting value for {element_id}: {str(e)}")
            return convert_type() if convert_type != int else 0

    def get_attendance(self):
        """Fetch attendance data"""
        try:
            logger.info("Fetching attendance data")
            
            response = self.session.get(self.attendance_url, timeout=15)
            
            # Check if redirected to login (session expired)
            if "studentLogin.aspx" in response.url:
                logger.warning("Session expired - redirected to login")
                return None, "Session expired, please login again"
            
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract attendance data with multiple possible element IDs
            attendance_data = {
                'total_classes': 0,
                'present': 0,
                'absent': 0,
                'leave': 0,
                'not_applicable': 0,
                'on_duty': 0
            }

            # Try multiple possible element ID patterns
            id_patterns = {
                'total_classes': [
                    'ctl00_ContentPlaceHolder1_lbltotperiod111',
                    'lbltotperiod111',
                    'lblTotalClasses'
                ],
                'present': [
                    'ctl00_ContentPlaceHolder1_lbltotalp11',
                    'lbltotalp11',
                    'lblPresent'
                ],
                'absent': [
                    'ctl00_ContentPlaceHolder1_lbltotala11',
                    'lbltotala11',
                    'lblAbsent'
                ],
                'leave': [
                    'ctl00_ContentPlaceHolder1_lbltotall11',
                    'lbltotall11',
                    'lblLeave'
                ],
                'not_applicable': [
                    'ctl00_ContentPlaceHolder1_lbltotaln11',
                    'lbltotaln11',
                    'lblNA'
                ],
                'on_duty': [
                    'ctl00_ContentPlaceHolder1_lbltotalo11',
                    'lbltotalo11',
                    'lblOnDuty'
                ]
            }

            for key, possible_ids in id_patterns.items():
                for element_id in possible_ids:
                    value = self.extract_value(soup, element_id, int)
                    if value > 0:  # Found a valid value
                        attendance_data[key] = value
                        break

            # Calculate percentage
            total_classes = attendance_data['total_classes']
            present = attendance_data['present']
            
            if total_classes > 0:
                percentage = round((present / total_classes) * 100, 2)
            else:
                percentage = 0.0

            # Prepare final response
            result = {
                **attendance_data,
                'percentage': percentage,
                'overall_percentage': percentage,
                'attended_classes': present,
                'timestamp': datetime.now().isoformat(),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            logger.info(f"Attendance data retrieved successfully: {result}")
            return result, "Success"

        except requests.RequestException as e:
            logger.error(f"Network error fetching attendance: {str(e)}")
            return None, f"Network error: {str(e)}"
        except Exception as e:
            logger.error(f"Error fetching attendance: {str(e)}")
            return None, f"Attendance fetch error: {str(e)}"

def cleanup_expired_sessions():
    """Remove sessions older than 1 hour"""
    current_time = datetime.now()
    expired_users = []
    
    for username, session_data in user_sessions.items():
        if current_time - session_data['last_login'] > timedelta(hours=1):
            expired_users.append(username)
    
    for username in expired_users:
        del user_sessions[username]
        logger.info(f"Cleaned up expired session for user: {username}")

@app.get("/attendance")
def get_attendance(username: str = "", password: str = ""):
    """Get attendance data for a student"""
    
    if not username or not password:
        raise HTTPException(
            status_code=400, 
            detail="Username and password are required parameters"
        )

    username = username.strip()
    
    # Clean up expired sessions
    cleanup_expired_sessions()

    # Try to reuse existing session
    if username in user_sessions:
        logger.info(f"Attempting to reuse session for user: {username}")
        cached_data = user_sessions[username]
        lnct = cached_data['lnct']
        
        # Try to get attendance with cached session
        data, message = lnct.get_attendance()
        
        if data:
            logger.info(f"Successfully used cached session for user: {username}")
            return {
                "success": True,
                "message": "Data fetched using cached session",
                "data": data
            }
        else:
            logger.warning(f"Cached session failed for user: {username}, will retry with fresh login")
            # Remove invalid session
            del user_sessions[username]

    # Fresh login required
    logger.info(f"Performing fresh login for user: {username}")
    lnct = LNCTAttendance()
    
    login_success, login_message = lnct.login(username, password)
    
    if not login_success:
        logger.error(f"Login failed for user {username}: {login_message}")
        raise HTTPException(status_code=401, detail=login_message)

    # Cache the session
    user_sessions[username] = {
        'lnct': lnct,
        'last_login': datetime.now()
    }

    # Get attendance data
    data, message = lnct.get_attendance()
    
    if not data:
        logger.error(f"Failed to fetch attendance for user {username}: {message}")
        raise HTTPException(status_code=500, detail=message)

    logger.info(f"Successfully fetched attendance for user: {username}")
    return {
        "success": True,
        "message": "Data fetched after fresh login",
        "data": data
    }

@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "LNCT Attendance API",
        "version": "2.0",
        "usage": "/attendance?username=YOUR_USERNAME&password=YOUR_PASSWORD",
        "active_sessions": len(user_sessions)
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(user_sessions)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
