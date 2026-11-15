/**
 * @file tests/cpp/big/test_big_overlay.cpp
 * @brief Unit tests for the BigOverlay SAGE load-order emulation engine.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>

#include <big/big_overlay.hpp>
#include <big/big_packer.hpp>
#include <big/exceptions.hpp>
#include <core/endian.hpp>

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace lotm::big;

class ScopedOverlayEnv {
public:
    std::filesystem::path root_dir;

    ScopedOverlayEnv() {
        root_dir = std::filesystem::temp_directory_path() / "lotm_overlay_test";
        std::filesystem::create_directories(root_dir);
    }

    ~ScopedOverlayEnv() {
        std::filesystem::remove_all(root_dir);
    }

    std::filesystem::path create_archive(
        const std::string& filename,
        const std::vector<std::pair<std::string, std::string>>& entries
    ) const {
        std::vector<std::pair<std::string, std::vector<uint8_t>>> mem_files;
        mem_files.reserve(entries.size());
        for (const auto& [name, content] : entries) {
            mem_files.emplace_back(
                name,
                std::vector<uint8_t>(content.begin(), content.end())
            );
        }
        auto raw_bytes = BigPacker::pack_to_memory(mem_files);
        std::filesystem::path dest = root_dir / filename;
        std::ofstream out(dest, std::ios::binary);
        out.write(reinterpret_cast<const char*>(raw_bytes.data()), static_cast<std::streamsize>(raw_bytes.size()));
        return dest;
    }

    std::filesystem::path create_raw_archive(
        const std::string& filename,
        const std::vector<std::pair<std::string, std::string>>& entries
    ) const {
        std::filesystem::path dest = root_dir / filename;
        std::ofstream out(dest, std::ios::binary);
        out.write("BIG4", 4);

        uint32_t dummy_total = 0;
        out.write(reinterpret_cast<const char*>(&dummy_total), 4);

        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(entries.size()));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        uint32_t header_size = 16;
        for (const auto& entry : entries) {
            header_size += 8 + static_cast<uint32_t>(entry.first.size()) + 1;
        }

        uint32_t be_header_size = lotm::core::to_big_endian(header_size);
        out.write(reinterpret_cast<const char*>(&be_header_size), 4);

        uint32_t current_offset = header_size;
        for (const auto& entry : entries) {
            uint32_t be_offset = lotm::core::to_big_endian(current_offset);
            uint32_t be_size = lotm::core::to_big_endian(static_cast<uint32_t>(entry.second.size()));
            out.write(reinterpret_cast<const char*>(&be_offset), 4);
            out.write(reinterpret_cast<const char*>(&be_size), 4);
            out.write(entry.first.c_str(), static_cast<std::streamsize>(entry.first.size() + 1));
            current_offset += static_cast<uint32_t>(entry.second.size());
        }

        for (const auto& entry : entries) {
            out.write(entry.second.c_str(), static_cast<std::streamsize>(entry.second.size()));
        }

        out.seekp(4, std::ios::beg);
        uint32_t le_total_size = lotm::core::to_little_endian(current_offset);
        out.write(reinterpret_cast<const char*>(&le_total_size), 4);
        return dest;
    }
};

TEST_CASE("BigOverlay Load-Order Resolution and Override Semantics", "[big_overlay][resolve]") {
    ScopedOverlayEnv env;

    // Create three archives that sort alphabetically as:
    // 1. 01_base.big
    // 2. 02_patch.big
    // 3. 03_mod.BIG
    auto arc1 = env.create_archive("01_base.big", {
        { "data/ini/weapon.ini", "Damage=10" },
        { "data/ini/armor.ini", "Armor=Base" },
        { "readme.txt", "BaseReadme" }
        });

    auto arc2 = env.create_archive("02_patch.big", {
        { "DATA\\INI\\WEAPON.INI", "Damage=20" },
        { "data/ini/armor.ini", "Armor=Patch" }
        });

    auto arc3 = env.create_archive("03_mod.BIG", {
        { "data/ini/weapon.ini", "Damage=30" },
        { "art/hero.dds", "DDS_MOD" }
        });

    // Add non-archive noise (a directory and a .txt file) to verify directory filtering
    std::filesystem::create_directories(env.root_dir / "subfolder");
    std::ofstream(env.root_dir / "notes.txt") << "ignore me";

    SECTION("Positive scenario: from_directory mounts .big files alphabetically and resolves overrides") {
        auto overlay = BigOverlay::from_directory(env.root_dir);

        const auto mounted = overlay.get_mounted_archives();
        REQUIRE(mounted.size() == 3);
        REQUIRE(mounted[0] == arc1);
        REQUIRE(mounted[1] == arc2);
        REQUIRE(mounted[2] == arc3);

        // Verify all 4 unique files are present and sorted alphabetically
        const auto all_entries = overlay.get_entries();
        REQUIRE(all_entries.size() == 4);
        REQUIRE(all_entries[0].entry.name == "art\\hero.dds");
        REQUIRE(all_entries[1].entry.name == "data\\ini\\armor.ini");
        REQUIRE(all_entries[2].entry.name == "data\\ini\\weapon.ini");
        REQUIRE(all_entries[3].entry.name == "readme.txt");

        // Verify glob filtering on overlay entries
        const auto ini_entries = overlay.get_entries("*.ini");
        REQUIRE(ini_entries.size() == 2);

        // Verify resolve() and override counts
        auto weapon_res = overlay.resolve("DATA/ini/weapon.ini");
        REQUIRE(weapon_res.source_archive == arc3);
        REQUIRE(weapon_res.override_count == 2);

        auto armor_res = overlay.resolve("data\\ini\\armor.ini");
        REQUIRE(armor_res.source_archive == arc2);
        REQUIRE(armor_res.override_count == 1);

        auto readme_res = overlay.resolve("readme.txt");
        REQUIRE(readme_res.source_archive == arc1);
        REQUIRE(readme_res.override_count == 0);

        // Verify read_entry() returns the winning payload
        auto weapon_bytes = overlay.read_entry("data/ini/weapon.ini");
        REQUIRE(std::string(weapon_bytes.begin(), weapon_bytes.end()) == "Damage=30");
    }

    SECTION("Positive scenario: from_archives respects explicit custom mount order") {
        // Mount in reverse order: arc3 first, then arc1 overrides it
        auto overlay = BigOverlay::from_archives({ arc3, arc1 });

        REQUIRE_FALSE(overlay.is_closed());
        REQUIRE(overlay.get_mounted_archives().size() == 2);

        auto weapon_bytes = overlay.read_entry("data/ini/weapon.ini");
        REQUIRE(std::string(weapon_bytes.begin(), weapon_bytes.end()) == "Damage=10");
        REQUIRE(overlay.resolve("data/ini/weapon.ini").source_archive == arc1);

        overlay.close();
        REQUIRE(overlay.is_closed());
        REQUIRE_THROWS_AS(overlay.resolve("data/ini/weapon.ini"), BigArchiveError);
    }

    SECTION("Positive scenario: get_entries deduplicates intra-archive case-insensitive duplicates") {
        auto dup_arc = env.create_raw_archive("dup.big", {
            { "data\\weapon.ini", "Damage=10" },
            { "DATA\\WEAPON.INI", "Damage=20" }
            });

        auto overlay = BigOverlay::from_archives({ dup_arc });
        const auto entries = overlay.get_entries();
        REQUIRE(entries.size() == 1);
        REQUIRE(entries[0].override_count == 1);
    }

    SECTION("Negative scenarios: Missing directory or unresolvable entry throws appropriate exception") {
        REQUIRE_THROWS_AS(BigOverlay::from_directory(env.root_dir / "non_existent"), std::invalid_argument);

        auto overlay = BigOverlay::from_archives({ arc1 });
        REQUIRE_THROWS_AS(overlay.resolve("missing/file.ini"), BigArchiveError);
        REQUIRE_THROWS_AS(overlay.read_entry("missing/file.ini"), BigArchiveError);
    }

    SECTION("Negative scenario: Mounting to a closed overlay throws BigArchiveError") {
        auto overlay = BigOverlay::from_archives({ arc1 });
        overlay.close();
        REQUIRE_THROWS_AS(overlay.mount(arc2), BigArchiveError);
    }
}
