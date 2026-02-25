# LNCT Attendance Tracker

A FastAPI-based web application that scrapes and displays attendance data from the LNCTU student portal with an interactive dashboard and intelligent prediction system.

## Features

### 📊 Dashboard
- **Real-time Attendance Display** - View your overall attendance percentage with visual charts
- **Subject-wise Breakdown** - Detailed attendance for each subject with color-coded status badges
- **Date-wise History** - Complete attendance records organized by date and lecture
- **Interactive Donut Chart** - Visual representation of present vs absent classes

### 🎯 Smart Prediction Calculator
- **Target-based Predictions** - Calculate how many classes you can skip or need to attend
- **7 Classes Per Day** - Predictions account for the daily class schedule (7 classes/day)
- **Day-based Results** - Shows results in both days and individual classes
  - Example: "You can bunk 15 classes (2 days + 1 class) and still maintain 75%"
- **Real-time Calculation** - Set your target percentage and get instant predictions

### 🔐 Security
- Session management with automatic cleanup
- Secure credential handling
- SSL verification disabled for LNCTU portal compatibility

## API Endpoints

### `GET /`
Serves the main dashboard interface

### `GET /attendance?username=ID&password=PASS`
Fetch complete attendance data including overall, subject-wise, and date-wise attendance.

**Response Example:**
```json
{
  "success": true,
  "message": "Logged in and fetched",
  "data": {
    "total_classes": 120,
    "present": 95,
    "absent": 25,
    "percentage": 79.17,
    "overall_percentage": 79.17,
    "attended_classes": 95,
    "subjects": [
      {
        "name": "Data Structures",
        "total": 25,
        "present": 20,
        "absent": 5,
        "percentage": 80.0
      }
    ],
    "datewise": [
      {
        "date": "08 Sep 2025",
        "lecture": "Lecture No-3",
        "subject": "Data Structures",
        "status": "P"
      }
    ]
  }
}
```

## Run Locally

### Prerequisites
- Python 3.8+
- pip

### Installation & Setup

1. Clone the repository:
```bash
git clone https://github.com/utkarshgupta188/lnctu.git
cd lnctu
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
uvicorn at:app --host 0.0.0.0 --port 8000
```

4. Open your browser:
- Dashboard: http://localhost:8000/
- API: http://localhost:8000/attendance?username=YOUR_ID&password=YOUR_PASS

## Deployment

### Vercel
- Configured via `vercel.json`
- Serves both API and static files
- Automatic deployments from main branch

### Render
- Use `render.yaml` configuration
- Command: `uvicorn at:app --host 0.0.0.0 --port $PORT`

## Project Structure

```
lnctu/
├── at.py                 # FastAPI backend with web scraping logic
├── requirements.txt      # Python dependencies
├── vercel.json          # Vercel deployment configuration
├── static/
│   ├── index.html       # Dashboard interface
│   ├── style.css        # Modern dark-themed styles
│   └── script.js        # Frontend logic & prediction calculator
└── README.md
```

## How It Works

1. **Authentication** - Logs into LNCTU portal using your credentials
2. **Data Extraction** - Scrapes attendance data from multiple portal pages
3. **Data Processing** - Parses and structures attendance information
4. **Visualization** - Displays data in an interactive dashboard
5. **Predictions** - Calculates attendance scenarios based on 7 classes/day schedule

## Technologies Used

- **Backend**: FastAPI, Python
- **Web Scraping**: BeautifulSoup4, Requests
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Charts**: Chart.js
- **Deployment**: Vercel

## Security Notes

- Credentials are passed via query parameters (GET). For production use, consider implementing POST with JSON body for better security.
- SSL verification is disabled for compatibility with the LNCTU portal. Exercise caution when using on untrusted networks.
- Sessions are stored in-memory and expire after 1 hour of inactivity.

## Contributing

Feel free to submit issues or pull requests to improve the project!

## License

This project is for educational purposes. Use responsibly and in accordance with LNCTU's terms of service.
