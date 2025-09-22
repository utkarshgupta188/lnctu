# LNCT Attendance Portal

A modern web application for viewing LNCT University attendance data with a React frontend and Flask backend.

## Features

### Frontend (React)
- **Modern UI**: Clean, responsive design built with React and Tailwind CSS
- **Login Interface**: Secure authentication form with LNCT credentials
- **Attendance Dashboard**: Comprehensive view of attendance statistics
- **Subject-wise Breakdown**: Detailed attendance data for individual subjects
- **Real-time Status**: Live site connectivity checking
- **Mobile Responsive**: Works seamlessly on desktop and mobile devices

### Backend (Flask)
- **API Endpoints**: RESTful API for attendance data
- **Rate Limiting**: Built-in protection against excessive requests
- **Error Handling**: Comprehensive error management and logging
- **Session Management**: Secure handling of user sessions

## API Endpoints

- `GET /api/check-site` - Check LNCT site accessibility
- `POST /api/attendance` - Get attendance data (secure)
- `GET /api/login-test` - Test login credentials
- `GET /api/debug-login` - Debug login process

## Setup and Installation

### Prerequisites
- Python 3.7+
- Node.js 16+
- npm or yarn

### Backend Setup
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the Flask application:
   ```bash
   python main.py
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build the production version:
   ```bash
   npm run build
   ```

### Running the Application
1. Build the React frontend (if not already done):
   ```bash
   cd frontend && npm run build
   ```

2. Start the Flask server:
   ```bash
   python main.py
   ```

3. Open your browser and navigate to `http://localhost:5000`

## Usage

1. **Login**: Enter your LNCT username and password
2. **Check Site Status**: Verify LNCT site connectivity before logging in
3. **View Dashboard**: See overall attendance percentage and statistics
4. **Subject Details**: Review individual subject attendance
5. **Monitor Progress**: Track attendance trends and warnings

## Technology Stack

- **Frontend**: React, Tailwind CSS, Lucide React Icons, Axios
- **Backend**: Flask, BeautifulSoup4, Requests
- **Build Tools**: Vite, PostCSS
- **Deployment**: Vercel-ready with render.yaml support

## Security Features

- Rate limiting on API endpoints
- Secure credential handling
- HTTPS support for production
- Input validation and sanitization
- Error logging without exposing sensitive data

## Development

### Frontend Development
```bash
cd frontend
npm run dev
```

### Backend Development
```bash
python main.py
```

The React dev server will proxy API requests to the Flask backend running on port 5000.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational purposes and LNCT University students.