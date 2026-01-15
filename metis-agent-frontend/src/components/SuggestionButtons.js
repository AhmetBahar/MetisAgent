// src/components/SuggestionButtons.js
import React, { useState, useEffect } from 'react';
import { Button, Card, Badge } from 'react-bootstrap';
import { 
  Zap, 
  Target, 
  Camera, 
  Hash, 
  Palette, 
  Users, 
  MessageSquare, 
  TrendingUp,
  Clock,
  CheckCircle,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import './SuggestionButtons.css';

/**
 * Akıllı öneri butonları - Persona durumuna göre dinamik öneriler
 */
function SuggestionButtons({ 
  personaId = 'assistant',
  currentContext = {},
  currentStep = 'briefing',
  collectedInfo = {},
  onSuggestionClick,
  onQuickFill,
  className = ''
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [showAll, setShowAll] = useState(false);
  
  // Persona türüne göre öneriler
  useEffect(() => {
    const newSuggestions = generateSuggestions(personaId, currentStep, collectedInfo, currentContext);
    setSuggestions(newSuggestions);
  }, [personaId, currentStep, collectedInfo, currentContext]);
  
  // Gösterilecek öneri sayısı
  const displaySuggestions = showAll ? suggestions : suggestions.slice(0, 4);
  
  if (suggestions.length === 0) {
    return null;
  }
  
  return (
    <Card className={`suggestion-buttons-container ${className}`}>
      <Card.Header className="suggestion-header">
        <div className="d-flex align-items-center justify-content-between">
          <div className="d-flex align-items-center">
            <Sparkles size={16} className="me-2 text-primary" />
            <span className="fw-bold">Akıllı Öneriler</span>
          </div>
          {suggestions.length > 4 && (
            <Button 
              variant="link" 
              size="sm"
              onClick={() => setShowAll(!showAll)}
              className="show-more-btn"
            >
              {showAll ? 'Daha az' : `+${suggestions.length - 4} daha`}
            </Button>
          )}
        </div>
      </Card.Header>
      <Card.Body className="suggestion-body">
        <div className="suggestions-grid">
          {displaySuggestions.map((suggestion, index) => (
            <SuggestionButton
              key={suggestion.id || index}
              suggestion={suggestion}
              onClick={onSuggestionClick}
              onQuickFill={onQuickFill}
              delay={index * 100} // Staggered animation
            />
          ))}
        </div>
        
        {/* Progress Indicator */}
        {personaId === 'social-media' && (
          <ProgressIndicator 
            currentStep={currentStep} 
            collectedInfo={collectedInfo}
          />
        )}
      </Card.Body>
    </Card>
  );
}

/**
 * Tek bir öneri butonu
 */
function SuggestionButton({ suggestion, onClick, onQuickFill, delay = 0 }) {
  const [isAnimating, setIsAnimating] = useState(false);
  
  const handleClick = () => {
    setIsAnimating(true);
    setTimeout(() => setIsAnimating(false), 300);
    
    if (suggestion.quickFill && onQuickFill) {
      onQuickFill(suggestion.quickFill);
    } else if (onClick) {
      onClick(suggestion);
    }
  };
  
  return (
    <Button
      variant={suggestion.variant || 'outline-primary'}
      className={`suggestion-button ${isAnimating ? 'animating' : ''}`}
      onClick={handleClick}
      style={{ animationDelay: `${delay}ms` }}
      title={suggestion.description}
    >
      <div className="suggestion-content">
        {suggestion.icon && (
          <suggestion.icon size={16} className="suggestion-icon" />
        )}
        <span className="suggestion-text">{suggestion.text}</span>
        {suggestion.badge && (
          <Badge bg="secondary" className="suggestion-badge">
            {suggestion.badge}
          </Badge>
        )}
      </div>
      {suggestion.quickFill && (
        <div className="quick-fill-indicator">
          <Zap size={12} />
        </div>
      )}
    </Button>
  );
}

/**
 * İlerleme göstergesi
 */
function ProgressIndicator({ currentStep, collectedInfo }) {
  const steps = ['briefing', 'creative_idea', 'post_content', 'sharing_content', 'final_review'];
  const currentIndex = steps.indexOf(currentStep);
  const progress = ((currentIndex + 1) / steps.length) * 100;
  const infoCount = Object.keys(collectedInfo).length;
  
  return (
    <div className="progress-indicator mt-3">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <small className="text-muted">İlerleme Durumu</small>
        <small className="text-primary fw-bold">{Math.round(progress)}%</small>
      </div>
      <div className="progress-track">
        <div 
          className="progress-fill" 
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="d-flex justify-content-between mt-1">
        <small className="text-muted">{infoCount} bilgi toplandı</small>
        <small className="text-success">
          <CheckCircle size={12} className="me-1" />
          {steps[currentIndex]?.replace('_', ' ')}
        </small>
      </div>
    </div>
  );
}

// Öneri üretme fonksiyonu
function generateSuggestions(personaId, currentStep, collectedInfo, context) {
  const suggestions = [];
  
  if (personaId === 'social-media') {
    // Sosyal medya persona önerileri
    if (currentStep === 'briefing') {
      suggestions.push(
        {
          id: 'instagram-post',
          text: 'Instagram Postu',
          icon: Camera,
          variant: 'primary',
          description: 'Instagram için görsel post oluştur',
          quickFill: { platform: 'Instagram', post_type: 'image' }
        },
        {
          id: 'linkedin-article',
          text: 'LinkedIn Makalesi',
          icon: MessageSquare,
          variant: 'outline-primary',
          description: 'Profesyonel LinkedIn içeriği',
          quickFill: { platform: 'LinkedIn', post_type: 'article', tone: 'professional' }
        },
        {
          id: 'twitter-thread',
          text: 'Twitter Thread',
          icon: TrendingUp,
          variant: 'outline-info',
          description: 'Viral Twitter thread dizisi',
          quickFill: { platform: 'Twitter', post_type: 'thread', tone: 'engaging' }
        }
      );
      
      if (!collectedInfo.target_audience) {
        suggestions.push({
          id: 'audience-young',
          text: 'Genç Kitle (18-25)',
          icon: Users,
          variant: 'outline-success',
          description: 'Genç yetişkinlere yönelik içerik',
          quickFill: { target_audience: 'Genç yetişkinler (18-25 yaş)' }
        });
      }
    }
    
    if (currentStep === 'creative_idea') {
      suggestions.push(
        {
          id: 'trend-content',
          text: 'Trend İçerik',
          icon: TrendingUp,
          variant: 'warning',
          description: 'Popüler trendlere dayalı içerik',
          badge: 'Viral'
        },
        {
          id: 'educational',
          text: 'Eğitici İçerik',
          icon: Target,
          variant: 'outline-info',
          description: 'Bilgilendirici ve öğretici post'
        },
        {
          id: 'behind-scenes',
          text: 'Sahne Arkası',
          icon: Camera,
          variant: 'outline-secondary',
          description: 'Şirket/marka arkası görüntüleri'
        }
      );
    }
    
    if (currentStep === 'post_content') {
      suggestions.push(
        {
          id: 'generate-caption',
          text: 'Caption Oluştur',
          icon: MessageSquare,
          variant: 'success',
          description: 'AI ile caption üret'
        },
        {
          id: 'add-emojis',
          text: 'Emoji Ekle',
          icon: Palette,
          variant: 'outline-warning',
          description: 'Uygun emojiler ekle'
        }
      );
    }
    
    if (currentStep === 'sharing_content') {
      suggestions.push(
        {
          id: 'hashtag-generator',
          text: 'Hashtag Üret',
          icon: Hash,
          variant: 'info',
          description: 'Viral hashtag önerileri'
        },
        {
          id: 'best-time',
          text: 'En İyi Saat',
          icon: Clock,
          variant: 'outline-success',
          description: 'Optimal paylaşım zamanı'
        }
      );
    }
    
    // Her zaman mevcut öneriler
    suggestions.push(
      {
        id: 'preview-post',
        text: 'Post Önizleme',
        icon: CheckCircle,
        variant: 'outline-primary',
        description: 'Şu anki post durumunu görüntüle'
      }
    );
    
    // Eksik bilgilere göre öneriler
    if (!collectedInfo.platform) {
      suggestions.unshift({
        id: 'select-platform',
        text: 'Platform Seç',
        icon: Target,
        variant: 'primary',
        description: 'Hangi platform için içerik üretileceğini belirle',
        badge: 'Gerekli'
      });
    }
    
    if (!collectedInfo.tone) {
      suggestions.push({
        id: 'set-tone',
        text: 'Ton Belirle',
        icon: Palette,
        variant: 'outline-warning',
        description: 'İçeriğin tonunu seç (profesyonel, samimi, eğlenceli...)'
      });
    }
    
  } else {
    // Genel persona önerileri
    suggestions.push(
      {
        id: 'help',
        text: 'Yardım',
        icon: Target,
        variant: 'outline-info',
        description: 'Nasıl başlayacağınızı öğrenin'
      },
      {
        id: 'examples',
        text: 'Örnekler',
        icon: Sparkles,
        variant: 'outline-secondary',
        description: 'Örnek görevleri görün'
      }
    );
  }
  
  return suggestions;
}

export default SuggestionButtons;