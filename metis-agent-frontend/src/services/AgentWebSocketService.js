// services/AgentWebSocketService.js - Geliştirilmiş versiyon

const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NODE_ENV === 'development' 
        ? 'localhost:6001' 
        : window.location.host;
    return `${protocol}//${host}/ws/agent`;
};

class AgentWebSocketService {
    constructor() {
        this.ws = null;
        this.wsId = null;
        this.listeners = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Initial delay in ms
        this.messageQueue = []; // Queue for messages when disconnected
        this.connectionState = 'disconnected'; // disconnected, connecting, connected, error
        this.heartbeatInterval = null;
        this.responseTimeouts = new Map(); // Track message timeouts
        this.lastActivity = Date.now();
        
        // Performance monitoring
        this.stats = {
            messagesSent: 0,
            messagesReceived: 0,
            averageResponseTime: 0,
            errors: 0,
            reconnections: 0
        };
    }
    
    connect() {
        if (this.connectionState === 'connecting' || this.connectionState === 'connected') {
            console.log('WebSocket already connecting or connected');
            return;
        }
        
        const wsUrl = getWebSocketUrl();
        console.log('WebSocket bağlantısı deneniyor:', wsUrl);
        
        this.connectionState = 'connecting';
        this.emit('connecting');
        
        try {
            this.ws = new WebSocket(wsUrl);
            this.setupEventHandlers();
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.connectionState = 'error';
            this.emit('error', { message: 'Connection failed' });
            this.scheduleReconnect();
        }
    }
    
    setupEventHandlers() {
        this.ws.onopen = () => {
            console.log('Agent WebSocket bağlantısı kuruldu');
            this.connectionState = 'connected';
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.lastActivity = Date.now();
            
            // Process queued messages
            this.processMessageQueue();
            
            // Start heartbeat
            this.startHeartbeat();
            
            this.emit('connected', { wsId: this.wsId });
        };
        
        this.ws.onmessage = (event) => {
            this.lastActivity = Date.now();
            this.stats.messagesReceived++;
            
            console.log('WebSocket mesajı alındı:', event.data);
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('WebSocket mesaj parse hatası:', error);
                this.stats.errors++;
                this.emit('error', { message: 'Message parse error', error });
            }
        };
        
        this.ws.onclose = (event) => {
            console.log('Agent WebSocket bağlantısı kapandı', event.code, event.reason);
            this.connectionState = 'disconnected';
            this.stopHeartbeat();
            
            this.emit('disconnected', { 
                code: event.code, 
                reason: event.reason,
                wasClean: event.wasClean 
            });
            
            // Don't auto-reconnect if it was a clean close (user logout)
            if (!event.wasClean || event.code !== 1000) {
                this.scheduleReconnect();
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket hatası:', error);
            this.connectionState = 'error';
            this.stats.errors++;
            this.emit('error', { message: 'WebSocket error', error });
        };
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Maximum reconnection attempts reached');
            this.emit('max_reconnects_reached');
            return;
        }
        
        this.reconnectAttempts++;
        this.stats.reconnections++;
        
