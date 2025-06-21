from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import time
import logging
import os
from datetime import datetime

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS for Railway deployment
CORS(app, origins=["*"])  # You can restrict this to specific domains in production

class LNCTUAttendanceTracker:
    def __init__(self, session_id=None):
        self.base_url = 'https://accsoft2.lnctu.ac.in/'
        self.dashboard_url = self.base_url + 'AccSoft2/parents/ParentDesk.aspx'
        self.attendance_url = self.base_url + 'AccSoft2/parents/StuAttendanceStatus.aspx'
        
        # Configure session
        self.session = requests.Session()
        
        # Set session cookie if provided
        if session_id:
            self.session.cookies.set(
                'ASP.NET_SessionId',
                session_id,
                domain='accsoft2.lnctu.ac.in',
                path='/'
            )
        
        # Set realistic browser headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def verify_session(self):
        """Check if the session is still valid"""
        try:
            response = self.session.get(self.dashboard_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return "Parent Desk" in response.text or "Dashboard" in response.text
        except Exception as e:
            logger.error(f"Session verification failed: {str(e)}")
            return False

    def get_attendance_data(self):
        """Extract complete attendance information"""
        try:
            if not self.verify_session():
                return {
                    'success': False,
                    'error': 'Invalid or expired session',
                    'error_code': 'INVALID_SESSION'
                }

            logger.info("Fetching attendance page...")
            response = self.session.get(self.attendance_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Verify we're on the right page
            page_title = soup.title.string if soup.title else ""
            if "Attendance" not in page_title and "attendance" not in response.text.lower():
                return {
                    'success': False,
                    'error': 'Could not access attendance page',
                    'error_code': 'PAGE_ACCESS_ERROR'
                }

            # Extract all attendance metrics
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
                'error_code': 'NETWORK_ERROR',
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': 'An unexpected error occurred',
                'error_code': 'UNKNOWN_ERROR',
                'details': str(e)
            }

    def _extract_value(self, soup, element_id, convert_type=str):
        """Helper to extract and convert element values"""
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

# API Routes
@app.route('/', methods=['GET'])
def home():
    """Root endpoint - API info"""
    return jsonify({
        'service': 'LNCTU Attendance API',
        'status': 'running',
        'version': '1.0.0',
        'platform': 'Railway',
        'endpoints': {
            'health': '/api/health',
            'docs': '/api/docs',
            'attendance': '/api/attendance'
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    """
    Get attendance data
    Query Parameters:
    - id: Session ID (required)
    """
    try:
        # Get session ID from 'id' parameter
        session_id = request.args.get('id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'Session ID is required',
                'error_code': 'MISSING_ID',
                'message': 'Please provide session ID using ?id=your_session_id'
            }), 400
        
        # Create tracker instance
        tracker = LNCTUAttendanceTracker(session_id)
        
        # Get attendance data
        attendance_data = tracker.get_attendance_data()
        
        # Set appropriate HTTP status code
        status_code = 200 if attendance_data.get('success') else 400
        
        return jsonify(attendance_data), status_code
        
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'SERVER_ERROR',
            'details': str(e)
        }), 500

@app.route('/api/attendance', methods=['POST'])
def post_attendance():
    """
    Get attendance data via POST request
    JSON Body:
    {
        "id": "your_session_id_here"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON body required',
                'error_code': 'MISSING_BODY'
            }), 400
        
        session_id = data.get('id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'Session ID is required',
                'error_code': 'MISSING_ID',
                'message': 'Please provide session ID in JSON body: {"id": "your_session_id"}'
            }), 400
        
        # Create tracker instance
        tracker = LNCTUAttendanceTracker(session_id)
        
        # Get attendance data
        attendance_data = tracker.get_attendance_data()
        
        # Set appropriate HTTP status code
        status_code = 200 if attendance_data.get('success') else 400
        
        return jsonify(attendance_data), status_code
        
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'SERVER_ERROR',
            'details': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'LNCTU Attendance API',
        'platform': 'Railway'
    })

@app.route('/api/docs', methods=['GET'])
def api_docs():
    """API documentation"""
    docs = {
        'service': 'LNCTU Attendance API',
        'version': '1.0.0',
        'platform': 'Railway',
        'endpoints': {
            'GET /api/attendance': {
                'description': 'Get attendance data',
                'parameters': {
                    'id': 'Session ID (query parameter, required)'
                },
                'example': '/api/attendance?id=your_session_id'
            },
            'POST /api/attendance': {
                'description': 'Get attendance data via POST',
                'body': {
                    'id': 'Session ID (required)'
                },
                'example_body': '{"id": "your_session_id"}'
            },
            'GET /api/health': {
                'description': 'Health check endpoint'
            }
        },
        'response_format': {
            'success_response': {
                'success': True,
                'total_classes': 'int',
                'present': 'int',
                'absent': 'int',
                'leave': 'int',
                'not_applicable': 'int',
                'on_duty': 'int',
                'percentage': 'float',
                'timestamp': 'ISO datetime',
                'last_updated': 'formatted datetime'
            },
            'error_response': {
                'success': False,
                'error': 'Error message',
                'error_code': 'ERROR_CODE',
                'details': 'Additional details (optional)'
            }
        }
    }
    return jsonify(docs)

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'error_code': 'NOT_FOUND',
        'available_endpoints': ['/api/health', '/api/docs', '/api/attendance']
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'error_code': 'SERVER_ERROR'
    }), 500

# Railway automatically sets PORT environment variable
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
