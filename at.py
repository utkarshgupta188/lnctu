import logging
import math
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import requests
import urllib3
from bs4 import BeautifulSoup

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Don't mount static files for Vercel
user_sessions = {}

# ==============================
# SCRAPER CLASS (UNCHANGED)
# ==============================

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

    def _is_valid_form_input(self, inp):
        name = inp.get('name')
        if not name: return False
        type_ = inp.get('type')
        return type_ == 'hidden' or (type_ == 'radio' and inp.get('checked'))

    def get_form_data(self, soup):
        return {
            inp.get('name'): inp.get('value', '')
            for inp in soup.find_all('input')
            if self._is_valid_form_input(inp)
        }

    def _get_login_fields(self, soup):
        u_field = next((f for f in ['ctl00$cph1$txtStuUser', 'txtUserName', 'UserId'] if soup.find('input', {'name': f})), None)
        p_field = next((f for f in ['ctl00$cph1$txtStuPsw', 'txtPassword', 'Password'] if soup.find('input', {'name': f})), None)
        return u_field, p_field

    def _check_login_success(self, res):
        if "studentLogin.aspx" not in res.url and any(x in res.text.lower() for x in ['dashboard', 'attendance', 'logout']):
            name = ""
            try:
                soup = BeautifulSoup(res.content, 'html.parser')
                name_span = soup.find('span', class_='d-lg-inline-flex d-none')
                if name_span:
                    name = name_span.text.strip()
            except Exception as e:
                logger.error(f"Error extracting name: {e}")
            return True, "Login successful", name
        return False, "Invalid credentials", ""

    def login(self, username, password):
        try:
            logger.info(f"Logging in as {username}")
            r = self.session.get(self.login_url, timeout=15)
            soup = BeautifulSoup(r.content, 'html.parser')
            data = self.get_form_data(soup)

            u_field, p_field = self._get_login_fields(soup)
            if not (u_field and p_field):
                return False, "Login fields not found"

            data[u_field] = username
            data[p_field] = password
            
            btn = soup.find('input', {'type': 'submit'})
            if btn and btn.get('name'):
                data[btn.get('name')] = btn.get('value', 'Login')

            self.session.headers.update({'Referer': self.login_url})
            res = self.session.post(self.login_url, data=data, timeout=15)

            return self._check_login_success(res)

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, str(e), ""

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

    def _is_subject_table(self, table):
        headers = [c.text.lower().strip() for c in table.find_all('th')]
        if not headers and table.find('tr'):
            headers = [c.text.lower().strip() for c in table.find('tr').find_all('td')]
        return any('subject name' in h for h in headers) and any('classes held' in h for h in headers)

    def _find_subject_table(self, soup):
        for table in soup.find_all('table'):
            if self._is_subject_table(table):
                return table
        return None

    def _parse_subject_row(self, row):
        cols = [c.text.strip() for c in row.find_all('td')]
        if len(cols) < 4: return None
        
        try:
            total = int(cols[2]) if cols[2].isdigit() else 0
            present = int(cols[3]) if cols[3].isdigit() else 0
            return {
                "name": cols[0],
                "total": total,
                "present": present,
                "absent": total - present,
                "percentage": round((present / total * 100), 2) if total > 0 else 0.0
            }
        except:
            return None

    def get_subject_attendance(self):
        subjects = []
        try:
            url = "https://accsoft2.lnctu.ac.in/AccSoft2/parents/subwiseattn.aspx"
            r = self.session.get(url, timeout=15)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            target_table = self._find_subject_table(soup)
            if not target_table:
                logger.warning("No subject table found in subwiseattn.aspx")
                return []

            for row in target_table.find_all('tr')[1:]:
                subject = self._parse_subject_row(row)
                if subject:
                    subjects.append(subject)
                        
        except Exception as e:
            logger.error(f"Error parsing subjects: {e}")
            
        return subjects

    def get_datewise_attendance(self, soup):
        datewise = []
        try:
            table = soup.find('table', {'id': 'ctl00_ctl00_ContentPlaceHolder1_cp2_Gridview1'})
            if not table:
                return []

            rows = table.find_all('tr')[1:]
            for row in rows:
                cols = row.find_all('td')
                if not cols: continue
                
                if len(cols) >= 5:
                    datewise.append({
                        "date": cols[1].text.strip(),
                        "lecture": cols[2].text.strip(),
                        "subject": cols[3].text.strip(),
                        "status": cols[4].text.strip()
                    })
                    
        except Exception as e:
            logger.error(f"Error parsing datewise: {e}")
            
        return datewise

    def get_attendance(self):
        try:
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

            percentage = round((data['present'] / data['total_classes']) * 100, 2) if data['total_classes'] > 0 else 0.0

            subjects = self.get_subject_attendance()
            datewise = self.get_datewise_attendance(soup)

            return {
                **data,
                'percentage': percentage,
                'overall_percentage': percentage,
                'attended_classes': data['present'],
                'subjects': subjects,
                'datewise': datewise
            }, "Success"

        except Exception as e:
            logger.error(f"Attendance error: {e}")
            return None, f"Attendance error: {e}"


