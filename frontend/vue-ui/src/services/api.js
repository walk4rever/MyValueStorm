import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: process.env.VUE_APP_API_URL || '/api',
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Research API endpoints
export const researchApi = {
  // Get all research topics
  getTopics: () => api.get('/research/topics'),
  
  // Start a new research
  startResearch: (data) => api.post('/research/start', data),
  
  // Get research progress
  getProgress: (id) => api.get(`/research/progress/${id}`),
  
  // Get all research results
  getResults: () => api.get('/research/results'),
  
  // Get a specific research result
  getResult: (id) => api.get(`/research/results/${id}`)
};

// Add request interceptor for error handling
api.interceptors.request.use(
  config => {
    // You can add auth tokens here if needed
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    // Handle common errors
    if (error.response) {
      // Server responded with an error status
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // Request was made but no response received
      console.error('API No Response:', error.request);
    } else {
      // Something else happened while setting up the request
      console.error('API Request Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default api;
