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
#include <core/endian.hpp>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <stdio.h>
#include <string>
#include <utility>
#include <vector>

using namespace lotm::big;

class ScopedDiffEnv {
public:
    std::filesystem::path root_dir;
    std::filesystem::path base_file;
    std::filesystem::path target_file;
    std::filesystem::path patch_file;

    ScopedDiffEnv() {
        root_dir = std::filesystem::temp_directory_path() / "lotm_diff_test";
        std::filesystem::remove_all(root_dir);
        std::filesystem::create_directories(root_dir);
        base_file = root_dir / "base.big";
        target_file = root_dir / "target.big";
        patch_file = root_dir / "patch.big";
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

    SECTION("Negative scenario: Comparing or patching a Zip-Bomb archive throws BigSecurityError") {
        env.write_archive(env.base_file, { { "a.txt", "1" } });

        // Construct an archive with 30 overlapping entries pointing to the same 1KB payload
        std::ofstream out(env.target_file, std::ios::binary);
        out.write("BIG4", 4);
        constexpr uint32_t file_count = 30;
        constexpr uint32_t payload_size = 1024;
        uint32_t header_size = 16 + file_count * 15;
        uint32_t total_size = header_size + payload_size;

        uint32_t le_total = lotm::core::to_little_endian(total_size);
        uint32_t be_count = lotm::core::to_big_endian(file_count);
        uint32_t be_header = lotm::core::to_big_endian(header_size);
        out.write(reinterpret_cast<const char*>(&le_total), 4);
        out.write(reinterpret_cast<const char*>(&be_count), 4);
        out.write(reinterpret_cast<const char*>(&be_header), 4);

        uint32_t be_offset = lotm::core::to_big_endian(header_size);
        uint32_t be_size = lotm::core::to_big_endian(payload_size);
        for (uint32_t i = 0; i < file_count; ++i) {
            out.write(reinterpret_cast<const char*>(&be_offset), 4);
            out.write(reinterpret_cast<const char*>(&be_size), 4);
            char name[7];
            snprintf(name, sizeof(name), "f%02u.in", i);
            out.write(name, 7);
        }
        std::vector<char> payload(payload_size, 'Z');
        out.write(payload.data(), static_cast<std::streamsize>(payload.size()));
        out.close();

        REQUIRE_THROWS_AS(BigDiff::compare(env.base_file, env.target_file), BigSecurityError);
        REQUIRE_THROWS_AS(BigDiff::create_patch_to_memory(env.base_file, env.target_file), BigSecurityError);
    }

    SECTION("Negative scenario: File I/O locks during streaming compare throw BigArchiveError") {
        env.write_archive(env.base_file, { { "a.txt", "AAAA" } });
        env.write_archive(env.target_file, { { "a.txt", "BBBB" } });

        BigArchive base_arc(env.base_file);
        BigArchive target_arc(env.target_file);

        FILE* locked_target = _fsopen(env.target_file.string().c_str(), "rb", 0x10);
        if (locked_target) {
            REQUIRE_THROWS_AS(BigDiff::compare(base_arc, target_arc), BigArchiveError);
            fclose(locked_target);
        }
    }

    SECTION("Negative scenario: Truncated physical file during streaming compare throws BigArchiveError") {
        env.write_archive(env.base_file, { { "a.txt", "AAAA" } });
        env.write_archive(env.target_file, { { "a.txt", "BBBB" } });

        BigArchive base_arc(env.base_file);
        BigArchive target_arc(env.target_file);

        // Truncate target payload physically to trigger stream read failure
        std::filesystem::resize_file(env.target_file, std::filesystem::file_size(env.target_file) - 2);

        REQUIRE_THROWS_AS(BigDiff::compare(base_arc, target_arc), BigArchiveError);
    }
}

TEST_CASE("BigDiff Delta Patch Generation", "[big_diff][patch]") {
    ScopedDiffEnv env;

    env.write_archive(env.base_file, {
        { "data/unchanged.ini", "Keep=1" },
        { "data/removed.ini", "Old=1" },
        { "data/modified.ini", "Damage=50" }
        });

    env.write_archive(env.target_file, {
        { "data/unchanged.ini", "Keep=1" },
        { "data/modified.ini", "Damage=99" },
        { "art/added.dds", "NEW_DDS" }
        });

    SECTION("Positive scenario: create_patch and create_patch_to_memory pack only added and modified files") {
        std::vector<std::string> reported_mem;
        auto mem_patch = BigDiff::create_patch_to_memory(
            env.base_file, env.target_file, "", [&](const ProgressReport& report) -> bool {
                reported_mem.emplace_back(report.entry_name);
                return true;
            }
        );

        REQUIRE(reported_mem.size() == 2);
        REQUIRE(reported_mem[0] == "art\\added.dds");
        REQUIRE(reported_mem[1] == "data\\modified.ini");

        std::vector<std::string> reported_disk;
        BigDiff::create_patch(
            env.base_file, env.target_file, env.patch_file, "", [&](const ProgressReport& report) -> bool {
                reported_disk.emplace_back(report.entry_name);
                return true;
            }
        );

        REQUIRE(std::filesystem::exists(env.patch_file));
        REQUIRE(reported_disk == reported_mem);

        // Verify disk patch matches in-memory patch byte-for-byte
        std::ifstream in(env.patch_file, std::ios::binary);
        std::vector<uint8_t> disk_bytes((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        REQUIRE(disk_bytes == mem_patch);

        // Verify contents via BigArchive
        BigArchive patch_arc(env.patch_file);
        const auto entries = patch_arc.get_entries();
        REQUIRE(entries.size() == 2);
        REQUIRE(entries[0].name == "art\\added.dds");
        REQUIRE(entries[1].name == "data\\modified.ini");

        auto mod_payload = patch_arc.read_entry("data/modified.ini");
        REQUIRE(std::string(mod_payload.begin(), mod_payload.end()) == "Damage=99");
    }

    SECTION("Positive and negative scenarios: Zero-byte patch entries and cooperative cancellation") {
        env.write_archive(env.target_file, {
            { "data/unchanged.ini", "Keep=1" },
            { "art/empty_added.txt", "" }
            });

        std::vector<std::string> reported;
        BigDiff::create_patch(
            env.base_file, env.target_file, env.patch_file, "", [&](const ProgressReport& report) -> bool {
                reported.emplace_back(report.entry_name);
                REQUIRE(report.file_size == 0);
                return true;
            }
        );
        REQUIRE(reported.size() == 1);
        REQUIRE(reported[0] == "art\\empty_added.txt");

        auto cancel_cb = [](const ProgressReport&) -> bool {
            return false;
            };
        REQUIRE_THROWS_AS(
            BigDiff::create_patch(env.base_file, env.target_file, env.patch_file, "", cancel_cb),
            BigArchiveError
        );
    }

    SECTION("Positive scenario: create_patch with open BigArchive instances and filter_pattern") {
        BigArchive base_arc(env.base_file);
        BigArchive target_arc(env.target_file);

        BigDiff::create_patch(base_arc, target_arc, env.patch_file, "*.ini");

        BigArchive patch_arc(env.patch_file);
        const auto entries = patch_arc.get_entries();
        REQUIRE(entries.size() == 1);
        REQUIRE(entries[0].name == "data\\modified.ini");
    }

    SECTION("Negative scenario: create_patch validates output directory, missing parent, input aliasing, and locked output file") {
        BigArchive base_arc(env.base_file);
        BigArchive target_arc(env.target_file);

        // Output path is an existing directory
        std::filesystem::path dir_out = env.root_dir / "existing_dir";
        std::filesystem::create_directories(dir_out);
        REQUIRE_THROWS_AS(BigDiff::create_patch(base_arc, target_arc, dir_out), std::invalid_argument);

        // Output path parent directory does not exist
        std::filesystem::path missing_parent_out = env.root_dir / "missing_folder" / "patch.big";
        REQUIRE_THROWS_AS(BigDiff::create_patch(base_arc, target_arc, missing_parent_out), std::invalid_argument);

        // Output path aliases base or target archive
        REQUIRE_THROWS_AS(BigDiff::create_patch(base_arc, target_arc, env.base_file), std::invalid_argument);
        REQUIRE_THROWS_AS(BigDiff::create_patch(base_arc, target_arc, env.target_file), std::invalid_argument);

        // Locked output file triggers BigArchiveError and preserves pre-existing file
        {
            std::ofstream pre(env.patch_file, std::ios::binary);
            pre << "locked";
        }
        FILE* locked_out = _fsopen(env.patch_file.string().c_str(), "rb", 0x10);
        if (locked_out) {
            REQUIRE_THROWS_AS(
                BigDiff::create_patch(base_arc, target_arc, env.patch_file),
                BigArchiveError
            );
            fclose(locked_out);
        }
        REQUIRE(std::filesystem::exists(env.patch_file));

        // Interrupted patch creation preserves pre-existing target file intact
        auto throwing_cb = [](const ProgressReport&) -> bool {
            throw std::runtime_error("Simulated patch interrupt");
            };
        REQUIRE_THROWS_AS(
            BigDiff::create_patch(base_arc, target_arc, env.patch_file, "", throwing_cb),
            std::runtime_error
        );
        std::ifstream verify_in(env.patch_file, std::ios::binary);
        std::string preserved((std::istreambuf_iterator<char>(verify_in)), std::istreambuf_iterator<char>());
        REQUIRE(preserved == "locked");
    }

    SECTION("Positive scenario: ProgressReport objects safely outlive callback execution") {
        std::vector<ProgressReport> retained_reports;
        BigDiff::create_patch_to_memory(
            env.base_file, env.target_file, "", [&](const ProgressReport& report) -> bool {
                retained_reports.push_back(report); // Copy the struct
                return true;
            }
        );

        REQUIRE(retained_reports.size() == 2);
        // Validates ownership fix: entry_name (std::string) persists safely after C++ transient vectors drop out of scope
        REQUIRE(retained_reports[0].entry_name == "art\\added.dds");
        REQUIRE(retained_reports[1].entry_name == "data\\modified.ini");
    }

    SECTION("Negative scenario: BufferAllocator failure throws std::bad_alloc") {
        BigArchive base_arc(env.base_file);
        BigArchive target_arc(env.target_file);

        auto failing_allocator = [](std::size_t) -> uint8_t* {
            return nullptr;
            };

        REQUIRE_THROWS_AS(
            BigDiff::create_patch_to_memory(base_arc, target_arc, failing_allocator),
            std::bad_alloc
        );
    }
}
