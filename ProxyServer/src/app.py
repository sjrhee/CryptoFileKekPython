import os
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from services.hsm_service import HsmService

# Load Env
load_dotenv()

app = Flask(__name__)
hsm_service = HsmService()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/encrypt', methods=['POST'])
def encrypt():
    try:
        data = request.json
        plaintext_b64 = data.get('plaintext')
        if not plaintext_b64:
             return jsonify({'error': 'plaintext field required'}), 400
        
        plaintext = base64.b64decode(plaintext_b64)
        ciphertext = hsm_service.encrypt(plaintext)
        ciphertext_b64 = base64.b64encode(ciphertext).decode('utf-8')
        
        return jsonify({'ciphertext': ciphertext_b64})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/decrypt', methods=['POST'])
def decrypt():
    try:
        data = request.json
        ciphertext_b64 = data.get('ciphertext')
        if not ciphertext_b64:
             return jsonify({'error': 'ciphertext field required'}), 400
        
        ciphertext = base64.b64decode(ciphertext_b64)
        plaintext = hsm_service.decrypt(ciphertext)
        plaintext_b64 = base64.b64encode(plaintext).decode('utf-8')
        
        return jsonify({'plaintext': plaintext_b64})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
