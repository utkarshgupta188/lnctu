import { useState, useEffect } from 'react';
import { RefreshCw, Calendar, BookOpen, TrendingUp, AlertTriangle } from 'lucide-react';
import AttendanceCard from './AttendanceCard';
import SubjectList from './SubjectList';
import { attendanceAPI } from '../services/api';

const AttendanceDashboard = ({ user, attendanceData, setAttendanceData, loading, setLoading }) => {
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    if (attendanceData) {
      setLastUpdated(new Date());
    }
  }, [attendanceData]);

  const refreshAttendance = async () => {
    setLoading(true);
    try {
      // We'll need to store credentials for refresh, or implement a session-based approach
      // For now, we'll just show a message that refresh requires re-login
      alert('Please logout and login again to refresh attendance data');
    } catch (error) {
      console.error('Failed to refresh attendance:', error);
    } finally {
      setLoading(false);
    }
  };

  const getAttendanceStatusColor = (percentage) => {
    if (percentage >= 75) return 'text-green-600';
    if (percentage >= 65) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getAttendanceStatusIcon = (percentage) => {
    if (percentage >= 75) return <TrendingUp className="h-5 w-5 text-green-600" />;
    return <AlertTriangle className="h-5 w-5 text-red-600" />;
  };

  if (!attendanceData) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No attendance data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with refresh button */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Attendance Dashboard</h2>
          <p className="text-gray-600">
            {lastUpdated && (
              <>Last updated: {lastUpdated.toLocaleString()}</>
            )}
          </p>
        </div>
        <button
          onClick={refreshAttendance}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Overall attendance summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <AttendanceCard
          title="Overall Attendance"
          value={`${attendanceData.percentage}%`}
          icon={<Calendar className="h-6 w-6" />}
          color={getAttendanceStatusColor(attendanceData.percentage)}
          subtitle={`${attendanceData.present}/${attendanceData.total_classes} classes`}
          statusIcon={getAttendanceStatusIcon(attendanceData.percentage)}
        />
        
        <AttendanceCard
          title="Present"
          value={attendanceData.present}
          icon={<BookOpen className="h-6 w-6" />}
          color="text-green-600"
          subtitle="Classes attended"
        />
        
        <AttendanceCard
          title="Absent"
          value={attendanceData.absent}
          icon={<AlertTriangle className="h-6 w-6" />}
          color="text-red-600"
          subtitle="Classes missed"
        />
        
        <AttendanceCard
          title="Leave"
          value={attendanceData.leave || 0}
          icon={<Calendar className="h-6 w-6" />}
          color="text-yellow-600"
          subtitle="Approved leaves"
        />
      </div>

      {/* Attendance breakdown */}
      {attendanceData.percentage < 75 && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded-lg">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
            <div>
              <h3 className="text-sm font-medium text-red-800">Low Attendance Warning</h3>
              <p className="text-sm text-red-700 mt-1">
                Your attendance is below 75%. You need to attend{' '}
                {Math.ceil((75 * attendanceData.total_classes - 100 * attendanceData.present) / 25)} more classes
                to reach 75% attendance.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Subject-wise attendance */}
      {attendanceData.subjects && attendanceData.subjects.length > 0 && (
        <div className="bg-white rounded-lg shadow-md">
          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold text-gray-900">Subject-wise Attendance</h3>
            <p className="text-gray-600">Detailed breakdown by subject</p>
          </div>
          <SubjectList subjects={attendanceData.subjects} />
        </div>
      )}

      {/* Additional stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Not Applicable</h4>
          <p className="text-2xl font-bold text-gray-900 mt-2">{attendanceData.not_applicable || 0}</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wide">On Duty</h4>
          <p className="text-2xl font-bold text-gray-900 mt-2">{attendanceData.on_duty || 0}</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Total Classes</h4>
          <p className="text-2xl font-bold text-gray-900 mt-2">{attendanceData.total_classes}</p>
        </div>
      </div>
    </div>
  );
};

export default AttendanceDashboard;