# ==============================
# SESSION HELPERS
# ==============================

def cleanup_expired_sessions():
    now = datetime.now()
    expired = [u for u, s in user_sessions.items() if now - s['last_login'] > timedelta(hours=1)]
    for u in expired:
        del user_sessions[u]

def _get_or_create_session(username, password):
    if username in user_sessions:
        lnct = user_sessions[username]['lnct']
        name = user_sessions[username].get('name', '')
        data, msg = lnct.get_attendance()
        if data:
            data['student_name'] = name
            return data, "Used cached session"
        del user_sessions[username]

    lnct = LNCTAttendance()
    result = lnct.login(username, password)
    ok = result[0]
    msg = result[1]
    name = result[2] if len(result) > 2 else ""
    if not ok:
        raise HTTPException(status_code=401, detail=msg)

    user_sessions[username] = {
        'lnct': lnct,
        'name': name,
        'last_login': datetime.now()
    }

    data, msg = lnct.get_attendance()
    if not data:
        raise HTTPException(status_code=500, detail=msg)
    
    data['student_name'] = name
    return data, "Logged in and fetched"


# ==============================
# FULL ATTENDANCE (UNCHANGED)
# ==============================

@app.get("/attendance")
def attendance(username: str = "", password: str = ""):
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    cleanup_expired_sessions()
    data, msg = _get_or_create_session(username, password)
    return {"success": True, "message": msg, "data": data}


# ==============================
# 🔥 NEW LITE ENDPOINT (ONLY ADDITION)
# ==============================

@app.get("/attendance-lite")
def attendance_lite(username: str = "", password: str = ""):
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    cleanup_expired_sessions()
    data, msg = _get_or_create_session(username, password)

    return {
        "success": True,
        "message": msg,
        "data": {
            "student_name": data.get("student_name", ""),
            "total_classes": data["total_classes"],
            "present": data["present"],
            "absent": data["absent"],
            "percentage": data["percentage"],
            "overall_percentage": data["overall_percentage"],
            "attended_classes": data["attended_classes"]
        }
    }


# ==============================
# TIMETABLE DATA ENDPOINT
# ==============================

