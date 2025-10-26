import axios from 'axios';

// For Expo/React Native: Use your computer's local IP address
// Port 8000 is the database API server (backend/database/main.py)
const api = axios.create({
  baseURL: 'http://100.66.74.139:8000',
});

export default api;
