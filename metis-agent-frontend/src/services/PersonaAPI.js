// src/services/PersonaAPI.js
import axios from 'axios';

class PersonaAPI {
  static async listPersonas() {
    return axios.get('/api/personas');
  }
  
  static async getPersonas() {
    return axios.get('/api/personas');
  }
  
  static async getPersona(personaId) {
    return axios.get(`/api/personas/${personaId}`);
  }
  
  static async createPersona(personaData) {
    return axios.post('/api/personas', personaData);
  }
  
  static async updatePersona(personaId, personaData) {
    return axios.put(`/api/personas/${personaId}`, personaData);
  }
  
  static async deletePersona(personaId) {
    return axios.delete(`/api/personas/${personaId}`);
  }
  
  static async getPersonaStatus(personaId) {
    return axios.get(`/api/personas/${personaId}/status`);
  }
  
  static async startPersona(personaId) {
    return axios.post(`/api/personas/${personaId}/start`);
  }
  
  static async stopPersona(personaId) {
    return axios.post(`/api/personas/${personaId}/stop`);
  }
  
  static async restartPersona(personaId) {
    return axios.post(`/api/personas/${personaId}/restart`);
  }
  
  static async executeWithPersona(task, personaId, context = {}) {
    return axios.post('/api/a2a/task', {
      task: task,
      context: context,
      target_persona: personaId
    });
  }
}

export default PersonaAPI;