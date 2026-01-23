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
        # Determine mechanism
        # CKM_AES_KEY_WRAP (RFC 3394) is standard for wrapping keys.
        # We use C_Encrypt which takes raw bytes and returns raw bytes (wrapped key).
        # This avoids C_WrapKey/C_UnwrapKey which require creating/managing Object Handles and Templates,
        # often leading to CKR_TEMPLATE_INCONSISTENT if attributes don't perfectly match HSM policies.
        
        kek_handle = self._find_key()
        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_KEY_WRAP)
        
        try:
            # encrypt returns tuple/list of bytes
            wrapped_data = self.session.encrypt(kek_handle, plaintext, mechanism)
            return bytes(wrapped_data)
        except Exception as e:
            logger.error(f"HSM Encrypt (Wrap) failed: {e}")
            raise

    def decrypt_with_kek(self, ciphertext: bytes) -> bytes:
        kek_handle = self._find_key()
        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_KEY_WRAP)
        
        try:
            # decrypt returns tuple/list of bytes
            decrypted_data = self.session.decrypt(kek_handle, list(ciphertext), mechanism)
            return bytes(decrypted_data)
        except Exception as e:
            logger.error(f"HSM Decrypt (Unwrap) failed: {e}")
            raise
