import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Standardize error handling
    const customError = {
      message: error.response?.data?.error?.message || error.response?.data?.detail || error.message || 'Unknown network error',
      status: error.response?.status,
      data: error.response?.data,
    };
    return Promise.reject(customError);
  }
);
