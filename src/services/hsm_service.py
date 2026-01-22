from abc import ABC, abstractmethod
import os
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging
# For Real HSM
try:
    import PyKCS11
except ImportError:
    PyKCS11 = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HsmService(ABC):
    @abstractmethod
    def encrypt_with_kek(self, plaintext: bytes) -> bytes:
        pass

    @abstractmethod
    def decrypt_with_kek(self, ciphertext: bytes) -> bytes:
        pass

class SimulatedHsmService(HsmService):
    def __init__(self, key_file='simulated_kek.key', key_size=32):
        self.key_file = key_file
        self.key_size = key_size
        self.kek = self._load_or_generate_kek()

    def _load_or_generate_kek(self):
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, 'rb') as f:
                    logger.info(f"Loaded existing KEK from {self.key_file}")
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to load KEK: {e}")
        
        logger.info("Generating new Simulated KEK")
        kek = secrets.token_bytes(self.key_size)
        try:
            with open(self.key_file, 'wb') as f:
                f.write(kek)
        except Exception as e:
            logger.error(f"Failed to save KEK: {e}")
        return kek

    def encrypt_with_kek(self, plaintext: bytes) -> bytes:
        # Simulate AES-GCM encryption as wrapping
        iv = secrets.token_bytes(12)
        encryptor = Cipher(
            algorithms.AES(self.kek),
            modes.GCM(iv),
            backend=default_backend()
        ).encryptor()
        
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        return iv + ciphertext + encryptor.tag

    def decrypt_with_kek(self, ciphertext: bytes) -> bytes:
        if len(ciphertext) < 28: # IV(12) + Tag(16)
            raise ValueError("Ciphertext too short")
            
        iv = ciphertext[:12]
        tag = ciphertext[-16:]
        actual_ciphertext = ciphertext[12:-16]
        
        decryptor = Cipher(
            algorithms.AES(self.kek),
            modes.GCM(iv, tag),
            backend=default_backend()
        ).decryptor()
        
        return decryptor.update(actual_ciphertext) + decryptor.finalize()

class RealHsmService(HsmService):
    def __init__(self, lib_path=None, slot_id=0, label='mk'):
        self.session = None # Initialize first for safety in __del__
        self.label = label
        
        if not PyKCS11:
            raise ImportError("PyKCS11 is not installed")
        
        # Auto-detect lib path if not provided (common locations)
        if not lib_path:
            possible_libs = [
                "/usr/lib/libcryptoki.so",
                "/usr/lib/pkcs11/libopendcpt.so"
            ]
            
            # Add PTK Library path if env var is set (by setvars.sh)
            ptk_lib = os.environ.get('PTKLIB')
            if ptk_lib:
                # Prioritize libcryptoki.so as per user instruction
                possible_libs.insert(0, os.path.join(ptk_lib, 'libcryptoki.so'))

            for lib in possible_libs:
                if os.path.exists(lib):
                    lib_path = lib
                    break
        
        if not lib_path:
            raise ValueError(f"HSM Library path could not be determined. Checked: {', '.join(possible_libs)}")

        self.lib_path = lib_path
        self.slot_id = slot_id
        
        try:
            self.pkcs11 = PyKCS11.PyKCS11Lib()
            self.pkcs11.load(self.lib_path)
            self.session = self.pkcs11.openSession(self.slot_id, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
            logger.info(f"Connected to HSM at slot {slot_id} using lib {lib_path}. KEK Label: {self.label}")
        except Exception as e:
            logger.error(f"Failed to initialize HSM connection: {e} (Label: {self.label})")
            raise

    def login(self, pin):
        try:
            self.session.login(pin)
            logger.info("HSM Login Successful")
        except PyKCS11.PyKCS11Error as e:
            logger.error(f"HSM Login Failed: {e}")
            raise

    def logout(self):
        if self.session:
            try:
                self.session.logout()
            except:
                pass

    def __del__(self):
        if hasattr(self, 'session') and self.session:
            try:
                self.session.closeSession()
            except:
                pass

    def _find_key(self, label=None):
        # Find KEK by label
        target_label = label if label else self.label
        keys = self.session.findObjects([
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
            (PyKCS11.CKA_LABEL, target_label)
        ])
        if not keys:
            raise ValueError(f"Key with label '{target_label}' not found")
        return keys[0]

    def encrypt_with_kek(self, plaintext: bytes) -> bytes:
        # Wrap Data (Treat plaintext as a key to be wrapped for C_WrapKey behavior simulation)
        # Note: True WrapKey wraps a handle. 
        # Since we have bytes, we can use C_Encrypt if the KEK allows it, OR
        # better for 'Key Wrapping' semantics, acts as if we are protecting a key.
        # However, Java code used wrapping. 
        # Standard AES Wrap mechanism: CKM_AES_KEY_WRAP
        
        kek_handle = self._find_key()
        
        # Mechanism: CKM_AES_KEY_WRAP (AES Key Wrap) receives raw data in some implementations
        # OR requires a handle. 
        # If we just want to encrypt data with the KEK:
        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_KEY_WRAP)
        
        # PyKCS11 might require the plaintext to be a key handle for wrapKey.
        # But 'Simulated' effectively just encrypted bytes.
        # If the input IS a key (DEK), we should create a session key object first.
        
        # 1. Create temporary object for DEK
        dek_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_AES),
            (PyKCS11.CKA_VALUE, plaintext),
            (PyKCS11.CKA_SENSITIVE, False),
            (PyKCS11.CKA_EXTRACTABLE, True)
        ]
        dek_handle = self.session.createObject(dek_template)
        
        try:
            # 2. Wrap it
            # Note: PyKCS11 wrapKey returns a tuple/list of bytes
            wrapped_key = self.session.wrapKey(kek_handle, dek_handle, mechanism)
            return bytes(wrapped_key)
        finally:
             self.session.destroyObject(dek_handle)

    def decrypt_with_kek(self, ciphertext: bytes) -> bytes:
        kek_handle = self._find_key()
        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_KEY_WRAP)
        
        # Template for the unwrapped key
        dek_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_AES),
            (PyKCS11.CKA_SENSITIVE, False),
            (PyKCS11.CKA_EXTRACTABLE, True)
        ]
        
        # Unwrap returns a handle
        dek_handle = self.session.unwrapKey(kek_handle, list(ciphertext), dek_template, mechanism)
        
        try:
            # Get Value
            value = self.session.getAttributeValue(dek_handle, [PyKCS11.CKA_VALUE])[0]
            return bytes(value)
        finally:
            self.session.destroyObject(dek_handle)
