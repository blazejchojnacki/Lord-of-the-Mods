# demo_selective_extraction.py
import shutil
from pathlib import Path
import lotm.big as big

def main():
    archive_path = Path("virtual_mod.big")
    if not archive_path.exists():
        print(f"Error: {archive_path} not found. Run demo_in_memory_packing.py first.")
        return

    # 1. Preview filtered files without extracting them
    print("Previewing files matching '*.ini':")
    with big.BigArchive(archive_path) as arc:
        # get_entries() now accepts a glob filter
        ini_entries = arc.get_entries("*.ini")
        for entry in ini_entries:
            print(f" - Found: {entry.name}")
            # We can also read specific payloads directly into memory
            payload = arc.read_entry(entry)
            print(f"   Content: {payload.decode('utf-8').strip()}")

    # 2. Extract only matching files to disk
    out_dir = Path("extracted_selective")
    if out_dir.exists():
        shutil.rmtree(out_dir)

    print(f"\nExtracting '*.ini' to {out_dir.resolve()}...")
    
    # unpack() avoids dumping non-matching files (like .dds or .txt) to disk
    extracted = big.unpack(archive_path, out_dir, filter_pattern="*.ini")
    
    print(f"Successfully extracted {len(extracted)} files.")
    for file in out_dir.rglob("*.*"):
        if file.is_file():
            print(f" - On disk: {file.relative_to(out_dir)}")

if __name__ == "__main__":
    main()
