import { useState } from 'react';
import LoginForm from './components/LoginForm';
import AttendanceDashboard from './components/AttendanceDashboard';
import Header from './components/Header';

function App() {
  const [user, setUser] = useState(null);
  const [attendanceData, setAttendanceData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = (userData, data) => {
    setUser(userData);
    setAttendanceData(data);
  };

  const handleLogout = () => {
    setUser(null);
    setAttendanceData(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header user={user} onLogout={handleLogout} />
      
      <main className="container mx-auto px-4 py-8">
        {user ? (
          <AttendanceDashboard 
            user={user} 
            attendanceData={attendanceData}
            setAttendanceData={setAttendanceData}
            loading={loading}
            setLoading={setLoading}
          />
        ) : (
          <LoginForm 
            onLogin={handleLogin} 
            loading={loading}
            setLoading={setLoading}
          />
        )}
      </main>
    </div>
  );
}

export default App;
