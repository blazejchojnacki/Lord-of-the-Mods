# demo_in_memory_packing.py
from pathlib import Path
import lotm.big as big


def main():
    # Define virtual mod files completely in memory
    # lotm supports zero-copy Buffer Protocol objects (bytes, bytearray, memoryview) natively.
    raw_buffer = bytearray(b"HEADER_PADDING_Damage=150\nRadius=50_FOOTER")
    
    virtual_mod = {
        "data/ini/weapon.ini": memoryview(raw_buffer)[15:36],  # Sliced without copying
        "data/ini/armor.ini": b"Armor=Heavy\nHealth=2000",
        "art/textures/hero.dds": bytearray(b"DDS_HEADER_DATA_..."),
        "readme.txt": b"Lord of the Mods in-memory packing demo."
    }

    print(f"Packing {len(virtual_mod)} files into memory...")
    
    # Serialize directly to a Python bytes object without disk I/O
    archive_bytes = big.pack_to_memory(virtual_mod)
    print(f"Generated BIG4 archive size: {len(archive_bytes)} bytes")

    # Write the resulting buffer to disk for future use
    archive_path = Path("virtual_mod.big")
    archive_path.write_bytes(archive_bytes)
    print(f"Saved archive to {archive_path.resolve()}")

    # Verify the contents using the context manager
    print("\nVerifying archive contents:")
    with big.BigArchive(archive_path) as arc:
        for entry in arc.get_entries():
            print(f" - {entry.name} (Offset: {entry.offset}, Size: {entry.size})")
            
    archive_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
