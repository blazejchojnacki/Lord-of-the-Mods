
/**
 * @file tests/cpp/big/test_big_unpack.cpp
 * @brief Unit tests for the BigArchive unpacking implementation.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include <big/big_unpack.hpp>
#include <core/endian.hpp>
#include <filesystem>
#include <fstream>
#include <vector>
#include <string>

    using namespace lotm::big;

// RAII Helper to create temporary binary files and directories for testing
class ScopedTempEnv {
public:
    std::filesystem::path root_dir;
    std::filesystem::path test_file;
    std::filesystem::path out_dir;

    ScopedTempEnv() {
        root_dir = std::filesystem::temp_directory_path() / "lotm_unpack_test";
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
            header_size += 8 + entry.first.size() + 1;
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
            out.write(entry.first.c_str(), entry.first.size() + 1); // include null terminator

            current_offset += static_cast<uint32_t>(entry.second.size());
        }

        // Write Payloads
        for (const auto& entry : entries) {
            out.write(entry.second.c_str(), entry.second.size());
        }

        // Fix up total size (Little Endian)
        uint32_t total_size = current_offset;
        out.seekp(4, std::ios::beg);
        out.write(reinterpret_cast<const char*>(&total_size), 4);
    }
};


TEST_CASE("BigArchive Initialization and Basic Error Handling", "[big_unpack][error]") {
    ScopedTempEnv env;

    SECTION("Negative scenario: File does not exist") {
        BigArchive archive(env.root_dir / "non_existent.big");
        REQUIRE_THROWS_AS(archive.read_header(), std::runtime_error);
    }

    SECTION("Negative scenario: Invalid magic string") {
        env.write_big_file("BOGUS", {});
        BigArchive archive(env.test_file);
        REQUIRE_THROWS_AS(archive.read_header(), std::invalid_argument);
    }
}

TEST_CASE("BigArchive Header Parsing", "[big_unpack][header]") {
    ScopedTempEnv env;

    SECTION("Positive scenario: Valid BIG4 file with zero entries") {
        env.write_big_file("BIG4", {});
        BigArchive archive(env.test_file);
        REQUIRE_NOTHROW(archive.read_header());
        REQUIRE(archive.get_entries().empty());
    }

    SECTION("Positive scenario: Valid BIG4 file with multiple entries") {
        env.write_big_file("BIG4", {
            { "file1.txt", "Hello World" },
            { "data/file2.ini", "ConfigData=1" }
            });

        BigArchive archive(env.test_file);
        REQUIRE_NOTHROW(archive.read_header());

        const auto& entries = archive.get_entries();
        REQUIRE(entries.size() == 2);

        // Validate first entry
        REQUIRE(entries[0].name == "file1.txt");
        REQUIRE(entries[0].size == 11);

        // Validate second entry
        REQUIRE(entries[1].name == "data/file2.ini");
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
        archive.read_header();

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
        archive.read_header();

        // Delete file underneath the object before extracting
        std::filesystem::remove(env.test_file);

        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), std::runtime_error);
    }

    SECTION("Positive scenario: Extract all files preserves data and creates directories") {
        env.write_big_file("BIG4", {
            { "root.txt", "Root Data" },
            { "nested/deep/file.txt", "Deep Data" }
            });

        BigArchive archive(env.test_file);
        archive.read_header();
        archive.extract_all(env.out_dir);

        // Verify root file
        std::filesystem::path p1 = env.out_dir / "root.txt";
        REQUIRE(std::filesystem::exists(p1));

        std::ifstream in1(p1);
        std::string content1((std::istreambuf_iterator<char>(in1)), std::istreambuf_iterator<char>());
        REQUIRE(content1 == "Root Data");

        // Verify nested file and directory creation
        std::filesystem::path p2 = env.out_dir / "nested" / "deep" / "file.txt";
        REQUIRE(std::filesystem::exists(p2));

        std::ifstream in2(p2);
        std::string content2((std::istreambuf_iterator<char>(in2)), std::istreambuf_iterator<char>());
        REQUIRE(content2 == "Deep Data");
    }
}

TEST_CASE("BigArchive Malformed and Edge-Case Archives", "[big_unpack][edge_cases]") {
    ScopedTempEnv env;

    SECTION("Negative scenario: Truncated header (file too small for metadata)") {
        std::ofstream out(env.test_file, std::ios::binary);
        out.write("BIG4", 4);
        uint32_t dummy = 0;
        out.write(reinterpret_cast<const char*>(&dummy), 4);
        // File ends at 8 bytes, missing num_files and header_size
        out.close();

        BigArchive archive(env.test_file);
        // Expect the implementation to check stream state and throw
        REQUIRE_THROWS_AS(archive.read_header(), std::runtime_error);
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

        BigArchive archive(env.test_file);
        // Must throw instead of allocating a massive vector of garbage
        REQUIRE_THROWS_AS(archive.read_header(), std::runtime_error);
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
        archive.read_header(); // Header parses fine

        // Extraction should fail upon detecting bad offset limits
        REQUIRE_THROWS_AS(archive.extract_all(env.out_dir), std::runtime_error);
    }

    SECTION("Positive scenario: Zero-byte file extraction succeeds safely") {
        env.write_big_file("BIG4", { { "empty.txt", "" } });

        BigArchive archive(env.test_file);
        archive.read_header();
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
        archive.read_header();
        REQUIRE_NOTHROW(archive.extract_all(env.out_dir));
        REQUIRE(std::filesystem::exists(env.out_dir / "file.txt"));
    }
}
