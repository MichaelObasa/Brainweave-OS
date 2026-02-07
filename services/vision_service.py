import base64
import os
import json
from openai import OpenAI
from models.schemas import UniversalMetadata

class VisionService:
    """
    The 'Eyes' of Brainweave. 
    Takes raw image pixels -> Converts to structured JSON metadata.
    """
    def __init__(self):
        # Uses OPENAI_API_KEY and OPENAI_BASE_URL from environment
        # When using OpenRouter, OPENAI_BASE_URL should be https://openrouter.ai/api/v1
        import os
        base_url = os.getenv("OPENAI_BASE_URL", None)
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url
        ) if base_url else OpenAI()

    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_image(self, image_path: str) -> UniversalMetadata:
        print(f"👁️ VisionService: Analyzing {os.path.basename(image_path)}...")
        base64_image = self._encode_image(image_path)
        
        # CHANGED: Using Google's Gemini 2.0 Flash (Free Tier via OpenRouter)
        # It is faster and currently free.
        model_id = "google/gemini-2.0-pro-exp-02-05:free"
        
        try:
            response = self.client.beta.chat.completions.parse(
                model=model_id, 
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a 'Commercial Engineer' Librarian. Analyze this image. If Receipt -> 'Finance'. If Chart -> 'Research'. If Social -> 'Brainweave-OS'."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract metadata."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ],
                    }
                ],
                response_format=UniversalMetadata
            )
            return response.choices[0].message.parsed
        except Exception as e:
            # Fallback: Free models sometimes return raw text instead of strict JSON
            # Try to parse the raw content if structured parsing fails
            print(f"⚠️ Structured parsing failed, trying fallback: {e}")
            try:
                # Get raw response
                response = self.client.beta.chat.completions.create(
                    model=model_id,
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are a 'Commercial Engineer' Librarian. Analyze this image. If Receipt -> 'Finance'. If Chart -> 'Research'. If Social -> 'Brainweave-OS'. Return ONLY valid JSON matching the UniversalMetadata schema."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract metadata as JSON."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ],
                        }
                    ],
                    response_format={"type": "json_object"}
                )
                # Parse raw JSON and validate against schema
                content = response.choices[0].message.content
                # Remove markdown code blocks if present
                if content.strip().startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
                parsed_json = json.loads(content)
                return UniversalMetadata(**parsed_json)
            except Exception as fallback_error:
                print(f"❌ Fallback parsing also failed: {fallback_error}")
                raise