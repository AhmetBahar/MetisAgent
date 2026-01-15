/**
 * User Manager - Handles user identification and session management
 */

class UserManager {
  constructor() {
    this.userId = null;
    this.sessionId = null;
    this.sessionData = null;
    this.storageKey = 'metisagent2_user';
    
    // Initialize from localStorage
    this.loadFromStorage();
  }

  /**
   * Generate a unique user ID
   */
  generateUserId() {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substr(2, 5);
    return `user_${timestamp}_${random}`;
  }

  /**
   * Generate a display name for user
   */
  generateDisplayName() {
    const adjectives = ['Quick', 'Smart', 'Clever', 'Bright', 'Swift', 'Sharp', 'Wise', 'Bold'];
    const nouns = ['User', 'Agent', 'Mind', 'Brain', 'Thinker', 'Explorer', 'Helper', 'Assistant'];
    
    const adjective = adjectives[Math.floor(Math.random() * adjectives.length)];
    const noun = nouns[Math.floor(Math.random() * nouns.length)];
    const number = Math.floor(Math.random() * 1000);
    
    return `${adjective}${noun}${number}`;
  }

  /**
   * Load user data from localStorage
   */
  loadFromStorage() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        const userData = JSON.parse(stored);
        this.userId = userData.userId;
        this.sessionId = userData.sessionId;
        this.sessionData = userData.sessionData;
      }
    } catch (error) {
      console.error('Error loading user data from storage:', error);
      this.clearStorage();
    }
  }

  /**
   * Save user data to localStorage
   */
  saveToStorage() {
    try {
      const userData = {
        userId: this.userId,
        sessionId: this.sessionId,
        sessionData: this.sessionData,
        lastUpdated: new Date().toISOString()
      };
      localStorage.setItem(this.storageKey, JSON.stringify(userData));
    } catch (error) {
      console.error('Error saving user data to storage:', error);
    }
  }

  /**
   * Clear user data from storage
   */
  clearStorage() {
    try {
      localStorage.removeItem(this.storageKey);
      this.userId = null;
      this.sessionId = null;
      this.sessionData = null;
    } catch (error) {
      console.error('Error clearing user data from storage:', error);
    }
  }

  /**
   * Initialize user (create if doesn't exist)
   */
  async initializeUser(apiService) {
    try {
      if (!this.userId) {
        this.userId = this.generateUserId();
      }

      // Create new session
      const response = await apiService.createSession(this.userId);
      
      if (response.success) {
        this.sessionId = response.session.session_id;
        this.sessionData = {
          ...response.session,
          displayName: this.generateDisplayName(),
          isAnonymous: true
        };
        
        this.saveToStorage();
        return this.sessionData;
      } else {
        throw new Error('Failed to create session');
      }
    } catch (error) {
      console.error('Error initializing user:', error);
      // Fallback to anonymous session
      this.userId = this.generateUserId();
      this.sessionData = {
        user_id: this.userId,
        session_id: 'local_' + Date.now(),
        displayName: this.generateDisplayName(),
        isAnonymous: true,
        created_at: new Date().toISOString()
      };
      this.saveToStorage();
      return this.sessionData;
    }
  }

  /**
   * Get current user data for API calls
   */
  getUserData() {
    return {
      user_id: this.userId,
      session_id: this.sessionId
    };
  }

  /**
   * Get user display info
   */
  getDisplayInfo() {
    return {
      displayName: this.sessionData?.displayName || 'Anonymous User',
      userId: this.userId,
      sessionId: this.sessionId,
      isAnonymous: this.sessionData?.isAnonymous || true,
      createdAt: this.sessionData?.created_at
    };
  }

  /**
   * Update user display name
   */
  updateDisplayName(newName) {
    if (this.sessionData) {
      this.sessionData.displayName = newName;
      this.saveToStorage();
    }
  }

  /**
   * Start new session (keeping same user ID)
   */
  async startNewSession(apiService) {
    try {
      const response = await apiService.createSession(this.userId);
      
      if (response.success) {
        this.sessionId = response.session.session_id;
        this.sessionData = {
          ...response.session,
          displayName: this.sessionData?.displayName || this.generateDisplayName(),
          isAnonymous: true
        };
        
        this.saveToStorage();
        return this.sessionData;
      }
    } catch (error) {
      console.error('Error starting new session:', error);
    }
    return null;
  }

  /**
   * Reset user (clear everything and start fresh)
   */
  async resetUser(apiService) {
    // Delete current session if exists
    if (this.sessionId && apiService) {
      try {
        await apiService.deleteSession(this.sessionId);
      } catch (error) {
        console.error('Error deleting session:', error);
      }
    }

    this.clearStorage();
    return await this.initializeUser(apiService);
  }
}

// Export singleton instance
export const userManager = new UserManager();
export default userManager;