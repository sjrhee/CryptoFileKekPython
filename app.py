import os
from dotenv import load_dotenv

load_dotenv()

import base64
from flask import Flask, render_template, jsonify, request, send_from_directory
from src.services.file_storage_service import FileStorageService
from src.services.hsm_service import HsmService, SimulatedHsmService, RealHsmService, AwsKmsService
from src.services.dek_service import DekService
from src.services.file_encryption_service import FileEncryptionService

import logging

# Initialize App
app = Flask(__name__)
app.config['DATA_DIR'] = os.path.join(os.getcwd(), 'DATA')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB Limit

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure DATA directory exists
if not os.path.exists(app.config['DATA_DIR']):
    os.makedirs(app.config['DATA_DIR'])

# Initialize Services
# By default start with Simulated HSM. Real HSM can be enabled via settings.
hsm_service = SimulatedHsmService()
current_hsm_type = 'SIMULATED'
dek_service = DekService(hsm_service)
file_storage_service = FileStorageService(app.config['DATA_DIR'])
file_encryption_service = FileEncryptionService()

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': f"Internal Server Error: {str(error)}"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # pass through HTTP errors
    if hasattr(e, 'code'):
        return jsonify({'success': False, 'message': str(e)}), e.code
    # now you're handling non-HTTP exceptions only
    return jsonify({'success': False, 'message': f"Unexpected Error: {str(e)}"}), 500

# API Routes

@app.route('/api/config/defaults', methods=['GET'])
def get_config_defaults():
    return jsonify({
        'luna': {
            'pin': os.getenv('LUNA_HSM_PIN', '12341234'),
            'slotId': os.getenv('LUNA_HSM_SLOT', '1'),
            'label': os.getenv('LUNA_HSM_LABEL', 'master_key')
        },
        'pse': {
            'pin': os.getenv('PSE_HSM_PIN', '1111'),
            'slotId': os.getenv('PSE_HSM_SLOT', '1'),
            'label': os.getenv('PSE_HSM_LABEL', 'master_key')
        },
        'aws': {
            'region': os.getenv('AWS_REGION', 'ap-northeast-2'),
            'keyId': os.getenv('AWS_KMS_KEY_ID', ''),
            'accessKey': os.getenv('AWS_ACCESS_KEY_ID', ''),
            'secretKey': os.getenv('AWS_SECRET_ACCESS_KEY', '')
        }
    })




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
    hsm_type = 'SIMULATED'
    if isinstance(hsm_service, RealHsmService):
        # We need to distinguish between PSE and LUNA based on lib_path or a stored flag.
        # simpler way: store a global hsm_type_str
        pass 
    
    # Actually, let's just use a global variable or attribute since we are stateless-ish here
    # accessing the global hsm_type variable defined effectively by config
    return jsonify({'hsmType': current_hsm_type})

@app.route('/api/hsm/config', methods=['POST'])
def hsm_config():
    global hsm_service, dek_service, current_hsm_type
    data = request.json
    
    # New parameter hsmType: 'SIMULATED' | 'PSE' | 'LUNA'
    # Fallback to useHsm for backward compatibility if needed, but we are changing frontend too.
    hsm_type = data.get('hsmType', 'SIMULATED')
    
    
    # Defaults depend on type
    default_pin = ''
    default_label = 'mk'
    default_slot = 0
    
    if hsm_type == 'LUNA':
        default_pin = os.getenv('LUNA_HSM_PIN', '')
        default_label = os.getenv('LUNA_HSM_LABEL', 'master_key')
        default_slot = int(os.getenv('LUNA_HSM_SLOT', '1'))
    elif hsm_type == 'PSE':
        default_pin = os.getenv('PSE_HSM_PIN', '')
        default_label = os.getenv('PSE_HSM_LABEL', 'master_key')
        default_slot = int(os.getenv('PSE_HSM_SLOT', '1'))
    elif hsm_type == 'AWS':
        default_label = os.getenv('AWS_KMS_KEY_ID', '') # Use label field for KeyID


    pin = data.get('pin', default_pin)
    label = data.get('label', default_label)
    slot_id = data.get('slotId', default_slot)


    try:
        if hsm_type == 'LUNA':

            # Luna Specifics
            lib_path = os.getenv('LUNA_LIB_PATH', '/opt/safenet/lunaclient/lib/libCryptoki2_64.so')

            # Note: User provided slot and pin are used, but frontend will default them.
            new_hsm = RealHsmService(lib_path=lib_path, label=label, slot_id=slot_id)
            new_hsm.login(pin)
            hsm_service = new_hsm
            current_hsm_type = 'LUNA'
            
        elif hsm_type == 'PSE':
            # PSE HSM
            # User specified path:
            pse_lib_path = os.getenv('PSE_LIB_PATH', '/opt/safenet/protecttoolkit7/ptk/lib/libcryptoki.so')

            
            new_hsm = RealHsmService(lib_path=pse_lib_path, label=label, slot_id=slot_id)
            new_hsm.login(pin)
            hsm_service = new_hsm
            current_hsm_type = 'PSE'
            
        elif hsm_type == 'AWS':
            # AWS KMS
            # User might provide keys in request or we use env vars (priority to env if not provided or empty)
            # For simplicity, we assume env vars or IAM role if not provided in UI (though UI fields don't exist yet for keys)
            
            access_key = os.getenv('AWS_ACCESS_KEY_ID')
            secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            region = os.getenv('AWS_REGION', 'ap-northeast-2')
            
            # Label field is re-used for KeyID
            kms_key_id = label 
            
            new_hsm = AwsKmsService(key_id=kms_key_id, access_key=access_key, secret_key=secret_key, region=region)
            hsm_service = new_hsm
            current_hsm_type = 'AWS'

        else:
            # SIMULATED

            hsm_service = SimulatedHsmService()
            current_hsm_type = 'SIMULATED'
        
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
