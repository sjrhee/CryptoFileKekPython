import requests
import base64
import logging
from .hsm_service import HsmService

logger = logging.getLogger(__name__)

class RemoteHsmService(HsmService):
    def __init__(self, url, client_cert_path, client_key_path, ca_cert_path):
        self.url = url.rstrip('/')
        self.cert = (client_cert_path, client_key_path)
        self.verify = ca_cert_path
        
        # Test connection
        try:
            resp = requests.get(f"{self.url}/health", cert=self.cert, verify=self.verify, timeout=5)
            resp.raise_for_status()
            logger.info(f"Connected to Remote HSM at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Remote HSM: {e}")
            raise

    def encrypt_with_kek(self, plaintext: bytes) -> bytes:
        try:
            plaintext_b64 = base64.b64encode(plaintext).decode('utf-8')
            payload = {'plaintext': plaintext_b64}
            
            resp = requests.post(f"{self.url}/encrypt", json=payload, cert=self.cert, verify=self.verify, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            if 'error' in data:
                raise Exception(data['error'])
                
            ciphertext_b64 = data['ciphertext']
            return base64.b64decode(ciphertext_b64)
        except Exception as e:
            logger.error(f"Remote HSM Encrypt failed: {e}")
            raise

    def decrypt_with_kek(self, ciphertext: bytes) -> bytes:
        try:
            ciphertext_b64 = base64.b64encode(ciphertext).decode('utf-8')
            payload = {'ciphertext': ciphertext_b64}
            
            resp = requests.post(f"{self.url}/decrypt", json=payload, cert=self.cert, verify=self.verify, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            if 'error' in data:
                raise Exception(data['error'])
                
            plaintext_b64 = data['plaintext']
            return base64.b64decode(plaintext_b64)
        except Exception as e:
            logger.error(f"Remote HSM Decrypt failed: {e}")
            raise