        // Exponential backoff with jitter
        const jitter = Math.random() * 1000;
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1) + jitter, 30000);
        
        console.log(`WebSocket yeniden bağlanma denemesi: ${this.reconnectAttempts}/${this.maxReconnectAttempts} (${delay}ms sonra)`);
        
        this.emit('reconnecting', { 
            attempt: this.reconnectAttempts, 
            maxAttempts: this.maxReconnectAttempts,
            delay: delay 
        });
        
        setTimeout(() => {
            if (this.connectionState !== 'connected') {
                this.connect();
            }
        }, delay);
    }
    
    startHeartbeat() {
        this.stopHeartbeat(); // Clear any existing heartbeat
        
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected()) {
                const timeSinceLastActivity = Date.now() - this.lastActivity;
                
                // Send ping if no activity for 30 seconds
                if (timeSinceLastActivity > 30000) {
                    this.send('ping', { timestamp: Date.now() });
                }
                
                // Consider connection dead if no activity for 60 seconds
                if (timeSinceLastActivity > 60000) {
                    console.warn('WebSocket appears to be dead, forcing reconnection');
                    this.ws.close();
                }
            }
        }, 15000); // Check every 15 seconds
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    processMessageQueue() {
        while (this.messageQueue.length > 0 && this.isConnected()) {
            const queuedMessage = this.messageQueue.shift();
            this.sendImmediate(queuedMessage.command, queuedMessage.data);
        }
    }
    
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN && this.connectionState === 'connected';
    }
    
    getConnectionState() {
        return this.connectionState;
    }
    
    getStats() {
        return {
            ...this.stats,
            connectionState: this.connectionState,
            reconnectAttempts: this.reconnectAttempts,
            queuedMessages: this.messageQueue.length,
            timeSinceLastActivity: Date.now() - this.lastActivity
        };
    }
    
    sendMessage(personaId, message, timeout = 30000) {
        const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const startTime = Date.now();
        
        // Set up timeout tracking
        if (timeout > 0) {
            const timeoutId = setTimeout(() => {
                this.responseTimeouts.delete(messageId);
                this.emit('message_timeout', { messageId, personaId, message });
            }, timeout);
            
            this.responseTimeouts.set(messageId, { timeoutId, startTime });
        }
        
        this.send('send_message', {
            messageId,
            persona_id: personaId,
            message: message,
            user_id: 'default', // TODO: Gerçek user authentication ile değiştirilecek
            timestamp: Date.now()
        });
        
        this.stats.messagesSent++;
        return messageId;
    }
    
    send(command, data = {}) {
        const message = { command, ...data };
        
        if (this.isConnected()) {
            this.sendImmediate(command, data);
        } else {
            // Queue the message for later
            console.log('WebSocket not connected, queueing message:', command);
            this.messageQueue.push({ command, data });
            
            // Limit queue size
            if (this.messageQueue.length > 50) {
                this.messageQueue.shift(); // Remove oldest message
            }
            
            // Try to reconnect if not already trying
            if (this.connectionState === 'disconnected') {
                this.connect();
            }
        }
    }
    
    sendImmediate(command, data = {}) {
        try {
            const message = JSON.stringify({ command, ...data });
            this.ws.send(message);
            this.lastActivity = Date.now();
        } catch (error) {
            console.error('Error sending WebSocket message:', error);
            this.stats.errors++;
            this.emit('send_error', { command, data, error });
        }
    }
    
    handleMessage(message) {
        const { type, data } = message;
        
        // Handle response time tracking
        if (data && data.messageId && this.responseTimeouts.has(data.messageId)) {
            const tracking = this.responseTimeouts.get(data.messageId);
            const responseTime = Date.now() - tracking.startTime;
            
            // Update average response time
            const currentAvg = this.stats.averageResponseTime;
            const totalMessages = this.stats.messagesReceived;
            this.stats.averageResponseTime = (currentAvg * (totalMessages - 1) + responseTime) / totalMessages;
            
            clearTimeout(tracking.timeoutId);
            this.responseTimeouts.delete(data.messageId);
            
            // Add response time to the data
            if (data) {
                data.responseTime = responseTime;
            }
        }
        
        // Handle special message types
        if (type === 'connected' && data.ws_id) {
            this.wsId = data.ws_id;
        } else if (type === 'pong') {
            // Heartbeat response
            console.log('Heartbeat pong received');
            return;
        } else if (type === 'error') {
            this.stats.errors++;
        }
        
        // Emit to listeners
        this.emit(type, data);
    }
    
    on(eventType, callback) {
        if (!this.listeners[eventType]) {
            this.listeners[eventType] = [];
        }
        this.listeners[eventType].push(callback);
    }
    
    off(eventType, callback) {
        if (this.listeners[eventType]) {
            this.listeners[eventType] = this.listeners[eventType].filter(cb => cb !== callback);
        }
    }
    
    emit(eventType, data = null) {
        if (this.listeners[eventType]) {
            this.listeners[eventType].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event listener for ${eventType}:`, error);
                }
            });
        }
    }
    
    subscribe(events) {
        this.send('subscribe', { events });
    }
    
    unsubscribe(events) {
        this.send('unsubscribe', { events });
    }
    
    disconnect(code = 1000, reason = 'User initiated') {
        console.log('Disconnecting WebSocket:', reason);
        
        this.stopHeartbeat();
        this.connectionState = 'disconnected';
        
        // Clear all timeouts
        this.responseTimeouts.forEach(tracking => {
            clearTimeout(tracking.timeoutId);
        });
        this.responseTimeouts.clear();
        
        // Clear message queue
        this.messageQueue = [];
        
        if (this.ws) {
            this.ws.close(code, reason);
            this.ws = null;
        }
    }
    
    // Utility methods for common operations
    startPersona(personaId) {
        this.send('start_persona', { persona_id: personaId });
    }
    
    stopPersona(personaId) {
        this.send('stop_persona', { persona_id: personaId });
    }
    
    getPersonaStatus(personaId) {
        this.send('get_persona_status', { persona_id: personaId });
    }
    
    executeTask(personaId, task) {
        this.send('execute_task', { 
            persona_id: personaId, 
            task: task,
            timestamp: Date.now()
        });
    }
    
    // Debug and monitoring methods
    enableDebugMode() {
        this.on('*', (data) => {
            console.log('WebSocket Debug:', data);
        });
    }
    
    getConnectionInfo() {
        return {
            url: getWebSocketUrl(),
            state: this.connectionState,
            wsId: this.wsId,
            reconnectAttempts: this.reconnectAttempts,
            stats: this.getStats(),
            queueLength: this.messageQueue.length,
            activeTimeouts: this.responseTimeouts.size
        };
    }
}

// Create and export singleton instance
const agentWebSocketService = new AgentWebSocketService();

// Add some debugging in development
if (process.env.NODE_ENV === 'development') {
    window.wsService = agentWebSocketService; // For debugging
}

export default agentWebSocketService;