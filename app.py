import os
import base64
from flask import Flask, render_template, jsonify, request, send_from_directory
from src.services.file_storage_service import FileStorageService
from src.services.hsm_service import HsmService, SimulatedHsmService, RealHsmService
from src.services.dek_service import DekService
from src.services.file_encryption_service import FileEncryptionService

# Initialize App
app = Flask(__name__)
app.config['DATA_DIR'] = os.path.join(os.getcwd(), 'DATA')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB Limit

# Ensure DATA directory exists
if not os.path.exists(app.config['DATA_DIR']):
    os.makedirs(app.config['DATA_DIR'])

# Initialize Services
# By default start with Simulated HSM. Real HSM can be enabled via settings.
hsm_service = SimulatedHsmService()
dek_service = DekService(hsm_service)
file_storage_service = FileStorageService(app.config['DATA_DIR'])
file_encryption_service = FileEncryptionService()

@app.route('/')
def index():
    return render_template('index.html')

# API Routes

@app.route('/api/files/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
    if file:
        try:
            # Save directly to DATA dir
            path = file_storage_service.save_file(file.filename, file.read())
            return jsonify({'success': True, 'message': 'File uploaded successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/files/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['DATA_DIR'], filename, as_attachment=True)
    except Exception as e:
        return str(e), 404

@app.route('/api/files/cleanup-temp', methods=['POST'])
def cleanup_temp():
    # Python version might not need explicit temp cleanup if we don't create temp files
    # but we can implement it if needed.
    return jsonify({'success': True})


@app.route('/api/files/list', methods=['GET'])
def list_files():
    try:
        files = file_storage_service.list_files()
        return jsonify({'success': True, 'data': files})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/hsm/status', methods=['GET'])
def hsm_status():
    use_hsm = isinstance(hsm_service, RealHsmService)
    return jsonify({'useHsm': use_hsm})

@app.route('/api/hsm/config', methods=['POST'])
def hsm_config():
    global hsm_service, dek_service
    data = request.json
    use_hsm = data.get('useHsm', False)
    pin = data.get('pin', '')
    label = data.get('label', 'mk') # Default to 'mk' if not provided
    slot_id = data.get('slotId', 0)

    try:
        if use_hsm:
            # Switch to Real HSM
            new_hsm = RealHsmService(label=label, slot_id=slot_id)
            new_hsm.login(pin) # Try login
            hsm_service = new_hsm
        else:
            # Switch to Simulated HSM
            hsm_service = SimulatedHsmService()
        
        # Re-inject dependency
        dek_service = DekService(hsm_service)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# --- Encryption Flow ---

@app.route('/api/encrypt/select', methods=['POST'])
def encrypt_select():
    data = request.json
    filename = data.get('filename')
    try:
        # Verify file exists
        path = file_storage_service.get_file_path(filename)
        if not os.path.exists(path):
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        # In Python we can just return the filename as ID or handle, 
        # but to match Java flow let's return a "fileId" (which is just the filename here)
        return jsonify({'success': True, 'data': {'fileId': filename}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/encrypt/process/<file_id>', methods=['POST'])
def encrypt_process(file_id):
    filename = file_id # In this simple impl, ID is filename
    try:
        # 1. Read Original File
        file_data = file_storage_service.read_file(filename)
        
        # 2. Generate DEK
        dek = dek_service.generate_dek()
        
        # 3. Encrypt File
        encrypted_data = file_encryption_service.encrypt_file_data(file_data, dek)
        
        # 4. Save Encrypted File
        encrypted_filename = filename + ".encrypted"
        file_storage_service.save_file(encrypted_filename, encrypted_data)
        
        # 5. Encrypt DEK (Wrap)
        encrypted_dek = dek_service.encrypt_dek(dek)
        
        # 6. Save Encrypted DEK
        dek_filename = filename + ".dek"
        file_storage_service.save_file(dek_filename, encrypted_dek)
        
        # 7. Prepare Result
        encrypted_dek_b64 = base64.b64encode(encrypted_dek).decode('utf-8')
        
        return jsonify({
            'success': True, 
            'data': {
                'originalFilename': filename,
                'originalSize': len(file_data),
                'encryptedSize': len(encrypted_data),
                'encryptedFilename': encrypted_filename,
                'encryptedDek': encrypted_dek_b64
            }
        })
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# --- Decryption Flow ---

@app.route('/api/decrypt/select', methods=['POST'])
def decrypt_select():
    data = request.json
    enc_filename = data.get('encryptedFilename')
    dek_filename = data.get('dekFilename')
    
    try:
        # Verify files exist
        p1 = file_storage_service.get_file_path(enc_filename)
        p2 = file_storage_service.get_file_path(dek_filename)
        
        if not os.path.exists(p1) or not os.path.exists(p2):
             return jsonify({'success': False, 'message': 'One or more files not found'}), 404
             
        # Create a "Job ID" or complex object if needed, checking compatibility etc.
        # For now, simplistic approach:
        return jsonify({'success': True, 'data': {'fileId': f"{enc_filename}|{dek_filename}"}})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/decrypt/process/<file_id>', methods=['POST'])
def decrypt_process(file_id):
    try:
        # Parse composite ID
        enc_filename, dek_filename = file_id.split('|')
        
        # 1. Read Encrypted DEK
        encrypted_dek = file_storage_service.read_file(dek_filename)
        
        # 2. Decrypt DEK (Unwrap)
        try:
            dek = dek_service.decrypt_dek(encrypted_dek)
        except Exception as e:
             return jsonify({'success': False, 'message': f"DeK Decryption Failed: {str(e)}"}), 500
             
        # 3. Read Encrypted File
        encrypted_data = file_storage_service.read_file(enc_filename)
        
        # 4. Decrypt File
        try:
            plaintext = file_encryption_service.decrypt_file_data(encrypted_data, dek)
        except Exception as e:
             return jsonify({'success': False, 'message': f"File Decryption Failed (Bad Key?): {str(e)}"}), 500

        # 5. Restore Filename (Remove .encrypted)
        original_filename = enc_filename.replace('.encrypted', '')
        if original_filename == enc_filename:
            original_filename += ".restored"
            
        # 6. Save Decrypted File
        file_storage_service.save_file(original_filename, plaintext)
        
        return jsonify({
            'success': True,
            'data': {
                'originalFilename': original_filename
            }
        })

    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True)