# Sample timetable structure - You can modify this based on your actual timetable
# Format: Day -> [Periods] where each period has subject, time, and optional faculty
TIMETABLE_DATA = {
    "Monday": [
        {"time": "09:00-09:45", "subject": "Data Visualization and Story Telling"},
        {"time": "09:45-10:30", "subject": "Web Technology"},
        {"time": "10:30-11:20", "subject": "Analysis and Design of Algorithms"},
        {"time": "11:20-12:10", "subject": "Innovative Practices"},
        {"time": "12:10-01:00", "subject": "LUNCH"},
        {"time": "01:00-01:50", "subject": "Software Engineering and Project Management"},
        {"time": "01:50-03:30", "subject": "Machine Learning and Pattern Recognition"},
    ],
    "Tuesday": [
        {"time": "09:00-10:30", "subject": "Web Technology-P"},
        {"time": "10:30-11:20", "subject": "Software Engineering and Project Management"},
        {"time": "11:20-12:10", "subject": "Analysis and Design of Algorithms-T"},
        {"time": "12:10-01:00", "subject": "LUNCH"},
        {"time": "01:00-01:50", "subject": "Web Technology"},
        {"time": "01:50-02:40", "subject": "Analysis and Design of Algorithms"},
        {"time": "02:40-03:30", "subject": "Machine Learning and Pattern Recognition"},
    ],
    "Wednesday": [
        {"time": "09:00-09:45", "subject": "Data Visualization and Story Telling"},
        {"time": "09:45-10:30", "subject": "Mentor/Library"},
        {"time": "10:30-11:20", "subject": "Software Engineering and Project Management-T"},
        {"time": "11:20-12:10", "subject": "Web Technology"},
        {"time": "12:10-01:00", "subject": "LUNCH"},
        {"time": "01:00-02:40", "subject": "Analysis and Design of Algorithms-P"},
        {"time": "02:40-03:30", "subject": "Machine Learning and Pattern Recognition"},
    ],
    "Thursday": [
        {"time": "09:00-09:45", "subject": "Data Visualization and Story Telling"},
        {"time": "09:45-10:30", "subject": "Web Technology"},
        {"time": "10:30-11:20", "subject": "Software Engineering and Project Management"},
        {"time": "11:20-12:10", "subject": "Web Technology-T"},
        {"time": "12:10-01:00", "subject": "LUNCH"},
        {"time": "01:00-02:40", "subject": "MINOR PROJECT-I"},
        {"time": "02:40-03:30", "subject": "Machine Learning and Pattern Recognition"},
    ],
    "Friday": [
        {"time": "09:00-10:30", "subject": "Data Visualization and Story Telling"},
        {"time": "10:30-11:20", "subject": "Software Engineering and Project Management"},
        {"time": "11:20-12:10", "subject": "Analysis and Design of Algorithms"},
        {"time": "12:10-01:00", "subject": "LUNCH"},
        {"time": "01:00-02:40", "subject": "Software Engineering and Project Management-P"},
        {"time": "02:40-03:30", "subject": "Analysis and Design of Algorithms"},
    ],
}

@app.get("/timetable")
def get_timetable():
    """Returns the weekly timetable"""
    return {"success": True, "data": TIMETABLE_DATA}


def normalize_subject(name):
    """Normalize subject name for display"""
    return name.strip()


def subjects_match(name1, name2):
    """
    Check if two subject names refer to the same subject.
    Uses EXACT matching to treat Theory (-T) and Practical (-P) as separate subjects.
    """
    # Exact match
    if name1.strip() == name2.strip():
        return True
    
    # Case-insensitive exact match
    if name1.strip().upper() == name2.strip().upper():
        return True
    
    return False


@app.get("/debug-subjects")
def debug_subjects(username: str = "", password: str = ""):
    """Debug endpoint to see actual subject names and matching"""
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    cleanup_expired_sessions()
    data, msg = _get_or_create_session(username, password)
    
    if not data or 'subjects' not in data:
        raise HTTPException(status_code=500, detail="Failed to fetch attendance data")
    
    subjects = data.get('subjects', [])
    
    # Get all unique timetable subjects
    timetable_subjects = set()
    for day, periods in TIMETABLE_DATA.items():
        for p in periods:
            if p['subject'] not in ['LUNCH', 'Lunch Break']:
                timetable_subjects.add(p['subject'])
    
    # Check matching
    matching_report = []
    for subj in subjects:
        matches = []
        for tt_subj in timetable_subjects:
            if subjects_match(subj['name'], tt_subj):
                matches.append(tt_subj)
        
        matching_report.append({
            'attendance_subject': subj['name'],
            'normalized': normalize_subject(subj['name']),
            'matches_timetable': matches,
            'has_match': len(matches) > 0
        })
    
    return {
        "success": True,
        "data": {
            "attendance_subjects": [s['name'] for s in subjects],
            "timetable_subjects": list(timetable_subjects),
            "matching_report": matching_report
        }
    }


