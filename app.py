from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class LNCTUAttendanceTracker:
    def __init__(self, session_id=None):
        self.base_url = 'https://accsoft2.lnctu.ac.in/'
        self.dashboard_url = self.base_url + 'AccSoft2/parents/ParentDesk.aspx'
        self.attendance_url = self.base_url + 'AccSoft2/parents/StuAttendanceStatus.aspx'
        
        self.session = requests.Session()
        
        if session_id:
            self.session.cookies.set(
                'ASP.NET_SessionId',
                session_id,
                domain='accsoft2.lnctu.ac.in',
                path='/'
            )
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def verify_session(self):
        try:
            response = self.session.get(self.dashboard_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return "Parent Desk" in response.text or "Dashboard" in response.text
        except Exception as e:
            logger.error(f"Session verification failed: {str(e)}")
            return False

    def get_attendance_data(self):
        try:
            if not self.verify_session():
                return {
                    'success': False,
                    'error': 'Invalid or expired session',
                    'error_code': 'INVALID_SESSION'
                }

            response = self.session.get(self.attendance_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            page_title = soup.title.string if soup.title else ""
            if "Attendance" not in page_title and "attendance" not in response.text.lower():
                return {
                    'success': False,
                    'error': 'Could not access attendance page',
                    'error_code': 'PAGE_ACCESS_ERROR'
                }

            attendance_data = {
                'total_classes': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotperiod111', int),
                'present': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotalp11', int),
                'absent': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotala11', int),
                'leave': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotall11', int),
                'not_applicable': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotaln11', int),
                'on_duty': self._extract_value(soup, 'ctl00_ContentPlaceHolder1_lbltotalo11', int),
            }

            if attendance_data['total_classes'] > 0:
                attendance_data['percentage'] = round(
                    (attendance_data['present'] / attendance_data['total_classes']) * 100, 2
                )
            else:
                attendance_data['percentage'] = 0.0

            attendance_data.update({
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            })

            return attendance_data
            
        except requests.RequestException as e:
            logger.error(f"Network error: {str(e)}")
            return {
                'success': False,
                'error': 'Network error occurred',
                'error_code': 'NETWORK_ERROR'
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': 'An unexpected error occurred',
                'error_code': 'UNKNOWN_ERROR'
            }

    def _extract_value(self, soup, element_id, convert_type=str):
        element = soup.find('span', {'id': element_id})
        if not element:
            return convert_type() if convert_type != int else 0
            
        try:
            text = element.text.strip()
            if ':' in text:
                value = text.split(':')[-1].strip()
            else:
                value = text
            
            return convert_type(value) if value else (0 if convert_type == int else "")
        except (ValueError, IndexError):
            return convert_type() if convert_type != int else 0

# Routes
@app.route('/')
def home():
    return jsonify({
        'service': 'LNCTU Attendance API',
        'version': '1.0.0',
        'status': 'online',
        'endpoints': [
            'GET /api/attendance',
            'POST /api/attendance', 
            'GET /api/health',
            'GET /api/docs'
        ]
    })

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    try:
        session_id = request.args.get('session_id', 'u4zbxgeuhe5f5nnl2hzp5amo')
        tracker = LNCTUAttendanceTracker(session_id)
        data = tracker.get_attendance_data()
        return jsonify(data), 200 if data.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error',
            'error_code': 'SERVER_ERROR'
        }), 500

@app.route('/api/attendance', methods=['POST'])
def post_attendance():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON body required',
                'error_code': 'MISSING_BODY'
            }), 400
        
        session_id = data.get('session_id', 'u4zbxgeuhe5f5nnl2hzp5amo')
        tracker = LNCTUAttendanceTracker(session_id)
        result = tracker.get_attendance_data()
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error',
            'error_code': 'SERVER_ERROR'
        }), 500

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/docs')
def docs():
    return jsonify({
        'service': 'LNCTU Attendance API',
        'version': '1.0.0',
        'endpoints': {
            'GET /api/attendance': 'Get attendance data with ?session_id=your_id',
            'POST /api/attendance': 'Post with {"session_id": "your_id"}',
            'GET /api/health': 'Health check',
            'GET /api/docs': 'This documentation'
        },
        'example_response': {
            'success': True,
            'total_classes': 100,
            'present': 85,
            'absent': 15,
            'percentage': 85.0,
            'timestamp': '2025-01-01T12:00:00'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
