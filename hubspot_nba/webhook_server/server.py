from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# You can also pull this from an environment variable for flexibility:
FORWARD_URL = os.getenv('FORWARD_URL', 'https://eb75-2401-4900-1c42-77b1-799f-aaec-b2e9-54b2.ngrok-free.app')

@app.before_request
def startup_message():
    print("🚀 Forwarder starting up and listening on /webhook")
    app.logger.info("Forwarder ready, forwarding to %s", FORWARD_URL)

@app.route('/webhook', methods=['POST'])
def webhook():
    print("📥 /webhook endpoint hit")
    data = request.get_json()
    print(f"🔍 Received data: {data}")
    app.logger.info("Received data: %s", data)

    try:
        # Forward the payload to the public URL
        print(f"➡️ Forwarding payload to {FORWARD_URL}...")
        resp = requests.post(FORWARD_URL, json=data, timeout=5)
        resp.raise_for_status()
        print(f"✅ Forwarded successfully: status {resp.status_code}")
        print(f"📄 Response body: {resp.text}")
        app.logger.info("Forwarded to %s, status %s, response: %s",
                        FORWARD_URL, resp.status_code, resp.text)
    except requests.exceptions.RequestException as e:
        print(f"❌ Error forwarding to {FORWARD_URL}: {e}")
        app.logger.error("Error forwarding to %s: %s", FORWARD_URL, e)
        # Return a 500 so HubSpot (or other sender) can retry if desired
        return jsonify({'status': 'forward_error', 'error': str(e)}), 500

    print("🏁 Done handling /webhook request")
    return jsonify({'status': 'received_and_forwarded'}), 200

if __name__ == '__main__':
    # Make sure you have installed requests: pip install requests
    app.run(host='0.0.0.0', port=5000, debug=True)