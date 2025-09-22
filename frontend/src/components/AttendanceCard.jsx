const AttendanceCard = ({ title, value, icon, color = 'text-gray-900', subtitle, statusIcon }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className={color}>
            {icon}
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              {title}
            </h3>
            <div className="flex items-center space-x-2">
              <p className={`text-2xl font-bold ${color}`}>
                {value}
              </p>
              {statusIcon}
            </div>
            {subtitle && (
              <p className="text-sm text-gray-600 mt-1">
                {subtitle}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AttendanceCard;