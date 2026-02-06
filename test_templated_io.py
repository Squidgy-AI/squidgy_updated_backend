"""
Test script for Templated.io API integration
"""

import requests
import json
import os

# Templated.io API configuration
API_URL = "https://api.templated.io/v1/render"
LAYERS_URL = "https://api.templated.io/v1/template"

# Set your API key here or via environment variable
API_KEY = os.getenv("TEMPLATED_API_KEY", "766b3695-1bf1-4f6e-b759-34e7376a12be")


def get_template_layers(template_id: str, include_locked: bool = True):
    """
    Get all layers of a template with their current content/values.
    
    Args:
        template_id: The template ID
        include_locked: Include locked layers (default True)
    
    Returns:
        List of layer objects with name, type, description, and current value
    """
    # Use retrieve template endpoint with includeLayers=true to get current values
    url = f"{LAYERS_URL}/{template_id}?includeLayers=true"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print("=" * 60)
    print("Get Template Layers (with current content)")
    print("=" * 60)
    print(f"\nTemplate ID: {template_id}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            template_data = response.json()
            layers = template_data.get('layers', [])
            
            print(f"\n✅ Found {len(layers)} layers:\n")
            
            for layer in layers:
                layer_name = layer.get('name', layer.get('layer', 'unknown'))
                layer_type = layer.get('type', 'unknown')
                description = layer.get('description', '')
                
                print(f"  📌 {layer_name}")
                print(f"     Type: {layer_type}")
                if description:
                    print(f"     Description: {description}")
                
                # Show current content based on layer type
                if layer_type == 'text':
                    current_text = layer.get('text', layer.get('content', ''))
                    if current_text:
                        # Truncate long text
                        display_text = current_text[:50] + "..." if len(current_text) > 50 else current_text
                        print(f"     Current: \"{display_text}\"")
                elif layer_type == 'image':
                    current_url = layer.get('image_url', layer.get('src', layer.get('url', '')))
                    if current_url:
                        display_url = current_url[:60] + "..." if len(current_url) > 60 else current_url
                        print(f"     Current: {display_url}")
                elif layer_type in ['shape', 'rectangle', 'ellipse']:
                    current_fill = layer.get('fill', layer.get('color', ''))
                    if current_fill:
                        print(f"     Current fill: {current_fill}")
                
                print()
            
            return layers
        else:
            print(f"\n❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        return None


def test_templated_io(template_id: str, layers_config: dict = None):
    """Test Templated.io image generation with the provided parameters."""
    
    # Use provided layers or default example
    if layers_config is None:
        layers_config = {
            "Boost": {"text": "The future"},
            "productivity": {"text": "is autonomous"},
            "by-20%": {"text": "starts now"},
        }
    
    payload = {
        "template": template_id,
        "layers": layers_config,
        "format": "png"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print("=" * 60)
    print("Templated.io API Test")
    print("=" * 60)
    print(f"\nAPI URL: {API_URL}")
    print(f"Template ID: {payload['template']}")
    print(f"Format: {payload['format']}")
    print(f"\nLayers being modified:")
    for layer_name, layer_config in payload['layers'].items():
        print(f"  - {layer_name}: {layer_config}")
    
    print("\n" + "-" * 60)
    print("Sending request...")
    print("-" * 60)
    
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS!")
            print(f"Response: {json.dumps(result, indent=2)}")
            
            # If there's a render URL, print it
            if "render_url" in result:
                print(f"\n🖼️  Rendered Image URL: {result['render_url']}")
            elif "url" in result:
                print(f"\n🖼️  Rendered Image URL: {result['url']}")
                
        else:
            print("\n❌ ERROR!")
            print(f"Response Body: {response.text}")
            
            # Try to parse error details
            try:
                error_data = response.json()
                print(f"\nError Details: {json.dumps(error_data, indent=2)}")
            except:
                pass
                
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out after 60 seconds")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

    print("\n" + "=" * 60)


def test_with_different_endpoints():
    """Test with alternative API endpoints if the main one fails."""
    
    endpoints = [
        "https://api.templated.io/v1/render",
        "https://api.templated.io/v2/render",
        "https://api.templated.io/render",
    ]
    
    payload = {
        "template": "549259c2-e1fc-45aa-b32f-1984dab5768d",
        "layers": {
            "Boost": {
                "text": "The future",
                "autofit": "width"
            },
            "productivity": {
                "text": "is autonomous",
                "autofit": "height"
            },
            "by-20%": {
                "text": "starts now",
                "autofit": "width"
            },
            "center-circle": {
                "fill": "#000321"
            },
            "top-left-circle": {
                "fill": "#0038FF"
            },
            "bg-image": {
                "image_url": "https://images.unsplash.com/photo-1761912149936-8f662fc2a13e?w=1080"
            },
            "ait-logo-bare": {
                "image_url": "https://framerusercontent.com/images/N42WJeDninXMBZaNFNcS1YdJxs.png"
            }
        },
        "format": "png"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("\n" + "=" * 60)
    print("Testing Multiple Endpoints")
    print("=" * 60)
    
    for endpoint in endpoints:
        print(f"\nTrying: {endpoint}")
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ This endpoint works!")
                print(f"  Response: {response.json()}")
                break
            else:
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    # Check if API key is set
    if API_KEY == "YOUR_API_KEY_HERE":
        print("⚠️  Please set your API key:")
        print("   Option 1: set TEMPLATED_API_KEY=your_key")
        print("   Option 2: Edit line 13 in this script\n")
    
    # Get template ID from user
    print("\n" + "=" * 60)
    print("Templated.io - Template Layer Inspector")
    print("=" * 60)
    TEMPLATE_ID = input("\n📋 Enter Template ID: ").strip()
    
    if not TEMPLATE_ID:
        print("❌ No template ID provided. Exiting.")
        exit(1)
    
    # First, get template layers to see what's available
    print("\n🔍 STEP 1: Get template layers...\n")
    layers = get_template_layers(TEMPLATE_ID)
    
    if layers:
        print("\n" + "=" * 60)
        print("📋 LAYER SUMMARY (for rendering):")
        print("=" * 60)
        for layer in layers:
            layer_type = layer.get('type', 'unknown')
            layer_name = layer.get('layer', 'unknown')
            if layer_type == 'text':
                print(f'  "{layer_name}": {{"text": "your text here"}}')
            elif layer_type == 'image':
                print(f'  "{layer_name}": {{"image_url": "https://..."}}')
            elif layer_type in ['shape', 'rectangle', 'ellipse']:
                print(f'  "{layer_name}": {{"fill": "#HEXCOLOR"}}')
            else:
                print(f'  "{layer_name}": {{...}}  # type: {layer_type}')
        print()
    
    # Ask if user wants to proceed with rendering
    proceed = input("\n🎨 Proceed with test render? (y/n): ").strip().lower()
    if proceed == 'y':
        # Build layers config from user input
        print("\n📝 Enter layer values (press Enter to skip a layer):\n")
        layers_config = {}
        if layers:
            for layer in layers:
                layer_name = layer.get('name', layer.get('layer', ''))
                layer_type = layer.get('type', 'unknown')
                
                # Get current value for display
                current_val = ""
                if layer_type == 'text':
                    current_val = layer.get('text', layer.get('content', ''))
                    if current_val:
                        current_val = f" [current: \"{current_val[:30]}...\"]" if len(current_val) > 30 else f" [current: \"{current_val}\"]"
                    value = input(f"  {layer_name} (text){current_val}: ").strip()
                    if value:
                        layers_config[layer_name] = {"text": value}
                elif layer_type == 'image':
                    current_val = layer.get('image_url', layer.get('src', ''))
                    if current_val:
                        current_val = " [has image]"
                    value = input(f"  {layer_name} (image URL){current_val}: ").strip()
                    if value:
                        layers_config[layer_name] = {"image_url": value}
                elif layer_type in ['shape', 'rectangle', 'ellipse']:
                    current_val = layer.get('fill', layer.get('color', ''))
                    if current_val:
                        current_val = f" [current: {current_val}]"
                    value = input(f"  {layer_name} (fill color){current_val}: ").strip()
                    if value:
                        layers_config[layer_name] = {"fill": value}
        
        if not layers_config:
            print("⚠️  No layers configured, using defaults")
            layers_config = None
        
        test_templated_io(TEMPLATE_ID, layers_config)
    
    # Optionally test different endpoints
    # test_with_different_endpoints()
