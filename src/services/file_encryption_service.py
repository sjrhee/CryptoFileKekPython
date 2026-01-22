import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging
import secrets

logger = logging.getLogger(__name__)

class FileEncryptionService:
    def __init__(self):
        self.backend = default_backend()

    def encrypt_file_data(self, data: bytes, dek: bytes) -> bytes:
        """
        Encrypts file data using AES-GCM.
        Returns IV + Ciphertext (incl tag)
        """
        logger.info(f"Encrypting data size: {len(data)}")
        iv = secrets.token_bytes(12)
        encryptor = Cipher(
            algorithms.AES(dek),
            modes.GCM(iv),
            backend=self.backend
        ).encryptor()

        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Result: IV + Ciphertext + Tag
        # Note: GCM encryptor.finalize() does NOT return the tag appended to ciphertext in 'cryptography' lib?
        # Actually in `cryptography` library, `encryptor.tag` must be accessed after finalize().
        # Ciphertext result of update+finalize is just the ciphertext.
        
        tag = encryptor.tag
        return iv + ciphertext + tag

    def decrypt_file_data(self, encrypted_data: bytes, dek: bytes) -> bytes:
        """
        Decrypts file data using AES-GCM.
        Expects IV + Ciphertext + Tag
        """
        logger.info(f"Decrypting data size: {len(encrypted_data)}")
        if len(encrypted_data) < 28:
            raise ValueError("Data too short")

        iv = encrypted_data[:12]
        tag = encrypted_data[-16:]
        ciphertext = encrypted_data[12:-16]

        decryptor = Cipher(
            algorithms.AES(dek),
            modes.GCM(iv, tag),
            backend=self.backend
        ).decryptor()

        return decryptor.update(ciphertext) + decryptor.finalize()
