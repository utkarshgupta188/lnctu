from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import threading
import time
import json
import os
import re

app = Flask(__name__)
CACHE_TTL = 120  # 2 minutes
CACHE_FILE = "attendance_cache.json"
cache = {}

def extract_number(text):
    matches = re.findall(r"[0-9]+(?:\.[0-9]+)?", text)
    if matches:
        num = matches[0]
        return float(num) if "." in num else int(num)
    return 0

def fetch_attendance(username, password):
    try:
        s = requests.Session()
        login_url = 'https://accsoft2.lnctu.ac.in/AccSoft2/parentLogin'
        dashboard_url = 'https://accsoft2.lnctu.ac.in/AccSoft2/parents/parentStudentProfile'

        payload = {
            "userid": username,
            "password": password
        }

        r = s.post(login_url, data=payload, timeout=10)
        if "Invalid UserId or Password" in r.text:
            return {"success": False, "message": "Invalid credentials"}

        dash = s.get(dashboard_url)
        soup = BeautifulSoup(dash.text, 'html.parser')

        def from_span(id_):
            span = soup.find("span", {"id": id_})
            return extract_number(span.get_text(strip=True)) if span else 0

        data = {
            "total_classes": from_span("ctl00_ContentPlaceHolder1_lbltotperiod111"),
            "attended_classes": from_span("ctl00_ContentPlaceHolder1_lbltotalp11"),
            "absent": from_span("ctl00_ContentPlaceHolder1_lbltotala11"),
            "overall_percentage": from_span("ctl00_ContentPlaceHolder1_lblPer119"),
            "last_updated": time.strftime("%d-%m-%Y %H:%M")
        }

        return {"success": True, "data": data}

    except Exception as e:
        return {"success": False, "message": str(e)}

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def auto_fetch():
    while True:
        time.sleep(CACHE_TTL)
        for username in list(cache.keys()):
            password = cache[username]["password"]
            result = fetch_attendance(username, password)
            if result["success"]:
                cache[username]["data"] = result["data"]
                cache[username]["last_updated"] = time.time()
        save_cache()

@app.route('/')
def home():
    return "✅ LNCTU Attendance API is running."

@app.route('/attendance')
def get_attendance():
    username = request.args.get("username")
    password = request.args.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "Missing credentials"})

    if username in cache and cache[username]["password"] == password:
        return jsonify({"success": True, "data": cache[username]["data"]})

    result = fetch_attendance(username, password)
    if result["success"]:
        cache[username] = {
            "data": result["data"],
            "password": password,
            "last_updated": time.time()
        }
        save_cache()
    return jsonify(result)

# Load and start
cache = load_cache()
threading.Thread(target=auto_fetch, daemon=True).start()
