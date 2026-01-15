"""
Simple Visual Creator Tool - Working implementation from SimpleAgent
Ported to MetisAgent2 MCP architecture
"""

import os
import requests
import logging
import base64
from typing import Dict, Any, List
from datetime import datetime
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor

# MetisAgent2 MCP core import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult
from ..internal.user_storage import get_user_storage

logger = logging.getLogger(__name__)

class SimpleVisualCreatorTool(MCPTool):
    """Simple but working visual creator using GPT-4o (gpt-image-1)"""
    
    def __init__(self):
        super().__init__(
            name="simple_visual_creator",
            description="Simple and reliable GPT-4o image generation using gpt-image-1 model",
            version="1.0.0",
            llm_description="AI-powered image and visual content generator using multiple providers (OpenAI DALL-E, HuggingFace, Gemini)",
            use_cases=[
                "Generate images from text descriptions",
                "Create visual content for social media",
                "Generate artwork, illustrations, and graphics",
                "Create images of animals, objects, scenes, people",
                "Generate logos, banners, and visual designs"
            ],
            keywords=[
                "görsel", "resim", "image", "picture", "visual", "photo", "grafik",
                "üret", "oluştur", "create", "generate", "yap", "çiz", "draw",
                "köpek", "kedi", "hayvan", "animal", "dog", "cat", "insan", "person",
                "manzara", "landscape", "logo", "banner", "tasarım", "design"
            ]
        )
        
        # Add capabilities
        self.add_capability("image_generation")
        self.add_capability("visual_content_creation") 
        self.add_capability("social_media_images")
        
        # Storage setup
        self.image_storage_path = os.path.join(os.getcwd(), "generated_images")
        if not os.path.exists(self.image_storage_path):
            os.makedirs(self.image_storage_path, exist_ok=True)
        
        # Memory integration
        self.graph_memory = None
        self._initialize_memory()
        
        # Register OpenAI-specific actions
        self.register_action(
            "generate_image_with_openai",
            self._generate_image_with_openai,
            required_params=["prompt"],
            optional_params=["size", "quality"]
        )
        
        self.register_action(
            "create_image_with_openai", 
            self._generate_image_with_openai,
            required_params=["prompt"],
            optional_params=["size", "quality"]
        )
        
        # Gemini API removed
        
        # Register free alternatives
        self.register_action(
            "generate_image_with_huggingface",
            self._generate_image_with_huggingface,
            required_params=["prompt"],
            optional_params=["model"]
        )
        
        # Register multi-provider actions
        self.register_action(
            "generate_image",
            self._generate_image_multi_provider,
            required_params=["prompt"],
            optional_params=["providers", "size", "quality"]
        )
        
        self.register_action(
            "create_image", 
            self._generate_image_multi_provider,
            required_params=["prompt"],
            optional_params=["providers", "size", "quality"]
        )
        
        self.register_action(
            "generate_social_media_image",
            self._generate_social_media_image,
            required_params=["prompt"],
            optional_params=["platform", "providers"]
        )
        
        self.register_action(
            "generate_variations",
            self._generate_variations_multi_provider,
            required_params=["prompt"],
            optional_params=["count", "providers"]
        )
        
        # Register image display action
        self.register_action(
            "load_and_display_image",
            self._load_and_display_image,
            required_params=["image_path"],
            optional_params=[]
        )
        
        # Debug action for checking provider status
        self.register_action(
            "check_provider_status",
            self._check_provider_status,
            required_params=[],
            optional_params=["user_id"]
        )
        
        # Context-aware retrieval actions
        self.register_action(
            "get_latest_image", 
            self._get_latest_image,
            required_params=[],
            optional_params=["user_id"]
        )
        
        # Visual Asset Management actions
        self.register_action(
            "list_available_images",
            self._list_available_images,
            required_params=[],
            optional_params=["folder_path", "pattern", "limit"]
        )
        
        self.register_action(
            "select_existing_image",
            self._select_existing_image,
            required_params=["selection_criteria"],
            optional_params=["folder_path", "copy_to_new_location"]
        )
        
        self.register_action(
            "search_images_by_name",
            self._search_images_by_name,
            required_params=["search_term"],
            optional_params=["folder_path", "case_sensitive"]
        )
        
        self.register_action(
            "get_image_info",
            self._get_image_info,
            required_params=["image_path"],
            optional_params=[]
        )
    
    def _initialize_memory(self):
        """Initialize graph memory connection for operation logging"""
        try:
            from app.mcp_core import registry
            self.graph_memory = registry.get_tool("graph_memory")
            if not self.graph_memory:
                logger.warning("Graph memory tool not available - context features disabled")
        except Exception as e:
            logger.error(f"Failed to initialize memory: {e}")
    
    def _log_operation_to_memory(self, action_name: str, prompt: str, result_data: Dict):
        """Log visual operation to graph memory for context-aware retrieval"""
        try:
            if not self.graph_memory:
                return
            
            # Get current user ID (from kwargs or default)
            user_id = getattr(self, 'current_user_id', 'system')
            
            # Enhanced result data with file info
            enhanced_result = {
                "success": True,
                "prompt": prompt,
                "file_path": result_data.get("saved_path"),
                "local_filename": result_data.get("local_filename"),
                "timestamp": result_data.get("created_at"),
                "provider": result_data.get("provider", "openai")
            }
            
            # Log to graph memory
            self.graph_memory._log_tool_operation(
                tool_name="simple_visual_creator",
                action_name=action_name,
                result=enhanced_result,
                user_id=user_id,
                parameters={"prompt": prompt}
            )
            
            logger.info(f"Operation logged to memory: {action_name} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log operation to memory: {e}")
    
    def _get_latest_image(self, user_id: str = "system") -> MCPToolResult:
        """Get the latest generated image for context-aware operations"""
        try:
            if not self.graph_memory:
                return MCPToolResult(success=False, error="Memory system not available")
            
            # Get latest visual operation
            result = self.graph_memory._get_latest_operation(
                user_id=user_id,
                tool_name="simple_visual_creator",
                action_type="generate"
            )
            
            if result.success:
                operation_data = result.data
                
                # Extract file path from operation data
                file_path = None
                for obs in operation_data.get("entity", {}).get("observations", []):
                    if "saved_path" in obs or ".jpg" in obs or ".png" in obs:
                        # Parse file path from observation
                        if ":" in obs:
                            file_path = obs.split(": ", 1)[1] if ": " in obs else obs
                        break
                
                if file_path and os.path.exists(file_path):
                    return MCPToolResult(success=True, data={
                        "file_path": file_path,
                        "operation_timestamp": operation_data.get("timestamp"),
                        "context": "latest_image"
                    })
                else:
                    return MCPToolResult(success=False, error="Latest image file not found")
            else:
                return MCPToolResult(success=False, error="No image generation history found")
                
        except Exception as e:
            return MCPToolResult(success=False, error=f"Error retrieving latest image: {str(e)}")
    
    def _generate_image_with_openai(self, prompt: str = None, description: str = None, theme: str = None,
                       size: str = "1024x1024", quality: str = "medium", **kwargs) -> MCPToolResult:
        """
        Generate image with GPT-4o (gpt-image-1) - flexible parameter handling
        
        Args:
            prompt/description/theme: Image description (flexible naming)
            size: Image size (1024x1024, 1024x1792, 1792x1024)
            quality: Image quality (low, medium, high, auto)
        """
        try:
            # Handle flexible parameter naming
            final_prompt = prompt or description or theme
            if not final_prompt:
                return MCPToolResult(
                    success=False,
                    error="Image description required (use 'prompt', 'description', or 'theme' parameter)"
                )
            
            # Check API key from database first, then fallback to environment
            api_key = None
            user_id = kwargs.get('user_id', 'default')
            
            try:
                # Try to get API key from database using settings manager
                from .settings_manager import get_settings_manager
                settings_manager = get_settings_manager()
                api_key = settings_manager.get_api_key(user_id, 'openai')
                if api_key:
                    logger.info("Using OpenAI API key from JSON storage for image generation")
            except Exception as e:
                logger.warning(f"Could not get OpenAI API key from database: {e}")
            
            # Fallback to environment variable
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    logger.info("Using OpenAI API key from environment for image generation")
            
            if not api_key:
                return MCPToolResult(
                    success=False,
                    error="OpenAI API key not found. Please add OpenAI API key in Settings or set OPENAI_API_KEY environment variable"
                )
            
            # Validate and fix size parameter for DALL-E 3
            valid_sizes = ['1024x1024', '1024x1536', '1536x1024']
            if size not in valid_sizes:
                # Map common invalid sizes to valid ones
                size_mapping = {
                    '1024x768': '1024x1024',  # Map 4:3 to 1:1
                    '768x1024': '1024x1536',  # Map portrait to valid portrait
                    '1920x1080': '1536x1024', # Map landscape to valid landscape
                    '512x512': '1024x1024',   # Scale up small square
                    'auto': '1024x1024'       # Default for auto
                }
                if size in size_mapping:
                    original_size = size
                    size = size_mapping[size]
                    logger.info(f"Mapped invalid size '{original_size}' to valid size '{size}'")
                else:
                    size = '1024x1024'  # Default fallback
                    logger.warning(f"Unknown size parameter '{size}', using default '1024x1024'")
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Use GPT-4o image generation model
            data = {
                "model": "gpt-image-1",
                "prompt": final_prompt,
                "n": 1,
                "size": size,
                "quality": quality
            }
            
            # Make API call to image generation endpoint
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Debug: Log response structure without base64 spam
                response_summary = {k: v for k, v in result.items() if k not in ['data', 'b64_json']}
                if 'data' in result:
                    response_summary['data_items'] = len(result['data']) if isinstance(result['data'], list) else 1
                logger.info(f"GPT-4o Image API Response Summary: {response_summary}")
                print(f"[DEBUG] API Response Summary (base64 excluded): {response_summary}")
                
                # Handle different possible response formats
                image_url = None
                base64_data = None
                saved_path = None
                revised_prompt = final_prompt  # Initialize with default
                
                if "data" in result and len(result["data"]) > 0:
                    image_data_item = result["data"][0]
                    image_url = image_data_item.get("url") or image_data_item.get("image_url")
                    b64_json = image_data_item.get("b64_json")
                    revised_prompt = image_data_item.get("revised_prompt", final_prompt)
                else:
                    # Alternative response format check
                    image_url = result.get("url") or result.get("image_url")
                    b64_json = result.get("b64_json")
                    revised_prompt = result.get("revised_prompt", final_prompt)
                
                # Prioritize base64 if available (newer models use this)
                if b64_json:
                    try:
                        base64_data = b64_json
                        # Save base64 image to file
                        saved_path = self._save_image_from_base64(base64_data, final_prompt)
                        logger.debug("Image received as base64")
                    except Exception as e:
                        logger.error(f"Base64 processing error: {str(e)}")
                        return MCPToolResult(
                            success=False,
                            error=f"Base64 image processing failed: {str(e)}"
                        )
                
                # Fallback to URL if no base64
                elif image_url:
                    try:
                        # URL'den görsel indir ve base64'e çevir
                        saved_path = self._save_image_from_url(image_url, final_prompt)
                        base64_data = self._url_to_base64(image_url)
                        
                        if not base64_data:
                            logger.warning("Base64 conversion failed, using URL only")
                            
                    except Exception as e:
                        logger.error(f"Image URL processing error: {str(e)}")
                        return MCPToolResult(
                            success=False,
                            error=f"Image URL processing failed: {str(e)}"
                        )
                
                # Check if we got any image data
                if not base64_data and not image_url:
                    return MCPToolResult(
                        success=False,
                        error=f"No image data found in response. Response structure: {result}"
                    )
                
                image_data = {
                    "prompt": final_prompt,
                    "revised_prompt": revised_prompt,
                    "image_url": image_url,
                    "base64_image": base64_data,
                    "saved_path": saved_path,
                    "local_filename": os.path.basename(saved_path) if saved_path else None,
                    "model": "gpt-image-1",
                    "size": size,
                    "quality": quality,
                    "created_at": datetime.now().isoformat(),
                    "success": True,
                    "base64_preview": base64_data[:100] + "..." if base64_data else None  # Önizleme için
                }
                
                logger.info(f"Image generated successfully with GPT-4o: {saved_path}")
                
                # Log operation to memory for context-aware retrieval
                self._log_operation_to_memory("generate_image_with_openai", final_prompt, image_data)
                
                # Kısa mesaj formatı
                url_preview = image_url[:50] + "..." if image_url else "Base64 format"
                success_message = f"✅ Görsel başarıyla oluşturuldu!\n🎨 Prompt: {final_prompt[:50]}...\n📁 Dosya: {os.path.basename(saved_path) if saved_path else 'N/A'}\n🔗 URL: {url_preview}"
                
                return MCPToolResult(
                    success=True, 
                    data=image_data
                )
                
            else:
                error_msg = f"GPT-4o Image API error: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg += f" - {error_data.get('error', {}).get('message', 'Unknown error')}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                        
                return MCPToolResult(success=False, error=error_msg)
                
        except Exception as e:
            import traceback
            logger.error(f"OpenAI image generation failed: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            print(f"[DEBUG] Exception details: {traceback.format_exc()}")  # Console debug
            return MCPToolResult(success=False, error=f"OpenAI image generation failed: {str(e)}")
    
    # Gemini API removed - only OpenAI and HuggingFace providers available
    
    def _generate_image_with_huggingface(self, prompt: str = None, description: str = None, theme: str = None,
                                        model: str = "runwayml/stable-diffusion-v1-5", **kwargs) -> MCPToolResult:
        """
        Generate image with HuggingFace free models
        
        Args:
            prompt/description/theme: Image description
            model: HuggingFace model to use
        """
        try:
            final_prompt = prompt or description or theme
            if not final_prompt:
                return MCPToolResult(
                    success=False,
                    error="Image description required"
                )
            
            # Check API key from database first, then fallback to environment
            api_key = None
            user_id = kwargs.get('user_id', 'default')
            
            try:
                # Try to get API key from database using settings manager
                from .settings_manager import get_settings_manager
                settings_manager = get_settings_manager()
                api_key = settings_manager.get_api_key(user_id, 'huggingface')
                if api_key:
                    logger.info("Using HuggingFace API key from JSON storage for image generation")
            except Exception as e:
                logger.warning(f"Could not get HuggingFace API key from database: {e}")
            
            # Fallback to environment variables
            if not api_key:
                api_key = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_API_KEY")
                if api_key:
                    logger.info("Using HuggingFace API key from environment")
            
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Prepare request
            data = {"inputs": final_prompt}
            
            # Make API call to HuggingFace
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                # HuggingFace returns image bytes directly
                image_bytes = response.content
                base64_data = base64.b64encode(image_bytes).decode('utf-8')
                
                # Save image
                saved_path = self._save_image_from_base64(base64_data, final_prompt)
                
                image_data = {
                    "prompt": final_prompt,
                    "revised_prompt": final_prompt,
                    "image_url": None,
                    "base64_image": base64_data,
                    "saved_path": saved_path,
                    "local_filename": os.path.basename(saved_path) if saved_path else None,
                    "model": model,
                    "provider": "huggingface",
                    "created_at": datetime.now().isoformat(),
                    "success": True
                }
                
                logger.info(f"HuggingFace image generated successfully: {saved_path}")
                
                # Log operation to memory for context-aware retrieval
                self._log_operation_to_memory("generate_image_with_huggingface", final_prompt, image_data)
                
                return MCPToolResult(success=True, data=image_data)
                
            else:
                error_msg = f"HuggingFace API error: {response.status_code} - {response.text[:200]}"
                
                # Special handling for quota exceeded (402 error)
                if response.status_code == 402:
                    error_msg = (
                        "🚫 HuggingFace monthly quota exceeded. "
                        "Öneriler:\n"
                        "1. HuggingFace PRO subscription alın (20x daha fazla quota)\n"
                        "2. Kendi HuggingFace API key'inizi settings'e ekleyin\n"
                        "3. Sadece OpenAI provider kullanın: providers=['openai']\n"
                        "4. Alternatif: Gemini web scraping (ücretsiz ama login gerekli)"
                    )
                
                return MCPToolResult(success=False, error=error_msg)
                
        except Exception as e:
            logger.error(f"HuggingFace image generation failed: {str(e)}")
            return MCPToolResult(success=False, error=f"HuggingFace image generation failed: {str(e)}")
    
    # Gemini web scraping removed
    def _removed_gemini_scraping_method(self):
        """
        Generate image with Gemini web scraping (Free alternative)
        
        Args:
            prompt/description/theme: Image description (flexible naming)
            size: Image size (ignored for scraping)
            quality: Image quality (ignored for scraping)
        """
        try:
            # Handle flexible parameter naming
            final_prompt = prompt or description or theme
            if not final_prompt:
                return MCPToolResult(
                    success=False,
                    error="Image description required (use 'prompt', 'description', or 'theme' parameter)"
                )
            
            logger.info(f"Generating image with Gemini scraping: {final_prompt}")
            
            # Use Playwright for Gemini scraping (modern, stable)
            from .playwright_browser import playwright_gemini_scraper
            result = playwright_gemini_scraper.scrape_gemini_image(
                prompt=final_prompt,
                headless=kwargs.get('headless', True)
            )
            
            if result.success:
                logger.info("Playwright Gemini scraping başarılı")
            else:
                logger.error(f"Playwright Gemini scraping failed: {result.error}")
                
                # Login gerekli durumlarda kullanıcıya açıklayıcı mesaj ver
                if "login gerekli" in result.error.lower():
                    return MCPToolResult(
                        success=False,
                        error="🔐 Gemini web scraping için Google hesabına giriş gerekli. "
                               "Alternatif olarak OpenAI DALL-E 3 veya HuggingFace kullanabilirsiniz. "
                               "Önce tarayıcınızda https://gemini.google.com adresine gidip giriş yapın."
                    )
            
            if result.success:
                image_data = result.data
                return MCPToolResult(
                    success=True,
                    data={
                        'prompt': final_prompt,
                        'image_path': image_data.get('image_path'),
                        'image_url': None,  # Local file olduğu için URL yok
                        'base64_image': image_data.get('base64_image'),  # Frontend için base64 data
                        'method': 'gemini_scraping',
                        'provider': 'gemini_scraping',
                        'size': 'screenshot',  # Browser screenshot boyutu
                        'image_found': image_data.get('image_found', False),
                        'note': image_data.get('note', ''),
                        'created_at': datetime.now().isoformat()
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Gemini scraping failed: {result.error}"
                )
                
        except Exception as e:
            logger.error(f"Gemini scraping generation failed: {str(e)}")
            return MCPToolResult(success=False, error=f"Gemini scraping generation failed: {str(e)}")
    
    def _generate_image_multi_provider(self, prompt: str = None, description: str = None, theme: str = None,
                                      providers: List[str] = None, size: str = "1024x1024", quality: str = "medium", **kwargs) -> MCPToolResult:
        """
        Generate images using multiple providers in parallel and return all successful results
        
        Args:
            prompt/description/theme: Image description
            providers: List of providers to use ['openai', 'gemini', 'huggingface']
            size: Image size
            quality: Image quality
        """
        try:
            final_prompt = prompt or description or theme
            if not final_prompt:
                return MCPToolResult(
                    success=False,
                    error="Image description required"
                )
            
            # Default providers if not specified (web scraping removed)
            if not providers:
                # Try both providers but prioritize OpenAI for reliability
                providers = ['openai', 'huggingface']  # Web scraping abandoned
            
            available_providers = {
                'openai': self._generate_image_with_openai,
                'huggingface': self._generate_image_with_huggingface
                # Gemini API also removed - only OpenAI and HuggingFace
            }
            
            logger.info(f"Starting PARALLEL multi-provider image generation with providers: {providers}")
            
            # Use ThreadPoolExecutor for parallel execution
            def generate_with_provider(provider):
                if provider not in available_providers:
                    return {
                        'provider': provider,
                        'success': False,
                        'data': None,
                        'error': f"Unknown provider: {provider}"
                    }
                
                try:
                    logger.info(f"🚀 Starting {provider} generation in parallel")
                    method = available_providers[provider]
                    result = method(prompt=final_prompt, size=size, quality=quality, **kwargs)
                    
                    result_data = {
                        'provider': provider,
                        'success': result.success,
                        'data': result.data if result.success else None,
                        'error': result.error if not result.success else None,
                        'generation_time': datetime.now().isoformat()
                    }
                    
                    if result.success:
                        logger.info(f"✅ {provider} generation completed successfully")
                    else:
                        logger.warning(f"❌ {provider} generation failed: {result.error}")
                    
                    return result_data
                    
                except Exception as e:
                    logger.error(f"❌ {provider} generation exception: {str(e)}")
                    return {
                        'provider': provider,
                        'success': False,
                        'data': None,
                        'error': f"Exception: {str(e)}",
                        'generation_time': datetime.now().isoformat()
                    }
            
            # Execute all providers in parallel
            with ThreadPoolExecutor(max_workers=len(providers)) as executor:
                results = list(executor.map(generate_with_provider, providers))
            
            # Separate successful and failed results
            successful_results = [r for r in results if r['success']]
            failed_results = [r for r in results if not r['success']]
            
            logger.info(f"Parallel generation completed: {len(successful_results)} successful, {len(failed_results)} failed")
            
            if successful_results:
                # Auto-display first successful image
                first_success = successful_results[0]
                # Check for both 'image_path' and 'saved_path' keys
                image_path = None
                if first_success['data']:
                    image_path = first_success['data'].get('image_path') or first_success['data'].get('saved_path')
                
                if image_path:
                    logger.info(f"Auto-displaying generated image: {image_path}")
                    
                    # Call display action automatically
                    display_result = self._load_and_display_image(image_path)
                    
                    # Merge display info into response
                    display_info = {
                        'auto_displayed': True,
                        'display_success': display_result.success,
                        'display_path': image_path
                    }
                    if not display_result.success:
                        display_info['display_error'] = display_result.error
                else:
                    display_info = {'auto_displayed': False, 'reason': 'No image path found'}
                
                # Extract primary image info for direct access
                primary_image = {}
                if successful_results:
                    first_result = successful_results[0]
                    if first_result.get('data'):
                        primary_image = {
                            'saved_path': first_result['data'].get('saved_path'),
                            'image_path': first_result['data'].get('saved_path'),  # Alias for compatibility
                            'local_filename': first_result['data'].get('local_filename'),
                            'base64_image': first_result['data'].get('base64_image')
                        }
                
                # Return ALL successful results for user choice
                return MCPToolResult(
                    success=True,
                    data={
                        'prompt': final_prompt,
                        'generation_type': 'multi_provider_parallel',
                        'successful_generations': successful_results,
                        'failed_generations': failed_results,
                        'total_attempts': len(results),
                        'success_count': len(successful_results),
                        'success_rate': len(successful_results) / len(results) if results else 0,
                        'providers_used': providers,
                        'generation_summary': f"Generated {len(successful_results)} images from {len(providers)} providers",
                        'created_at': datetime.now().isoformat(),
                        'display_info': display_info,
                        # Add primary image info at top level for easy frontend access
                        **primary_image
                    }
                )
            else:
                # All providers failed
                error_summary = f"All {len(providers)} providers failed to generate images"
                for result in results:
                    error_summary += f"\n- {result['provider']}: {result['error']}"
                
                return MCPToolResult(
                    success=False,
                    error=error_summary,
                    metadata={'provider_results': results}
                )
                
        except Exception as e:
            logger.error(f"Multi-provider parallel image generation failed: {str(e)}")
            return MCPToolResult(success=False, error=f"Multi-provider parallel image generation failed: {str(e)}")
    
    def _generate_social_media_image(self, prompt: str, platform: str = "instagram", **kwargs) -> MCPToolResult:
        """Generate platform-optimized social media image"""
        try:
            # Platform size mapping
            size_map = {
                "instagram": "1024x1024",  # Square
                "facebook": "1024x1024",   # Square for posts
                "twitter": "1792x1024",    # Landscape
                "linkedin": "1792x1024",   # Landscape
                "story": "1024x1792",      # Vertical
                "tiktok": "1024x1792"      # Vertical
            }
            
            size = size_map.get(platform.lower(), "1024x1024")
            
            # Platform-specific prompt enhancement
            enhanced_prompt = f"{prompt}, optimized for {platform}, high quality, engaging, social media ready"
            
            # Generate with platform specs using multi-provider
            providers = kwargs.get('providers', ['openai', 'huggingface'])
            result = self._generate_image_multi_provider(prompt=enhanced_prompt, size=size, quality="medium", providers=providers)
            
            if result.success:
                result.data["platform"] = platform
                result.data["optimized_for"] = platform
                result.data["original_prompt"] = prompt
                result.data["enhanced_prompt"] = enhanced_prompt
            
            return result
            
        except Exception as e:
            logger.error(f"Social media image generation failed: {str(e)}")
            return MCPToolResult(success=False, error=f"Social media image generation failed: {str(e)}")
    
    def _generate_variations_multi_provider(self, prompt: str, count: int = 3, providers: List[str] = None, **kwargs) -> MCPToolResult:
        """Generate multiple variations of the same concept"""
        try:
            count = min(max(count, 1), 4)  # Limit 1-4
            
            # Style variations
            styles = [
                "photorealistic style",
                "artistic illustration style", 
                "minimalist design style",
                "vibrant and colorful style",
                "professional commercial style"
            ]
            
            variations = []
            successful_count = 0
            
            for i in range(count):
                try:
                    style = styles[i % len(styles)]
                    enhanced_prompt = f"{prompt}, {style}"
                    
                    result = self._generate_image_multi_provider(prompt=enhanced_prompt, providers=providers)
                    
                    if result.success:
                        variation_data = result.data.copy()
                        variation_data.update({
                            "variation_id": i + 1,
                            "style": style,
                            "original_prompt": prompt
                        })
                        variations.append(variation_data)
                        successful_count += 1
                    else:
                        variations.append({
                            "variation_id": i + 1,
                            "style": style,
                            "status": "failed",
                            "error": result.error
                        })
                        
                except Exception as e:
                    logger.error(f"Variation {i+1} failed: {str(e)}")
                    variations.append({
                        "variation_id": i + 1,
                        "status": "failed", 
                        "error": str(e)
                    })
            
            return MCPToolResult(
                success=True,
                data={
                    "original_prompt": prompt,
                    "requested_count": count,
                    "successful_count": successful_count,
                    "variations": variations,
                    "total_generated": len(variations)
                }
            )
            
        except Exception as e:
            logger.error(f"Variations generation failed: {str(e)}")
            return MCPToolResult(success=False, error=f"Variations generation failed: {str(e)}")
    
    def _save_image_from_url(self, image_url: str, prompt: str) -> str:
        """Download and save image from URL"""
        try:
            # Generate safe filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_prompt = safe_prompt.replace(' ', '_')
            filename = f"{timestamp}_{safe_prompt}.png"
            filepath = os.path.join(self.image_storage_path, filename)
            
            # Download image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Save to file
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Image saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save image: {str(e)}")
            return None
    
    def _save_image_from_base64(self, b64_data: str, prompt: str) -> str:
        """Save base64 image data to file"""
        try:
            # Generate safe filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_prompt = safe_prompt.replace(' ', '_')
            filename = f"{timestamp}_{safe_prompt}.png"
            filepath = os.path.join(self.image_storage_path, filename)
            
            logger.info(f"Attempting to save base64 image: {filepath}")
            logger.debug(f"Base64 data length: {len(b64_data) if b64_data else 'None'}")
            logger.info(f"Image storage path exists: {os.path.exists(self.image_storage_path)}")
            
            # Decode base64 and save
            image_bytes = base64.b64decode(b64_data)
            logger.info(f"Decoded image bytes length: {len(image_bytes)}")
            
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            # Verify file was created
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                logger.info(f"✅ Base64 image saved successfully: {filepath} ({file_size} bytes)")
                return filepath
            else:
                logger.error(f"❌ File was not created: {filepath}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to save base64 image: {str(e)}")
            return None
    
    def _url_to_base64(self, image_url: str) -> str:
        """Convert image URL to base64 string"""
        try:
            # Download image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Convert to base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            
            logger.debug(f"Image converted to base64 successfully")
            return image_base64
            
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {str(e)}")
            return None
    
    def _load_and_display_image(self, image_path: str) -> MCPToolResult:
        """Load and display an existing image file with environment-aware display strategy"""
        try:
            # Detect execution environment first
            is_workflow_context = self._detect_workflow_context()
            has_display = self._has_display_capability()
            
            # Check if image_path is absolute or relative
            if not os.path.isabs(image_path):
                # Try current working directory first
                full_path = os.path.abspath(image_path)
                if not os.path.exists(full_path):
                    # Try in generated_images folder
                    full_path = os.path.join(self.image_storage_path, image_path)
            else:
                full_path = image_path
            
            # Check if file exists
            if not os.path.exists(full_path):
                return MCPToolResult(
                    success=False,
                    error=f"Image file not found: {image_path}"
                )
            
            # Check if it's an image file
            allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
            file_extension = os.path.splitext(full_path)[1].lower()
            
            if file_extension not in allowed_extensions:
                return MCPToolResult(
                    success=False,
                    error=f"Unsupported file format: {file_extension}. Supported: {', '.join(allowed_extensions)}"
                )
            
            # For workflow context, we only need the path - no base64 needed
            image_base64 = None
            if not is_workflow_context:
                # Only read base64 for standalone context if needed
                with open(full_path, 'rb') as f:
                    image_bytes = f.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Get file info
            file_size = os.path.getsize(full_path)
            created_time = datetime.fromtimestamp(os.path.getctime(full_path))
            
            # ENVIRONMENT-AWARE DISPLAY STRATEGY
            display_success = False
            display_method = "none"
            display_error = None
            
            if not is_workflow_context and has_display:
                # Standalone execution with display capability - use native display
                display_success, display_method, display_error = self._native_display(full_path)
            elif is_workflow_context:
                # Workflow context - prioritize base64 return for frontend display
                display_success = True
                display_method = "workflow_base64_return"
                display_error = None
                logger.debug(f"WORKFLOW DISPLAY: Returning base64 data for frontend display (workflow context detected)")
            else:
                # Fallback - base64 only
                display_success = True
                display_method = "base64_only"
            
            logger.info(f"Image loaded and displayed: {full_path} (method: {display_method})")
            
            # Build response data - only include base64 if not workflow context
            response_data = {
                'image_path': full_path,
                'filename': os.path.basename(full_path),
                'file_size': file_size,
                'created_at': created_time.isoformat(),
                'format': file_extension[1:].upper(),
                'display_ready': True,
                'display_method': display_method,
                'display_success': display_success,
                'display_error': display_error,
                'execution_context': 'workflow' if is_workflow_context else 'standalone'
            }
            
            # Only add base64 for non-workflow contexts
            if image_base64 is not None:
                response_data['base64_image'] = image_base64
            
            return MCPToolResult(
                success=True,
                data=response_data
            )
            
        except Exception as e:
            logger.error(f"Failed to load and display image: {str(e)}")
            return MCPToolResult(
                success=False,
                error=f"Failed to load image: {str(e)}"
            )
    
    def _detect_workflow_context(self) -> bool:
        """Detect if we're running in workflow orchestrator context"""
        import inspect
        
        # Check call stack for workflow orchestrator
        for frame_info in inspect.stack():
            frame_filename = frame_info.filename
            function_name = frame_info.function
            
            # Check for workflow orchestrator in call stack
            if 'workflow_orchestrator' in frame_filename.lower():
                return True
            if 'orchestrator' in function_name.lower():
                return True
            if 'workflow' in function_name.lower() and 'execute' in function_name.lower():
                return True
                
        return False
    
    def _has_display_capability(self) -> bool:
        """Check if current environment can display images natively"""
        # Check DISPLAY environment variable (X11)
        if os.environ.get('DISPLAY'):
            return True
            
        # Check if we're in a GUI environment
        if os.environ.get('XDG_SESSION_TYPE') == 'x11':
            return True
            
        # Check for Windows environment
        if os.name == 'nt':
            return True
            
        # Check for macOS environment
        if os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
            return True
            
        return False
    
    def _native_display(self, image_path: str) -> tuple:
        """Display image using native system capabilities"""
        try:
            # Try different display methods based on platform
            if os.name == 'nt':  # Windows
                os.startfile(image_path)
                return True, "windows_native", None
            elif os.name == 'posix':
                # Linux/Unix - try common image viewers
                viewers = ['eog', 'feh', 'display', 'xdg-open']
                for viewer in viewers:
                    try:
                        import subprocess
                        subprocess.Popen([viewer, image_path], 
                                       stdout=subprocess.DEVNULL, 
                                       stderr=subprocess.DEVNULL)
                        return True, f"linux_{viewer}", None
                    except (FileNotFoundError, OSError):
                        continue
                        
                # Fallback: try opening with default handler
                try:
                    import subprocess
                    subprocess.Popen(['xdg-open', image_path], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    return True, "linux_xdg_open", None
                except:
                    pass
                    
            return False, "native_failed", "No suitable image viewer found"
            
        except Exception as e:
            return False, "native_error", str(e)
    
    def _workflow_display_strategy(self, image_path: str, base64_image: str) -> tuple:
        """Alternative display strategy for workflow context"""
        try:
            # Strategy 1: Try to open with system default (non-blocking)
            try:
                import subprocess
                if os.name == 'nt':
                    subprocess.Popen(['cmd', '/c', 'start', '', image_path], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    return True, "workflow_windows_start", None
                else:
                    # Linux: Try non-blocking display
                    subprocess.Popen(['xdg-open', image_path], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    return True, "workflow_xdg_open", None
            except Exception as e:
                logger.warning(f"Workflow display strategy failed: {e}")
                
            # Strategy 2: Copy to a temporary location with notification
            try:
                import tempfile
                import shutil
                
                # Create temp copy for user access
                temp_dir = tempfile.gettempdir()
                temp_filename = f"metis_display_{os.path.basename(image_path)}"
                temp_path = os.path.join(temp_dir, temp_filename)
                shutil.copy2(image_path, temp_path)
                
                logger.info(f"Image copied to temp location for display: {temp_path}")
                return True, "workflow_temp_copy", f"Image available at: {temp_path}"
                
            except Exception as e:
                logger.warning(f"Temp copy strategy failed: {e}")
            
            # Strategy 3: Base64 only (always works)
            return True, "workflow_base64_only", None
            
        except Exception as e:
            return False, "workflow_error", str(e)
    
    def _check_provider_status(self, user_id: str = 'default', **kwargs) -> MCPToolResult:
        """
        Check the status and availability of all image generation providers
        
        Args:
            user_id: User ID for API key checking
            
        Returns:
            Status report for all providers
        """
        try:
            provider_status = {}
            
            # Check OpenAI provider
            try:
                from .settings_manager import get_settings_manager
                settings_manager = get_settings_manager()
                openai_key = settings_manager.get_api_key(user_id, 'openai')
                env_openai_key = os.getenv("OPENAI_API_KEY")
                
                provider_status['openai'] = {
                    'available': True,
                    'api_key_db': bool(openai_key),
                    'api_key_env': bool(env_openai_key),
                    'status': 'Ready' if (openai_key or env_openai_key) else 'Missing API Key',
                    'model': 'gpt-image-1 (DALL-E 3)'
                }
            except Exception as e:
                provider_status['openai'] = {
                    'available': False,
                    'error': str(e),
                    'status': 'Error'
                }
            
            # Check HuggingFace provider
            try:
                huggingface_key = settings_manager.get_api_key(user_id, 'huggingface')
                env_hf_key = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_API_KEY")
                
                provider_status['huggingface'] = {
                    'available': True,
                    'api_key_db': bool(huggingface_key),
                    'api_key_env': bool(env_hf_key),
                    'status': 'Ready (but may have quota limits)',
                    'model': 'runwayml/stable-diffusion-v1-5',
                    'note': 'Free tier has monthly quotas - may get 402 errors'
                }
            except Exception as e:
                provider_status['huggingface'] = {
                    'available': False,
                    'error': str(e),
                    'status': 'Error'
                }
            
            # Generate summary
            working_providers = [p for p, status in provider_status.items() if status.get('available', False)]
            
            return MCPToolResult(
                success=True,
                data={
                    'user_id': user_id,
                    'providers': provider_status,
                    'working_providers': working_providers,
                    'total_providers': len(provider_status),
                    'working_count': len(working_providers),
                    'default_providers': ['openai', 'huggingface'],
                    'recommended_provider': 'openai' if 'openai' in working_providers else None,
                    'summary': f"{len(working_providers)}/{len(provider_status)} providers available"
                }
            )
            
        except Exception as e:
            logger.error(f"Provider status check failed: {str(e)}")
            return MCPToolResult(
                success=False,
                error=f"Provider status check failed: {str(e)}"
            )
    
    def _list_available_images(self, folder_path: str = None, pattern: str = "*.png", limit: int = 50, **kwargs) -> MCPToolResult:
        """List available images in specified folder or default image storage"""
        try:
            import glob
            
            # Use provided folder or default image storage
            search_path = folder_path or self.image_storage_path
            
            if not os.path.exists(search_path):
                return MCPToolResult(
                    success=False,
                    error=f"Folder does not exist: {search_path}"
                )
            
            # Search for images
            search_pattern = os.path.join(search_path, pattern)
            image_files = glob.glob(search_pattern)
            
            # Also search for other common image formats
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp"]:
                if ext != pattern:
                    additional_pattern = os.path.join(search_path, ext)
                    image_files.extend(glob.glob(additional_pattern))
            
            # Remove duplicates and sort
            image_files = list(set(image_files))
            image_files.sort(key=os.path.getmtime, reverse=True)  # Sort by modification time, newest first
            
            # Apply limit
            if limit:
                image_files = image_files[:limit]
            
            # Get file info
            image_info = []
            for filepath in image_files:
                try:
                    stat = os.stat(filepath)
                    filename = os.path.basename(filepath)
                    
                    # Extract date from filename if possible
                    date_match = None
                    if filename.startswith('2025'):
                        date_part = filename[:15]  # 20250731_184455
                        try:
                            date_match = datetime.strptime(date_part, '%Y%m%d_%H%M%S').isoformat()
                        except:
                            pass
                    
                    image_info.append({
                        "filepath": filepath,
                        "filename": filename,
                        "size_bytes": stat.st_size,
                        "size_mb": round(stat.st_size / 1024 / 1024, 2),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "created_date": date_match,
                        "description": self._extract_description_from_filename(filename)
                    })
                except Exception as e:
                    logger.warning(f"Error getting info for {filepath}: {e}")
            
            return MCPToolResult(
                success=True,
                data={
                    "search_path": search_path,
                    "pattern": pattern,
                    "total_found": len(image_info),
                    "images": image_info,
                    "message": f"Found {len(image_info)} images in {search_path}"
                }
            )
            
        except Exception as e:
            logger.error(f"Error listing available images: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _extract_description_from_filename(self, filename: str) -> str:
        """Extract description from generated image filename"""
        try:
            # Remove timestamp and extension
            if filename.startswith('2025'):
                # Format: 20250731_184455_description.png
                parts = filename.split('_', 2)
                if len(parts) >= 3:
                    desc_part = parts[2].replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
                    # Replace underscores with spaces and clean up
                    description = desc_part.replace('_', ' ').strip()
                    return description[:100]  # Limit length
            return "Image file"
        except:
            return "Image file"
    
    def _select_existing_image(self, selection_criteria: str, folder_path: str = None, 
                              copy_to_new_location: bool = False, **kwargs) -> MCPToolResult:
        """Select existing image based on criteria (latest, by name, by description)"""
        try:
            # List available images first
            list_result = self._list_available_images(folder_path=folder_path, limit=100)
            if not list_result.success:
                return list_result
            
            images = list_result.data["images"]
            if not images:
                return MCPToolResult(success=False, error="No images found")
            
            selected_image = None
            selection_method = ""
            
            # Parse selection criteria
            criteria_lower = selection_criteria.lower()
            
            if any(word in criteria_lower for word in ["latest", "son", "en son", "newest", "last"]):
                # Select latest image
                selected_image = images[0]  # Already sorted by modification time
                selection_method = "latest"
                
            elif any(word in criteria_lower for word in ["köpek", "dog", "puppy", "yavru"]):
                # Search for dog-related images
                for img in images:
                    if any(word in img["description"].lower() for word in ["dog", "puppy", "köpek", "yavru"]):
                        selected_image = img
                        selection_method = "keyword_search"
                        break
                        
            elif any(word in criteria_lower for word in ["kedi", "cat", "kitten"]):
                # Search for cat-related images
                for img in images:
                    if any(word in img["description"].lower() for word in ["cat", "kitten", "kedi"]):
                        selected_image = img
                        selection_method = "keyword_search"
                        break
                        
            elif any(word in criteria_lower for word in ["çiçek", "flower", "gül", "rose"]):
                # Search for flower-related images
                for img in images:
                    if any(word in img["description"].lower() for word in ["flower", "çiçek", "gül", "rose", "lale", "karanfil"]):
                        selected_image = img
                        selection_method = "keyword_search"
                        break
                        
            elif any(word in criteria_lower for word in ["güneş", "sun", "solar"]):
                # Search for sun-related images
                for img in images:
                    if any(word in img["description"].lower() for word in ["sun", "güneş", "solar"]):
                        selected_image = img
                        selection_method = "keyword_search"
                        break
                        
            else:
                # Try to find by filename or description containing the criteria
                for img in images:
                    if (selection_criteria.lower() in img["filename"].lower() or 
                        selection_criteria.lower() in img["description"].lower()):
                        selected_image = img
                        selection_method = "text_search"
                        break
                
                # If no match found, select the latest
                if not selected_image:
                    selected_image = images[0]
                    selection_method = "fallback_latest"
            
            if not selected_image:
                return MCPToolResult(success=False, error="No suitable image found")
            
            # Copy to new location if requested
            result_filepath = selected_image["filepath"]
            if copy_to_new_location:
                try:
                    import shutil
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_filename = f"{timestamp}_selected_{os.path.basename(selected_image['filepath'])}"
                    new_filepath = os.path.join(self.image_storage_path, new_filename)
                    shutil.copy2(selected_image["filepath"], new_filepath)
                    result_filepath = new_filepath
                    logger.info(f"Image copied to: {new_filepath}")
                except Exception as e:
                    logger.warning(f"Failed to copy image: {e}")
            
            # Log operation to memory
            self._log_operation_to_memory(
                "select_existing_image",
                f"Selected image: {selection_criteria}",
                {
                    "saved_path": result_filepath,
                    "local_filename": os.path.basename(result_filepath),
                    "created_at": datetime.now().isoformat(),
                    "provider": "existing_image"
                }
            )
            
            return MCPToolResult(
                success=True,
                data={
                    "selected_image": selected_image,
                    "selection_criteria": selection_criteria,
                    "selection_method": selection_method,
                    "final_path": result_filepath,
                    "copied": copy_to_new_location,
                    "message": f"Selected image using {selection_method}: {selected_image['filename']}"
                }
            )
            
        except Exception as e:
            logger.error(f"Error selecting existing image: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _search_images_by_name(self, search_term: str, folder_path: str = None, 
                              case_sensitive: bool = False, **kwargs) -> MCPToolResult:
        """Search images by filename or description"""
        try:
            # List available images
            list_result = self._list_available_images(folder_path=folder_path, limit=200)
            if not list_result.success:
                return list_result
            
            images = list_result.data["images"]
            matching_images = []
            
            # Search through images
            search_lower = search_term if case_sensitive else search_term.lower()
            
            for img in images:
                filename_text = img["filename"] if case_sensitive else img["filename"].lower()
                description_text = img["description"] if case_sensitive else img["description"].lower()
                
                if search_lower in filename_text or search_lower in description_text:
                    matching_images.append(img)
            
            return MCPToolResult(
                success=True,
                data={
                    "search_term": search_term,
                    "case_sensitive": case_sensitive,
                    "total_searched": len(images),
                    "matches_found": len(matching_images),
                    "matching_images": matching_images,
                    "message": f"Found {len(matching_images)} images matching '{search_term}'"
                }
            )
            
        except Exception as e:
            logger.error(f"Error searching images: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_image_info(self, image_path: str, **kwargs) -> MCPToolResult:
        """Get detailed information about a specific image"""
        try:
            if not os.path.exists(image_path):
                return MCPToolResult(success=False, error=f"Image not found: {image_path}")
            
            stat = os.stat(image_path)
            filename = os.path.basename(image_path)
            
            # Try to get image dimensions
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    width, height = img.size
                    format_info = img.format
                    mode = img.mode
            except ImportError:
                width = height = format_info = mode = "Unknown (PIL not available)"
            except Exception as e:
                width = height = format_info = mode = f"Error: {e}"
            
            info = {
                "filepath": image_path,
                "filename": filename,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "description": self._extract_description_from_filename(filename),
                "dimensions": f"{width}x{height}" if width != "Unknown (PIL not available)" else "Unknown",
                "format": format_info,
                "color_mode": mode,
                "directory": os.path.dirname(image_path)
            }
            
            return MCPToolResult(
                success=True,
                data={
                    "image_info": info,
                    "message": f"Image info retrieved for: {filename}"
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting image info: {str(e)}")
            return MCPToolResult(success=False, error=str(e))

def register_tool(registry):
    """Register the simple visual creator tool"""
    tool = SimpleVisualCreatorTool()
    registry.register_tool(tool)
    logger.info("Simple Visual Creator tool registered successfully")