import { BookOpen, TrendingUp, TrendingDown } from 'lucide-react';

const SubjectList = ({ subjects }) => {
  const getAttendanceColor = (percentage) => {
    if (percentage >= 75) return 'text-green-600 bg-green-50';
    if (percentage >= 65) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getAttendanceIcon = (percentage) => {
    if (percentage >= 75) return <TrendingUp className="h-4 w-4" />;
    return <TrendingDown className="h-4 w-4" />;
  };

  if (!subjects || subjects.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500">
        <p>No subject-wise attendance data available</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-200">
      {subjects.map((subject, index) => (
        <div key={index} className="p-6 hover:bg-gray-50 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <BookOpen className="h-5 w-5 text-gray-400" />
              <div>
                <h4 className="text-sm font-medium text-gray-900">
                  {subject.name || subject.subject || `Subject ${index + 1}`}
                </h4>
                <p className="text-sm text-gray-500">
                  {subject.present}/{subject.total} classes attended
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className={`flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium ${getAttendanceColor(subject.percentage)}`}>
                {getAttendanceIcon(subject.percentage)}
                <span>{subject.percentage}%</span>
              </div>
            </div>
          </div>
          
          {/* Progress bar */}
          <div className="mt-3">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  subject.percentage >= 75 
                    ? 'bg-green-500' 
                    : subject.percentage >= 65 
                    ? 'bg-yellow-500' 
                    : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(subject.percentage, 100)}%` }}
              ></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default SubjectList;