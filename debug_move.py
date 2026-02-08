import os
import shutil

# 1. Setup Paths
staging_file = "staging/test_move.txt"
vault_path = r"G:\My Drive\Brainweave OS ⚔️"
target_folder = os.path.join(vault_path, "04 Library", "YouTube")
target_file = os.path.join(target_folder, "test_move.txt")

print(f"🕵️ Testing MOVE operation...")

# 2. Create Dummy File in Staging (C: Drive)
os.makedirs("staging", exist_ok=True)
with open(staging_file, "w") as f:
    f.write("This is a test file moving from C: to G:")
print(f"✅ Created dummy file at: {staging_file}")

# 3. Ensure Target Folder Exists
try:
    os.makedirs(target_folder, exist_ok=True)
    print(f"✅ Target folder confirmed: {target_folder}")
except Exception as e:
    print(f"❌ FAILED to create target folder: {e}")
    exit()

# 4. Attempt the Move
try:
    print(f"🚚 Moving file...")
    shutil.move(staging_file, target_file)
    print(f"✅ SUCCESS! File moved to: {target_file}")
    
    # Clean up (optional, comment out if you want to see the file)
    # os.remove(target_file)
    # print("🧹 Cleaned up test file.")
    
except Exception as e:
    print(f"❌ FAILED to move file: {e}")