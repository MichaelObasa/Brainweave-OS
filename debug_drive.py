import os

# The path exactly as we have it in main.py
vault_path = r"G:\My Drive\Brainweave OS ⚔️"

print(f"🕵️ Testing connection to: {vault_path}")

if os.path.exists(vault_path):
    print("✅ SUCCESS: Python can see the folder!")
    
    # Try to write a test file
    test_file = os.path.join(vault_path, "probe_test.txt")
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("System Check: Connected.")
        print(f"✅ SUCCESS: Wrote test file to {test_file}")
    except Exception as e:
        print(f"❌ FAILED to write file: {e}")
else:
    print("❌ FAILED: Python cannot find the folder.")
    print("   (It might be the emoji causing encoding issues.)")