import io
import os
import gc
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from waitress import serve
import requests

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route('/convert', methods=['POST'])
def convert_image():
    try:
        data = request.get_json()
        image_url = data.get('url')
        target_width = int(data.get('width', 100))
        target_height = int(data.get('height', 100))

        if not image_url:
            return jsonify({'error': 'Image URL (url) is required'}), 400

        print(f"Processing: {image_url} -> {target_width}x{target_height}")

        # 1. Download image (stream=True is safer for large files)
        response = requests.get(image_url, timeout=15, stream=True)
        response.raise_for_status()
        
        # 2. Load into Pillow
        # We read the content once. BytesIO is efficient here.
        image_bytes = response.content
        source_img = Image.open(io.BytesIO(image_bytes))
        
        # Immediately clear the raw bytes and response object from memory
        del image_bytes
        response.close()
        del response
        
        # 3. Convert and Resize
        # convert() creates a new image, allowing us to close the source immediately
        img = source_img.convert("RGB")
        source_img.close() # Free source memory
        
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # 4. Build String with Generator (Memory Optimization)
        # Original: list(img.getdata()) -> List of tuples (High Memory)
        # Optimization: Generator expression inside join (Low Memory)
        # This avoids creating a massive intermediate list of pixel tuples.
        
        # We use the generator directly in join. 
        # Since img.getdata() has a known length (__len__), join is efficient.
        pixel_generator = (f"{r},{g},{b}" for r, g, b in img.getdata())
        final_string = ";".join(pixel_generator)
        
        pixel_count = target_width * target_height

        # 5. Cleanup before returning
        # Explicitly close the image and delete reference to free RAM before JSON serialization
        img.close()
        del img
        
        # Optional: Force garbage collection if memory is extremely tight
        # gc.collect() 

        print(f"Success! Processed {pixel_count} pixels.")

        return jsonify({
            'success': True,
            'rgb_data': final_string,
            'width': target_width,
            'height': target_height,
            'pixel_count': pixel_count
        })

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return jsonify({'error': f'Failed to download image: {str(e)}'}), 400
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("  CandyzHub Image Converter API (Optimized)")
    print("  Server engine : waitress")
    print(f"  Listening on : http://{HOST}:{PORT}")
    print("=" * 50)
    serve(app, host=HOST, port=PORT, threads=4)
