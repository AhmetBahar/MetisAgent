// src/services/AuthAPI.js
import axios from 'axios';

// API base URL - environment variable veya localhost fallback
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';
// Remove /api suffix for axios baseURL since endpoints already include /api
const BASE_URL = API_BASE_URL.replace(/\/api$/, '');

// Axios base URL'i ayarla
const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

class AuthAPI {
  static async login(email, password) {
    try {
      console.log('Login API çağrılıyor:', { email }); // Debug log
      const response = await apiClient.post('/api/auth/login', { email, password });
      console.log('Login API yanıtı:', response.data); // Debug log
      return response;
    } catch (error) {
      console.error('Login API hatası:', error.response?.data || error.message);
      console.error('Request data:', { email, password: '***' });
      throw error;
    }
  }
  
  static async register(username, email, password) {
    try {
      console.log('Register API çağrılıyor:', { username, email }); // Debug log
      const response = await apiClient.post('/api/auth/register', { username, email, password });
      console.log('Register API yanıtı:', response.data); // Debug log
      return response;
    } catch (error) {
      console.error('Register API hatası:', error.response?.data || error.message);
      throw error;
    }
  }
  
  static async logout() {
    return apiClient.post('/api/auth/logout');
  }
  
  static async getCurrentUser() {
    return apiClient.get('/api/auth/current-user');
  }
  
  static async changePassword(oldPassword, newPassword) {
    return apiClient.post('/api/auth/change-password', { oldPassword, newPassword });
  }
  
  static async createApiKey(permissions = ['read']) {
    return apiClient.post('/api/auth/api-key', { permissions });
  }
  
  static async getApiKeys() {
    return apiClient.get('/api/auth/api-keys');
  }
  
  static async revokeApiKey(apiKey) {
    return apiClient.delete(`/api/auth/api-key/${apiKey}`);
  }
}

export default AuthAPI;