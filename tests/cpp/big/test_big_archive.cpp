/**
 * @file tests/cpp/big/test_big_archive.cpp
 * @brief Unit tests for the BigArchive unpacking implementation.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include <big/big_archive.hpp>
#include <big/exceptions.hpp>
#include <core/endian.hpp>
#include <filesystem>
#include <fstream>
#include <vector>
#include <string>
#include <stdio.h>

using namespace lotm::big;

// RAII Helper to create temporary binary files and directories for testing
class ScopedTempEnv {
public:
    std::filesystem::path root_dir;
    std::filesystem::path test_file;
    std::filesystem::path out_dir;

    ScopedTempEnv() {
        root_dir = std::filesystem::temp_directory_path() / "lotm_unpack_test";
        std::filesystem::remove_all(root_dir);
        std::filesystem::create_directories(root_dir);
        test_file = root_dir / "test.big";
        out_dir = root_dir / "out";
    }

    ~ScopedTempEnv() {
        std::filesystem::remove_all(root_dir);
    }

    // Helper to generate a valid BIG4 file dynamically
    void write_big_file(const char* magic, const std::vector<std::pair<std::string, std::string>>& entries) {
        std::ofstream out(test_file, std::ios::binary);

        out.write(magic, 4);

        // Placeholder for total size
        uint32_t dummy_total = 0;
        out.write(reinterpret_cast<const char*>(&dummy_total), 4);

        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(entries.size()));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        // Calculate Header Size: 16 bytes base + size of all index entries
        uint32_t header_size = 16;
        for (const auto& entry : entries) {
            header_size += 8 + static_cast<uint32_t>(entry.first.size()) + 1;
        }

        uint32_t be_header_size = lotm::core::to_big_endian(header_size);
        out.write(reinterpret_cast<const char*>(&be_header_size), 4);

        // Write Index
        uint32_t current_offset = header_size;
        for (const auto& entry : entries) {
            uint32_t be_offset = lotm::core::to_big_endian(current_offset);
            uint32_t be_size = lotm::core::to_big_endian(static_cast<uint32_t>(entry.second.size()));

            out.write(reinterpret_cast<const char*>(&be_offset), 4);
            out.write(reinterpret_cast<const char*>(&be_size), 4);
            out.write(entry.first.c_str(), static_cast<std::streamsize>(entry.first.size() + 1)); // include null terminator

            current_offset += static_cast<uint32_t>(entry.second.size());
        }

        // Write Payloads
        for (const auto& entry : entries) {
            out.write(entry.second.c_str(), static_cast<std::streamsize>(entry.second.size()));
        }

        // Fix up total size (Little Endian)
        uint32_t total_size = current_offset;
        out.seekp(4, std::ios::beg);
        uint32_t le_total_size = lotm::core::to_little_endian(total_size);
        out.write(reinterpret_cast<const char*>(&le_total_size), 4);
    }
};


TEST_CASE("BIG4 Type and Constant Invariants", "[big][types][constexpr]") {
    // Validate constant size contracts required by the BIG4 specification
    STATIC_REQUIRE(lotm::big::BIG4_MAGIC.size() == 4);
    STATIC_REQUIRE(lotm::big::EA_PADDING_TAG.size() == 8);
    STATIC_REQUIRE(lotm::big::HEADER_BASE_SIZE == 16);
    STATIC_REQUIRE(lotm::big::EA_PADDING_SIZE == 8);

    // Ensure BigEntry remains cheap to move and standard-conforming
    STATIC_REQUIRE(std::is_nothrow_move_constructible_v<lotm::big::BigEntry>);
    STATIC_REQUIRE(std::is_nothrow_move_assignable_v<lotm::big::BigEntry>);
}


TEST_CASE("BigArchive Initialization and Basic Error Handling", "[big_unpack][error]") {
    ScopedTempEnv env;

    SECTION("Negative scenario: File does not exist") {
        REQUIRE_THROWS_AS(BigArchive(env.root_dir / "non_existent.big"), BigArchiveError);
    }

    SECTION("Negative scenario: Invalid magic string") {
        env.write_big_file("BOGUS", {});
        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Negative scenario: Non-printable binary magic bytes") {
        env.write_big_file("\x80\xFF\x00\x7F", {});
        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }
}

TEST_CASE("BigArchive Header Parsing", "[big_unpack][header]") {
    ScopedTempEnv env;

    SECTION("Positive scenario: Valid BIG4 file with zero entries") {
        env.write_big_file("BIG4", {});
        REQUIRE_NOTHROW(BigArchive(env.test_file));
        BigArchive archive(env.test_file);
        REQUIRE(archive.get_entries().empty());
        REQUIRE(archive.file_path() == env.test_file);
    }

    SECTION("Positive scenario: Valid BIG4 file with multiple entries") {
        env.write_big_file("BIG4", {
            { "file1.txt", "Hello World" },
            { "data/file2.ini", "ConfigData=1" }
            });

        BigArchive archive(env.test_file);

        const auto& entries = archive.get_entries();
        REQUIRE(entries.size() == 2);

        // Validate first entry
        REQUIRE(entries[0].name == "file1.txt");
        REQUIRE(entries[0].size == 11);

        // Validate second entry
        char expected_sep = static_cast<char>(std::filesystem::path::preferred_separator);
        std::string expected_nested = std::string("data") + expected_sep + "file2.ini";
        REQUIRE(entries[1].name == expected_nested);
        REQUIRE(entries[1].size == 12);

        // Ensure sequential offsets without overlap
        REQUIRE(entries[0].offset < entries[1].offset);
    }

    SECTION("Positive scenario: Path separator normalization") {
        // Windows uses backslashes, BIG4 uses backslashes or forward slashes.
        env.write_big_file("BIG4", {
            { "art\\textures\\image.dds", "DDS_PAYLOAD" }
            });

        BigArchive archive(env.test_file);

        char expected_sep = static_cast<char>(std::filesystem::path::preferred_separator);
        std::string expected_name = std::string("art") + expected_sep + "textures" + expected_sep + "image.dds";

        REQUIRE(archive.get_entries()[0].name == expected_name);
    }
}

TEST_CASE("BigArchive Extraction", "[big_unpack][extraction]") {
    ScopedTempEnv env;

    SECTION("Negative scenario: Missing file during extraction") {
        env.write_big_file("BIG4", { { "test.txt", "data" } });
        BigArchive archive(env.test_file);

        // Delete file underneath the object before extracting
        std::filesystem::remove(env.test_file);

        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigArchiveError);
    }

    SECTION("Positive scenario: Extract all files preserves data and creates directories") {
        std::string large_payload(1500000, 'X'); // 1.5 MB payload spanning multiple chunks
        env.write_big_file("BIG4", {
            { "root.txt", "Root Data" },
            { "nested/deep/file.txt", large_payload }
            });

        BigArchive archive(env.test_file);
        archive.extract_all(env.out_dir);

        // Verify root file
        std::filesystem::path p1 = env.out_dir / "root.txt";
        REQUIRE(std::filesystem::exists(p1));

        std::ifstream in1(p1, std::ios::binary);
        std::string content1((std::istreambuf_iterator<char>(in1)), std::istreambuf_iterator<char>());
        REQUIRE(content1 == "Root Data");

        // Verify nested file and directory creation
        std::filesystem::path p2 = env.out_dir / "nested" / "deep" / "file.txt";
        REQUIRE(std::filesystem::exists(p2));

        std::ifstream in2(p2, std::ios::binary);
        std::string content2((std::istreambuf_iterator<char>(in2)), std::istreambuf_iterator<char>());
        REQUIRE(content2 == large_payload);
    }

    SECTION("Positive scenario: UTF-8 entry names extract and read cleanly without CP_ACP errors") {
        env.write_big_file("BIG4", {
            { "data/\xC5\xBC\xC3\xB3\xC5\x82\xC4\x87.ini", "Damage=100" }
            });

        BigArchive archive(env.test_file);
        REQUIRE_NOTHROW(archive.extract_all(env.out_dir));

        auto expected_path = env.out_dir / std::filesystem::path(u8"data/\u017C\u00F3\u0142\u0107.ini");
        REQUIRE(std::filesystem::exists(expected_path));

        auto buf = archive.read_entry("data/\xC5\xBC\xC3\xB3\xC5\x82\xC4\x87.ini");
        REQUIRE(std::string(buf.begin(), buf.end()) == "Damage=100");
    }
}

TEST_CASE("BigArchive Malformed and Edge-Case Archives", "[big_unpack][edge_cases]") {
    ScopedTempEnv env;

    SECTION("Negative scenario: 0-byte .big file completely empty") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.close();

        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Negative scenario: Truncated header (file too small for metadata)") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);
        uint32_t dummy = 0;
        out.write(reinterpret_cast<const char*>(&dummy), 4);
        // File ends at 8 bytes, missing num_files and header_size
        out.close();

        // Expect the implementation to check stream state and throw upon construction
        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Negative scenario: Truncated index (EOF before reading all claimed files)") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);
        uint32_t dummy = 0;
        out.write(reinterpret_cast<const char*>(&dummy), 4);

        // Claim 10,000 files exist
        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(10000));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        uint32_t header_size = lotm::core::to_big_endian(static_cast<uint32_t>(16));
        out.write(reinterpret_cast<const char*>(&header_size), 4);
        out.close();

        // Must throw instead of allocating a massive vector of garbage
        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Negative scenario: Header size is smaller than HEADER_BASE_SIZE (16)") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);
        uint32_t total_size = lotm::core::to_little_endian(static_cast<uint32_t>(16));
        out.write(reinterpret_cast<const char*>(&total_size), 4);

        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(0));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        // Header size claimed is 12 (invalid, must be >= 16)
        uint32_t header_size = lotm::core::to_big_endian(static_cast<uint32_t>(12));
        out.write(reinterpret_cast<const char*>(&header_size), 4);
        out.close();

        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Negative scenario: Header reserve OOM DoS (small header_size inside larger physical file)") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);
        uint32_t total_size = lotm::core::to_little_endian(static_cast<uint32_t>(1024));
        out.write(reinterpret_cast<const char*>(&total_size), 4);

        // Claim 100 files, which fits in physical_size (1024 >= 800) but not in header_size (16)
        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(100));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        uint32_t header_size = lotm::core::to_big_endian(static_cast<uint32_t>(16));
        out.write(reinterpret_cast<const char*>(&header_size), 4);

        std::vector<char> padding(1008, 'A');
        out.write(padding.data(), static_cast<std::streamsize>(padding.size()));
        out.close();

        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Negative scenario: Empty entry name in index table throws BigFormatError") {
        env.write_big_file("BIG4", { { "", "payload" } });
        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Negative scenario: Unterminated string in index table throws BigFormatError") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);
        uint32_t total_size = 32;
        out.write(reinterpret_cast<const char*>(&total_size), 4);

        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(1));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        uint32_t header_size = lotm::core::to_big_endian(static_cast<uint32_t>(28));
        out.write(reinterpret_cast<const char*>(&header_size), 4);

        uint32_t offset = lotm::core::to_big_endian(static_cast<uint32_t>(28));
        uint32_t size = lotm::core::to_big_endian(static_cast<uint32_t>(4));
        out.write(reinterpret_cast<const char*>(&offset), 4);
        out.write(reinterpret_cast<const char*>(&size), 4);

        // Write 4 non-null characters up to header_size (28) + 4 payload bytes without any '\0'
        out.write("ABCDDATA", 8);
        out.close();

        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Negative scenario: Payload offset out of physical file bounds") {
        env.write_big_file("BIG4", { { "test.txt", "data" } });

        // Corrupt the offset in the binary file to point past EOF
        std::fstream file(env.test_file, std::ios::in | std::ios::out | std::ios::binary);
        file.seekp(16, std::ios::beg); // Seek to offset of first entry
        uint32_t bad_offset = lotm::core::to_big_endian(static_cast<uint32_t>(999999));
        file.write(reinterpret_cast<const char*>(&bad_offset), 4);
        file.close();

        BigArchive archive(env.test_file);

        // Extraction should fail upon detecting bad offset limits
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigFormatError);
    }

    SECTION("Negative scenario: 32-bit addition wrap-around in extraction bounds check") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);

        uint32_t total_size = lotm::core::to_little_endian(static_cast<uint32_t>(38));
        out.write(reinterpret_cast<const char*>(&total_size), 4);

        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(1));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        uint32_t header_size = lotm::core::to_big_endian(static_cast<uint32_t>(38));
        out.write(reinterpret_cast<const char*>(&header_size), 4);

        // offset + size = 0xFFFFFFF0 + 0x20 = 0x100000010.
        // Cast to uint32_t = 0x10. If the engine didn't safely upcast to uintmax_t,
        // 0x10 < 38, so it would pass bounds checking maliciously.
        uint32_t offset = lotm::core::to_big_endian(static_cast<uint32_t>(0xFFFFFFF0));
        uint32_t size = lotm::core::to_big_endian(static_cast<uint32_t>(0x20));
        out.write(reinterpret_cast<const char*>(&offset), 4);
        out.write(reinterpret_cast<const char*>(&size), 4);

        out.write("A.txt", 5);
        out.write("\0", 1);
        out.write("L219\0\0\0\0", 8);
        out.close();

        BigArchive archive(env.test_file);
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigFormatError);
    }

    SECTION("Positive scenario: Zero-byte file extraction succeeds safely") {
        env.write_big_file("BIG4", { { "empty.txt", "" } });

        BigArchive archive(env.test_file);
        REQUIRE_NOTHROW(archive.extract_all(env.out_dir));

        std::filesystem::path empty_path = env.out_dir / "empty.txt";
        REQUIRE(std::filesystem::exists(empty_path));
        REQUIRE(std::filesystem::file_size(empty_path) == 0);
    }

    SECTION("Positive scenario: Extraction into pre-existing directory succeeds") {
        env.write_big_file("BIG4", { { "file.txt", "data" } });

        // Manually create the output directory before extraction
        std::filesystem::create_directories(env.out_dir);

        BigArchive archive(env.test_file);
        REQUIRE_NOTHROW(archive.extract_all(env.out_dir));
        REQUIRE(std::filesystem::exists(env.out_dir / "file.txt"));
    }

    SECTION("Negative scenario: Header total_size smaller than header_size throws BigFormatError") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);
        uint32_t total_size = lotm::core::to_little_endian(static_cast<uint32_t>(12));
        out.write(reinterpret_cast<const char*>(&total_size), 4);

        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(0));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        uint32_t header_size = lotm::core::to_big_endian(static_cast<uint32_t>(24));
        out.write(reinterpret_cast<const char*>(&header_size), 4);

        out.write("L219\0\0\0\0", 8);
        out.close();

        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }
}

TEST_CASE("BigArchive Windows Path Security and NTFS Evasions", "[big_unpack][security]") {
    ScopedTempEnv env;

    SECTION("Negative scenario: Zip-Slip relative path traversal is blocked") {
        env.write_big_file("BIG4", { { "..\\escaped.txt", "malicious_payload" } });
        BigArchive archive(env.test_file);
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigSecurityError);
        REQUIRE_FALSE(std::filesystem::exists(env.root_dir / "escaped.txt"));
        REQUIRE_FALSE(std::filesystem::exists(env.out_dir));
    }

    SECTION("Negative scenario: Rooted paths in entry are blocked") {
        env.write_big_file("BIG4", { { "\\rooted_evil.txt", "malicious_payload" } });
        BigArchive archive(env.test_file);
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigSecurityError);
    }

    SECTION("Negative scenario: Strict abort on symlink in extraction path") {
        // Create a symlink in the output directory
        std::filesystem::create_directories(env.out_dir);
        std::filesystem::path safe_target = env.root_dir / "safe_folder";
        std::filesystem::create_directories(safe_target);

        std::filesystem::path link_path = env.out_dir / "link_dir";
        std::error_code ec;
        std::filesystem::create_directory_symlink(safe_target, link_path, ec);

        // Only run test if OS privileges allow symlink creation
        if (!ec) {
            env.write_big_file("BIG4", { { "link_dir\\payload.txt", "malicious_payload" } });
            BigArchive archive(env.test_file);

            // Extraction must strictly abort because a component is a symlink
            REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigSecurityError);
        }
    }

    SECTION("Negative scenario: Windows DOS device name evasion") {
        // Test names that evade simple base == "CON" checks due to spaces or extensions
        env.write_big_file("BIG4", { { "data\\CON .txt", "payload" } });
        BigArchive archive1(env.test_file);
        REQUIRE_THROWS_AS(archive1.extract_all(env.out_dir), BigSecurityError);

        env.write_big_file("BIG4", { { "data\\COM1.ini", "payload" } });
        BigArchive archive2(env.test_file);
        REQUIRE_THROWS_AS(archive2.extract_all(env.out_dir), BigSecurityError);

        // Superscript UTF-8 COM¹ and CLOCK$ device names
        env.write_big_file("BIG4", { { "data\\COM\xC2\xB9.ini", "payload" } });
        BigArchive archive3(env.test_file);
        REQUIRE_THROWS_AS(archive3.extract_all(env.out_dir), BigSecurityError);

        env.write_big_file("BIG4", { { "data\\COM\xB2.ini", "payload" } });
        BigArchive archive4(env.test_file);
        REQUIRE_THROWS_AS(archive4.extract_all(env.out_dir), BigSecurityError);

        env.write_big_file("BIG4", { { "data\\CLOCK$.ini", "payload" } });
        BigArchive archive5(env.test_file);
        REQUIRE_THROWS_AS(archive5.extract_all(env.out_dir), BigSecurityError);
    }

    SECTION("Negative scenario: Zip-Bomb Amplification Threshold Exceeded") {
        // Create an archive where entries heavily overlap to claim massive extracted size
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);

        constexpr uint32_t file_count = 50;
        constexpr std::string_view entry_name = "A.txt"; // 5 chars + 1 null = 6 bytes
        constexpr uint32_t entry_record_size = 4 + 4 + static_cast<uint32_t>(entry_name.size() + 1); // 14 bytes
        constexpr uint32_t header_size = 16 + (file_count * entry_record_size);
        constexpr uint32_t payload_size = 1024 * 1024;
        constexpr uint32_t total_size = header_size + payload_size;

        uint32_t le_total_size = lotm::core::to_little_endian(total_size);
        out.write(reinterpret_cast<const char*>(&le_total_size), 4);

        uint32_t num_files = lotm::core::to_big_endian(file_count);
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        uint32_t be_header_size = lotm::core::to_big_endian(header_size);
        out.write(reinterpret_cast<const char*>(&be_header_size), 4);

        // 50 files all pointing to the exact same 1MB byte range
        uint32_t be_offset = lotm::core::to_big_endian(header_size);
        uint32_t be_size = lotm::core::to_big_endian(payload_size);

        for (uint32_t i = 0; i < file_count; ++i) {
            out.write(reinterpret_cast<const char*>(&be_offset), 4);
            out.write(reinterpret_cast<const char*>(&be_size), 4);
            out.write(entry_name.data(), static_cast<std::streamsize>(entry_name.size() + 1));
        }

        // Write 1MB of actual payload
        std::vector<char> test_payload(payload_size, 'X');
        out.write(test_payload.data(), static_cast<std::streamsize>(test_payload.size()));
        out.close();

        // Total physical size is ~1MB. Claimed extracted size is 50MB.
        // If MAX_AMPLIFICATION_RATIO is 20, this exceeds it (50 > 20).
        BigArchive archive(env.test_file);
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigSecurityError);
    }

    SECTION("Negative scenario: Extended Win32 namespace prefixes are blocked") {
        env.write_big_file("BIG4", { { "\\\\?\\C:\\Windows\\system32.dll", "payload" } });
        BigArchive archive1(env.test_file);
        REQUIRE_THROWS_AS(archive1.extract_all(env.out_dir), BigSecurityError);

        env.write_big_file("BIG4", { { "\\??\\malicious.exe", "payload" } });
        BigArchive archive2(env.test_file);
        REQUIRE_THROWS_AS(archive2.extract_all(env.out_dir), BigSecurityError);
    }

    SECTION("Negative scenario: Windows drive-relative directory traversals are blocked") {
        env.write_big_file("BIG4", { { "C:../escaped.txt", "payload" } });
        BigArchive archive1(env.test_file);
        REQUIRE_THROWS_AS(archive1.extract_all(env.out_dir), BigSecurityError);

        env.write_big_file("BIG4", { { "D:file.txt", "payload" } });
        BigArchive archive2(env.test_file);
        REQUIRE_THROWS_AS(archive2.extract_all(env.out_dir), BigSecurityError);
    }

    SECTION("Negative scenario: NTFS reserved characters are blocked") {
        env.write_big_file("BIG4", { { "data\\file<name>.txt", "payload" } });
        BigArchive archive(env.test_file);
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigSecurityError);
    }

    SECTION("Negative scenario: Trailing spaces and dots on path components are blocked") {
        env.write_big_file("BIG4", { { "hidden_folder .\\file.txt", "payload" } });
        BigArchive archive1(env.test_file);
        REQUIRE_THROWS_AS(archive1.extract_all(env.out_dir), BigSecurityError);

        env.write_big_file("BIG4", { { "data\\...\\file.txt", "payload" } });
        BigArchive archive2(env.test_file);
        REQUIRE_THROWS_AS(archive2.extract_all(env.out_dir), BigSecurityError);
    }
}

TEST_CASE("BigArchive Progress Callback Integration", "[big_unpack][callback]") {
    ScopedTempEnv env;

    SECTION("Positive scenario: Callback is invoked for each extracted file") {
        env.write_big_file("BIG4", {
            { "fileA.txt", "data" },
            { "fileB.txt", "" }
            });

        BigArchive archive(env.test_file);
        std::vector<std::string> reported_files;
        auto cb = [&](const ProgressReport& report) -> bool {
            reported_files.emplace_back(report.entry_name);
            REQUIRE(report.bytes_transferred == report.file_size);
            REQUIRE(report.total_archive_size == 4);
            return true;
            };

        REQUIRE_NOTHROW(archive.extract_all(env.out_dir, cb));

        REQUIRE(reported_files.size() == 2);
        REQUIRE(reported_files[0] == "fileA.txt");
        REQUIRE(reported_files[1] == "fileB.txt");
    }

    SECTION("Negative scenario: Returning false from callback cancels extraction and removes partial file") {
        env.write_big_file("BIG4", {
            { "fileA.txt", "data" },
            { "fileB.txt", "more_data" }
            });

        BigArchive archive(env.test_file);
        auto cancel_cb = [](const ProgressReport&) -> bool {
            return false;
            };

        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir, cancel_cb), BigArchiveError);
        REQUIRE_FALSE(std::filesystem::exists(env.out_dir / "fileA.txt"));
        REQUIRE_FALSE(std::filesystem::exists(env.out_dir / "fileB.txt"));

        // Cancellation on zero-byte file
        env.write_big_file("BIG4", { { "empty.txt", "" } });
        BigArchive empty_arc(env.test_file);
        REQUIRE_THROWS_AS(empty_arc.extract_all(env.out_dir, cancel_cb), BigArchiveError);
        REQUIRE_FALSE(std::filesystem::exists(env.out_dir / "empty.txt"));
    }
}

TEST_CASE("BigArchive File I/O Error Handling", "[big_unpack][io]") {
    ScopedTempEnv env;

    SECTION("Negative scenario: Extraction fails if target output cannot be created") {
        env.write_big_file("BIG4", { { "conflict.txt", "data" } });

        // Force a collision by creating a DIRECTORY with the exact same name 
        // as the target file. std::ofstream will fail to open a directory for writing.
        std::filesystem::create_directories(env.out_dir / "conflict.txt");

        BigArchive archive(env.test_file);

        // This exercises !out_file.is_open() and covers the throw BigArchiveError block
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigArchiveError);
    }
}

TEST_CASE("BigArchive Coverage Padding Edge Cases", "[big_unpack][coverage]") {
    ScopedTempEnv env;

    SECTION("Path contains reserved colon") {
        env.write_big_file("BIG4", { { "C:\\Windows\\system32.dll", "data" } });
        BigArchive archive(env.test_file);
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigSecurityError);
    }

    SECTION("Truncated index (EOF during offset/size read)") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);
        uint32_t total = lotm::core::to_little_endian(24u); out.write(reinterpret_cast<char*>(&total), 4);
        uint32_t num = lotm::core::to_big_endian(1u); out.write(reinterpret_cast<char*>(&num), 4);
        uint32_t head = lotm::core::to_big_endian(24u); out.write(reinterpret_cast<char*>(&head), 4);
        out.write("\0\0\0", 3); // 3 bytes out of 8 required for offset+size
        out.close();
        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Truncated string table (EOF before null terminator)") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);
        uint32_t total = lotm::core::to_little_endian(25u); out.write(reinterpret_cast<char*>(&total), 4);
        uint32_t num = lotm::core::to_big_endian(1u); out.write(reinterpret_cast<char*>(&num), 4);
        uint32_t head = lotm::core::to_big_endian(25u); out.write(reinterpret_cast<char*>(&head), 4);
        uint32_t offset = lotm::core::to_big_endian(25u); out.write(reinterpret_cast<char*>(&offset), 4);
        uint32_t size = lotm::core::to_big_endian(0u); out.write(reinterpret_cast<char*>(&size), 4);
        out.write("A", 1); // No null terminator
        out.close();
        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }
}

TEST_CASE("BigArchive Fast-Fail Logic Paths", "[big_unpack][malformed]") {
    ScopedTempEnv env;

    SECTION("Negative scenario: Alternate Data Stream (ADS) evasion detected") {
        // Triggers the ':' check in is_unsafe_filename
        env.write_big_file("BIG4", { { "data\\stream.txt:hidden", "payload" } });
        BigArchive archive(env.test_file);
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigSecurityError);
    }

    SECTION("Negative scenario: Truncated BIG4 file index") {
        // Triggers the !file check inside the index reading loop
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);

        uint32_t total_size = lotm::core::to_little_endian(static_cast<uint32_t>(32));
        out.write(reinterpret_cast<const char*>(&total_size), 4);

        // Claim 2 files exist
        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(2));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        uint32_t header_size = lotm::core::to_big_endian(static_cast<uint32_t>(32));
        out.write(reinterpret_cast<const char*>(&header_size), 4);

        // Write only ONE entry's offset and size, then abruptly end the file
        uint32_t offset = lotm::core::to_big_endian(static_cast<uint32_t>(32));
        uint32_t size = lotm::core::to_big_endian(static_cast<uint32_t>(100));
        out.write(reinterpret_cast<const char*>(&offset), 4);
        out.write(reinterpret_cast<const char*>(&size), 4);
        out.close();

        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }

    SECTION("Negative scenario: Truncated BIG4 string table") {
        // Triggers the string table bounds check (current_pos >= header_size_)
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);

        uint32_t total_size = lotm::core::to_little_endian(static_cast<uint32_t>(32));
        out.write(reinterpret_cast<const char*>(&total_size), 4);

        uint32_t num_files = lotm::core::to_big_endian(static_cast<uint32_t>(1));
        out.write(reinterpret_cast<const char*>(&num_files), 4);

        // Set header size exactly to where the offset/size fields end (24 bytes total)
        uint32_t header_size = lotm::core::to_big_endian(static_cast<uint32_t>(24));
        out.write(reinterpret_cast<const char*>(&header_size), 4);

        uint32_t offset = lotm::core::to_big_endian(static_cast<uint32_t>(32));
        uint32_t size = lotm::core::to_big_endian(static_cast<uint32_t>(100));
        out.write(reinterpret_cast<const char*>(&offset), 4);
        out.write(reinterpret_cast<const char*>(&size), 4);
        // End the file immediately. There is no string and no null terminator.
        out.close();

        REQUIRE_THROWS_AS(BigArchive(env.test_file), BigFormatError);
    }
}

TEST_CASE("BigArchive In-Memory Single-File Extraction and Lifecycle", "[big_unpack][memory][lifecycle]") {
    ScopedTempEnv env;

    SECTION("Positive scenario: Read single entry by name and by BigEntry record") {
        env.write_big_file("BIG4", {
            { "root.txt", "RootPayload" },
            { "data\\nested/weapon.ini", "Damage=50" }
            });

        BigArchive archive(env.test_file);

        // Read using normalized forward-slash and case-insensitive path
        auto buf_by_name = archive.read_entry("DATA/nested\\WEAPON.INI");
        std::string str_by_name(reinterpret_cast<const char*>(buf_by_name.data()), buf_by_name.size());
        REQUIRE(str_by_name == "Damage=50");

        // Read directly using BigEntry struct
        const auto entries = archive.get_entries();
        REQUIRE(entries.size() == 2);
        auto buf_by_entry = archive.read_entry(entries[0]);
        std::string str_by_entry(reinterpret_cast<const char*>(buf_by_entry.data()), buf_by_entry.size());
        REQUIRE(str_by_entry == "RootPayload");
    }

    SECTION("Positive scenario: Read zero-byte entry returns empty buffer safely") {
        env.write_big_file("BIG4", { { "empty.txt", "" } });

        BigArchive archive(env.test_file);
        auto buf = archive.read_entry("empty.txt");
        REQUIRE(buf.empty());
    }

    SECTION("Negative scenario: Reading non-existent entry throws BigArchiveError") {
        env.write_big_file("BIG4", { { "fileA.txt", "data" } });

        BigArchive archive(env.test_file);
        // Different length mismatch and identical length mismatch
        REQUIRE_THROWS_AS(archive.read_entry("missing.txt"), BigArchiveError);
        REQUIRE_THROWS_AS(archive.read_entry("fileB.txt"), BigArchiveError);
    }

    SECTION("Negative scenario: Entry bounds exceeding physical file size throws BigFormatError") {
        env.write_big_file("BIG4", { { "test.txt", "data" } });

        BigArchive archive(env.test_file);
        BigEntry out_of_bounds_entry{ 999999u, 10u, "test.txt" };
        REQUIRE_THROWS_AS(archive.read_entry(out_of_bounds_entry), BigFormatError);
    }

    SECTION("Negative scenario: Missing or locked archive file during read_entry throws BigArchiveError") {
        env.write_big_file("BIG4", { { "test.txt", "data" } });
        BigArchive archive(env.test_file);
        const auto entry = archive.get_entries().front();

        // Exclusive lock (_SH_DENYRW = 0x10) allows file_size() metadata check but blocks ifstream::open()
        FILE* locked_file = _fsopen(env.test_file.string().c_str(), "rb", 0x10);
        if (locked_file) {
            REQUIRE_THROWS_AS(archive.read_entry(entry), BigArchiveError);
            fclose(locked_file);
        }

        // Removing the file triggers the file_size(ec) error branch
        std::filesystem::remove(env.test_file);
        REQUIRE_THROWS_AS(archive.read_entry(entry), BigArchiveError);
    }

    SECTION("Positive and negative scenarios: Archive close() lifecycle state and post-close guards") {
        env.write_big_file("BIG4", { { "test.txt", "data" } });

        BigArchive archive(env.test_file);
        const auto entry = archive.get_entries().front();
        REQUIRE_FALSE(archive.is_closed());

        archive.close();
        REQUIRE(archive.is_closed());

        // All operations on a closed archive must throw BigArchiveError
        REQUIRE_THROWS_AS(archive.get_entries(), BigArchiveError);
        REQUIRE_THROWS_AS(archive.read_entry("test.txt"), BigArchiveError);
        REQUIRE_THROWS_AS(archive.read_entry(entry), BigArchiveError);
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), BigArchiveError);
    }
}

TEST_CASE("BigArchive Selective Glob Extraction", "[big_unpack][filter]") {
    ScopedTempEnv env;

    env.write_big_file("BIG4", {
        { "readme.txt", "ReadmeData" },
        { "data\\ini\\weapon.ini", "WeaponData" },
        { "data\\ini\\armor.ini", "ArmorData" },
        { "art\\textures\\hero01.dds", "DDS1" },
        { "art\\textures\\hero02.dds", "DDS2" }
        });

    BigArchive archive(env.test_file);

    SECTION("Positive scenario: get_entries filters with '*', '?', trailing '*', and slash/case normalization") {
        // Universal wildcard
        REQUIRE(archive.get_entries("*").size() == 5);

        // Multi-segment star backtracking and forward-slash normalization
        auto ini_entries = archive.get_entries("DATA/ini/*.INI");
        REQUIRE(ini_entries.size() == 2);

        // Single-character '?' wildcard matching
        auto dds_entries = archive.get_entries("art\\textures\\hero0?.dds");
        REQUIRE(dds_entries.size() == 2);

        // Trailing star after full match
        auto readme_entries = archive.get_entries("readme.txt**");
        REQUIRE(readme_entries.size() == 1);

        // Non-matching pattern returns empty vector
        REQUIRE(archive.get_entries("music/*.mp3").empty());
    }

    SECTION("Positive scenario: extract_all with filter_pattern extracts only matching entries") {
        std::vector<std::string> extracted;
        archive.extract_all(env.out_dir, [&](const ProgressReport& report) -> bool {
            extracted.emplace_back(report.entry_name);
            return true;
            }, "data/ini/*.ini");

        REQUIRE(extracted.size() == 2);
        REQUIRE(std::filesystem::exists(env.out_dir / "data" / "ini" / "weapon.ini"));
        REQUIRE(std::filesystem::exists(env.out_dir / "data" / "ini" / "armor.ini"));
        REQUIRE_FALSE(std::filesystem::exists(env.out_dir / "readme.txt"));
        REQUIRE_FALSE(std::filesystem::exists(env.out_dir / "art" / "textures" / "hero01.dds"));
    }
}
