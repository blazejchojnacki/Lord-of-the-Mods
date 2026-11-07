# demo_sage_overlay.py
import shutil
from pathlib import Path
import lotm.big as big


def main() -> None:
    workspace_dir = Path("virtual_game_dir")
    workspace_dir.mkdir(exist_ok=True)

    # Create archives in a directory simulating SAGE game load order:
    # Files are loaded alphabetically: 01_ini.big -> 02_patch.big -> 03_mod.big
    arc1_path = workspace_dir / "01_ini.big"
    arc2_path = workspace_dir / "02_patch.big"
    arc3_path = workspace_dir / "03_mod.big"

    arc1_path.write_bytes(big.pack_to_memory({
        "data/ini/weapon.ini": b"Damage=10",
        "data/ini/armor.ini": b"Armor=Heavy",
        "readme.txt": b"Official SAGE release",
    }))

    arc2_path.write_bytes(big.pack_to_memory({
        "data/ini/weapon.ini": b"Damage=25",      # Overrides 01_ini.big
        "art/textures/icon.dds": b"DDS_ICON_V1",
    }))

    arc3_path.write_bytes(big.pack_to_memory({
        "data/ini/weapon.ini": b"Damage=75",      # Overrides 02_patch.big
        "art/textures/icon.dds": b"DDS_ICON_V2",  # Overrides 02_patch.big
        "data/ini/spell.ini": b"Mana=100",        # New file
    }))

    print(f"Created 3 test archives inside '{workspace_dir.name}'.\n")

    # Mount directory simulating SAGE alphabetical load order
    print("=== Mounting Directory Load Order ===")
    overlay = big.load_overlay(workspace_dir)

    print("Mounted archives in effective execution order:")
    for path in overlay.mounted_archives:
        print(f"  [{path.name}]")

    # Inspect effective virtual file tree and override counts
    print("\n=== Effective Virtual File Tree ===")
    effective_entries = overlay.get_entries()
    for item in effective_entries:
        print(f"  * {item.name:<25} -> Winning Archive: {item.source_archive.name:<15} (overrides={item.override_count})")

    # Resolve specific file and read winning payload
    target_file = "data/ini/weapon.ini"
    resolved = overlay.resolve(target_file)
    print(f"\nResolving '{target_file}':")
    print(f"  Source Archive : {resolved.source_archive.name}")
    print(f"  Times Overridden: {resolved.override_count}")
    print(f"  Resolved Size  : {resolved.size} bytes")

    payload = overlay.read_entry(target_file)
    print(f"  Winning Content : {payload.decode('utf-8')}")

    # Mount using custom/explicit sequence order
    print("=== Custom Explicit Load Order ===")
    # Force 01_ini.big to load AFTER 03_mod.big
    custom_overlay = big.load_overlay([arc3_path, arc1_path])
    custom_resolved = custom_overlay.resolve(target_file)
    print(f"  Reverse order winning archive for '{target_file}': {custom_resolved.source_archive.name}")
    print(f"  Reverse order content: {custom_overlay.read_entry(target_file).decode('utf-8')}")

    # Clean up temporary directory
    shutil.rmtree(workspace_dir, ignore_errors=True)
    print("\nCleaned up overlay demo artifacts.")


if __name__ == "__main__":
    main()
