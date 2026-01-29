import os
import logging
try:
    import PyKCS11
except ImportError:
    PyKCS11 = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HsmService:
    def __init__(self):
        self.lib_path = os.getenv('HSM_LIB_PATH', '/opt/safenet/lunaclient/lib/libCryptoki2_64.so')
        self.slot_id = int(os.getenv('HSM_SLOT_ID', '1'))
        self.pin = os.getenv('HSM_PIN', '12341234')
        self.label = os.getenv('HSM_LABEL', 'master_key')
        self.session = None
        self.pkcs11 = None

        self._initialize()

    def _initialize(self):
        if not PyKCS11:
            logger.warning("PyKCS11 not installed. Running in SIMULATION mode.")
            return

        try:
            self.pkcs11 = PyKCS11.PyKCS11Lib()
            self.pkcs11.load(self.lib_path)
            self.session = self.pkcs11.openSession(self.slot_id, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
            self.session.login(self.pin)
            logger.info(f"Connected to HSM at slot {self.slot_id} using lib {self.lib_path}")
        except Exception as e:
            logger.error(f"Failed to initialize HSM: {e}")
            self.session = None

    def _find_key(self):
        if not self.session:
            raise RuntimeError("HSM session not active")
        
        keys = self.session.findObjects([
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
            (PyKCS11.CKA_LABEL, self.label)
        ])
        if not keys:
            raise ValueError(f"Key with label '{self.label}' not found")
        return keys[0]

    def encrypt(self, plaintext: bytes) -> bytes:
        if not self.session:
             # Simulation mode for testing in environments without HSM
             logger.warning("Simulated Encryption (Reversing bytes)")
             return plaintext[::-1]

        try:
            kek_handle = self._find_key()
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_KEY_WRAP)
            wrapped_data = self.session.encrypt(kek_handle, plaintext, mechanism)
            return bytes(wrapped_data)
        except Exception as e:
            logger.error(f"HSM Encrypt failed: {e}")
            raise

    def decrypt(self, ciphertext: bytes) -> bytes:
        if not self.session:
             # Simulation mode
             logger.warning("Simulated Decryption (Reversing bytes)")
             return ciphertext[::-1]

        try:
            kek_handle = self._find_key()
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_KEY_WRAP)
            decrypted_data = self.session.decrypt(kek_handle, list(ciphertext), mechanism)
            return bytes(decrypted_data)
        except Exception as e:
            logger.error(f"HSM Decrypt failed: {e}")
            raise

    def __del__(self):
        if self.session:
            try:
                self.session.logout()
                self.session.closeSession()
            except:
                pass
