import base64
import os
from openai import OpenAI
from models.schemas import UniversalMetadata

class VisionService:
    """
    The 'Eyes' of Brainweave. 
    Takes raw image pixels -> Converts to structured JSON metadata.
    """
    def __init__(self):
        self.client = OpenAI() # Uses your env OPENAI_API_KEY

    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_image(self, image_path: str) -> UniversalMetadata:
        print(f"👁️ VisionService: Analyzing {os.path.basename(image_path)}...")
        base64_image = self._encode_image(image_path)
        
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o", 
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