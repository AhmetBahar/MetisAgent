// src/components/NotificationSystem.js
import React, { useState, useEffect, useRef } from 'react';
import { Toast, ToastContainer } from 'react-bootstrap';
import { 
  CheckCircle, 
  AlertCircle, 
  Info, 
  X, 
  Zap, 
  Users, 
  MessageSquare,
  TrendingUp,
  Clock,
  Bell
} from 'lucide-react';
import './NotificationSystem.css';

/**
 * Gerçek zamanlı bildirim sistemi
 * - Toast bildirimleri
 * - Workflow güncellemeleri
 * - Persona durumu
 * - Sistem bildirimleri
 */
class NotificationManager {
  constructor() {
    this.listeners = [];
    this.notifications = [];
    this.maxNotifications = 5;
  }
  
  addListener(callback) {
    this.listeners.push(callback);
  }
  
  removeListener(callback) {
    this.listeners = this.listeners.filter(l => l !== callback);
  }
  
  notify(notification) {
    const id = Date.now() + Math.random();
    const newNotification = {
      id,
      timestamp: new Date(),
      ...notification
    };
    
    this.notifications.unshift(newNotification);
    
    // Maksimum sayıyı aş
    if (this.notifications.length > this.maxNotifications) {
      this.notifications = this.notifications.slice(0, this.maxNotifications);
    }
    
    // Listener'ları bilgilendir
    this.listeners.forEach(callback => callback(this.notifications));
    
    return id;
  }
  
  remove(id) {
    this.notifications = this.notifications.filter(n => n.id !== id);
    this.listeners.forEach(callback => callback(this.notifications));
  }
  
  clear() {
    this.notifications = [];
    this.listeners.forEach(callback => callback(this.notifications));
  }
  
  // Önceden tanımlı bildirim türleri
  success(title, message, options = {}) {
    return this.notify({
      type: 'success',
      title,
      message,
      icon: CheckCircle,
      autoHide: true,
      duration: 4000,
      ...options
    });
  }
  
  error(title, message, options = {}) {
    return this.notify({
      type: 'error',
      title,
      message,
      icon: AlertCircle,
      autoHide: true,
      duration: 6000,
      ...options
    });
  }
  
  info(title, message, options = {}) {
    return this.notify({
      type: 'info',
      title,
      message,
      icon: Info,
      autoHide: true,
      duration: 4000,
      ...options
    });
  }
  
  workflow(title, message, options = {}) {
    return this.notify({
      type: 'workflow',
      title,
      message,
      icon: Zap,
      autoHide: true,
      duration: 5000,
      ...options
    });
  }
  
  persona(title, message, options = {}) {
    return this.notify({
      type: 'persona',
      title,
      message,
      icon: Users,
      autoHide: true,
      duration: 4000,
      ...options
    });
  }
}

// Global notification manager
export const notificationManager = new NotificationManager();

/**
 * Notification System Component
 */
function NotificationSystem({ position = 'top-end' }) {
  const [notifications, setNotifications] = useState([]);
  
  useEffect(() => {
    const handleNotifications = (newNotifications) => {
      setNotifications([...newNotifications]);
    };
    
    notificationManager.addListener(handleNotifications);
    
    return () => {
      notificationManager.removeListener(handleNotifications);
    };
  }, []);
  
  return (
    <ToastContainer position={position} className="notification-container">
      {notifications.map(notification => (
        <NotificationToast
          key={notification.id}
          notification={notification}
          onClose={() => notificationManager.remove(notification.id)}
        />
      ))}
    </ToastContainer>
  );
}

/**
 * Tek bir bildirim toast'ı
 */