def calculate_risk_metrics(subj, threshold=75.0):
    """Calculate detailed risk metrics for a subject"""
    total = subj.get('total', 0)
    present = subj.get('present', 0)
    absent = subj.get('absent', 0)
    pct = subj.get('percentage', 0)
    
    # Classes that can be missed before falling below threshold
    # (present) / (total + x) >= threshold/100
    # present >= (threshold/100) * (total + x)
    # present >= (threshold/100) * total + (threshold/100) * x
    # present - (threshold/100) * total >= (threshold/100) * x
    # x <= (present - (threshold/100) * total) / (threshold/100)
    if pct >= threshold:
        absents_allowed = math.floor((present - (threshold/100) * total) / (threshold/100))
    else:
        absents_allowed = -1  # Already below threshold
    
    # Required consecutive presents to recover to threshold
    if pct < threshold:
        # Need: (present + x) / (total + x) >= threshold/100
        # present + x >= (threshold/100) * (total + x)
        # present + x >= (threshold/100) * total + (threshold/100) * x
        # present - (threshold/100) * total >= (threshold/100) * x - x
        # present - (threshold/100) * total >= x * ((threshold/100) - 1)
        # x >= (present - (threshold/100) * total) / ((threshold/100) - 1)
        needed = math.ceil((present - (threshold/100) * total) / ((threshold/100) - 1))
        consecutive_needed = max(0, needed)
    else:
        consecutive_needed = 0
    
    # Days to recover (assuming avg classes per day for this subject)
    avg_classes_per_day = 1  # Conservative estimate
    days_to_recover = math.ceil(consecutive_needed / avg_classes_per_day) if consecutive_needed > 0 else 0
    
    return {
        'absents_allowed': max(0, absents_allowed) if absents_allowed >= 0 else 0,
        'already_below_threshold': absents_allowed < 0,
        'consecutive_needed': consecutive_needed,
        'days_to_recover': days_to_recover,
        'current_percentage': pct,
        'projected_percentage_if_miss_one': round((present / (total + 1)) * 100, 2) if total > 0 else 0
    }


@app.get("/risk-engine")
def get_risk_engine(username: str = "", password: str = "", threshold: float = 75.0):
    """
    Attendance Risk Engine - Detailed risk analysis
    """
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    cleanup_expired_sessions()
    data, msg = _get_or_create_session(username, password)
    
    if not data or 'subjects' not in data:
        raise HTTPException(status_code=500, detail="Failed to fetch attendance data")
    
    subjects = data.get('subjects', [])
    
    # Find lowest attendance subject
    lowest_subject = min(subjects, key=lambda x: x['percentage']) if subjects else None
    
    # Calculate risk metrics for all subjects
    risk_analysis = []
    for subj in subjects:
        metrics = calculate_risk_metrics(subj, threshold)
        risk_level = 'CRITICAL' if subj['percentage'] < 65 else ('HIGH' if subj['percentage'] < threshold else 'LOW')
        
        risk_analysis.append({
            'subject': subj['name'],
            'total': subj['total'],
            'present': subj['present'],
            'absent': subj['absent'],
            'percentage': subj['percentage'],
            'risk_level': risk_level,
            'absents_allowed_before_threshold': metrics['absents_allowed'],
            'already_below_threshold': metrics['already_below_threshold'],
            'consecutive_presents_needed': metrics['consecutive_needed'],
            'estimated_days_to_recover': metrics['days_to_recover'],
            'projected_percentage_if_miss_one': metrics['projected_percentage_if_miss_one']
        })
    
    # Sort by risk (lowest percentage first)
    risk_analysis.sort(key=lambda x: x['percentage'])
    
    # Calculate overall risk
    at_risk_count = sum(1 for r in risk_analysis if r['risk_level'] in ['CRITICAL', 'HIGH'])
    
    return {
        "success": True,
        "data": {
            "threshold": threshold,
            "lowest_attendance_subject": lowest_subject,
            "overall_risk_status": 'DANGER' if at_risk_count >= 3 else ('WARNING' if at_risk_count >= 1 else 'SAFE'),
            "at_risk_subjects_count": at_risk_count,
            "subject_risks": risk_analysis,
            "critical_alert": any(r['risk_level'] == 'CRITICAL' for r in risk_analysis)
        }
    }


