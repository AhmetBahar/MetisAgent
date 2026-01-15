import os
import json
import time
import base64
import requests
import logging
from typing import Dict, Any, List, Optional
from os_araci.mcp_core import MCPTool

logger = logging.getLogger(__name__)

class ImageGeneratorTool(MCPTool):
    """GPT-4o native image generation tool using gpt-image-1 model"""
    
    def __init__(self):
        super().__init__("image_generator", "GPT-4o Native Image Generation Tool")
        
        # Register actions
        self.register_action(
            "generate_image",
            self.generate_image,
            ["prompt"],
            "Generate image using GPT-4o native capabilities"
        )
        
        self.register_action(
            "generate_social_media_image",
            self.generate_social_media_image,
            ["prompt", "platform"],
            "Generate platform-optimized social media image"
        )
        
        self.register_action(
            "generate_image_with_text",
            self.generate_image_with_text,
            ["prompt", "text_content"],
            "Generate image with embedded text content"
        )
        
        self.register_action(
            "refine_image",
            self.refine_image,
            ["original_prompt", "refinement_request"],
            "Refine existing image based on feedback"
        )
        
        self.register_action(
            "generate_image_variations",
            self.generate_image_variations,
            ["base_prompt", "variation_count"],
            "Generate multiple variations of an image concept"
        )
        
        # Platform-specific image specifications
        self.platform_specs = {
            "instagram": {
                "feed_post": {"size": "1024x1024", "aspect_ratio": "1:1"},
                "story": {"size": "1024x1536", "aspect_ratio": "9:16"},
                "reel": {"size": "1024x1536", "aspect_ratio": "9:16"},
                "carousel": {"size": "1024x1024", "aspect_ratio": "1:1"}
            },
            "linkedin": {
                "post": {"size": "1024x1024", "aspect_ratio": "1:1"},
                "article": {"size": "1536x1024", "aspect_ratio": "16:9"},
                "cover": {"size": "1536x1024", "aspect_ratio": "16:9"}
            },
            "twitter": {
                "post": {"size": "1536x1024", "aspect_ratio": "16:9"},
                "header": {"size": "1536x1024", "aspect_ratio": "3:1"}
            },
            "facebook": {
                "post": {"size": "1024x1024", "aspect_ratio": "1:1"},
                "cover": {"size": "1536x1024", "aspect_ratio": "16:9"},
                "event": {"size": "1536x1024", "aspect_ratio": "16:9"}
            },
            "tiktok": {
                "video": {"size": "1024x1536", "aspect_ratio": "9:16"}
            }
        }
        
        # Style presets for different use cases
        self.style_presets = {
            "professional": "clean, modern, professional photography style, corporate aesthetic, high-end commercial photography",
            "creative": "artistic, creative, innovative design, vibrant colors, contemporary art style",
            "minimalist": "minimalist design, clean lines, simple composition, white background, modern aesthetic",
            "social_media": "eye-catching, social media optimized, engaging visual design, trendy aesthetic",
            "brand_friendly": "brand-safe content, commercial appropriate, professional quality, marketing ready",
            "educational": "clear, informative, educational design, easy to understand, instructional style",
            "lifestyle": "lifestyle photography, natural lighting, authentic moments, relatable content",
            "tech": "modern technology aesthetic, digital design, futuristic elements, clean tech style"
        }
        
        # Image generation statistics
        self.generation_stats = {
            "total_generated": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_generation_time": 0,
            "total_tokens_used": 0
        }

    async def generate_image(self, prompt: str, size: str = "1024x1024", 
                           quality: str = "high", style: str = "natural",
                           moderation: str = "auto") -> Dict[str, Any]:
        """Generate image using GPT-4o native image generation"""
        start_time = time.time()
        
        try:
            # Update stats
            self.generation_stats["total_generated"] += 1
            
            # Enhance prompt with style if specified
            enhanced_prompt = self._enhance_prompt(prompt, style)
            
            # Prepare API request
            api_data = {
                "model": "gpt-image-1",
                "prompt": enhanced_prompt,
                "size": size,
                "quality": quality,
                "response_format": "b64_json",
                "moderation": moderation
            }
            
            # Make API call to OpenAI
            response = await self._call_openai_api(api_data)
            
            if response.get("success"):
                # Process successful response
                image_data = response["data"]
                
                # Save image to disk
                image_path = await self._save_image(image_data, prompt)
                
                # Calculate generation time
                generation_time = time.time() - start_time
                self.generation_stats["average_generation_time"] = (
                    self.generation_stats["average_generation_time"] * 
                    (self.generation_stats["successful_generations"]) + generation_time
                ) / (self.generation_stats["successful_generations"] + 1)
                
                self.generation_stats["successful_generations"] += 1
                
                result = {
                    "status": "success",
                    "image_path": image_path,
                    "prompt_used": enhanced_prompt,
                    "generation_time": generation_time,
                    "size": size,
                    "quality": quality,
                    "tokens_used": response.get("tokens_used", 0),
                    "image_url": image_data.get("url") if "url" in image_data else None
                }
                
                logger.info(f"Image generated successfully: {image_path}")
                return result
            else:
                # Handle API error
                self.generation_stats["failed_generations"] += 1
                return {
                    "status": "error",
                    "message": response.get("error", "Unknown error occurred"),
                    "prompt_used": enhanced_prompt
                }
                
        except Exception as e:
            self.generation_stats["failed_generations"] += 1
            logger.error(f"Image generation error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "prompt_used": prompt
            }

    async def generate_social_media_image(self, prompt: str, platform: str, 
                                        content_type: str = "post", 
                                        style: str = "social_media") -> Dict[str, Any]:
        """Generate platform-optimized social media image"""
        try:
            # Get platform specifications
            platform_spec = self.platform_specs.get(platform.lower(), {})
            content_spec = platform_spec.get(content_type.lower(), {"size": "1024x1024"})
            
            # Platform-specific prompt enhancement
            platform_enhanced_prompt = self._enhance_prompt_for_platform(
                prompt, platform, content_type, style
            )
            
            # Generate image with platform specs
            result = await self.generate_image(
                prompt=platform_enhanced_prompt,
                size=content_spec["size"],
                quality="high",
                style=style
            )
            
            if result["status"] == "success":
                result["platform"] = platform
                result["content_type"] = content_type
                result["aspect_ratio"] = content_spec.get("aspect_ratio", "1:1")
                result["platform_optimized"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Social media image generation error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "platform": platform,
                "content_type": content_type
            }

    async def generate_image_with_text(self, prompt: str, text_content: str,
                                     size: str = "1024x1024") -> Dict[str, Any]:
        """Generate image with embedded text content"""
        try:
            # Create text-enhanced prompt
            text_enhanced_prompt = f"""
            {prompt}
            
            Include the following text clearly visible in the image:
            "{text_content}"
            
            The text should be:
            - Clearly readable and well-positioned
            - Integrated naturally into the design
            - Using appropriate font style for the context
            - High contrast for readability
            - Professional typography
            """
            
            result = await self.generate_image(
                prompt=text_enhanced_prompt,
                size=size,
                quality="high"
            )
            
            if result["status"] == "success":
                result["text_content"] = text_content
                result["text_embedded"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Text image generation error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "text_content": text_content
            }

    async def refine_image(self, original_prompt: str, refinement_request: str) -> Dict[str, Any]:
        """Refine existing image based on feedback"""
        try:
            # Create refinement prompt
            refined_prompt = f"""
            Original concept: {original_prompt}
            
            Refinement request: {refinement_request}
            
            Generate an improved version that addresses the refinement request while maintaining the core concept.
            """
            
            result = await self.generate_image(
                prompt=refined_prompt,
                quality="high"
            )
            
            if result["status"] == "success":
                result["original_prompt"] = original_prompt
                result["refinement_applied"] = refinement_request
                result["is_refinement"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Image refinement error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "original_prompt": original_prompt,
                "refinement_request": refinement_request
            }

    async def generate_image_variations(self, base_prompt: str, variation_count: int = 3) -> Dict[str, Any]:
        """Generate multiple variations of an image concept"""
        try:
            variations = []
            variation_prompts = self._create_variation_prompts(base_prompt, variation_count)
            
            for i, variation_prompt in enumerate(variation_prompts):
                result = await self.generate_image(
                    prompt=variation_prompt,
                    quality="medium"  # Use medium quality for variations to save tokens
                )
                
                if result["status"] == "success":
                    result["variation_number"] = i + 1
                    result["base_prompt"] = base_prompt
                    variations.append(result)
                else:
                    logger.warning(f"Variation {i+1} generation failed: {result.get('message')}")
            
            return {
                "status": "success" if variations else "error",
                "variations": variations,
                "successful_count": len(variations),
                "requested_count": variation_count,
                "base_prompt": base_prompt
            }
            
        except Exception as e:
            logger.error(f"Image variations generation error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "base_prompt": base_prompt,
                "requested_count": variation_count
            }

    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """Enhance prompt with style and quality markers"""
        style_enhancement = self.style_presets.get(style, "")
        
        enhanced = f"{prompt}"
        
        if style_enhancement:
            enhanced += f", {style_enhancement}"
        
        # Add general quality markers
        enhanced += ", high quality, professional composition, excellent lighting"
        
        return enhanced

    def _enhance_prompt_for_platform(self, prompt: str, platform: str, 
                                   content_type: str, style: str) -> str:
        """Enhance prompt specifically for social media platform"""
        enhanced = self._enhance_prompt(prompt, style)
        
        platform_enhancements = {
            "instagram": {
                "feed_post": "Instagram-ready, aesthetic composition, engaging visual, mobile-optimized",
                "story": "Instagram Story format, vertical composition, eye-catching design",
                "reel": "Instagram Reel thumbnail, attention-grabbing, vibrant colors",
                "carousel": "Instagram carousel slide, consistent style, informative design"
            },
            "linkedin": {
                "post": "LinkedIn professional post, business-appropriate, corporate aesthetic",
                "article": "LinkedIn article header, professional design, thought leadership visual"
            },
            "twitter": {
                "post": "Twitter/X post image, concise visual message, trending aesthetic"
            },
            "facebook": {
                "post": "Facebook post image, community-friendly, engaging visual"
            },
            "tiktok": {
                "video": "TikTok video thumbnail, Gen Z aesthetic, viral potential, mobile vertical"
            }
        }
        
        platform_enhancement = platform_enhancements.get(platform, {}).get(content_type, "")
        
        if platform_enhancement:
            enhanced += f", {platform_enhancement}"
        
        return enhanced

    def _create_variation_prompts(self, base_prompt: str, count: int) -> List[str]:
        """Create variation prompts for the same concept"""
        variations = []
        
        variation_styles = [
            "artistic interpretation",
            "modern minimalist style",
            "vintage aesthetic",
            "bold and vibrant colors",
            "soft and dreamy atmosphere",
            "dramatic lighting",
            "abstract interpretation",
            "photorealistic style"
        ]
        
        for i in range(count):
            style = variation_styles[i % len(variation_styles)]
            variation = f"{base_prompt}, {style}, variation {i+1}"
            variations.append(variation)
        
        return variations

    async def _call_openai_api(self, api_data: Dict) -> Dict[str, Any]:
        """Make API call to OpenAI GPT-4o image generation"""
        try:
            import openai
            import os
            
            # API anahtarını al
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return {
                    "success": False,
                    "error": "OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
                }
            
            # OpenAI client oluştur
            client = openai.OpenAI(api_key=api_key)
            
            # API çağrısı yap
            response = client.images.generate(
                model=api_data["model"],
                prompt=api_data["prompt"],
                size=api_data["size"],
                quality=api_data["quality"],
                response_format=api_data["response_format"]
            )
            
            # Yanıtı işle
            if response.data:
                image_data = response.data[0]
                return {
                    "success": True,
                    "data": {
                        "b64_json": image_data.b64_json if hasattr(image_data, 'b64_json') else None,
                        "url": image_data.url if hasattr(image_data, 'url') else None,
                        "revised_prompt": image_data.revised_prompt if hasattr(image_data, 'revised_prompt') else api_data["prompt"]
                    },
                    "tokens_used": 1000  # GPT-4o image generation token kullanımı
                }
            else:
                return {
                    "success": False,
                    "error": "No image data received from API"
                }
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _save_image(self, image_data: Dict, prompt: str) -> str:
        """Save generated image to disk"""
        try:
            # Create images directory if not exists
            images_dir = os.path.join(os.getcwd(), "generated_images")
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            
            # Generate filename
            timestamp = int(time.time())
            safe_prompt = "".join(c for c in prompt[:50] if c.isalnum() or c in (' ', '_')).rstrip()
            safe_prompt = safe_prompt.replace(' ', '_')
            filename = f"{timestamp}_{safe_prompt}.png"
            filepath = os.path.join(images_dir, filename)
            
            # Decode and save image
            if "b64_json" in image_data:
                image_bytes = base64.b64decode(image_data["b64_json"])
                with open(filepath, "wb") as f:
                    f.write(image_bytes)
            elif "url" in image_data:
                # Download from URL
                response = requests.get(image_data["url"])
                with open(filepath, "wb") as f:
                    f.write(response.content)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Image save error: {str(e)}")
            raise e

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get image generation statistics"""
        success_rate = 0
        if self.generation_stats["total_generated"] > 0:
            success_rate = (self.generation_stats["successful_generations"] / 
                          self.generation_stats["total_generated"]) * 100
        
        return {
            "total_generated": self.generation_stats["total_generated"],
            "successful_generations": self.generation_stats["successful_generations"],
            "failed_generations": self.generation_stats["failed_generations"],
            "success_rate": f"{success_rate:.1f}%",
            "average_generation_time": f"{self.generation_stats['average_generation_time']:.2f}s",
            "total_tokens_used": self.generation_stats["total_tokens_used"],
            "supported_platforms": list(self.platform_specs.keys()),
            "available_styles": list(self.style_presets.keys())
        }

def register_tool(registry):
    """Register the ImageGeneratorTool with the MCP registry"""
    registry.register_tool(ImageGeneratorTool())