from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
import requests
import urllib3
from datetime import datetime, timedelta
import logging

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
user_sessions = {}

class LNCTAttendance:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive'
        })
        self.base_url = "https://accsoft2.lnctu.ac.in"
        self.login_url = f"{self.base_url}/Accsoft2/studentLogin.aspx"
        self.attendance_url = f"{self.base_url}/AccSoft2/Parents/StuAttendanceStatus.aspx"
        self.session.verify = False

    def get_form_data(self, soup):
        form_data = {}
        for inp in soup.find_all('input', {'type': 'hidden'}):
            if inp.get('name'):
                form_data[inp.get('name')] = inp.get('value', '')
        return form_data

    def login(self, username, password):
        try:
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
                return True, "Login successful"

            return False, "Login verification failed"

        except Exception as e:
            logger.error(f"Login error: {e}")
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
        try:
            r = self.session.get(self.attendance_url, timeout=15)
            if "studentLogin.aspx" in r.url:
                return None, "Session expired"
            soup = BeautifulSoup(r.content, 'html.parser')

            ids = {
                'total_classes': ['ctl00_ctl00_ContentPlaceHolder1_cp2_lbltotperiod111'],
                'present': ['ctl00_ContentPlaceHolder1_lbltotalp11'],
                'absent': ['ctl00_ContentPlaceHolder1_lbltotala11'],
                'leave': ['ctl00_ContentPlaceHolder1_lbltotall11'],
                'not_applicable': ['ctl00_ContentPlaceHolder1_lbltotaln11'],
                'on_duty': ['ctl00_ContentPlaceHolder1_lbltotalo11']
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

            return {
                **data,
                'percentage': percentage,
                'overall_percentage': percentage,
                'attended_classes': data['present'],
                'timestamp': datetime.now().isoformat(),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, "Success"

        except Exception as e:
            logger.error(f"Attendance error: {e}")
            return None, f"Attendance error: {e}"

def cleanup_expired_sessions():
    now = datetime.now()
    expired = [u for u, s in user_sessions.items() if now - s['last_login'] > timedelta(hours=1)]
    for u in expired:
        del user_sessions[u]

@app.get("/attendance")
def attendance(username: str = "", password: str = ""):
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    cleanup_expired_sessions()

    if username in user_sessions:
        lnct = user_sessions[username]['lnct']
        data, msg = lnct.get_attendance()
        if data:
            return {"success": True, "message": "Used cached session", "data": data}
        del user_sessions[username]

    lnct = LNCTAttendance()
    ok, msg = lnct.login(username, password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)

    user_sessions[username] = {
        'lnct': lnct,
        'last_login': datetime.now()
    }

    data, msg = lnct.get_attendance()
    if not data:
        raise HTTPException(status_code=500, detail=msg)

    return {"success": True, "message": "Logged in and fetched", "data": data}

@app.get("/")
def root():
    return {
        "message": "LNCT Attendance API",
        "usage": "/attendance?username=YOUR_ID&password=YOUR_PASS",
        "active_sessions": len(user_sessions)
    }

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}