@app.get("/leave-simulator")
def simulate_leave(username: str = "", password: str = "", day: str = ""):
    """
    Leave Simulation Engine - Simulate missing classes on a specific day
    """
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    if not day or day not in TIMETABLE_DATA:
        raise HTTPException(status_code=400, detail=f"Valid day required. Options: {', '.join(TIMETABLE_DATA.keys())}")

    cleanup_expired_sessions()
    data, msg = _get_or_create_session(username, password)
    
    if not data or 'subjects' not in data:
        raise HTTPException(status_code=500, detail="Failed to fetch attendance data")
    
    subjects = data.get('subjects', [])
    periods = TIMETABLE_DATA.get(day, [])
    
    # Calculate class units based on duration (labs = 2 units, regular = 1 unit)
    def get_class_units(time_str):
        """Calculate class units based on time duration"""
        try:
            start, end = time_str.split('-')
            start_h, start_m = map(int, start.split(':'))
            end_h, end_m = map(int, end.split(':'))
            duration_minutes = (end_h * 60 + end_m) - (start_h * 60 + start_m)
            # Labs are typically 90+ minutes and count as 2 class units
            return 2 if duration_minutes >= 80 else 1
        except:
            return 1
    
    # Build list of subjects with their class units for this day
    day_subjects_with_units = []
    for p in periods:
        if p['subject'] not in ['LUNCH', 'Lunch Break']:
            units = get_class_units(p['time'])
            day_subjects_with_units.append({'subject': p['subject'], 'units': units})
    
    # Calculate total class units for display
    total_class_units = sum(s['units'] for s in day_subjects_with_units)
    
    # Calculate current overall attendance
    current_total_classes = sum(s['total'] for s in subjects)
    current_present = sum(s['present'] for s in subjects)
    current_overall_percentage = round((current_present / current_total_classes) * 100, 2) if current_total_classes > 0 else 0
    
    # Simulate the impact
    simulation_results = []
    total_impact_score = 0
    affected_subjects = set()
    total_absences_on_day = 0
    
    for subj in subjects:
        subj_name = subj['name']
        
        # Count how many class units of this subject are on this day
        classes_on_day = 0
        for item in day_subjects_with_units:
            if subjects_match(subj_name, item['subject']):
                classes_on_day += item['units']
        
        if classes_on_day > 0:
            affected_subjects.add(subj_name)
            
            # Calculate new percentages if absent
            new_total = subj['total'] + classes_on_day
            new_present = subj['present']  # Didn't attend
            new_percentage = round((new_present / new_total) * 100, 2) if new_total > 0 else 0
            
            percentage_drop = round(subj['percentage'] - new_percentage, 2)
            
            # Determine impact level
            if subj['percentage'] < 75:
                impact_level = 'SEVERE' if percentage_drop > 2 else 'HIGH'
            else:
                impact_level = 'LOW'
            
            total_impact_score += {'SEVERE': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}.get(impact_level, 0)
            total_absences_on_day += classes_on_day
            
            simulation_results.append({
                'subject': subj_name,
                'current_percentage': subj['percentage'],
                'classes_on_this_day': classes_on_day,
                'projected_percentage': new_percentage,
                'percentage_drop': percentage_drop,
                'impact_level': impact_level,
                'will_fall_below_75': new_percentage < 75 and subj['percentage'] >= 75,
                'status_after_absence': 'AT RISK' if new_percentage < 75 else 'SAFE'
            })
    
    # Sort by impact severity
    severity_order = {'SEVERE': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    simulation_results.sort(key=lambda x: severity_order.get(x['impact_level'], 4))
    
    # Overall recommendation
    if total_impact_score >= 10:
        recommendation = 'STRONGLY_DISCOURAGED'
        advice = 'Taking leave on this day will severely impact your attendance!'
    elif total_impact_score >= 6:
        recommendation = 'NOT_RECOMMENDED'
        advice = 'Multiple subjects will be affected. Consider attending if possible.'
    elif total_impact_score >= 3:
        recommendation = 'YOU MAY CONSIDER'
        advice = 'Some impact expected. Only take leave if necessary.'
    else:
        recommendation = 'SAFE'
        advice = 'Low impact on attendance. Good day for leave!'
    
    # Calculate projected overall attendance after leave
    projected_total_classes = current_total_classes + total_absences_on_day
    projected_present = current_present  # Didn't attend any
    projected_overall_percentage = round((projected_present / projected_total_classes) * 100, 2) if projected_total_classes > 0 else 0
    overall_percentage_drop = round(current_overall_percentage - projected_overall_percentage, 2)
    
    return {
        "success": True,
        "data": {
            "simulated_day": day,
            "total_classes_on_day": total_class_units,
            "affected_subjects_count": len(simulation_results),
            "recommendation": recommendation,
            "advice": advice,
            "total_impact_score": total_impact_score,
            "subject_simulations": simulation_results,
            "subjects_not_affected": [s['name'] for s in subjects if s['name'] not in affected_subjects],
            "overall_attendance": {
                "current": current_overall_percentage,
                "projected": projected_overall_percentage,
                "drop": overall_percentage_drop
            }
        }
    }


@app.get("/analysis")
def get_attendance_analysis(username: str = "", password: str = ""):
    """
    Returns detailed analysis including:
    - Subject-wise attendance status
    - Which subjects are at risk (< 75%)
    - Best days to take leave (days with low-attendance subjects)
    - Days to avoid (days with high-attendance subjects)
    """
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    cleanup_expired_sessions()
    data, msg = _get_or_create_session(username, password)
    
    if not data or 'subjects' not in data:
        raise HTTPException(status_code=500, detail="Failed to fetch attendance data")
    
    subjects = data.get('subjects', [])
    
    # Categorize subjects by attendance
    at_risk = []  # < 75%
    moderate = []  # Not used with binary threshold
    safe = []  # >= 75%
    
    for subj in subjects:
        pct = subj.get('percentage', 0)
        if pct < 75:
            at_risk.append(subj)
        else:
            safe.append(subj)
    
    # Sort by percentage (ascending for at_risk, descending for safe)
    at_risk.sort(key=lambda x: x['percentage'])
    moderate.sort(key=lambda x: x['percentage'])
    safe.sort(key=lambda x: x['percentage'], reverse=True)
    
    # Analyze timetable to find best/worst days for leave
    day_analysis = {}
    for day, periods in TIMETABLE_DATA.items():
        # Filter out lunch and non-academic periods
        day_subjects_raw = [p['subject'] for p in periods if p['subject'] not in ['LUNCH', 'Lunch Break']]
        
        # Count at-risk and safe subjects for this day
        at_risk_count = 0
        safe_count = 0
        
        for timetable_subj in day_subjects_raw:
            # Check if this timetable subject matches any at-risk subject
            matched_at_risk = False
            for r in at_risk:
                if subjects_match(r['name'], timetable_subj):
                    at_risk_count += 1
                    matched_at_risk = True
                    break
            
            if not matched_at_risk:
                for saf in safe:
                    if subjects_match(saf['name'], timetable_subj):
                        safe_count += 1
                        break
        
        day_analysis[day] = {
            'subjects': day_subjects_raw,
            'at_risk_count': at_risk_count,
            'safe_count': safe_count,
            'total_classes': len(day_subjects_raw),
            'leave_recommendation': 'AVOID' if at_risk_count >= 2 else ('CAUTION' if at_risk_count == 1 else 'SAFE')
        }
    
    # Calculate how many classes can be missed per subject to maintain 75%
    predictions = []
    for subj in subjects:
        total = subj.get('total', 0)
        present = subj.get('present', 0)
        pct = subj.get('percentage', 0)
        
        metrics = calculate_risk_metrics(subj)
        
        if pct < 75:
            predictions.append({
                'subject': subj['name'],
                'current_percentage': pct,
                'status': 'CRITICAL' if pct < 65 else 'WARNING',
                'classes_needed': metrics['consecutive_needed'],
                'days_to_recover': metrics['days_to_recover'],
                'message': f"Need {metrics['consecutive_needed']} more classes ({metrics['days_to_recover']} days) to reach 75%"
            })
        else:
            predictions.append({
                'subject': subj['name'],
                'current_percentage': pct,
                'status': 'SAFE',
                'can_miss': metrics['absents_allowed'],
                'message': f"Can miss {metrics['absents_allowed']} classes and maintain 75%"
            })
    
    # Calculate overall attendance
    total_classes = sum(s['total'] for s in subjects)
    total_present = sum(s['present'] for s in subjects)
    overall_percentage = round((total_present / total_classes) * 100, 2) if total_classes > 0 else 0
    
    # Determine overall status message
    if overall_percentage >= 75:
        overall_status = "GOOD"
        overall_message = "Your attendance is in good shape! Keep it up!"
    elif overall_percentage >= 60:
        overall_status = "WARNING"
        overall_message = "Your attendance is manageable. Try to attend more classes."
    else:
        overall_status = "CRITICAL"
        overall_message = "Your attendance is very low! Attend classes regularly."
    
    return {
        "success": True,
        "data": {
            "summary": {
                "total_subjects": len(subjects),
                "at_risk_count": len(at_risk),
                "moderate_count": len(moderate),
                "safe_count": len(safe),
                "overall_percentage": overall_percentage,
                "overall_status": overall_status,
                "overall_message": overall_message
            },
            "at_risk_subjects": at_risk,
            "moderate_subjects": moderate,
            "safe_subjects": safe,
            "day_analysis": day_analysis,
            "predictions": predictions
        }
    }


@app.get("/leave-simulator-week")
def simulate_leave_week(username: str = "", password: str = ""):
    """
    Leave Simulation Engine - Simulate missing classes for the whole week
    Returns impact analysis for each day (Monday-Friday)
    """
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    cleanup_expired_sessions()
    data, msg = _get_or_create_session(username, password)
    
    if not data or 'subjects' not in data:
        raise HTTPException(status_code=500, detail="Failed to fetch attendance data")
    
    subjects = data.get('subjects', [])
    
    # Calculate current overall attendance
    current_total_classes = sum(s['total'] for s in subjects)
    current_present = sum(s['present'] for s in subjects)
    current_overall_percentage = round((current_present / current_total_classes) * 100, 2) if current_total_classes > 0 else 0
    
    # Calculate class units based on duration
    def get_class_units(time_str):
        try:
            start, end = time_str.split('-')
            start_h, start_m = map(int, start.split(':'))
            end_h, end_m = map(int, end.split(':'))
            duration_minutes = (end_h * 60 + end_m) - (start_h * 60 + start_m)
            return 2 if duration_minutes >= 80 else 1
        except:
            return 1
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    week_simulation = []
    
    for day in days:
        periods = TIMETABLE_DATA.get(day, [])
        
        # Build list of subjects with their class units
        day_subjects_with_units = []
        for p in periods:
            if p['subject'] not in ['LUNCH', 'Lunch Break']:
                units = get_class_units(p['time'])
                day_subjects_with_units.append({'subject': p['subject'], 'units': units})
        
        total_class_units = sum(s['units'] for s in day_subjects_with_units)
        
        # Simulate impact for this day
        simulation_results = []
        total_impact_score = 0
        total_absences_on_day = 0
        
        for subj in subjects:
            subj_name = subj['name']
            
            classes_on_day = 0
            for item in day_subjects_with_units:
                if subjects_match(subj_name, item['subject']):
                    classes_on_day += item['units']
            
            if classes_on_day > 0:
                new_total = subj['total'] + classes_on_day
                new_present = subj['present']
                new_percentage = round((new_present / new_total) * 100, 2) if new_total > 0 else 0
                percentage_drop = round(subj['percentage'] - new_percentage, 2)
                
                if subj['percentage'] < 75:
                    impact_level = 'SEVERE' if percentage_drop > 2 else 'HIGH'
                else:
                    impact_level = 'LOW'
                
                total_impact_score += {'SEVERE': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}.get(impact_level, 0)
                total_absences_on_day += classes_on_day
                
                simulation_results.append({
                    'subject': subj_name,
                    'current_percentage': subj['percentage'],
                    'classes_on_this_day': classes_on_day,
                    'projected_percentage': new_percentage,
                    'percentage_drop': percentage_drop,
                    'impact_level': impact_level,
                    'will_fall_below_75': new_percentage < 75 and subj['percentage'] >= 75
                })
        
        # Sort by impact
        severity_order = {'SEVERE': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        simulation_results.sort(key=lambda x: severity_order.get(x['impact_level'], 4))
        
        # Recommendation
        if total_impact_score >= 10:
            recommendation = 'AVOID'
            advice = 'Severe impact!'
        elif total_impact_score >= 6:
            recommendation = 'RISKY'
            advice = 'High impact'
        elif total_impact_score >= 3:
            recommendation = 'CAUTION'
            advice = 'Moderate impact'
        else:
            recommendation = 'SAFE'
            advice = 'Low impact'
        
        # Calculate projected overall
        projected_total = current_total_classes + total_absences_on_day
        projected_pct = round((current_present / projected_total) * 100, 2) if projected_total > 0 else 0
        
        week_simulation.append({
            'day': day,
            'total_class_units': total_class_units,
            'affected_subjects_count': len(simulation_results),
            'recommendation': recommendation,
            'advice': advice,
            'total_impact_score': total_impact_score,
            'projected_overall_percentage': projected_pct,
            'overall_drop': round(current_overall_percentage - projected_pct, 2),
            'subject_simulations': simulation_results[:3]  # Top 3 most impacted
        })
    
    # Calculate whole week leave impact using raw timetable data (not affected subjects)
    total_week_absences = 0
    for day in days:
        periods = TIMETABLE_DATA.get(day, [])
        for p in periods:
            if p['subject'] not in ['LUNCH', 'Lunch Break']:
                total_week_absences += get_class_units(p['time'])
    
    projected_total_week = current_total_classes + total_week_absences
    projected_pct_week = round((current_present / projected_total_week) * 100, 2) if projected_total_week > 0 else 0
    
    # Keep days in Monday-Friday order
    day_order = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4}
    week_simulation.sort(key=lambda x: day_order.get(x['day'], 5))
    
    return {
        "success": True,
        "data": {
            "current_overall_percentage": current_overall_percentage,
            "week_simulation": week_simulation,
            "whole_week_leave": {
                "total_absences": total_week_absences,
                "projected_overall_percentage": projected_pct_week,
                "overall_drop": round(current_overall_percentage - projected_pct_week, 2)
            }
        }
    }


# ==============================
# STATIC SITE (UNCHANGED)
# ==============================

@app.get("/")
def root():
    return FileResponse('static/index.html')

@app.get("/static/style.css")
def serve_css():
    return FileResponse('static/style.css', media_type='text/css')

@app.get("/static/script.js")
def serve_js():
    return FileResponse('static/script.js', media_type='application/javascript')
