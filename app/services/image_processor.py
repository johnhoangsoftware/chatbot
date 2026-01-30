"""
Image processing service using Vision Language Models (VLLM).
Supports multiple providers: Gemini, Local Ollama.
"""

import io
import base64
import logging
from typing import Optional
from PIL import Image
import google.generativeai as genai

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Process images using Vision Language Models to extract text, diagrams, UI designs, etc."""
    
    DEFAULT_PROMPTS = {
        "technical": """Analyze this image from a technical document. Describe:
1. Main content (text, diagram, chart, table, UI design, flowchart, etc.)
2. Any visible text or labels
3. Technical details and relationships shown
4. Key elements and their purpose
Be concise but comprehensive.""",
        
        "ui_design": """Analyze this UI/screen design image. Describe:
1. UI components visible (buttons, forms, navigation, etc.)
2. Layout and structure
3. Any text/labels visible
4. Design patterns used
Be specific about UI elements.""",
        
        "general": """Describe this image concisely, including any text, diagrams, charts, or visual elements shown."""
    }
    
    def __init__(self, provider: str = "gemini"):
        """
        Initialize image processor.
        
        Args:
            provider: "gemini" or "ollama"
        """
        self.provider = provider.lower()
        
        if self.provider not in ["gemini", "ollama"]:
            raise ValueError(f"Unsupported provider: {provider}. Use 'gemini' or 'ollama'")
        
        # Initialize provider
        if self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "ollama":
            self._init_ollama()
    
    def _init_gemini(self):
        """Initialize Gemini Vision API."""
        from ..config import get_settings
        settings = get_settings()
        
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("Initialized Gemini Vision model")
    
    def _init_ollama(self):
        """Initialize Ollama local model."""
        try:
            import ollama
            self.ollama_client = ollama
        except ImportError:
            raise ImportError("ollama package is required for local model. Install with: pip install ollama")
        
        from ..config import get_settings
        settings = get_settings()
        self.ollama_model = settings.ollama_vision_model
        logger.info(f"Initialized Ollama with model: {self.ollama_model}")
    
    def analyze_image(
        self, 
        image_data: bytes, 
        context: str = "technical",
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Analyze image and extract description.
        
        Args:
            image_data: Raw image bytes (PNG, JPEG, etc.)
            context: Context type - "technical", "ui_design", or "general"
            custom_prompt: Optional custom prompt to override default
            
        Returns:
            Description/analysis of the image
        """
        prompt = custom_prompt or self.DEFAULT_PROMPTS.get(context, self.DEFAULT_PROMPTS["general"])
        
        try:
            if self.provider == "gemini":
                return self._call_gemini_vision(image_data, prompt)
            elif self.provider == "ollama":
                return self._call_ollama_vision(image_data, prompt)
        except Exception as e:
            logger.error(f"Error analyzing image with {self.provider}: {e}")
            return f"[Image - analysis failed: {str(e)}]"
    
    def _call_gemini_vision(self, image_data: bytes, prompt: str) -> str:
        """Call Gemini Vision API."""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Generate content
            response = self.meodl.generate_content([prompt, image])
            
            if response and response.text:
                return response.text.strip()
            else:
                return "[Image - no description available]"
                
        except Exception as e:
            logger.error(f"Gemini Vision API error: {e}")
            raise
    
    def _call_ollama_vision(self, image_data: bytes, prompt: str) -> str:
        """Call local Ollama vision model."""
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Call Ollama
            response = self.ollama_client.chat(
                model=self.ollama_model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_b64]
                }]
            )
            
            if response and 'message' in response and 'content' in response['message']:
                return response['message']['content'].strip()
            else:
                return "[Image - no description available]"
                
        except Exception as e:
            logger.error(f"Ollama vision error: {e}")
            raise
    
    def batch_analyze_images(
        self, 
        images: list[bytes], 
        context: str = "technical"
    ) -> list[str]:
        """
        Analyze multiple images in batch.
        
        Args:
            images: List of image bytes
            context: Context type for all images
            
        Returns:
            List of descriptions
        """
        results = []
        for i, image_data in enumerate(images):
            try:
                description = self.analyze_image(image_data, context)
                results.append(description)
                logger.debug(f"Analyzed image {i+1}/{len(images)}")
            except Exception as e:
                logger.error(f"Failed to analyze image {i+1}: {e}")
                results.append(f"[Image {i+1} - analysis failed]")
        
        return results
    
    @staticmethod
    def classify_image_type(description: str) -> str:
        """
        Classify image type based on description.
        
        Returns: "diagram", "chart", "ui_design", "photo", "figure", "other"
        """
        description_lower = description.lower()
        
        if any(word in description_lower for word in ["flowchart", "diagram", "uml", "architecture"]):
            return "diagram"
        elif any(word in description_lower for word in ["chart", "graph", "plot", "bar chart", "pie chart"]):
            return "chart"
        elif any(word in description_lower for word in ["ui", "interface", "screen", "button", "form", "navigation"]):
            return "ui_design"
        elif any(word in description_lower for word in ["photo", "photograph", "picture"]):
            return "photo"
        elif any(word in description_lower for word in ["figure", "illustration", "schematic"]):
            return "figure"
        else:
            return "other"


def get_image_processor(enabled: bool = True) -> Optional[ImageProcessor]:
    """
    Factory function to get image processor based on config.
    
    Args:
        enabled: Whether image processing is enabled
        
    Returns:
        ImageProcessor instance or None if disabled
    """
    if not enabled:
        return None
    
    from ..config import get_settings
    settings = get_settings()
    
    try:
        processor = ImageProcessor(provider=settings.vllm_provider)
        return processor
    except Exception as e:
        logger.warning(f"Failed to initialize image processor: {e}")
        return None
