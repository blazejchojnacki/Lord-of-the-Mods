# demo_selective_extraction.py
import shutil
from pathlib import Path
import lotm.big as big


def on_extract_progress(report: big.ProgressReport) -> bool:
    """Telemetry callback that cancels extraction if it hits a massive file."""
    if report.file_size > 50_000_000:  # e.g., > 50 MB
        print(f"  [ABORT] Skipping overly large extraction task on '{report.entry_name}'")
        return False
    
    if report.bytes_transferred == report.file_size:
        print(f"  [OK] Extracted: {report.entry_name} ({report.file_size} bytes)")
    return True


def main():
    archive_path = Path("virtual_mod.big")
    
    # Provision a dummy archive for the demo
    archive_path.write_bytes(big.pack_to_memory({
        "data/ini/weapon.ini": b"Damage=50",
        "data/ini/armor.ini": b"Armor=Standard",
        "art/textures/hero.dds": b"DDS_DATA"
    }))

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
    extracted = big.unpack(archive_path, out_dir, filter_pattern="*.ini", progress_callback=on_extract_progress)
    
    print(f"Successfully extracted {len(extracted)} files.")
    for file in out_dir.rglob("*.*"):
        if file.is_file():
            print(f" - On disk: {file.relative_to(out_dir)}")
            
    # Cleanup
    archive_path.unlink(missing_ok=True)
    shutil.rmtree(out_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
