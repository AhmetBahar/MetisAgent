"""
Playwright Browser Tool - Modern web automation
"""

import asyncio
import time
import os
import logging
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult

from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class PlaywrightGeminiScraper(MCPTool):
    """Modern Gemini scraper using Playwright"""
    
    def __init__(self):
        super().__init__(
            name="playwright_gemini_scraper",
            description="Modern Gemini image scraping with Playwright",
            version="1.0.0"
        )
        self._register_actions()
    
    def _register_actions(self):
        """Register MCP actions"""
        self.register_action(
            "scrape_gemini_image",
            self.scrape_gemini_image,
            required_params=["prompt"],
            optional_params=["save_path", "headless"]
        )
    
    async def _scrape_async(self, prompt: str, save_path: str = None, headless: bool = True) -> Dict:
        """Async Gemini scraping logic"""
        async with async_playwright() as p:
            # Launch browser - WSL2 fix
            browser = await p.chromium.launch(
                headless=headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--single-process'
                ],
                timeout=30000
            )
            
            try:
                page = await browser.new_page()
                
                # Navigate to Gemini with extended timeout
                await page.goto("https://gemini.google.com", wait_until="domcontentloaded", timeout=60000)
                logger.info("Gemini sayfası yüklendi")
                
                # Wait for the page to fully load
                await page.wait_for_timeout(3000)
                
                # Check if login is required
                try:
                    # Look for sign-in button or login indicators
                    login_selectors = [
                        'button[data-test-id*="sign-in"]',
                        'a[href*="accounts.google.com"]',
                        'button:has-text("Sign in")',
                        'a:has-text("Sign in")',
                        '[aria-label*="Sign in"]'
                    ]
                    
                    login_needed = False
                    for selector in login_selectors:
                        try:
                            login_element = await page.wait_for_selector(selector, timeout=2000)
                            if login_element:
                                login_needed = True
                                logger.warning(f"Login gerekli - bulunan element: {selector}")
                                break
                        except:
                            continue
                    
                    if login_needed:
                        logger.info("Login gerekli - otomatik login başlatılıyor...")
                        
                        # Otomatik login denemesi
                        login_success = await self._perform_google_login(page)
                        if not login_success:
                            return {"success": False, "error": "Google login başarısız. Lütfen OAuth2 credentials'ınızı kontrol edin."}
                        
                        logger.info("Otomatik login başarılı!")
                        # Login sonrası sayfanın yüklenmesini bekle
                        await page.wait_for_timeout(3000)
                    
                except Exception as e:
                    logger.debug(f"Login kontrolü hatası: {str(e)}")
                    # Login kontrolü başarısız olsa bile devam et
                
                # Find and fill text input
                text_selectors = [
                    "textarea[placeholder*='Gemini']",
                    "textarea[placeholder*='Enter a prompt']", 
                    "textarea[placeholder*='Ask Gemini']",
                    "textarea[aria-label*='prompt']",
                    "textarea[data-test-id*='prompt']",
                    "[role='textbox']",
                    "textarea",
                    ".ql-editor"
                ]
                
                input_filled = False
                for selector in text_selectors:
                    try:
                        text_input = await page.wait_for_selector(selector, timeout=10000)
                        if text_input:
                            image_prompt = f"'{prompt}' görseli oluştur. Renkli, detaylı ve güzel bir görsel olsun."
                            await text_input.fill(image_prompt)
                            logger.info(f"Prompt yazıldı: {selector}")
                            
                            # Enter tuşuna bas veya send butonunu ara
                            try:
                                await text_input.press('Enter')
                                logger.info("Enter tuşu ile gönderildi")
                            except:
                                # Enter çalışmazsa send butonunu ara
                                send_selectors = [
                                    'button[aria-label*="Send"]',
                                    'button[aria-label*="Gönder"]',
                                    'button:has-text("Send")',
                                    'button[data-test-id*="send"]',
                                    '[role="button"][aria-label*="Send"]'
                                ]
                                
                                sent = False
                                for send_sel in send_selectors:
                                    try:
                                        send_btn = await page.wait_for_selector(send_sel, timeout=3000)
                                        if send_btn:
                                            await send_btn.click()
                                            logger.info(f"Send butonu ile gönderildi: {send_sel}")
                                            sent = True
                                            break
                                    except:
                                        continue
                                
                                if not sent:
                                    logger.warning("Send butonu bulunamadı, Enter ile devam ediliyor")
                            
                            input_filled = True
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {str(e)}")
                        continue
                
                if not input_filled:
                    return {"success": False, "error": "Input alanı bulunamadı ve prompt gönderilemedi"}
                
                # Wait for response with better detection
                logger.info("Gemini yanıtını bekliyorum...")
                
                # Wait for response indicators
                response_detected = False
                max_wait_cycles = 30  # 30 * 2 = 60 saniye max
                
                for cycle in range(max_wait_cycles):
                    await page.wait_for_timeout(2000)  # 2 saniye bekle
                    
                    # Yanıt geldi mi kontrol et
                    response_indicators = [
                        'div[data-test-id*="response"]',
                        'div[role="response"]',
                        'div[class*="response"]',
                        'div[class*="message"]',
                        'div[data-test-id*="conversation"]'
                    ]
                    
                    for indicator in response_indicators:
                        try:
                            response_element = await page.query_selector(indicator)
                            if response_element:
                                response_detected = True
                                logger.info(f"Yanıt algılandı: {indicator} (döngü {cycle+1})")
                                break
                        except:
                            continue
                    
                    if response_detected:
                        break
                    
                    # İmaj elementi kontrolü
                    current_images = await page.query_selector_all("img")
                    if len(current_images) > 3:  # Login öncesi sayısından fazla
                        logger.info(f"Yeni görsel algılandı: {len(current_images)} img elementi")
                        response_detected = True
                        break
                    
                    logger.debug(f"Yanıt bekleniyor... döngü {cycle+1}/{max_wait_cycles}, img sayısı: {len(current_images)}")
                
                if not response_detected:
                    logger.warning("Gemini yanıtı tespit edilemedi, screenshot alınacak")
                
                # Final image check
                images = await page.query_selector_all("img")
                image_found = len(images) > 3  # Login sayfasından daha fazla görsel varsa
                
                logger.info(f"Toplam {len(images)} adet img elementi bulundu, görsel oluşturuldu: {image_found}")
                
                # Take screenshot
                if save_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_prompt = "".join(c for c in prompt[:20] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    save_path = f"generated_images/gemini_pw_{timestamp}_{safe_prompt}.png"
                
                os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else "generated_images", exist_ok=True)
                
                await page.screenshot(path=save_path, full_page=False)
                
                # Encode to base64
                with open(save_path, "rb") as img_file:
                    base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                
                logger.info(f"Screenshot kaydedildi: {save_path}")
                
                return {
                    "success": True,
                    "data": {
                        "message": f"'{prompt}' görseli için Gemini sayfası kaydedildi",
                        "image_path": save_path,
                        "base64_image": base64_image,
                        "prompt": prompt,
                        "method": "playwright_scraping",
                        "provider": "gemini_playwright",
                        "image_found": image_found,
                        "created_at": datetime.now().isoformat()
                    }
                }
                
            finally:
                await browser.close()
    
    async def _perform_google_login(self, page) -> bool:
        """Adım adım debug Google login işlemi"""
        try:
            # ChromaDB'den kullanıcı bilgilerini al
            from ..internal.user_storage import get_user_storage
            from app.auth_manager import auth_manager
            
            logger.info("🔍 ADIM 1: ChromaDB'den Google credentials alınıyor...")
            
            # Bilinen kullanıcıyı bul
            user_email = None
            user_password = None
            
            # Get current user from context instead of hardcoded
            from config.user_context import get_current_user_context
            user_context = get_current_user_context()
            
            known_user = None
            if user_context:
                # Try to get user by context user_id
                known_user = auth_manager.get_user_by_email(user_context.user_id)
            
            if not known_user:
                # Fallback: try to find any authenticated user
                # This is still not ideal but better than hardcoded
                logger.warning("No user context available for Gemini login. Browser automation may fail.")
            if known_user:
                user_id = known_user["user_id"]
                google_creds = settings_manager.get_google_credentials(user_id)
                if google_creds:
                    user_email = google_creds.get('email')  # ahmetbahar.minor@gmail.com
                    user_password = google_creds.get('password')  # Şifreli olarak saklanmış
                    
                    # Password'u decrypt et (settings_manager pattern)
                    if user_password:
                        try:
                            # Önce decrypt dene
                            if len(user_password) > 10:  # Encrypted olabilir
                                user_password = settings_manager._decrypt_data(user_password)
                                logger.info(f"✅ Password decrypt edildi")
                            else:
                                logger.info(f"✅ Password raw format kullanılıyor")
                        except Exception as e:
                            logger.warning(f"⚠️ Password decrypt hatası, raw format deneniyor: {e}")
                            # Raw password'u kullan
                    
                    logger.info(f"✅ ADIM 1 BAŞARILI: {user_id} -> {user_email}")
            
            if not user_email:
                logger.error("❌ ADIM 1 BAŞARISIZ: Google credentials bulunamadı")
                return False
            
            # 2. Gemini.google.com'a git
            logger.info("🔍 ADIM 2: gemini.google.com adresine gidiliyor...")
            current_url = page.url
            logger.info(f"Mevcut URL: {current_url}")
            
            if "gemini.google.com" not in current_url:
                await page.goto("https://gemini.google.com", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                logger.info("✅ ADIM 2 BAŞARILI: Gemini sayfasına gidildi")
            
            # 3. "Oturum açın" butonunu bul ve tıkla
            logger.info("🔍 ADIM 3: 'Oturum açın' butonunu arıyor...")
            sign_in_selectors = [
                'button:has-text("Oturum açın")',
                'button:has-text("Sign in")',
                'a:has-text("Oturum açın")',
                'a:has-text("Sign in")',
                'a[href*="accounts.google.com"]',
                '[aria-label*="Sign in"]',
                '[aria-label*="Oturum"]'
            ]
            
            clicked = False
            for selector in sign_in_selectors:
                try:
                    sign_in_btn = await page.wait_for_selector(selector, timeout=3000)
                    if sign_in_btn:
                        btn_text = await sign_in_btn.text_content()
                        logger.info(f"Buton bulundu: '{btn_text}' ({selector})")
                        await sign_in_btn.click()
                        clicked = True
                        logger.info(f"✅ ADIM 3 BAŞARILI: Oturum açın butonuna tıklandı")
                        break
                except Exception as e:
                    logger.debug(f"Selector denendi: {selector} - {e}")
                    continue
            
            if not clicked:
                logger.warning("⚠️ ADIM 3: Oturum açın butonu bulunamadı, direkt accounts'a gidiliyor")
                await page.goto("https://accounts.google.com/signin/v2/identifier?continue=https://gemini.google.com", wait_until="domcontentloaded")
            
            # Google login sayfasını bekle - daha uzun süre
            await page.wait_for_timeout(5000)
            current_url = page.url
            logger.info(f"Login sayfası URL: {current_url}")
            
            # Sayfanın tam yüklenmesini bekle
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
                logger.info("✅ Sayfa network idle durumuna geldi")
            except:
                logger.warning("⚠️ Network idle timeout, devam ediliyor")
            
            # 4. "E-posta veya telefon" text alanına email yaz
            logger.info(f"🔍 ADIM 4: E-posta alanına {user_email} yazılıyor...")
            
            # Önce sayfadaki tüm input'ları listele
            all_inputs = await page.query_selector_all('input')
            logger.info(f"Sayfada toplam {len(all_inputs)} input bulundu")
            
            for i, inp in enumerate(all_inputs):
                input_type = await inp.get_attribute('type')
                input_name = await inp.get_attribute('name')
                input_id = await inp.get_attribute('id')
                input_placeholder = await inp.get_attribute('placeholder')
                input_aria = await inp.get_attribute('aria-label')
                logger.info(f"Input {i+1}: type='{input_type}', name='{input_name}', id='{input_id}', placeholder='{input_placeholder}', aria='{input_aria}'")
            
            email_selectors = [
                'input[type="email"]',
                'input[name="identifier"]',
                'input[id="identifierId"]',
                'input[aria-label*="email"]',
                'input[aria-label*="E-posta"]',
                'input[autocomplete="username"]',
                'input[placeholder*="email"]',
                'input[type="text"]',  # Text input da olabilir
                'input'  # Herhangi bir input
            ]
            
            email_filled = False
            for selector in email_selectors:
                try:
                    email_input = await page.wait_for_selector(selector, timeout=5000)
                    if email_input:
                        placeholder = await email_input.get_attribute('placeholder')
                        aria_label = await email_input.get_attribute('aria-label')
                        logger.info(f"Email input bulundu - placeholder: '{placeholder}', aria-label: '{aria_label}'")
                        
                        await email_input.clear()
                        await email_input.fill(user_email)
                        await page.wait_for_timeout(1000)
                        
                        logger.info(f"✅ ADIM 4 BAŞARILI: Email girildi")
                        email_filled = True
                        break
                except Exception as e:
                    logger.debug(f"Email selector denendi: {selector} - {e}")
                    continue
            
            if not email_filled:
                logger.error("❌ ADIM 4 BAŞARISIZ: Email input alanı bulunamadı")
                return False
            
            # 5. "Sonraki" butonuna bas
            logger.info("🔍 ADIM 5: 'Sonraki' butonuna basılıyor...")
            next_selectors = [
                'button:has-text("Sonraki")',
                'button:has-text("Next")',
                'button[id="identifierNext"]',
                'button[type="submit"]',
                '[data-continue-text]',
                'button[jsname]'
            ]
            
            next_clicked = False
            for selector in next_selectors:
                try:
                    next_btn = await page.wait_for_selector(selector, timeout=3000)
                    if next_btn:
                        btn_text = await next_btn.text_content()
                        logger.info(f"Sonraki buton bulundu: '{btn_text}' ({selector})")
                        await next_btn.click()
                        next_clicked = True
                        logger.info(f"✅ ADIM 5 BAŞARILI: Sonraki butonuna tıklandı")
                        break
                except Exception as e:
                    logger.debug(f"Next selector denendi: {selector} - {e}")
                    continue
            
            if not next_clicked:
                logger.warning("⚠️ ADIM 5: Sonraki butonu bulunamadı, Enter deneniyor...")
                # Email input'a Enter bas
                try:
                    email_input = await page.query_selector('input[name="identifier"]')
                    if email_input:
                        await email_input.press('Enter')
                        logger.info("✅ ADIM 5 (Alternatif): Enter ile devam edildi")
                except:
                    logger.error("❌ ADIM 5 BAŞARISIZ: Sonraki adımına geçilemedi")
                    return False
            
            # 6. Password sayfasını bekle
            logger.info("🔍 ADIM 6: Şifre sayfası bekleniyor...")
            await page.wait_for_timeout(4000)
            current_url = page.url
            logger.info(f"Password sayfası URL: {current_url}")
            
            # 7. "Şifrenizi girin" alanına decrypt edilmiş şifreyi yaz
            if user_password:
                logger.info("🔍 ADIM 7: Şifre giriliyor...")
                password_selectors = [
                    'input[type="password"]',
                    'input[name="password"]',
                    'input[aria-label*="password"]',
                    'input[aria-label*="Şifre"]',
                    'input[autocomplete="current-password"]',
                    'input[placeholder*="password"]',
                    'input[placeholder*="şifre"]'
                ]
                
                password_filled = False
                for selector in password_selectors:
                    try:
                        password_input = await page.wait_for_selector(selector, timeout=8000)
                        if password_input:
                            placeholder = await password_input.get_attribute('placeholder')
                            aria_label = await password_input.get_attribute('aria-label')
                            logger.info(f"Password input bulundu - placeholder: '{placeholder}', aria-label: '{aria_label}'")
                            
                            await password_input.clear()
                            await password_input.fill(user_password)
                            await page.wait_for_timeout(1000)
                            
                            logger.info("✅ ADIM 7 BAŞARILI: Şifre girildi")
                            password_filled = True
                            break
                    except Exception as e:
                        logger.debug(f"Password selector denendi: {selector} - {e}")
                        continue
                
                if not password_filled:
                    logger.warning("⚠️ ADIM 7: Şifre input alanı bulunamadı")
                else:
                    # 8. Password "Sonraki" butonuna bas
                    logger.info("🔍 ADIM 8: Password Sonraki butonuna basılıyor...")
                    password_next_selectors = [
                        'button:has-text("Sonraki")',
                        'button:has-text("Next")',
                        'button[id="passwordNext"]',
                        'button[type="submit"]'
                    ]
                    
                    password_next_clicked = False
                    for selector in password_next_selectors:
                        try:
                            pwd_next_btn = await page.wait_for_selector(selector, timeout=3000)
                            if pwd_next_btn:
                                btn_text = await pwd_next_btn.text_content()
                                logger.info(f"Password Sonraki buton bulundu: '{btn_text}'")
                                await pwd_next_btn.click()
                                password_next_clicked = True
                                logger.info(f"✅ ADIM 8 BAŞARILI: Password Sonraki butonuna tıklandı")
                                break
                        except Exception as e:
                            logger.debug(f"Password next selector denendi: {selector} - {e}")
                            continue
                    
                    if not password_next_clicked:
                        # Enter dene
                        try:
                            await password_input.press('Enter')
                            logger.info("✅ ADIM 8 (Alternatif): Enter ile devam edildi")
                        except:
                            logger.warning("⚠️ ADIM 8: Password Sonraki butonuna basılamadı")
            else:
                logger.warning("⚠️ ADIM 7: Password kayıtlı değil")
            
            # 9. 2FA/Login sonucunu bekle
            logger.info("🔍 ADIM 9: 2FA/Login sonucu bekleniyor...")
            await page.wait_for_timeout(6000)
            current_url = page.url
            logger.info(f"Final URL: {current_url}")
            
            # Sayfa içeriğini kontrol et
            page_title = await page.title()
            logger.info(f"Sayfa başlığı: {page_title}")
            
            # 10. Başarılı login kontrolü
            if "gemini.google.com" in current_url and "accounts.google.com" not in current_url:
                logger.info("🎉 ADIM 10: Login başarılı - Gemini ana sayfasındayız!")
                
                # Selamlama yazısını ara
                welcome_selectors = [
                    ':has-text("Merhaba")',
                    ':has-text("Hello")',
                    ':has-text("Welcome")',
                    ':has-text("Hoş geldin")',
                    '[data-test-id*="welcome"]'
                ]
                
                for selector in welcome_selectors:
                    try:
                        welcome_element = await page.wait_for_selector(selector, timeout=3000)
                        if welcome_element:
                            welcome_text = await welcome_element.text_content()
                            logger.info(f"🎊 Selamlama bulundu: '{welcome_text}'")
                            break
                    except:
                        continue
                
                return True
            elif "accounts.google.com" in current_url:
                logger.warning("⚠️ ADIM 10: Hala Google accounts sayfasında - 2FA gerekebilir")
                
                # 2FA alanını ara
                two_fa_selectors = [
                    'input[type="tel"]',
                    'input[aria-label*="doğrulama"]',
                    'input[placeholder*="kod"]',
                    ':has-text("2 Adımlı")',
                    ':has-text("verification")'
                ]
                
                for selector in two_fa_selectors:
                    try:
                        two_fa_element = await page.wait_for_selector(selector, timeout=2000)
                        if two_fa_element:
                            logger.info(f"🔐 2FA alanı bulundu: {selector}")
                            break
                    except:
                        continue
                
                return False
            else:
                logger.info("⚠️ ADIM 10: Login durumu belirsiz ama devam ediliyor...")
                return True
                
        except Exception as e:
            logger.error(f"❌ Google login hatası: {str(e)}")
            return False
    
    async def _fallback_google_login(self, page) -> bool:
        """Gmail helper pattern ile dinamik kullanıcı bulma ve login"""
        try:
            from ..internal.user_storage import get_user_storage
            from app.auth_manager import auth_manager
            
            logger.info("Gmail helper pattern ile kullanıcı aranıyor...")
            
            # Gmail helper'daki mantığı kopyala
            user_email = None
            user_id = None
            
            # Get current user from context
            from config.user_context import get_current_user_context
            user_context = get_current_user_context()
            
            known_user = None
            if user_context:
                known_user = auth_manager.get_user_by_email(user_context.user_id)
            if known_user:
                user_id = known_user["user_id"]
                google_creds = settings_manager.get_google_credentials(user_id)
                if google_creds and google_creds.get('email'):
                    user_email = google_creds['email']
                    logger.info(f"Kullanıcı bulundu: {user_id} -> {user_email}")
            
            if not user_email:
                # Test user kontrol et
                test_user = auth_manager.get_user("test_user")
                if test_user:
                    user_id = test_user["user_id"]
                    google_creds = settings_manager.get_google_credentials(user_id)
                    if google_creds and google_creds.get('email'):
                        user_email = google_creds['email']
                        logger.info(f"Test user bulundu: {user_id} -> {user_email}")
            
            if not user_email:
                logger.error("Hiç Google credentials'ı olan kullanıcı bulunamadı")
                return False
            
            # Bu email ile manual login yap
            logger.info(f"Manual login başlatılıyor: {user_email}")
            return await self._manual_google_login(page, user_email)
            
        except Exception as e:
            logger.error(f"Fallback login hatası: {str(e)}")
            return False
    
    async def _manual_google_login(self, page, email: str) -> bool:
        """Email ile manual Google login"""
        try:
            # Fallback: Manual login flow
            logger.info(f"Manual Google login: {email}")
            
            # Sign in butonuna tıkla
            sign_in_selectors = [
                'button:has-text("Sign in")',
                'a:has-text("Sign in")',
                'a[href*="accounts.google.com"]',
                '[data-test-id*="sign-in"]'
            ]
            
            clicked = False
            for selector in sign_in_selectors:
                try:
                    sign_in_btn = await page.wait_for_selector(selector, timeout=3000)
                    if sign_in_btn:
                        await sign_in_btn.click()
                        clicked = True
                        logger.info(f"Sign in butonuna tıklandı: {selector}")
                        break
                except:
                    continue
            
            if not clicked:
                logger.warning("Sign in butonu bulunamadı")
                return False
            
            # Google login sayfasını bekle
            await page.wait_for_timeout(3000)
            
            # Email input alanını bul ve doldur
            email_selectors = [
                'input[type="email"]',
                'input[name="identifier"]',
                'input[id="identifierId"]',
                'input[aria-label*="email"]'
            ]
            
            email_filled = False
            for selector in email_selectors:
                try:
                    email_input = await page.wait_for_selector(selector, timeout=5000)
                    if email_input:
                        await email_input.fill(email)
                        await email_input.press('Enter')
                        email_filled = True
                        logger.info(f"Email girildi: {selector}")
                        break
                except:
                    continue
            
            if not email_filled:
                logger.error("Email input alanı bulunamadı")
                return False
            
            # Login başarısını bekle - URL değişikliği veya Gemini ana sayfası
            await page.wait_for_timeout(5000)
            
            # Başarılı login kontrolü
            current_url = page.url
            if "gemini.google.com" in current_url and "accounts.google.com" not in current_url:
                logger.info("Manual login başarılı - Gemini ana sayfasındayız")
                return True
            else:
                logger.warning(f"Login durumu belirsiz, mevcut URL: {current_url}")
                # Password gerekebilir ya da 2FA, ama devam et
                return True
                
        except Exception as e:
            logger.error(f"Manual login hatası: {str(e)}")
            return False
    
    def scrape_gemini_image(self, prompt: str, save_path: str = None, headless: bool = True) -> MCPToolResult:
        """Sync wrapper for async scraping"""
        try:
            # Check if there's already a running loop
            try:
                loop = asyncio.get_running_loop()
                # If there's already a loop, create a new thread
                import threading
                import concurrent.futures
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            self._scrape_async(prompt, save_path, headless)
                        )
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    result = future.result(timeout=120)  # 2 minute timeout
                    
            except RuntimeError:
                # No loop running, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self._scrape_async(prompt, save_path, headless)
                )
                
                loop.close()
            
            if result["success"]:
                return MCPToolResult(success=True, data=result["data"])
            else:
                return MCPToolResult(success=False, error=result["error"])
                
        except Exception as e:
            logger.error(f"Playwright Gemini scraping hatası: {str(e)}")
            return MCPToolResult(success=False, error=f"Playwright scraping hatası: {str(e)}")


# Global tool instance
playwright_gemini_scraper = PlaywrightGeminiScraper()


def register_tool(registry):
    """Register with registry"""
    try:
        registry.register_tool(playwright_gemini_scraper)
        return True
    except Exception as e:
        print(f"Failed to register Playwright Gemini scraper: {str(e)}")
        return False


async def main():
    """Test function"""
    import sys
    
    test_prompt = sys.argv[1] if len(sys.argv) > 1 else "beautiful mountain sunset"
    
    tool = PlaywrightGeminiScraper()
    result = tool.scrape_gemini_image(test_prompt)
    
    print(f"Success: {result.success}")
    if result.success:
        print(f"Image saved: {result.data.get('image_path')}")
        print(f"Base64 length: {len(result.data.get('base64_image', ''))}")
    else:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())