from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import time
from functools import wraps
import urllib3
from urllib.parse import urljoin
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable SSL warnings if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

def rate_limit(calls_per_minute=30):
    """Simple rate limiting decorator"""
    def decorator(f):
        if not hasattr(f, 'last_called'):
            f.last_called = {}
        @wraps(f)
        def wrapper(*args, **kwargs):
            now = time.time()
            client_id = request.remote_addr
            
            if client_id in f.last_called:
                time_since_last_call = now - f.last_called[client_id]
                if time_since_last_call < (60 / calls_per_minute):
                    return jsonify({
                        'success': False,
                        'error': 'Rate limit exceeded. Please wait before making another request.'
                    }), 429
            
            f.last_called[client_id] = now
            return f(*args, **kwargs)
        return wrapper
    return decorator

class LNCTAttendance:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        # Updated URLs - check if these are correct
        self.base_url = "https://accsoft2.lnctu.ac.in"
        self.login_url = f"{self.base_url}/Accsoft2/studentLogin.aspx"
        self.dashboard_url = f"{self.base_url}/AccSoft2/Parents/ParentDesk.aspx"
        self.attendance_url = f"{self.base_url}/AccSoft2/Parents/StuAttendanceStatus.aspx"
        self.timeout = 15  # Increased timeout
        
        # Disable SSL verification if needed (for testing only)
        self.session.verify = False
    
    def get_form_data(self, soup):
        """Extract all necessary form data from ASP.NET page"""
        form_data = {}
        
        # Get all hidden inputs
        hidden_inputs = soup.find_all('input', {'type': 'hidden'})
        for inp in hidden_inputs:
            name = inp.get('name')
            value = inp.get('value', '')
            if name:
                form_data[name] = value
        
        return form_data
    
    def login(self, username, password):
        try:
            print(f"Attempting to access login page: {self.login_url}")
            
            # First, get the login page
            response = self.session.get(self.login_url, timeout=self.timeout)
            print(f"Login page status: {response.status_code}")
            
            if response.status_code != 200:
                return False, f"Cannot access login page. Status: {response.status_code}"
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: Check if we got the right page
            title = soup.find('title')
            print(f"Page title: {title.get_text() if title else 'No title'}")
            
            # Get all form data including hidden fields
            form_data = self.get_form_data(soup)
            
            # Find ALL input fields to debug
            all_inputs = soup.find_all('input')
            print(f"All input fields found: {len(all_inputs)}")
            
            for inp in all_inputs:
                field_type = inp.get('type', 'text')
                field_name = inp.get('name', 'no-name')
                field_id = inp.get('id', 'no-id')
                print(f"  - Type: {field_type}, Name: {field_name}, ID: {field_id}")
            
            # Try to find username field by multiple methods
            username_field = None
            password_field = None
            
            # Method 1: By common names
            username_candidates = ['txtUserName', 'txtUsername', 'username', 'UserId', 'txtUserId', 'user', 'login', 'studentId']
            password_candidates = ['txtPassword', 'password', 'Password', 'txtPass', 'pass', 'pwd']
            
            for field in username_candidates:
                if soup.find('input', {'name': field}):
                    username_field = field
                    break
            
            for field in password_candidates:
                if soup.find('input', {'name': field}):
                    password_field = field
                    break
            
            # Method 2: By type (if names don't work)
            if not username_field:
                text_inputs = soup.find_all('input', {'type': 'text'})
                if text_inputs:
                    username_field = text_inputs[0].get('name')
                    print(f"Found username field by type: {username_field}")
            
            if not password_field:
                password_inputs = soup.find_all('input', {'type': 'password'})
                if password_inputs:
                    password_field = password_inputs[0].get('name')
                    print(f"Found password field by type: {password_field}")
            
            # Method 3: By ID if name is not available
            if not username_field:
                for inp in all_inputs:
                    inp_id = inp.get('id', '').lower()
                    inp_name = inp.get('name', '').lower()
                    if any(keyword in inp_id for keyword in ['user', 'login', 'student']) or any(keyword in inp_name for keyword in ['user', 'login', 'student']):
                        username_field = inp.get('name') or inp.get('id')
                        break
            
            if not password_field:
                for inp in all_inputs:
                    inp_id = inp.get('id', '').lower()
                    inp_name = inp.get('name', '').lower()
                    if any(keyword in inp_id for keyword in ['pass', 'pwd']) or any(keyword in inp_name for keyword in ['pass', 'pwd']):
                        password_field = inp.get('name') or inp.get('id')
                        break
            
            print(f"Final fields - Username: {username_field}, Password: {password_field}")
            
            if not username_field or not password_field:
                # Return detailed info about what we found
                available_fields = [inp.get('name') for inp in all_inputs if inp.get('name')]
                return False, f"Could not find login fields. Available field names: {available_fields}. Username field: {username_field}, Password field: {password_field}"
            
            # Add credentials to form data
            form_data[username_field] = username
            form_data[password_field] = password
            
            # Find submit button
            submit_buttons = soup.find_all('input', {'type': 'submit'})
            login_buttons = soup.find_all('input', {'type': 'button'})
            
            # Add submit button value
            if submit_buttons:
                btn = submit_buttons[0]
                form_data[btn.get('name', 'btnLogin')] = btn.get('value', 'Login')
            elif login_buttons:
                btn = login_buttons[0]
                form_data[btn.get('name', 'btnLogin')] = btn.get('value', 'Login')
            else:
                form_data['btnLogin'] = 'Login'
            
            print(f"Form data keys: {list(form_data.keys())}")
            
            # Add delay to avoid being flagged as bot
            
            # Submit login form
            print("Submitting login form...")
            response = self.session.post(
                self.login_url, 
                data=form_data,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            print(f"Login response status: {response.status_code}")
            print(f"Final URL after login: {response.url}")
            
            # Check response
            if response.status_code != 200:
                return False, f"Login request failed. Status: {response.status_code}"
            
            # Parse response
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Check for error messages first
            error_indicators = [
                'invalid username or password',
                'login failed',
                'incorrect username',
                'incorrect password',
                'authentication failed',
                'invalid credentials',
                'error',
                'failed'
            ]
            
            for error in error_indicators:
                if error in page_text:
                    return False, f"Login failed: Found error '{error}'"
            
            # Check for success indicators
            success_indicators = [
                'welcome',
                'dashboard',
                'parent desk',
                'parentdesk',
                'student information',
                'attendance',
                'logout'
            ]
            
            success_found = []
            for indicator in success_indicators:
                if indicator in page_text:
                    success_found.append(indicator)
            
            # Check URL for success
            if 'parentdesk' in response.url.lower() or 'dashboard' in response.url.lower():
                return True, f"Login successful - Redirected to dashboard. Found indicators: {success_found}"
            
            # Check if we're still on login page
            if 'studentlogin' in response.url.lower():
                return False, "Login failed - Still on login page"
            
            # If we found success indicators but URL is unclear
            if success_found:
                return True, f"Login likely successful - Found indicators: {success_found}"
            
            return False, f"Login status unclear. URL: {response.url}, Page title: {soup.find('title').get_text() if soup.find('title') else 'No title'}"
            
        except requests.exceptions.Timeout:
            return False, "Login failed - Request timeout"
        except requests.exceptions.ConnectionError:
            return False, "Login failed - Connection error"
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    def verify_dashboard_access(self):
        """Verify we can access the dashboard"""
        try:
            response = self.session.get(self.dashboard_url, timeout=self.timeout)
            
            # If redirected back to login, session expired
            if "studentLogin.aspx" in response.url:
                return False, "Session expired - redirected to login"
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Check for dashboard indicators
            dashboard_indicators = ["parent desk", "parentdesk", "dashboard", "welcome", "logout", "student"]
            
            for indicator in dashboard_indicators:
                if indicator in page_text:
                    return True, f"Dashboard access verified - Found '{indicator}'"
            
            return False, "Dashboard access uncertain - No clear indicators found"
            
        except requests.exceptions.Timeout:
            return False, "Dashboard verification failed - Request timeout"
        except Exception as e:
            return False, f"Dashboard verification error: {str(e)}"
    
    def _extract_value(self, soup, element_id, convert_type=str):
        """Helper to extract and convert element values - same as your working code"""
        element = soup.find('span', {'id': element_id})
        if not element:
            logger.warning(f"Element {element_id} not found")
            return convert_type() if convert_type != int else 0
            
        try:
            # Get the last part after ":" which usually contains the value
            text = element.text.strip()
            if ':' in text:
                value = text.split(':')[-1].strip()
            else:
                value = text
            
            return convert_type(value) if value else (0 if convert_type == int else "")
        except (ValueError, IndexError) as e:
            logger.warning(f"Error converting value for {element_id}: {str(e)}")
            return convert_type() if convert_type != int else 0
    
    def get_attendance(self):
        """Updated attendance fetching using specific element IDs like your working code"""
        try:
            # First verify we still have dashboard access
            dashboard_ok, dashboard_msg = self.verify_dashboard_access()
            if not dashboard_ok:
                return None, dashboard_msg
            
            logger.info("Fetching attendance page...")
            response = self.session.get(self.attendance_url, timeout=self.timeout)
            
            # Check if redirected to login (session expired)
            if "studentLogin.aspx" in response.url:
                return None, "Session expired while accessing attendance"
            
            if response.status_code != 200:
                return None, f"Failed to access attendance page. Status: {response.status_code}"
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Verify we're on the right page
            page_title = soup.title.string if soup.title else ""
            if "Attendance" not in page_title and "attendance" not in response.text.lower():
                return None, "Could not access attendance page - wrong page loaded"
            
            # Extract attendance data using specific element IDs (same as your working code)
            attendance_data = {
                'total_classes': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotperiod111', int),
                'present': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotalp11', int),
                'absent': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotala11', int),
                'leave': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotall11', int),
                'not_applicable': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotaln11', int),
                'on_duty': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotalo11', int),
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
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
                'attended_classes': attendance_data['present'],  # For backward compatibility
                'overall_percentage': attendance_data['percentage']  # For backward compatibility
            })
            
            # Also try to get subject-wise attendance if available
            subjects = self._extract_subject_attendance(soup)
            if subjects:
                attendance_data['subjects'] = subjects
            else:
                attendance_data['subjects'] = []
            
            return attendance_data, "Attendance fetched successfully"
            
        except requests.exceptions.Timeout:
            return None, "Attendance fetch failed - Request timeout"
        except Exception as e:
            logger.error(f"Attendance fetch error: {str(e)}")
            return None, f"Attendance fetch error: {str(e)}"
    
    def _extract_subject_attendance(self, soup):
        """Try to extract subject-wise attendance if available"""
        subjects = []
        
        try:
            # Look for subject-wise attendance tables
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                # Skip tables with too few rows
                if len(rows) < 2:
                    continue
                
                # Check if this looks like a subject attendance table
                header_row = rows[0]
                header_text = header_row.get_text().lower()
                
                # Skip if header doesn't contain subject-related keywords
                if not any(keyword in header_text for keyword in ['subject', 'course', 'paper']):
                    continue
                    
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        cell_texts = [cell.get_text().strip() for cell in cells]
                        
                        # Skip empty rows
                        if not any(cell_texts):
                            continue
                        
                        # Extract subject name (usually first column)
                        subject_name = cell_texts[0]
                        
                        # Skip if subject name is empty or looks like a total row
                        skip_patterns = ['', 'total', 'overall', 'grand total', 'summary', 'grand', 'overall total']
                        if (not subject_name or 
                            subject_name.isdigit() or 
                            subject_name.lower() in skip_patterns or
                            len(subject_name) < 3):
                            continue
                        
                        # Look for attendance data in format "45/50" or "45 / 50" or separate columns
                        attended = total = None
                        
                        # Method 1: Look for "attended/total" pattern
                        for text in cell_texts[1:]:
                            match = re.search(r'(\d+)\s*/\s*(\d+)', text)
                            if match:
                                attended = int(match.group(1))
                                total = int(match.group(2))
                                break
                        
                        # Method 2: Look for separate columns with numbers
                        if attended is None:
                            numbers = []
                            for text in cell_texts[1:]:
                                if text.isdigit():
                                    numbers.append(int(text))
                            
                            if len(numbers) >= 2:
                                attended = numbers[0]
                                total = numbers[1]
                        
                        # If we found valid attendance data
                        if attended is not None and total is not None:
                            # Sanity check
                            if 0 <= attended <= total and total > 0:
                                percentage = round((attended / total) * 100, 2)
                                
                                subjects.append({
                                    'subject': subject_name,
                                    'attended': attended,
                                    'total': total,
                                    'percentage': percentage
                                })
        
        except Exception as e:
            logger.warning(f"Could not extract subject-wise attendance: {str(e)}")
        
        return subjects

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>LNCT Attendance API - Updated</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; }
            .form-group { margin: 15px 0; }
            input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            .example { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
            code { background: #e9ecef; padding: 2px 5px; border-radius: 3px; }
            .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 10px; border-radius: 5px; margin: 15px 0; }
            .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 10px; border-radius: 5px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎓 LNCT Attendance API - Fixed</h1>
            
            <div class="success">
                <strong>✅ Fixed:</strong> Attendance parsing now uses specific element IDs like your working example!
            </div>
            
            <div class="warning">
                <strong>⚠️ Security Note:</strong> For production use, consider using POST requests to avoid credentials in URL logs.
            </div>
            
            <h3>Test Your Credentials:</h3>
            <form action="/attendance" method="get">
                <div class="form-group">
                    <input type="text" name="username" placeholder="Enter Username" required>
                </div>
                <div class="form-group">
                    <input type="password" name="password" placeholder="Enter Password" required>
                </div>
                <button type="submit">Get Attendance</button>
            </form>
            
            <div class="example">
                <h3>API Endpoints:</h3>
                <p><strong>GET</strong> <code>/attendance?username=ID&password=PASS</code> - Get attendance data</p>
                <p><strong>POST</strong> <code>/attendance</code> - Get attendance data (secure)</p>
                <p><strong>GET</strong> <code>/login-test?username=ID&password=PASS</code> - Test login only</p>
                <p><strong>GET</strong> <code>/debug-login?username=ID&password=PASS</code> - Debug login process</p>
                <p><strong>GET</strong> <code>/check-site</code> - Check if LNCT site is accessible</p>
            </div>
            
            <div class="example">
                <h3>Updated Response Format:</h3>
                <pre>{
  "success": true,
  "data": {
    "total_classes": 120,
    "present": 95,
    "absent": 20,
    "leave": 3,
    "not_applicable": 2,
    "on_duty": 0,
    "percentage": 79.17,
    "subjects": [...],
    "timestamp": "2025-06-22T12:30:00",
    "last_updated": "2025-06-22 12:30:00"
  }
}</pre>
            </div>
            
            <div class="example">
                <h3>Key Improvements:</h3>
                <ul>
                    <li>✅ Fixed attendance parsing using specific element IDs</li>
                    <li>✅ Added detailed attendance breakdown (present, absent, leave, etc.)</li>
                    <li>✅ Improved error handling and logging</li>
                    <li>✅ Better session verification</li>
                    <li>✅ Backward compatibility with existing response format</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/check-site')
def check_site():
    """Check if the LNCT site is accessible"""
    try:
        lnct = LNCTAttendance()
        response = lnct.session.get(lnct.login_url, timeout=10)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title')
        
        return jsonify({
            'success': True,
            'status_code': response.status_code,
            'url': response.url,
            'title': title.get_text() if title else 'No title',
            'site_accessible': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'site_accessible': False
        })

@app.route('/attendance', methods=['GET', 'POST'])
@rate_limit(calls_per_minute=20)
def get_attendance():
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'JSON data required for POST requests'
                }), 400
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.args.get('username')
            password = request.args.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required',
                'usage': {
                    'GET': '/attendance?username=YOUR_ID&password=YOUR_PASSWORD',
                    'POST': 'Send JSON: {"username": "YOUR_ID", "password": "YOUR_PASSWORD"}'
                }
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
                'error': 'Failed to fetch attendance data',
                'details': fetch_message
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Attendance data retrieved successfully',
            'login_status': login_message,
            'data': attendance_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/login-test', methods=['GET'])
