// src/services/api.js
// Mevcut API servisleri (adapter pattern ile MCP'ye bağlanıyor)

import { 
  MCPLlmAPI, 
  MCPCommandExecutorAPI, 
  MCPFileManagerAPI, 
  MCPEditorAPI,
  MCPSystemInfoAPI, 
  MCPUserManagerAPI,
  MCPNetworkManagerAPI,
  MCPSchedulerAPI,
  MCPArchiveManagerAPI 
} from './mcp-api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

// Generic error handler - Korunuyor
const handleResponse = async (response) => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const errorMessage = errorData?.message || `API Error: ${response.status} ${response.statusText}`;
    throw new Error(errorMessage);
  }
  return response.json();
};

// System Info API - API adapter
export const getSystemInfo = async () => {
  try {
    // MCP API'e yönlendir
    return await MCPSystemInfoAPI.get('get_info');
  } catch (error) {
    // Geriye uyumluluk için eski API kullan
    const response = await fetch(`${API_BASE_URL}/system/info`);
    return handleResponse(response);
  }
};

// File Manager API - API adapter
export const FileManagerAPI = {
  listFiles: async (path) => {
    try {
      // MCP API'e yönlendir
      return await MCPFileManagerAPI.get('list_files', { path });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/files/list?path=${encodeURIComponent(path)}`);
      return handleResponse(response);
    }
  },
  
  createFile: async (path, content = '') => {
    try {
      // MCP API'e yönlendir
      return await MCPFileManagerAPI.post('create_file', { path, content });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/files/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, content })
      });
      return handleResponse(response);
    }
  },
  
  readFile: async (path) => {
    try {
      // MCP API'e yönlendir
      return await MCPFileManagerAPI.get('read_file', { path });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/files/read?path=${encodeURIComponent(path)}`);
      return handleResponse(response);
    }
  },
  
  updateFile: async (path, content) => {
    try {
      // MCP API'e yönlendir
      return await MCPFileManagerAPI.post('update_file', { path, content });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/files/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, content })
      });
      return handleResponse(response);
    }
  },
  
  deleteFile: async (path) => {
    try {
      // MCP API'e yönlendir
      return await MCPFileManagerAPI.post('delete_file', { path });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/files/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
      return handleResponse(response);
    }
  },
  
  moveFile: async (source, destination) => {
    try {
      // MCP API'e yönlendir
      return await MCPFileManagerAPI.post('move_file', { source, destination });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/files/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, destination })
      });
      return handleResponse(response);
    }
  },
  
  createDirectory: async (path) => {
    try {
      // MCP API'e yönlendir
      return await MCPFileManagerAPI.post('create_directory', { path });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/files/mkdir`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
      return handleResponse(response);
    }
  }
};

// User Manager API - API adapter
export const UserManagerAPI = {
  listUsers: async () => {
    try {
      // MCP API'e yönlendir
      return await MCPUserManagerAPI.get('list_users');
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/users/list`);
      return handleResponse(response);
    }
  },
  
  getUserInfo: async (username) => {
    try {
      // MCP API'e yönlendir
      return await MCPUserManagerAPI.get('get_user_info', { username });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/users/info?username=${encodeURIComponent(username)}`);
      return handleResponse(response);
    }
  },
  
  createUser: async (userData) => {
    try {
      // MCP API'e yönlendir
      return await MCPUserManagerAPI.post('create_user', userData);
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/users/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });
      return handleResponse(response);
    }
  },
  
  deleteUser: async (username) => {
    try {
      // MCP API'e yönlendir
      return await MCPUserManagerAPI.post('delete_user', { username });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/users/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      });
      return handleResponse(response);
    }
  }
};

// Network Manager API - API adapter
export const NetworkManagerAPI = {
  getNetworkInfo: async () => {
    try {
      // MCP API'e yönlendir
      return await MCPNetworkManagerAPI.get('get_network_info');
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/network/info`);
      return handleResponse(response);
    }
  },
  
  scanPorts: async (host, portRange) => {
    try {
      // MCP API'e yönlendir
      return await MCPNetworkManagerAPI.post('scan_ports', { host, portRange });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/network/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host, portRange })
      });
      return handleResponse(response);
    }
  },
  
  pingHost: async (host) => {
    try {
      // MCP API'e yönlendir
      return await MCPNetworkManagerAPI.post('ping_host', { host });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/network/ping`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host })
      });
      return handleResponse(response);
    }
  }
};

// Editor API - API adapter
export const EditorAPI = {
  getFiles: async () => {
    try {
      // MCP API'e yönlendir
      return await MCPEditorAPI.get('get_files');
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/editor/files`);
      return handleResponse(response);
    }
  },
  
  getFileContent: async (path) => {
    try {
      // MCP API'e yönlendir
      return await MCPEditorAPI.get('get_file_content', { path });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/editor/file?path=${encodeURIComponent(path)}`);
      return handleResponse(response);
    }
  },
  
  saveFile: async (path, content) => {
    try {
      // MCP API'e yönlendir
      return await MCPEditorAPI.post('save_file', { path, content });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/editor/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, content })
      });
      return handleResponse(response);
    }
  },
  
  getTemplates: async () => {
    try {
      // MCP API'e yönlendir
      return await MCPEditorAPI.get('get_templates');
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/editor/templates`);
      return handleResponse(response);
    }
  },
  
  applyTemplate: async (path, templateId, content) => {
    try {
      // MCP API'e yönlendir
      return await MCPEditorAPI.post('apply_template', { path, templateId, content });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/editor/apply-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, templateId, content })
      });
      return handleResponse(response);
    }
  },
  
  previewChanges: async (path, templateId, content) => {
    try {
      // MCP API'e yönlendir
      return await MCPEditorAPI.post('preview_changes', { path, templateId, content });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/editor/preview-changes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, templateId, content })
      });
      return handleResponse(response);
    }
  },
  
  saveTemplate: async (name, description, template) => {
    try {
      // MCP API'e yönlendir
      return await MCPEditorAPI.post('save_template', { name, description, template });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/editor/save-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, template })
      });
      return handleResponse(response);
    }
  },
  
  deleteTemplate: async (templateId) => {
    try {
      // MCP API'e yönlendir
      return await MCPEditorAPI.post('delete_template', { templateId });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/editor/delete-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ templateId })
      });
      return handleResponse(response);
    }
  }
};

