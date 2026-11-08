# demo_archive_diff.py
from pathlib import Path
import lotm.big as big


def main() -> None:
    base_path = Path("vanilla_sample.big")
    modded_path = Path("modded_sample.big")

    # Provision two sample archives in memory and write them to disk
    base_files = {
        "data/ini/weapon.ini": b"Damage=50\nRange=200",
        "data/ini/armor.ini": b"Armor=Standard",
        "data/ini/removed_unit.ini": b"Cost=100",
        "art/textures/hero.dds": b"DDS_TEXTURE_V1",
    }

    modded_files = {
        "data/ini/weapon.ini": b"Damage=75\nRange=250",      # Modified (same file length, content differs)
        "data/ini/armor.ini": b"Armor=Standard",             # Unchanged
        "data/ini/new_spell.ini": b"Mana=30",                # Added
        "art/textures/hero.dds": b"DDS_TEXTURE_V2_EXTENDED", # Modified (size differs)
    }

    base_path.write_bytes(big.pack_to_memory(base_files))
    modded_path.write_bytes(big.pack_to_memory(modded_files))
    print("Generated 'vanilla_sample.big' and 'modded_sample.big'.\n")

    # Perform a full archive comparison using the high-level API
    print("=== Full Archive Comparison ===")
    result = big.diff(base_path, modded_path)
    print(f"Differences detected: {result.has_differences}")
    print(f"Summary repr: {result}\n")

    print(f"Added ({len(result.added)}):")
    for entry in result.added:
        print(f"  + {entry.name} ({entry.size} bytes)")

    print(f"\nRemoved ({len(result.removed)}):")
    for entry in result.removed:
        print(f"  - {entry.name} ({entry.size} bytes)")

    print(f"\nModified ({len(result.modified)}):")
    for entry in result.modified:
        print(f"  ~ {entry.name} ({entry.size} bytes)")

    print(f"\nUnchanged ({len(result.unchanged)}):")
    for entry in result.unchanged:
        print(f"  = {entry.name} ({entry.size} bytes)")

    # Scoped comparison using a wildcard/glob filter
    print("\n=== Scoped Diff (filter_pattern='*.ini') ===")
    ini_diff = big.diff(base_path, modded_path, filter_pattern="*.ini")
    print(f"Added INIs:    {[e.name for e in ini_diff.added]}")
    print(f"Removed INIs:  {[e.name for e in ini_diff.removed]}")
    print(f"Modified INIs: {[e.name for e in ini_diff.modified]}")

    # Compare open BigArchive instances directly and inspect modified bytes
    print("\n=== In-Memory Inspection of Differences ===")
    with big.BigArchive(base_path) as base_arc, big.BigArchive(modded_path) as mod_arc:
        direct_diff = big.BigDiff.compare(base_arc, mod_arc, filter_pattern="data/ini/weapon.ini")

        for entry in direct_diff.modified:
            base_payload = base_arc.read_entry(entry.name)
            target_payload = mod_arc.read_entry(entry.name)
            print(f"Diff for '{entry.name}':")
            print(f"  Base content:\n    {base_payload.decode('utf-8')}")
            print(f"  Target content:\n    {target_payload.decode('utf-8')}")

    # Clean up demo artifacts
    base_path.unlink(missing_ok=True)
    modded_path.unlink(missing_ok=True)
    print("Cleaned up demo archives.")


if __name__ == "__main__":
    main()
