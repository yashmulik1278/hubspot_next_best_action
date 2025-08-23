# listener.py
import os
import json
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def receive():
     # 1. Parse the JSON payload
    payload = request.get_json()

    # 2. Ensure the target directory exists
    folder_name = 'hubspot_request'
    # __file__ is the current script; locate folder alongside it
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(base_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    # 3. Build a unique filename (here using UNIX timestamp)
    timestamp = int(time.time())
    filename = f"{timestamp}.txt"
    file_path = os.path.join(target_dir, filename)

    # 4. Write the JSON payload to that file
    with open(file_path, 'w') as f:
        # json.dump writes compact JSON; indent=2 makes it pretty-printed
        json.dump(payload, f, indent=2)

     # 5. (Optional) Log to console
    app.logger.info("Payload saved to %s: %s", file_path, payload)

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    # Run on port 5001 so it doesn't clash with your forwarder
    app.run(port=5001)
