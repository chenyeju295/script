import requests
import json
import base64
import os
import time
from typing import List, Dict, Optional

# API configurations
API_KEY = "132831df2130ff746e5cd984738dd1857d1a6a348e0bfb8a5d9986499a13b987"

DEFAULT_API_CONFIG = {
    "url": "https://api.together.xyz/v1/images/generations",
    "model": "black-forest-labs/FLUX.1-schnell-Free",
    "key": API_KEY,
    "rate_limit": {
        "max_queries_per_minute": 6,
        "min_delay_seconds": 15
    }
}

DEFAULT_IMAGE_CONFIG = {
    "width": 1440,
    "height": 1440,
    "steps": 2,
    "response_format": "b64_json",
    "output_path": "assets/images"
}

class TogetherApiService:
    def __init__(self, prompts: List[Dict]):
        self.prompts = prompts
        self.api_config = DEFAULT_API_CONFIG
        self.image_config = DEFAULT_IMAGE_CONFIG
        self.last_query_time = time.time() - self.api_config['rate_limit']['min_delay_seconds']
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_config['key']}",
            "Content-Type": "application/json"
        })

    def _get_image_dimensions(self, ratio: Optional[str]) -> tuple:
        if not ratio:
            return (self.image_config['width'], self.image_config['height'])
        
        try:
            # Parse custom ratio (e.g., "16/9", "4/3")
            width_ratio, height_ratio = map(int, ratio.split('/'))
            base_size = 1024
            
            if width_ratio > height_ratio:
                width = base_size
                height = int(base_size * (height_ratio / width_ratio))
            else:
                height = base_size
                width = int(base_size * (width_ratio / height_ratio))
                
            return (width, height)
        except:
            return (self.image_config['width'], self.image_config['height'])

    def generate_image(self, name: str, prompt: str, ratio: Optional[str] = None, subfolder: Optional[str] = None) -> bool:
        try:
            # Handle subfolder in output path
            output_base = self.image_config['output_path']
            if subfolder:
                output_base = os.path.join(output_base, subfolder)
            
            # Create output directory
            os.makedirs(output_base, exist_ok=True)
            
            # Setup output path
            output_path = os.path.join(output_base, f"{name.lower().replace(' ', '_')}.png")
            if os.path.exists(output_path):
                print(f"Image for {name} already exists at: {output_path}")
                return True

            # Rate limiting
            current_time = time.time()
            time_since_last_query = current_time - self.last_query_time
            min_delay = self.api_config['rate_limit']['min_delay_seconds']
            if time_since_last_query < min_delay:
                delay_needed = min_delay - time_since_last_query
                print(f"Rate limit: Waiting {delay_needed:.1f}s before next request...")
                time.sleep(delay_needed)

            # Get dimensions based on ratio
            width, height = self._get_image_dimensions(ratio)

            # Prepare API payload
            payload = {
                "model": self.api_config['model'],
                "prompt": prompt,
                "width": width,
                "height": height,
                "steps": self.image_config['steps'],
                "n": 1,
                "response_format": self.image_config['response_format'],
                "open_in_browser": "true"
            }

            print(f"Generating image for {name} ({width}x{height})...")
            self.last_query_time = time.time()
            response = self.session.post(self.api_config['url'], json=payload)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    image_data = data['data'][0].get('b64_json')
                    if image_data:
                        with open(output_path, 'wb') as f:
                            f.write(base64.b64decode(image_data))
                        print(f"Image saved to: {output_path}")
                        return True
                    
                print("No image data in response")
                return False
            elif response.status_code == 429:
                print("Rate limit exceeded. Adding extra delay...")
                time.sleep(15)  # Extra delay
                return False
            else:
                print(f"API request failed with status: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"Error generating image for {name}: {e}")
            return False

def load_prompts() -> List[Dict]:
    try:
        with open('./generate_images/prompts.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('prompts', [])
    except Exception as e:
        print(f"Error loading prompts.json: {e}")
        return []

def main():
    prompts = load_prompts()
    if not prompts:
        print("No prompts found. Please check prompts.json file.")
        return
        
    service = TogetherApiService(prompts)
    
    # Track assets for pubspec
    assets_paths = set()
    assets_paths.add(DEFAULT_IMAGE_CONFIG['output_path'])
    
    for prompt in prompts:
        print(f"\nProcessing {prompt['name']}...")
        subfolder = prompt.get('subfolder')
        if subfolder:
            assets_paths.add(os.path.join(DEFAULT_IMAGE_CONFIG['output_path'], subfolder))
            
        if service.generate_image(
            prompt['name'], 
            prompt['prompt'],
            ratio=prompt.get('ratio'),
            subfolder=subfolder
        ):
            output_path = DEFAULT_IMAGE_CONFIG['output_path']
            if subfolder:
                output_path = os.path.join(output_path, subfolder)
            filename = f"{prompt['name'].lower().replace(' ', '_')}.png"
            assets_paths.add(os.path.join(output_path, filename))
    
    # Print pubspec entries
    print("\nPubspec entries:")
    print("flutter:\n  assets:")
    for path in sorted(assets_paths):
        print(f"    - {path}")

if __name__ == "__main__":
    main() 