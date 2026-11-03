/**
 * @file tests/cpp/big/test_big_diff.cpp
 * @brief Unit tests for the BigDiff archive comparison engine.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include <big/big_archive.hpp>
#include <big/big_diff.hpp>
#include <big/big_packer.hpp>
#include <big/exceptions.hpp>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <utility>
#include <vector>

using namespace lotm::big;

class ScopedDiffEnv {
public:
    std::filesystem::path root_dir;
    std::filesystem::path base_file;
    std::filesystem::path target_file;

    ScopedDiffEnv() {
        root_dir = std::filesystem::temp_directory_path() / "lotm_diff_test";
        std::filesystem::create_directories(root_dir);
        base_file = root_dir / "base.big";
        target_file = root_dir / "target.big";
    }

    ~ScopedDiffEnv() {
        std::filesystem::remove_all(root_dir);
    }

    static void write_archive(
        const std::filesystem::path& dest,
        const std::vector<std::pair<std::string, std::string>>& entries
    ) {
        std::vector<std::pair<std::string, std::vector<uint8_t>>> mem_files;
        mem_files.reserve(entries.size());
        for (const auto& [name, content] : entries) {
            mem_files.emplace_back(
                name,
                std::vector<uint8_t>(content.begin(), content.end())
            );
        }
        auto raw_bytes = BigPacker::pack_to_memory(mem_files);
        std::ofstream out(dest, std::ios::binary);
        out.write(reinterpret_cast<const char*>(raw_bytes.data()), static_cast<std::streamsize>(raw_bytes.size()));
    }
};

TEST_CASE("BigDiff Comparison Scenarios", "[big_diff][compare]") {
    ScopedDiffEnv env;

    SECTION("Positive scenario: Identical archives yield no differences") {
        env.write_archive(env.base_file, {
            { "empty.txt", "" },
            { "data/weapon.ini", "Damage=50" }
            });
        env.write_archive(env.target_file, {
            { "EMPTY.TXT", "" },
            { "DATA\\weapon.ini", "Damage=50" }
            });

        auto res = BigDiff::compare(env.base_file, env.target_file);
        REQUIRE_FALSE(res.has_differences());
        REQUIRE(res.added.empty());
        REQUIRE(res.removed.empty());
        REQUIRE(res.modified.empty());
        REQUIRE(res.unchanged.size() == 2);
    }

    SECTION("Positive scenario: Detects added, removed, size-modified, and content-modified entries") {
        // Base contains:
        // - a_removed.txt (removed before middle entries)
        // - c_same.txt (unchanged)
        // - d_mod_size.txt (modified via different length)
        // - e_mod_bytes.txt (modified via same length, different bytes)
        // - z_removed.txt (removed in trailing base loop)
        env.write_archive(env.base_file, {
            { "a_removed.txt", "old" },
            { "c_same.txt", "same" },
            { "d_mod_size.txt", "short" },
            { "e_mod_bytes.txt", "AAAA" },
            { "z_removed.txt", "trailing_old" }
            });

        // Target contains:
        // - b_added.txt (added inside main loop)
        // - c_same.txt (unchanged)
        // - d_mod_size.txt (longer payload)
        // - e_mod_bytes.txt (same 4-byte length, different payload)
        // - zz_added.txt (added in trailing target loop)
        env.write_archive(env.target_file, {
            { "b_added.txt", "new" },
            { "c_same.txt", "same" },
            { "d_mod_size.txt", "much_longer" },
            { "e_mod_bytes.txt", "BBBB" },
            { "zz_added.txt", "trailing_new" }
            });

        BigArchive base_arc(env.base_file);
        BigArchive target_arc(env.target_file);
        auto res = BigDiff::compare(base_arc, target_arc);

        REQUIRE(res.has_differences());

        REQUIRE(res.added.size() == 2);
        REQUIRE(res.added[0].name == "b_added.txt");
        REQUIRE(res.added[1].name == "zz_added.txt");

        REQUIRE(res.removed.size() == 2);
        REQUIRE(res.removed[0].name == "a_removed.txt");
        REQUIRE(res.removed[1].name == "z_removed.txt");

        REQUIRE(res.modified.size() == 2);
        REQUIRE(res.modified[0].name == "d_mod_size.txt");
        REQUIRE(res.modified[1].name == "e_mod_bytes.txt");

        REQUIRE(res.unchanged.size() == 1);
        REQUIRE(res.unchanged[0].name == "c_same.txt");
    }

    SECTION("Positive scenario: Filter pattern scopes comparison to matching entries") {
        env.write_archive(env.base_file, {
            { "data/weapon.ini", "Damage=50" },
            { "art/texture.dds", "DDS_OLD" }
            });
        env.write_archive(env.target_file, {
            { "data/weapon.ini", "Damage=50" },
            { "art/texture.dds", "DDS_NEW" }
            });

        auto res_ini = BigDiff::compare(env.base_file, env.target_file, "*.ini");
        REQUIRE_FALSE(res_ini.has_differences());
        REQUIRE(res_ini.unchanged.size() == 1);

        auto res_dds = BigDiff::compare(env.base_file, env.target_file, "*.dds");
        REQUIRE(res_dds.has_differences());
        REQUIRE(res_dds.modified.size() == 1);
    }

    SECTION("Negative scenario: Comparing a closed BigArchive throws BigArchiveError") {
        env.write_archive(env.base_file, { { "a.txt", "1" } });
        env.write_archive(env.target_file, { { "a.txt", "1" } });

        BigArchive base_arc(env.base_file);
        BigArchive target_arc(env.target_file);
        base_arc.close();

        REQUIRE_THROWS_AS(BigDiff::compare(base_arc, target_arc), BigArchiveError);
    }
}