// Scheduler API - API adapter
export const SchedulerAPI = {
  getTasks: async () => {
    try {
      // MCP API'e yönlendir
      return await MCPSchedulerAPI.get('get_tasks');
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/scheduler/tasks`);
      return handleResponse(response);
    }
  },
  
  createTask: async (taskData) => {
    try {
      // MCP API'e yönlendir
      return await MCPSchedulerAPI.post('create_task', taskData);
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/scheduler/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskData)
      });
      return handleResponse(response);
    }
  },
  
  updateTask: async (taskId, taskData) => {
    try {
      // MCP API'e yönlendir
      return await MCPSchedulerAPI.post('update_task', { taskId, ...taskData });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/scheduler/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ taskId, ...taskData })
      });
      return handleResponse(response);
    }
  },
  
  deleteTask: async (taskId) => {
    try {
      // MCP API'e yönlendir
      return await MCPSchedulerAPI.post('delete_task', { taskId });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/scheduler/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ taskId })
      });
      return handleResponse(response);
    }
  },
  
  executeTask: async (taskId) => {
    try {
      // MCP API'e yönlendir
      return await MCPSchedulerAPI.post('execute_task', { taskId });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/scheduler/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ taskId })
      });
      return handleResponse(response);
    }
  }
};

// Archive Manager API - API adapter
export const ArchiveManagerAPI = {
  createArchive: async (sourcePath, archivePath, archiveType) => {
    try {
      // MCP API'e yönlendir
      return await MCPArchiveManagerAPI.post('create_archive', { sourcePath, archivePath, archiveType });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/archive/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sourcePath, archivePath, archiveType })
      });
      return handleResponse(response);
    }
  },
  
  extractArchive: async (archivePath, destPath) => {
    try {
      // MCP API'e yönlendir
      return await MCPArchiveManagerAPI.post('extract_archive', { archivePath, destPath });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/archive/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archivePath, destPath })
      });
      return handleResponse(response);
    }
  },
  
  listArchiveContents: async (archivePath) => {
    try {
      // MCP API'e yönlendir
      return await MCPArchiveManagerAPI.get('list_archive_contents', { archivePath });
    } catch (error) {
      // Geriye uyumluluk için eski API kullan
      const response = await fetch(`${API_BASE_URL}/archive/list?path=${encodeURIComponent(archivePath)}`);
      return handleResponse(response);
    }
  }
};

export const CommandExecutorAPI = {
  async executeCommand(command, workingDir = null, timeout = 30) {
    try {
      console.log("Executing command with params:", { command, workingDir, timeout });
      
      // Doğru endpoint'e yönlendir
      const response = await fetch('/api/command/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          command,
          workingDir,
          timeout
        }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Command execution error:', error);
      throw error;
    }
  }
};

// LLM API - Doğrudan MCP'yi kullan (yeni eklendi)
export const LlmAPI = {
  generateTasks: async (options) => {
    return MCPLlmAPI.post('generate_tasks', options);
  },
  
  generateText: async (options) => {
    return MCPLlmAPI.post('generate_text', options);
  },
  
  getModels: async (provider = 'openai') => {
    return MCPLlmAPI.get('get_models', { provider });
  },
  
  getProviders: async () => {
    return MCPLlmAPI.get('get_providers');
  },
  
  checkStatus: async (provider = 'openai') => {
    return MCPLlmAPI.get('check_status', { provider });
  },
  
  setupProvider: async (options) => {
    return MCPLlmAPI.post('setup_provider', options);
  }
};

export const TaskRunnerAPI = {
  // Mevcut fonksiyonlar
  generateTasks: async (prompt) => {
    return LlmAPI.generateTasks({ prompt });
  },
  
  executeCommand: async (command) => {
    return CommandExecutorAPI.executeCommand(command);
  },
  
  executeWithContext: async (task, llmSettings = null, clearContext = false) => {
    try {
      const response = await fetch(`${API_BASE_URL}/task/execute_with_context`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task,
          llm_settings: llmSettings,
          clear_context: clearContext
        }),
      });
      return handleResponse(response);
    } catch (error) {
      console.error('Task execution error:', error);
      throw error;
    }
  },
  
  executeSequential: async (tasks, failStrategy = 'continue', clearContext = true) => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/execute_sequential`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tasks,
          fail_strategy: failStrategy,
          clear_context: clearContext
        }),
      });
      return handleResponse(response);
    } catch (error) {
      console.error('Sequential task execution error:', error);
      throw error;
    }
  },
  
  getContext: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/context/get`);
      return handleResponse(response);
    } catch (error) {
      console.error('Get context error:', error);
      throw error;
    }
  },
  
  updateContext: async (contextUpdates) => {
    try {
      const response = await fetch(`${API_BASE_URL}/context/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          context: contextUpdates
        }),
      });
      return handleResponse(response);
    } catch (error) {
      console.error('Update context error:', error);
      throw error;
    }
  },
  
  runTasksWithLLMFeedback: async (tasks, options = {}) => {
    try {
      const response = await fetch(`${API_BASE_URL}/coordinator/run_tasks_with_feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tasks,
          ...options
        }),
      });
      return handleResponse(response);
    } catch (error) {
      console.error('Run tasks with LLM feedback error:', error);
      throw error;
    }
  },
  
  executeTask: async (task) => {
    try {
      const response = await fetch(`${API_BASE_URL}/task/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task
        }),
      });
      return handleResponse(response);
    } catch (error) {
      console.error('Execute task error:', error);
      throw error;
    }
  },
  
  executeTasks: async (tasks, mode = 'sequential') => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tasks,
          mode
        }),
      });
      return handleResponse(response);
    } catch (error) {
      console.error('Execute tasks error:', error);
      throw error;
    }
  }
};

// Utility to handle API errors in components
export const handleApiError = (error, setErrorState) => {
  console.error('API Error:', error);
  const message = error.message || 'An unexpected error occurred';
  setErrorState && setErrorState(message);
  return message;
};


export default {
  getSystemInfo,
  FileManagerAPI,
  UserManagerAPI,
  NetworkManagerAPI,
  EditorAPI,
  SchedulerAPI,
  ArchiveManagerAPI,
  CommandExecutorAPI,
  TaskRunnerAPI,
  LlmAPI, 
  handleApiError
};

export const runTasksWithLLMFeedback = async (tasks, options = {}) => {
  return TaskRunnerAPI.runTasksWithLLMFeedback(tasks, options);
};