# demo_delta_patch.py
from pathlib import Path
import lotm.big as big


def main() -> None:
    base_path = Path("vanilla_release.big")
    target_path = Path("modded_release.big")
    patch_disk_path = Path("delta_patch.big")

    # Provision sample baseline and updated mod archives
    base_files = {
        "data/ini/weapon.ini": b"Damage=50\nRange=200",     # Will be modified
        "data/ini/armor.ini": b"Armor=Standard",            # Unchanged
        "data/ini/deprecated.ini": b"ObsoleteFeature=1",     # Removed in target
    }

    target_files = {
        "data/ini/weapon.ini": b"Damage=120\nRange=350",    # Modified
        "data/ini/armor.ini": b"Armor=Standard",            # Unchanged (should NOT be in patch)
        "data/ini/new_ability.ini": b"Cooldown=15",         # Added
    }

    base_path.write_bytes(big.pack_to_memory(base_files))
    target_path.write_bytes(big.pack_to_memory(target_files))
    print(f"Generated base ({base_path.name}) and target ({target_path.name}) archives.\n")

    # Generate a delta patch in memory
    print("=== Generating In-Memory Delta Patch ===")
    patch_bytes = big.create_patch_to_memory(base_path, target_path)
    print(f"Serialized patch size in memory: {len(patch_bytes)} bytes")

    # Generate a standalone delta patch directly to disk
    print(f"\n=== Generating Disk Delta Patch ({patch_disk_path.name}) ===")
    big.create_patch(base_path, target_path, patch_disk_path)
    print(f"Saved delta patch to: {patch_disk_path.resolve()}")

    # Inspect the generated patch contents to verify inclusion criteria
    print("\n=== Verifying Delta Patch Archive Contents ===")
    with big.BigArchive(patch_disk_path) as patch_arc:
        entries = patch_arc.get_entries()
        print(f"Entries packed into patch ({len(entries)}):")
        for entry in entries:
            payload = patch_arc.read_entry(entry)
            print(f"  * {entry.name} ({entry.size} bytes)")
            print(f"    Payload: {payload.decode('utf-8').strip()}")

    # Clean up temporary archives
    base_path.unlink(missing_ok=True)
    target_path.unlink(missing_ok=True)
    patch_disk_path.unlink(missing_ok=True)
    print("\nCleaned up patch demo artifacts.")


if __name__ == "__main__":
    main()
