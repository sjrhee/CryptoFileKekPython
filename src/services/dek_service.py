import secrets
import base64
from .hsm_service import HsmService
import logging

logger = logging.getLogger(__name__)

class DekService:
    def __init__(self, hsm_service: HsmService):
        self.hsm_service = hsm_service
        self.dek_size = 32 # 256 bits

    def generate_dek(self) -> bytes:
        logger.info(f"Generating new DEK ({self.dek_size*8} bits)")
        return secrets.token_bytes(self.dek_size)

    def encrypt_dek(self, dek: bytes) -> bytes:
        logger.debug("Encrypting DEK with HSM KEK")
        return self.hsm_service.encrypt_with_kek(dek)

    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        logger.debug("Decrypting DEK with HSM KEK")
        return self.hsm_service.decrypt_with_kek(encrypted_dek)

    def encrypt_dek_to_base64(self, dek: bytes) -> str:
        encrypted_bytes = self.encrypt_dek(dek)
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt_dek_from_base64(self, encrypted_dek_b64: str) -> bytes:
        encrypted_bytes = base64.b64decode(encrypted_dek_b64)
        return self.decrypt_dek(encrypted_bytes)
