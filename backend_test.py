
import os
import unittest
import shutil
from src.services.hsm_service import SimulatedHsmService
from src.services.dek_service import DekService
from src.services.file_encryption_service import FileEncryptionService
from src.services.file_storage_service import FileStorageService

class TestCryptoKek(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'TEST_DATA'
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
            
        self.hsm_service = SimulatedHsmService(key_file=os.path.join(self.test_dir, 'sim_kek.key'))
        self.dek_service = DekService(self.hsm_service)
        self.fs_service = FileStorageService(self.test_dir)
        self.enc_service = FileEncryptionService()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_flow(self):
        print("\n--- Testing Full Encryption/Decryption Flow ---")
        
        # 1. Prepare Data
        original_data = b"Hello, World! This is a secret message."
        filename = "test.txt"
        self.fs_service.save_file(filename, original_data)
        
        # 2. Generate DEK
        dek = self.dek_service.generate_dek()
        self.assertEqual(len(dek), 32)
        print("[Pass] DEK Generated")

        # 3. Encrypt File
        encrypted_data = self.enc_service.encrypt_file_data(original_data, dek)
        self.assertNotEqual(original_data, encrypted_data)
        print(f"[Pass] File Encrypted (Size: {len(original_data)} -> {len(encrypted_data)})")

        # 4. Encrypt DEK (Wrap)
        encrypted_dek = self.dek_service.encrypt_dek(dek)
        self.assertNotEqual(dek, encrypted_dek)
        print("[Pass] DEK Encrypted (Wrapped)")

        # --- Simulate Storage/Transmission ---

        # 5. Decrypt DEK (Unwrap)
        restored_dek = self.dek_service.decrypt_dek(encrypted_dek)
        self.assertEqual(dek, restored_dek)
        print("[Pass] DEK Decrypted (Unwrapped)")

        # 6. Decrypt File
        restored_data = self.enc_service.decrypt_file_data(encrypted_data, restored_dek)
        self.assertEqual(original_data, restored_data)
        print("[Pass] File Decrypted Check")
        
        print("--- Test Complete ---\n")

if __name__ == '__main__':
    unittest.main()
