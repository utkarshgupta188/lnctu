Full LNCT Attendance API with session caching for faster response

from flask import Flask, request, jsonify import requests from bs4 import BeautifulSoup from datetime import datetime from cachetools import TTLCache import urllib3 import logging

Disable SSL warnings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

Configure logging

logging.basicConfig(level=logging.WARNING) logger = logging.getLogger(name)

app = Flask(name)

Session cache: holds LNCTAttendance objects per username:password pair

session_cache = TTLCache(maxsize=100, ttl=60)  # 1 min cache

class LNCTAttendance: def init(self): self.session = requests.Session() self.session.headers.update({ 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,/;q=0.8', 'Connection': 'keep-alive' }) self.base_url = "https://accsoft2.lnctu.ac.in" self.login_url = f"{self.base_url}/Accsoft2/studentLogin.aspx" self.attendance_url = f"{self.base_url}/AccSoft2/Parents/StuAttendanceStatus.aspx" self.session.verify = False

def get_form_data(self, soup):
    return {inp.get('name'): inp.get('value', '') for inp in soup.find_all('input', {'type': 'hidden'}) if inp.get('name')}

def login(self, username, password):
    try:
        res = self.session.get(self.login_url, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        form_data = self.get_form_data(soup)

        username_field = next((field for field in ['txtUserName', 'txtUsername', 'username', 'UserId', 'txtUserId'] if soup.find('input', {'name': field})), None)
        password_field = next((field for field in ['txtPassword', 'password', 'Password', 'txtPass'] if soup.find('input', {'name': field})), None)

        if not username_field:
            username_field = soup.find('input', {'type': 'text'}).get('name')
        if not password_field:
            password_field = soup.find('input', {'type': 'password'}).get('name')

        if not username_field or not password_field:
            return False, "Login fields not found"

        form_data[username_field] = username
        form_data[password_field] = password

        submit = soup.find('input', {'type': 'submit'})
        if submit:
            form_data[submit.get('name', 'btnLogin')] = submit.get('value', 'Login')

        res = self.session.post(self.login_url, data=form_data, timeout=10)

        if "studentLogin.aspx" in res.url:
            return False, "Invalid credentials"

        if any(tag in res.text.lower() for tag in ['welcome', 'parent', 'attendance']):
            return True, "Login successful"

        return False, "Login unclear"
    except Exception as e:
        return False, f"Login error: {str(e)}"

def extract_value(self, soup, element_id, convert_type=str):
    el = soup.find('span', {'id': element_id})
    try:
        val = el.text.strip().split(':')[-1].strip() if el else ''
        return convert_type(val) if val else (0 if convert_type == int else '')
    except:
        return 0 if convert_type == int else ''

def get_attendance(self):
    try:
        res = self.session.get(self.attendance_url, timeout=10)
        if "studentLogin.aspx" in res.url:
            return None, "Session expired"
        if res.status_code != 200:
            return None, f"Attendance page error: {res.status_code}"

        soup = BeautifulSoup(res.content, 'html.parser')

        data = {
            'total_classes': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotperiod111', int),
            'present': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotalp11', int),
            'absent': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotala11', int),
            'leave': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotall11', int),
            'not_applicable': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotaln11', int),
            'on_duty': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotalo11', int),
        }

        data['percentage'] = round((data['present'] / data['total_classes']) * 100, 2) if data['total_classes'] else 0.0
        data.update({
            'timestamp': datetime.now().isoformat(),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'attended_classes': data['present'],
            'overall_percentage': data['percentage']
        })
        return data, "Success"

    except Exception as e:
        return None, f"Attendance error: {str(e)}"

Util: get session from cache or login

def get_cached_session(username, password): key = f"{username}:{password}" if key in session_cache: return session_cache[key] lnct = LNCTAttendance() success, msg = lnct.login(username, password) if success: session_cache[key] = lnct return lnct return None

@app.route('/') def home(): return ''' <h1>LNCT Attendance API</h1> <form action="/attendance" method="get"> <input type="text" name="username" placeholder="Username" required><br><br> <input type="password" name="password" placeholder="Password" required><br><br> <button type="submit">Get Attendance</button> </form> <p>API: /attendance?username=ID&password=PASS</p> '''

@app.route('/attendance', methods=['GET', 'POST']) def get_attendance(): try: if request.method == 'POST': data = request.get_json() if not data: return jsonify({'success': False, 'error': 'JSON required'}), 400 username = data.get('username') password = data.get('password') else: username = request.args.get('username') password = request.args.get('password')

if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400

    lnct = get_cached_session(username, password)
    if not lnct:
        return jsonify({'success': False, 'error': 'Login failed'}), 401

    attendance_data, msg = lnct.get_attendance()
    if not attendance_data:
        return jsonify({'success': False, 'error': 'Fetch failed', 'details': msg}), 500

    return jsonify({'success': True, 'data': attendance_data})

except Exception as e:
    return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/check') def check_site(): try: lnct = LNCTAttendance() res = lnct.session.get(lnct.login_url, timeout=5) return jsonify({'success': True, 'status': res.status_code, 'accessible': res.status_code == 200}) except Exception as e: return jsonify({'success': False, 'error': str(e), 'accessible': False})

if name == 'main': print("🚀 LNCT Attendance API Running on http://localhost:5000") app.run(debug=False, host='0.0.0.0', port=5000)

