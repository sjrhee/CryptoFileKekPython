import os
import PyKCS11

def test():
    ptk_lib = os.environ.get('PTKLIB')
    print(f"PTKLIB: {ptk_lib}")
    if ptk_lib:
        # Check defaults logic reproduction
        possible_libs = []
        possible_libs.insert(0, os.path.join(ptk_lib, 'libjcprov.so'))
        possible_libs.insert(0, os.path.join(ptk_lib, 'libcryptoki.so'))
        
        print(f"Priority order: {possible_libs}")
        
        selected_lib = None
        for lib in possible_libs:
            if os.path.exists(lib):
                print(f"Found: {lib}")
                selected_lib = lib
                break
        
        if selected_lib:
            try:
                pkcs11 = PyKCS11.PyKCS11Lib()
                pkcs11.load(selected_lib)
                print(f"SUCCESS: Library loaded: {selected_lib}")
            except Exception as e:
                print(f"FAIL: Library load failed: {e}")
        else:
            print("No library found")

if __name__ == '__main__':
    test()