function NotificationToast({ notification, onClose }) {
  const [show, setShow] = useState(true);
  const [progress, setProgress] = useState(100);
  const intervalRef = useRef(null);
  
  const { type, title, message, icon: Icon, autoHide, duration = 4000 } = notification;
  
  // Auto-hide timer
  useEffect(() => {
    if (autoHide && show) {
      const startTime = Date.now();
      
      intervalRef.current = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const remaining = Math.max(0, duration - elapsed);
        const progressPercent = (remaining / duration) * 100;
        
        setProgress(progressPercent);
        
        if (remaining <= 0) {
          setShow(false);
        }
      }, 50);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [autoHide, show, duration]);
  
  // Toast kapandığında callback'i çağır
  const handleClose = () => {
    setShow(false);
    setTimeout(onClose, 300); // Animation için gecikme
  };
  
  // Pause on hover
  const handleMouseEnter = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };
  
  const handleMouseLeave = () => {
    if (autoHide && show) {
      const remainingDuration = (progress / 100) * duration;
      const startTime = Date.now();
      
      intervalRef.current = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const remaining = Math.max(0, remainingDuration - elapsed);
        const progressPercent = (remaining / remainingDuration) * 100;
        
        setProgress(progressPercent);
        
        if (remaining <= 0) {
          setShow(false);
        }
      }, 50);
    }
  };
  
  return (
    <Toast
      show={show}
      onClose={handleClose}
      className={`notification-toast notification-${type}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <Toast.Header className="notification-header">
        <div className="notification-icon">
          {Icon && <Icon size={18} />}
        </div>
        <strong className="notification-title">{title}</strong>
        <button 
          type="button" 
          className="notification-close"
          onClick={handleClose}
        >
          <X size={14} />
        </button>
      </Toast.Header>
      
      {message && (
        <Toast.Body className="notification-body">
          {message}
        </Toast.Body>
      )}
      
      {autoHide && (
        <div className="notification-progress">
          <div 
            className="notification-progress-bar"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </Toast>
  );
}

/**
 * Workflow güncellemeleri için özel hook
 */
export function useWorkflowNotifications() {
  const notifyStepChange = (from, to, personaName = 'Persona') => {
    notificationManager.workflow(
      'İş Akışı Güncellendi',
      `${personaName} "${to}" adımına geçti`,
      {
        data: { from, to, personaName }
      }
    );
  };
  
  const notifyTaskComplete = (taskName, personaName = 'Persona') => {
    notificationManager.success(
      'Görev Tamamlandı',
      `${personaName} "${taskName}" görevini başarıyla tamamladı`,
      {
        data: { taskName, personaName }
      }
    );
  };
  
  const notifyInfoCollected = (fieldName, value) => {
    notificationManager.info(
      'Yeni Bilgi Eklendi',
      `${fieldName}: ${value}`,
      {
        icon: TrendingUp,
        duration: 3000
      }
    );
  };
  
  return {
    notifyStepChange,
    notifyTaskComplete,
    notifyInfoCollected
  };
}

/**
 * Persona durumu için özel hook
 */
export function usePersonaNotifications() {
  const notifyPersonaOnline = (personaName) => {
    notificationManager.persona(
      'Persona Aktif',
      `${personaName} artık online`,
      {
        icon: Users,
        duration: 3000
      }
    );
  };
  
  const notifyPersonaOffline = (personaName) => {
    notificationManager.persona(
      'Persona Çevrimdışı',
      `${personaName} çevrimdışı oldu`,
      {
        icon: Users,
        type: 'warning',
        duration: 3000
      }
    );
  };
  
  const notifyPersonaResponse = (personaName, responseType = 'message') => {
    notificationManager.info(
      'Yeni Yanıt',
      `${personaName} yanıt verdi`,
      {
        icon: MessageSquare,
        duration: 2000
      }
    );
  };
  
  return {
    notifyPersonaOnline,
    notifyPersonaOffline,
    notifyPersonaResponse
  };
}

/**
 * Sistem bildirimleri için özel hook
 */
export function useSystemNotifications() {
  const notifyConnection = (status) => {
    if (status === 'connected') {
      notificationManager.success(
        'Bağlantı Kuruldu',
        'Sunucuya başarıyla bağlandı',
        {
          duration: 2000
        }
      );
    } else if (status === 'disconnected') {
      notificationManager.error(
        'Bağlantı Kesildi',
        'Sunucu bağlantısı kesildi',
        {
          autoHide: false
        }
      );
    } else if (status === 'reconnecting') {
      notificationManager.info(
        'Yeniden Bağlanıyor',
        'Sunucuya yeniden bağlanıyor...',
        {
          icon: Clock,
          autoHide: false
        }
      );
    }
  };
  
  const notifyError = (title, message, options = {}) => {
    notificationManager.error(title, message, {
      duration: 8000,
      ...options
    });
  };
  
  const notifyUpdate = (version) => {
    notificationManager.info(
      'Güncelleme Mevcut',
      `Yeni versiyon (${version}) mevcut`,
      {
        autoHide: false,
        actions: [
          {
            label: 'Güncelle',
            action: () => window.location.reload()
          }
        ]
      }
    );
  };
  
  return {
    notifyConnection,
    notifyError,
    notifyUpdate
  };
}

export default NotificationSystem;