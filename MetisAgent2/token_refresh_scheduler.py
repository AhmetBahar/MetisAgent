#!/usr/bin/env python3
"""
OAuth Token Auto Refresh Scheduler
Bu script OAuth token'ları otomatik olarak yeniler
"""

import time
import logging
from datetime import datetime, timedelta
from tools.settings_manager import settings_manager
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenRefreshScheduler:
    """OAuth token'ları otomatik yenileyen scheduler"""
    
    def __init__(self):
        self.settings_manager = settings_manager
        
        # SECURITY: Load OAuth credentials from environment
        from config import config
        oauth_config = config.google_oauth
        self.google_client_id = oauth_config['client_id']
        self.google_client_secret = oauth_config['client_secret']
        
        if not self.google_client_id or not self.google_client_secret:
            logger.error("Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file")
            raise ValueError("Missing Google OAuth configuration")
        
    def refresh_google_token(self, user_id: str, oauth_token: dict) -> bool:
        """Google OAuth token'ını yeniler"""
        try:
            refresh_token = oauth_token.get('refresh_token')
            if not refresh_token:
                logger.warning(f"No refresh token for user {user_id}")
                return False
            
            # Google'dan yeni token al
            refresh_data = {
                'client_id': self.google_client_id,
                'client_secret': self.google_client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post('https://oauth2.googleapis.com/token', data=refresh_data)
            result = response.json()
            
            if response.status_code == 200 and 'access_token' in result:
                # Token'ı güncelle
                oauth_token['access_token'] = result['access_token']
                oauth_token['expires_at'] = (datetime.now() + timedelta(seconds=result.get('expires_in', 3600))).isoformat()
                oauth_token['refreshed_at'] = datetime.now().isoformat()
                
                # Yeni refresh token varsa güncelle
                if 'refresh_token' in result:
                    oauth_token['refresh_token'] = result['refresh_token']
                
                # Kaydet
                success = self.settings_manager.save_oauth_token(user_id, 'google', oauth_token)
                if success:
                    logger.info(f"✅ Token refreshed for user {user_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to save refreshed token for {user_id}")
                    return False
            else:
                logger.error(f"❌ Token refresh failed for {user_id}: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Token refresh exception for {user_id}: {e}")
            return False
    
    def check_and_refresh_tokens(self):
        """Tüm token'ları kontrol eder ve gerekirse yeniler"""
        logger.info("🔄 Checking tokens for refresh...")
        
        try:
            # ChromaDB'den tüm OAuth token'ları al
            result = self.settings_manager.collection.get()
            refreshed_count = 0
            
            for i, (doc_id, metadata) in enumerate(zip(result['ids'], result['metadatas'])):
                if metadata.get('type') == 'oauth_token' and 'google' in doc_id:
                    user_id = metadata.get('user_id', 'unknown')
                    
                    # Token'ı al
                    oauth_token = self.settings_manager.get_oauth_token(user_id, 'google')
                    if oauth_token:
                        # Expire kontrolü
                        expires_at_str = oauth_token.get('expires_at')
                        if expires_at_str:
                            try:
                                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                                now = datetime.now()
                                
                                # 10 dakika kala refresh et
                                if expires_at <= now + timedelta(minutes=10):
                                    logger.info(f"🔄 Refreshing token for {user_id} (expires: {expires_at})")
                                    if self.refresh_google_token(user_id, oauth_token):
                                        refreshed_count += 1
                                else:
                                    logger.debug(f"✅ Token OK for {user_id} (expires: {expires_at})")
                            except Exception as e:
                                logger.error(f"❌ Date parse error for {user_id}: {e}")
            
            if refreshed_count > 0:
                logger.info(f"✅ Refreshed {refreshed_count} tokens")
            else:
                logger.info("✅ No tokens needed refresh")
                
        except Exception as e:
            logger.error(f"❌ Token check error: {e}")
    
    def run_scheduler(self, interval_minutes: int = 30):
        """Scheduler'ı belirtilen aralıklarla çalıştırır"""
        logger.info(f"🚀 Token refresh scheduler started (interval: {interval_minutes} minutes)")
        
        while True:
            try:
                self.check_and_refresh_tokens()
                logger.info(f"💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("🛑 Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                time.sleep(60)  # 1 dakika bekle ve tekrar dene

def main():
    """Ana fonksiyon - scheduler'ı başlatır"""
    scheduler = TokenRefreshScheduler()
    
    # İlk kontrol
    scheduler.check_and_refresh_tokens()
    
    # Sürekli çalış (30 dakikada bir kontrol)
    scheduler.run_scheduler(interval_minutes=30)

if __name__ == "__main__":
    main()