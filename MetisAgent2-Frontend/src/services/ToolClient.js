/**
 * Generic Tool Client for MetisAgent3
 * 
 * Provides unified interface for executing tool capabilities
 * across all tools in the system.
 */

class ToolClient {
    constructor() {
        this.baseUrl = process.env.REACT_APP_API_BASE_URL || '';
    }

    /**
     * Execute a tool capability
     * @param {string} toolName - Name of the tool (e.g., 'google_tool')
     * @param {string} capability - Tool capability (e.g., 'oauth2_management')
     * @param {string} action - Specific action (e.g., 'authorize')
     * @param {Object} parameters - Action parameters
     * @returns {Promise<Object>} Tool execution result
     */
    async executeToolCapability(toolName, capability, action, parameters = {}) {
        try {
            const response = await fetch(`${this.baseUrl}/api/tools/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    tool_name: toolName,
                    capability: capability,
                    action: action,
                    parameters: parameters
                })
            });

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || `HTTP ${response.status}`);
            }

            return result;
            
        } catch (error) {
            console.error(`Tool execution failed: ${toolName}.${capability}.${action}`, error);
            return {
                success: false,
                error: error.message,
                tool_name: toolName,
                capability: capability,
                action: action
            };
        }
    }

    /**
     * Get list of available tools
     * @returns {Promise<Object>} Available tools and their capabilities
     */
    async getAvailableTools() {
        try {
            const response = await fetch(`${this.baseUrl}/api/tools/available`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || `HTTP ${response.status}`);
            }

            return result;
            
        } catch (error) {
            console.error('Failed to get available tools', error);
            return {
                success: false,
                error: error.message,
                tools: {},
                count: 0
            };
        }
    }

    // ==================== GOOGLE TOOL METHODS ====================

    /**
     * Start Google OAuth2 authorization flow
     * @returns {Promise<Object>} Authorization URL and flow info
     */
    async googleOAuth2Authorize() {
        return this.executeToolCapability('google_tool', 'oauth2_management', 'authorize');
    }

    /**
     * Check Google OAuth2 authorization status
     * @returns {Promise<Object>} Authorization status and user info
     */
    async googleOAuth2Status() {
        return this.executeToolCapability('google_tool', 'oauth2_management', 'check_status');
    }

    /**
     * Revoke Google OAuth2 authorization
     * @returns {Promise<Object>} Revocation result
     */
    async googleOAuth2Revoke() {
        return this.executeToolCapability('google_tool', 'oauth2_management', 'revoke');
    }

    /**
     * Set Google user mapping (MetisAgent user → Google account)
     * @param {string} googleEmail - Google email address
     * @param {string} googleName - Google display name (optional)
     * @returns {Promise<Object>} Mapping creation result
     */
    async setGoogleUserMapping(googleEmail, googleName = '') {
        return this.executeToolCapability('google_tool', 'oauth2_management', 'set_user_mapping', {
            google_email: googleEmail,
            google_name: googleName
        });
    }

    /**
     * Get Google user mapping
     * @returns {Promise<Object>} Current user mapping info
     */
    async getGoogleUserMapping() {
        return this.executeToolCapability('google_tool', 'oauth2_management', 'get_user_mapping');
    }

    /**
     * Delete Google user mapping
     * @returns {Promise<Object>} Deletion result
     */
    async deleteGoogleUserMapping() {
        return this.executeToolCapability('google_tool', 'oauth2_management', 'delete_user_mapping');
    }

    /**
     * List Gmail emails
     * @param {Object} options - List options (max_results, query, etc.)
     * @returns {Promise<Object>} Gmail list result
     */
    async gmailList(options = {}) {
        return this.executeToolCapability('google_tool', 'gmail_operations', 'list', options);
    }

    /**
     * Read Gmail email
     * @param {string} messageId - Gmail message ID
     * @returns {Promise<Object>} Email content
     */
    async gmailRead(messageId) {
        return this.executeToolCapability('google_tool', 'gmail_operations', 'read', {
            message_id: messageId
        });
    }

    /**
     * Send Gmail email
     * @param {Object} emailData - Email data (to, subject, body, etc.)
     * @returns {Promise<Object>} Send result
     */
    async gmailSend(emailData) {
        return this.executeToolCapability('google_tool', 'gmail_operations', 'send', emailData);
    }

    /**
     * Get positional email from Gmail (e.g., latest, second latest)
     * @param {Object} options - Position options
     * @returns {Promise<Object>} Email content
     */
    async gmailGetPositional(options) {
        return this.executeToolCapability('google_tool', 'gmail_operations', 'get_positional_email', options);
    }

    // ==================== CALENDAR METHODS ====================

    /**
     * List Google Calendar events
     * @param {Object} options - Calendar options
     * @returns {Promise<Object>} Calendar events
     */
    async calendarListEvents(options = {}) {
        return this.executeToolCapability('google_tool', 'calendar_operations', 'list_events', options);
    }

    /**
     * Create Google Calendar event
     * @param {Object} eventData - Event data
     * @returns {Promise<Object>} Creation result
     */
    async calendarCreateEvent(eventData) {
        return this.executeToolCapability('google_tool', 'calendar_operations', 'create_event', eventData);
    }

    // ==================== DRIVE METHODS ====================

    /**
     * List Google Drive files
     * @param {Object} options - Drive options
     * @returns {Promise<Object>} Drive files
     */
    async driveListFiles(options = {}) {
        return this.executeToolCapability('google_tool', 'drive_operations', 'list_files', options);
    }

    /**
     * Upload file to Google Drive
     * @param {Object} fileData - File data
     * @returns {Promise<Object>} Upload result
     */
    async driveUploadFile(fileData) {
        return this.executeToolCapability('google_tool', 'drive_operations', 'upload_file', fileData);
    }

    // ==================== HELPER METHODS ====================

    /**
     * Handle tool execution with loading state management
     * @param {Function} toolOperation - Async tool operation
     * @param {Function} setLoading - Loading state setter
     * @param {Function} onSuccess - Success callback
     * @param {Function} onError - Error callback
     */
    async executeWithLoadingState(toolOperation, setLoading, onSuccess, onError) {
        try {
            setLoading(true);
            const result = await toolOperation();
            
            if (result.success) {
                onSuccess(result);
            } else {
                onError(result.error || 'Unknown error');
            }
            
            return result;
        } catch (error) {
            onError(error.message);
            return { success: false, error: error.message };
        } finally {
            setLoading(false);
        }
    }

    /**
     * Create a specialized client for a specific tool
     * @param {string} toolName - Tool name
     * @returns {Object} Specialized tool client
     */
    createToolClient(toolName) {
        const toolClient = this;
        
        return {
            execute(capability, action, parameters = {}) {
                return toolClient.executeToolCapability(toolName, capability, action, parameters);
            }
        };
    }
}

// Create singleton instance
const toolClient = new ToolClient();

export default toolClient;
export { ToolClient };