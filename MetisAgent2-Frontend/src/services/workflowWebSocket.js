/**
 * WebSocket Service for Real-Time Workflow Updates
 */

import io from 'socket.io-client';

class WorkflowWebSocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000;
    this.eventHandlers = new Map();
    this.userId = null;
  }

  /**
   * Initialize WebSocket connection
   */
  connect(userId = 'anonymous') {
    // Ensure userId is never null/undefined
    this.userId = userId || 'anonymous';
    console.log('🔗 WorkflowWebSocket connecting with userId:', this.userId);
    
    if (this.socket && this.socket.connected) {
      console.log('WebSocket already connected, joining room for user:', this.userId);
      // Join room for this user even if already connected
      this.socket.emit('join_workflow_room', { user_id: this.userId });
      return;
    }

    console.log('Connecting to workflow WebSocket...');
    
    const wsUrl = process.env.REACT_APP_API_URL?.replace('/api', '') || 'http://localhost:5001';
    this.socket = io(wsUrl, {
      transports: ['websocket', 'polling'],
      timeout: 20000,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
      forceNew: true
    });

    this.setupEventHandlers();
  }

  /**
   * Setup WebSocket event handlers
   */
  setupEventHandlers() {
    if (!this.socket) return;

    // Connection events
    this.socket.on('connect', () => {
      console.log('✅ WebSocket connected:', this.socket.id);
      this.isConnected = true;
      this.reconnectAttempts = 0;
      
      // Join user-specific workflow room with null safety
      const safeUserId = this.userId || 'anonymous';
      console.log('🏠 Joining workflow room for user:', safeUserId);
      this.socket.emit('join_workflow_room', { user_id: safeUserId });
      
      // Trigger connection event
      this.emit('connection_status', { connected: true });
    });

    this.socket.on('disconnect', (reason) => {
      console.log('❌ WebSocket disconnected:', reason);
      this.isConnected = false;
      this.emit('connection_status', { connected: false, reason });
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.emit('connection_error', error);
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts`);
      this.isConnected = true;
      this.emit('reconnected', { attempts: attemptNumber });
    });

    this.socket.on('reconnect_failed', () => {
      console.error('❌ WebSocket reconnection failed after max attempts');
      this.emit('reconnect_failed');
    });

    // Room events
    this.socket.on('room_joined', (data) => {
      console.log('🏠 Joined workflow room:', data.room);
      this.emit('room_joined', data);
    });

    this.socket.on('room_left', (data) => {
      console.log('🚪 Left workflow room:', data.room);
      this.emit('room_left', data);
    });

    // Workflow events
    this.socket.on('workflow_started', (data) => {
      console.log('🚀 Workflow started:', data);
      this.emit('workflow_started', data);
    });

    this.socket.on('workflow_update', (data) => {
      console.log('🔄 Workflow update:', data);
      this.emit('workflow_update', data);
    });

    this.socket.on('workflow_step_update', (data) => {
      console.log('📝 Step update:', data);
      this.emit('workflow_step_update', data);
    });

    this.socket.on('workflow_completed', (data) => {
      console.log('✅ Workflow completed:', data);
      this.emit('workflow_completed', data);
    });

    // Connection status events
    this.socket.on('connection_status', (data) => {
      console.log('📡 Connection status:', data);
      this.emit('connection_status', data);
    });
  }

  /**
   * Subscribe to workflow events
   */
  on(eventName, handler) {
    if (!this.eventHandlers.has(eventName)) {
      this.eventHandlers.set(eventName, []);
    }
    this.eventHandlers.get(eventName).push(handler);
  }

  /**
   * Unsubscribe from workflow events
   */
  off(eventName, handler) {
    if (this.eventHandlers.has(eventName)) {
      const handlers = this.eventHandlers.get(eventName);
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * Emit event to subscribed handlers
   */
  emit(eventName, data) {
    if (this.eventHandlers.has(eventName)) {
      this.eventHandlers.get(eventName).forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler for ${eventName}:`, error);
        }
      });
    }
  }

  /**
   * Join workflow room for specific user
   */
  joinWorkflowRoom(userId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('join_workflow_room', { user_id: userId });
      this.userId = userId;
    }
  }

  /**
   * Leave workflow room
   */
  leaveWorkflowRoom() {
    if (this.socket && this.socket.connected && this.userId) {
      this.socket.emit('leave_workflow_room', { user_id: this.userId });
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.socket) {
      console.log('Disconnecting WebSocket...');
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
    }
  }

  /**
   * Get connection status
   */
  getConnectionStatus() {
    return {
      isConnected: this.isConnected,
      socketId: this.socket?.id,
      userId: this.userId
    };
  }

  /**
   * Force reconnection
   */
  forceReconnect() {
    if (this.socket) {
      this.socket.disconnect();
      setTimeout(() => {
        this.connect(this.userId);
      }, 1000);
    }
  }
}

// Export singleton instance
export const workflowWebSocket = new WorkflowWebSocketService();
export default workflowWebSocket;