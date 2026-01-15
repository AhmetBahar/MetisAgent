// src/services/ToolsAPI.js
import axios from 'axios';

class ToolsAPI {
  static async getTools(url = '/api/registry/tools') {
    return axios.get(url);
  }
  
  static async getToolDetails(toolId) {
    return axios.get(`/api/registry/tool/${toolId}`);
  }
  
  static async getToolActions(toolId) {
    return axios.get(`/api/registry/tool/${toolId}/actions`);
  }
  
  static async getActionDetails(toolId, actionName) {
    return axios.get(`/api/registry/tool/${toolId}/action/${actionName}`);
  }
  
  static async callToolAction(toolId, actionName, params = {}) {
    return axios.post(`/api/registry/call/${toolId}/${actionName}`, { params });
  }
  
  static async addExternalTool(toolData) {
    return axios.post('/api/registry/external/add', toolData);
  }
  
  static async addRemoteTool(toolData) {
    return axios.post('/api/registry/remote/add', toolData);
  }
  
  static async syncRemoteTools(remoteUrl, authInfo = {}) {
    return axios.post('/api/registry/remote/sync', { remote_url: remoteUrl, auth_info: authInfo });
  }
  
  static async removeTool(toolId) {
    return axios.delete(`/api/registry/tool/${toolId}`);
  }
  
  static async getCategories() {
    return axios.get('/api/registry/categories');
  }
  
  static async getCapabilities() {
    return axios.get('/api/registry/capabilities');
  }
  
  static async checkToolHealth(toolId) {
    return axios.get(`/api/registry/tool/${toolId}/health`);
  }
}

export default ToolsAPI;