@rate_limit(calls_per_minute=10)
def test_login():
    try:
        username = request.args.get('username')
        password = request.args.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400
        
        lnct = LNCTAttendance()
        login_success, login_message = lnct.login(username, password)
        
        if login_success:
            dashboard_ok, dashboard_msg = lnct.verify_dashboard_access()
            return jsonify({
                'success': True,
                'login_status': login_message,
                'dashboard_access': dashboard_msg
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Login failed',
                'details': login_message
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/debug-login', methods=['GET'])
@rate_limit(calls_per_minute=5)
def debug_login():
    try:
        username = request.args.get('username')
        password = request.args.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400
        
        lnct = LNCTAttendance()
        
        # Get login page first
        response = lnct.session.get(lnct.login_url, timeout=lnct.timeout)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find form fields
        username_fields = soup.find_all('input', {'type': 'text'})
        password_fields = soup.find_all('input', {'type': 'password'})
        hidden_fields = soup.find_all('input', {'type': 'hidden'})
        
        # Attempt login
        login_success, login_message = lnct.login(username, password)
        
        return jsonify({
            'site_check': {
                'login_page_accessible': response.status_code == 200,
                'login_page_title': soup.find('title').get_text() if soup.find('title') else 'No title',
                'username_fields_found': [field.get('name') for field in username_fields],
                'password_fields_found': [field.get('name') for field in password_fields],
                'hidden_fields_count': len(hidden_fields),
                'form_count': len(soup.find_all('form'))
            },
            'login_attempt': {
                'success': login_success,
                'message': login_message
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("Starting LNCT Attendance API (Fixed Version)...")
    print("Access the API at: http://localhost:5000")
    print("Key improvements:")
    print("  ✅ Fixed attendance parsing using specific element IDs")
    print("  ✅ Added detailed attendance breakdown")
    print("  ✅ Better error handling and logging")
    print("  ✅ Improved session verification")
    app.run(debug=True, host='0.0.0.0', port=5000)
