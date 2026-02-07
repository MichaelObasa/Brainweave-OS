import shutil
import os
from datetime import datetime
from models.schemas import UniversalMetadata

def route_file(file_path: str, metadata: UniversalMetadata, base_vault_path: str):
    """
    Routes files into the 4 Pillars of Brainweave OS:
    1. 01 Personal (Finance, CV, Admin)
    2. 02 Work (Volant Media, Clients)
    3. 03 Founder Mode (Indexr, Startup Ideas)
    4. 04 Library (Everything else: Podcasts, YouTube, LinkedIn, Research)
    """
    
    # --- LOGIC MAP ---
    
    # 1. FOUNDER MODE (Highest Priority)
    if "Indexr" in metadata.tags or "Indexr" in metadata.topics:
        target_dir = os.path.join(base_vault_path, "03 Founder Mode", "Indexr")
    elif "Startup" in metadata.topics:
        target_dir = os.path.join(base_vault_path, "03 Founder Mode", "_Ideas")

    # 2. WORK (Volant Media)
    elif "Volant" in metadata.tags or "Volant Media" in metadata.topics:
        target_dir = os.path.join(base_vault_path, "02 Work", "Volant Media")
        
    # 3. PERSONAL (Finance, CVs)
    elif metadata.source_type == "receipt" or "Finance" in metadata.topics:
        target_dir = os.path.join(base_vault_path, "01 Personal", "Finances")
    elif "CV" in metadata.tags or "Resume" in metadata.topics:
        target_dir = os.path.join(base_vault_path, "01 Personal", "CV & Bio")

    # 4. LIBRARY (The Catch-All)
    else:
        # We organize Library by Source Type first
        if metadata.source_type == "youtube":
            folder_name = "YouTube"
        elif metadata.source_type == "linkedin_post":
            folder_name = "LinkedIn"
        elif metadata.source_type == "tweet":
            folder_name = "Tweets"
        else:
            folder_name = "General Knowledge"
            
        # Add Author subfolder if known (e.g., 04 Library/YouTube/A16z)
        if metadata.author:
            target_dir = os.path.join(base_vault_path, "04 Library", folder_name, metadata.author)
        else:
            target_dir = os.path.join(base_vault_path, "04 Library", folder_name)

    # --- EXECUTION ---
    os.makedirs(target_dir, exist_ok=True)
    
    # Sanitize filename
    safe_title = "".join([c for c in metadata.title if c.isalnum() or c in " -_"]).strip()
    date_prefix = metadata.date_published or datetime.now().strftime("%Y-%m-%d")
    
    new_filename = f"{date_prefix} - {safe_title}.jpg"
    final_path = os.path.join(target_dir, new_filename)

    shutil.move(file_path, final_path)
    return final_path