from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import threading
import time
import os
import json

app = Flask(__name__)
CACHE_TTL = 120  # 2 minutes
CACHE_FILE = "attendance_cache.json"
cache = {}

def extract_number(text):
    matches = re.findall(r"[0-9]+(?:\.[0-9]+)?", text)
    if matches:
        num = matches[-1]
        return float(num) if "." in num else int(num)
    return 0

def fetch_attendance(username, password):
    try:
        with requests.Session() as session:
            # Step 1: Load login page
            login_page = session.get("https://accsoft2.lnctu.ac.in/AccSoft2/parentLogin", timeout=15)
            soup = BeautifulSoup(login_page.text, 'html.parser')

            viewstate = soup.find("input", {"id": "__VIEWSTATE"})["value"]
            eventvalidation = soup.find("input", {"id": "__EVENTVALIDATION"})["value"]

            # Step 2: Submit login form
            payload = {
                "__VIEWSTATE": viewstate,
                "__EVENTVALIDATION": eventvalidation,
                "userid": username,
                "password": password,
                "btnlogin": "Login"
            }

            login_response = session.post("https://accsoft2.lnctu.ac.in/AccSoft2/parentLogin", data=payload, timeout=15)
            if "Invalid UserId or Password" in login_response.text:
                return {"success": False, "message": "Invalid credentials"}

            # Step 3: Visit attendance page
            r = session.get("https://accsoft2.lnctu.ac.in/AccSoft2/Parents/StuAttendanceStatus.aspx", timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            def get_value(id_):
                tag = soup.find("span", {"id": id_})
                return extract_number(tag.text) if tag else 0

            data = {
                "total_classes": get_value("ctl00_ContentPlaceHolder1_lbltotperiod111"),
                "attended_classes": get_value("ctl00_ContentPlaceHolder1_lbltotalp11"),
                "absent": get_value("ctl00_ContentPlaceHolder1_lbltotala11"),
                "overall_percentage": get_value("ctl00_ContentPlaceHolder1_lblPer119"),
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
        for username, entry in list(cache.items()):
            password = entry["password"]
            result = fetch_attendance(username, password)
            if result["success"]:
                cache[username] = {
                    "password": password,
                    "data": result["data"],
                    "last_updated": time.time()
                }
        save_cache()

@app.route('/')
def home():
    return "✅ LNCTU Fast Attendance API is running."

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

# Load cache and start background refresh
cache = load_cache()
threading.Thread(target=auto_fetch, daemon=True).start()
