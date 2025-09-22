import axios from 'axios';

const API_BASE_URL = '/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// API service functions
export const attendanceAPI = {
  // Get attendance data
  getAttendance: async (username, password) => {
    try {
      const response = await api.post('/attendance', {
        username,
        password
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to fetch attendance');
    }
  },

  // Test login credentials
  testLogin: async (username, password) => {
    try {
      const response = await api.get('/login-test', {
        params: { username, password }
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Login test failed');
    }
  },

  // Check if LNCT site is accessible
  checkSite: async () => {
    try {
      const response = await api.get('/check-site');
      return response.data;
    } catch (error) {
      throw new Error('Failed to check site status');
    }
  },

  // Debug login process
  debugLogin: async (username, password) => {
    try {
      const response = await api.get('/debug-login', {
        params: { username, password }
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Debug login failed');
    }
  }
};

export default api;