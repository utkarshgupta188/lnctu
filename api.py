from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import logging
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class LNCTAttendance:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive'
        })
        
        self.base_url = "https://accsoft2.lnctu.ac.in"
        self.login_url = f"{self.base_url}/Accsoft2/studentLogin.aspx"
        self.attendance_url = f"{self.base_url}/AccSoft2/Parents/StuAttendanceStatus.aspx"
        self.session.verify = False
    
    def get_form_data(self, soup):
        """Extract form data from ASP.NET page"""
        form_data = {}
        for inp in soup.find_all('input', {'type': 'hidden'}):
            if inp.get('name'):
                form_data[inp.get('name')] = inp.get('value', '')
        return form_data
    
    def login(self, username, password):
        try:
            # Get login page
            response = self.session.get(self.login_url, timeout=10)
            if response.status_code != 200:
                return False, f"Login page error: {response.status_code}"
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form_data = self.get_form_data(soup)
            
            # Find username and password fields
            username_field = None
            password_field = None
            
            # Check common field names
            username_candidates = ['txtUserName', 'txtUsername', 'username', 'UserId', 'txtUserId']
            password_candidates = ['txtPassword', 'password', 'Password', 'txtPass']
            
            for field in username_candidates:
                if soup.find('input', {'name': field}):
                    username_field = field
                    break
            
            for field in password_candidates:
                if soup.find('input', {'name': field}):
                    password_field = field
                    break
            
            # Fallback to input type search
            if not username_field:
                text_input = soup.find('input', {'type': 'text'})
                username_field = text_input.get('name') if text_input else None
            
            if not password_field:
                pwd_input = soup.find('input', {'type': 'password'})
                password_field = pwd_input.get('name') if pwd_input else None
            
            if not username_field or not password_field:
                return False, "Login fields not found"
            
            # Add credentials
            form_data[username_field] = username
            form_data[password_field] = password
            
            # Add submit button
            submit_btn = soup.find('input', {'type': 'submit'})
            if submit_btn:
                form_data[submit_btn.get('name', 'btnLogin')] = submit_btn.get('value', 'Login')
            
            # Submit login
            response = self.session.post(self.login_url, data=form_data, timeout=10)
            
            # Check if login successful
            if "studentLogin.aspx" in response.url:
                return False, "Invalid credentials"
            
            page_text = response.text.lower()
            success_indicators = ['welcome', 'dashboard', 'parent', 'attendance', 'logout']
            
            if any(indicator in page_text for indicator in success_indicators):
                return True, "Login successful"
            
            return False, "Login status unclear"
            
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    def extract_value(self, soup, element_id, convert_type=str):
        """Extract value from element"""
        element = soup.find('span', {'id': element_id})
        if not element:
            return convert_type() if convert_type != int else 0
            
        try:
            text = element.text.strip()
            value = text.split(':')[-1].strip() if ':' in text else text
            return convert_type(value) if value else (0 if convert_type == int else "")
        except:
            return convert_type() if convert_type != int else 0
    
    def get_attendance(self):
        try:
            response = self.session.get(self.attendance_url, timeout=10)
            
            if "studentLogin.aspx" in response.url:
                return None, "Session expired"
            
            if response.status_code != 200:
                return None, f"Attendance page error: {response.status_code}"
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract attendance data using specific IDs
            attendance_data = {
                'total_classes': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotperiod111', int),
                'present': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotalp11', int),
                'absent': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotala11', int),
                'leave': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotall11', int),
                'not_applicable': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotaln11', int),
                'on_duty': self.extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotalo11', int),
            }
            
            # Calculate percentage
            if attendance_data['total_classes'] > 0:
                attendance_data['percentage'] = round(
                    (attendance_data['present'] / attendance_data['total_classes']) * 100, 2
                )
            else:
                attendance_data['percentage'] = 0.0
            
            # Add metadata
            attendance_data.update({
                'timestamp': datetime.now().isoformat(),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'attended_classes': attendance_data['present'],
                'overall_percentage': attendance_data['percentage']
            })
            
            return attendance_data, "Success"
            
        except Exception as e:
            return None, f"Attendance error: {str(e)}"

@app.route('/')
def home():
    return '''
    <h1>LNCT Attendance API</h1>
    <form action="/attendance" method="get">
        <input type="text" name="username" placeholder="Username" required><br><br>
        <input type="password" name="password" placeholder="Password" required><br><br>
        <button type="submit">Get Attendance</button>
    </form>
    <p>API: /attendance?username=ID&password=PASS</p>
    '''

@app.route('/attendance', methods=['GET', 'POST'])
def get_attendance():
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'JSON required'}), 400
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.args.get('username')
            password = request.args.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400
        
        lnct = LNCTAttendance()
        login_success, login_message = lnct.login(username, password)
        
        if not login_success:
            return jsonify({
                'success': False,
                'error': 'Authentication failed',
                'details': login_message
            }), 401
        
        attendance_data, fetch_message = lnct.get_attendance()
        
        if attendance_data is None:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch attendance',
                'details': fetch_message
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Data retrieved successfully',
            'data': attendance_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error',
            'details': str(e)
        }), 500

@app.route('/check')
def check_site():
    try:
        lnct = LNCTAttendance()
        response = lnct.session.get(lnct.login_url, timeout=5)
        return jsonify({
            'success': True,
            'status': response.status_code,
            'accessible': response.status_code == 200
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'accessible': False
        })

if __name__ == '__main__':
    print("🚀 Starting Fast LNCT Attendance API...")
    print("📍 Access at: http://localhost:5000")
    app.run(debug=False, host='0.0.0.0', port=5000)
