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
        num = matches[-1]  # Take the last number
        return float(num) if "." in num else int(num)
    return 0

def fetch_attendance(username, password):
    try:
        s = requests.Session()
        login_url = "https://accsoft2.lnctu.ac.in/AccSoft2/parentLogin"
        attendance_url = "https://accsoft2.lnctu.ac.in/AccSoft2/Parents/StuAttendanceStatus.aspx"

        login_payload = {
            "userid": username,
            "password": password
        }

        # Login
        login = s.post(login_url, data=login_payload, timeout=15)
        if "Invalid UserId or Password" in login.text:
            return {"success": False, "message": "Invalid credentials"}

        # Attendance Page
        r = s.get(attendance_url, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        def from_span(span_id):
            tag = soup.find("span", {"id": span_id})
            return extract_number(tag.get_text(strip=True)) if tag else 0

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
        for username, user in cache.items():
            result = fetch_attendance(username, user["password"])
            if result["success"]:
                cache[username]["data"] = result["data"]
                cache[username]["last_updated"] = time.time()
        save_cache()

@app.route('/')
def home():
    return "✅ LNCTU Attendance API (Fast Cache) is running."

@app.route('/attendance')
def attendance():
    username = request.args.get("username")
    password = request.args.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "Missing credentials"})

    now = time.time()
    if username in cache:
        cached = cache[username]
        if cached["password"] == password and now - cached["last_updated"] < CACHE_TTL:
            return jsonify({"success": True, "data": cached["data"]})

    result = fetch_attendance(username, password)
    if result["success"]:
        cache[username] = {
            "password": password,
            "data": result["data"],
            "last_updated": now
        }
        save_cache()
    return jsonify(result)

# Load cache and start background updater
cache = load_cache()
threading.Thread(target=auto_fetch, daemon=True).start()
