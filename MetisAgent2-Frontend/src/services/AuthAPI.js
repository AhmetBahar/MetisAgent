// src/services/AuthAPI.js
import axios from 'axios';

// API base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

// Axios client for auth API
const authClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Request interceptor to add auth token
authClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('session_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
authClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid, clear storage
      localStorage.removeItem('session_token');
      localStorage.removeItem('user_data');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

class AuthAPI {
  static async login(username, password) {
    try {
      console.log('Login API çağrılıyor:', { email: username });
      const response = await authClient.post('/api/auth/login', { email: username, password });
      console.log('Login API yanıtı:', response.data);
      
      // Store session token and user data - Updated for MetisAgent3 format
      if (response.data.success) {
        localStorage.setItem('session_token', response.data.token);
        localStorage.setItem('user_data', JSON.stringify(response.data.user));
      }
      
      return response;
    } catch (error) {
      console.error('Login API hatası:', error.response?.data || error.message);
      throw error;
    }
  }
  
  static async register(username, email, password) {
    try {
      console.log('Register API çağrılıyor:', { username, email });
      const response = await authClient.post('/api/auth/register', { username, email, password });
      console.log('Register API yanıtı:', response.data);
      return response;
    } catch (error) {
      console.error('Register API hatası:', error.response?.data || error.message);
      throw error;
    }
  }
  
  static async logout() {
    try {
      const response = await authClient.post('/api/auth/logout');
      
      // Clear local storage
      localStorage.removeItem('session_token');
      localStorage.removeItem('user_data');
      
      return response;
    } catch (error) {
      // Even if logout fails, clear local storage
      localStorage.removeItem('session_token');
      localStorage.removeItem('user_data');
      throw error;
    }
  }
  
  static async validateSession() {
    try {
      const token = this.getStoredToken();
      if (!token) {
        return { valid: false };
      }
      
      // Request interceptor zaten Authorization header ekleyecek,
      // JSON body'de token göndermeye gerek yok
      const response = await authClient.post('/api/auth/validate', {});
      return response.data;
    } catch (error) {
      console.error('Session validation error:', error.response?.data || error.message);
      return { valid: false };
    }
  }
  
  static async getCurrentUser() {
    try {
      const response = await authClient.get('/api/auth/me');
      return response.data;
    } catch (error) {
      console.error('Get current user error:', error.response?.data || error.message);
      throw error;
    }
  }
  
  static async createApiKey(permissions = ['read']) {
    try {
      const response = await authClient.post('/api/auth/create-api-key', { permissions });
      return response.data;
    } catch (error) {
      console.error('Create API key error:', error.response?.data || error.message);
      throw error;
    }
  }
  
  // Helper methods
  static getStoredToken() {
    return localStorage.getItem('session_token');
  }
  
  static getStoredUser() {
    const userData = localStorage.getItem('user_data');
    return userData ? JSON.parse(userData) : null;
  }
  
  static isAuthenticated() {
    return !!this.getStoredToken();
  }
  
  static clearAuth() {
    localStorage.removeItem('session_token');
    localStorage.removeItem('user_data');
  }
}

export default AuthAPI;