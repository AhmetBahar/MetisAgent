import axios from 'axios';

const API_BASE_URL = (process.env.REACT_APP_API_URL || 'http://localhost:5001') + '/api';

class ApiService {
  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 120000, // 120 seconds for long-running operations like image generation
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to include auth token
    this.api.interceptors.request.use(
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

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error);
        
        // Handle authentication errors
        if (error.response?.status === 401) {
          localStorage.removeItem('session_token');
          localStorage.removeItem('user_data');
          // Don't redirect here, let the component handle it
        }
        
        return Promise.reject(error);
      }
    );
  }

  async healthCheck() {
    const response = await this.api.get('/health');
    return response.data;
  }

  async getTools() {
    const response = await this.api.get('/tools/available');
    return response.data;
  }

  async getToolInfo(toolName) {
    const response = await this.api.get(`/tools/${toolName}`);
    return response.data;
  }

  async executeToolAction(toolName, action, params = {}) {
    const response = await this.api.post(`/tools/${toolName}/execute`, {
      action,
      params,
    });
    return response.data;
  }

  async chat(message, options = {}) {
    const payload = {
      message,
      ...options,
    };
    const response = await this.api.post('/chat', payload);
    return response.data;
  }

  // Session Management
  async createSession(userId = null) {
    const response = await this.api.post('/sessions', { user_id: userId });
    return response.data;
  }

  async getSession(sessionId) {
    const response = await this.api.get(`/sessions/${sessionId}`);
    return response.data;
  }

  async deleteSession(sessionId) {
    const response = await this.api.delete(`/sessions/${sessionId}`);
    return response.data;
  }

  async getUserSessions(userId) {
    const response = await this.api.get(`/users/${userId}/sessions`);
    return response.data;
  }

  async getUserConversations(userId) {
    const response = await this.api.get(`/users/${userId}/conversations`);
    return response.data;
  }

  async getStats() {
    const response = await this.api.get('/stats');
    return response.data;
  }

  async executeCommand(command, options = {}) {
    const payload = {
      command,
      ...options,
    };
    const response = await this.api.post('/execute', payload);
    return response.data;
  }

  async validateCommand(command) {
    const response = await this.api.post('/validate-command', { command });
    return response.data;
  }

  async listConversations(userId) {
    const params = userId ? { user_id: userId } : {};
    const response = await this.api.get('/conversations', { params });
    return response.data;
  }

  async getConversation(conversationId, userId) {
    const params = userId ? { user_id: userId } : {};
    const response = await this.api.get(`/conversations/${conversationId}`, { params });
    return response.data;
  }

  async clearConversation(conversationId) {
    const response = await this.api.delete(`/conversations/${conversationId}`);
    return response.data;
  }

  async clearAllConversations() {
    const response = await this.api.post('/conversations/clear');
    return response.data;
  }

  async getProviders() {
    const response = await this.api.get('/providers');
    return response.data;
  }

  async submitDecision(decisionId, choice, options = {}) {
    const payload = {
      decision_id: decisionId,
      choice: choice,
      ...options,
    };
    const response = await this.api.post('/decision', payload);
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;