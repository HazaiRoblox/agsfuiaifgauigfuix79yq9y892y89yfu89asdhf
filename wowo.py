from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from waitress import serve
import io
import requests

app = Flask(__name__)
CORS(app)  # Allows requests from any origin

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
HOST = "0.0.0.0"   # Listen on all network interfaces
PORT = 5000         # Change this if you need a different port

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route('/convert', methods=['POST'])
def convert_image():
    try:
        data = request.get_json()
        image_url  = data.get('url')
        target_width  = int(data.get('width', 100))
        target_height = int(data.get('height', 100))

        if not image_url:
            return jsonify({'error': 'Image URL (url) is required'}), 400

        print(f"Processing: {image_url} -> {target_width}x{target_height}")

        # Download image from the provided URL
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()

        # Open and convert to RGB
        img = Image.open(io.BytesIO(response.content))
        img = img.convert("RGB")

        # Resize using LANCZOS for quality
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # Build the semicolon-separated RGB string
        pixels = list(img.getdata())
        output_data  = [f"{r},{g},{b}" for r, g, b in pixels]
        final_string = ";".join(output_data)

        print(f"Success! Processed {len(pixels)} pixels.")

        return jsonify({
            'success':     True,
            'rgb_data':    final_string,
            'width':       target_width,
            'height':      target_height,
            'pixel_count': len(pixels)
        })

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return jsonify({'error': f'Failed to download image: {str(e)}'}), 400
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

# ─────────────────────────────────────────────
# STARTUP  (waitress — production-ready server)
# ─────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("  CandyzHub Image Converter API")
    print("  Server engine : waitress")
    print(f"  Listening on : http://{HOST}:{PORT}")
    print("=" * 50)
    serve(app, host=HOST, port=PORT, threads=4)