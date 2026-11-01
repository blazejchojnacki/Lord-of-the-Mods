/**
 * @file tests/cpp/big/test_big_packer.cpp
 * @brief Unit tests for the BigPacker serialization implementation.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include <big/big_packer.hpp>
#include <big/exceptions.hpp>
#include <core/endian.hpp>
#include <filesystem>
#include <fstream>
#include <vector>
#include <string>
#include <string_view>
#include <stdio.h>

using namespace lotm::big;

// RAII Helper to create temporary environments and files
class ScopedPackEnv {
public:
    std::filesystem::path root_dir;
    std::filesystem::path src_dir;
    std::filesystem::path out_file;

    ScopedPackEnv() {
        root_dir = std::filesystem::temp_directory_path() / "lotm_pack_test";
        src_dir = root_dir / "src";
        out_file = root_dir / "output.big";

        std::filesystem::create_directories(src_dir);
    }

    ~ScopedPackEnv() {
        std::filesystem::remove_all(root_dir);
    }

    void create_dummy_file(const std::filesystem::path& rel_path, std::string_view content) {
        std::filesystem::path full_path = src_dir / rel_path;
        std::filesystem::create_directories(full_path.parent_path());
        std::ofstream out(full_path, std::ios::binary);
        out.write(content.data(), static_cast<std::streamsize>(content.size()));
    }
};

// Helper to read null-terminated string from binary stream
static std::string read_null_terminated(std::ifstream& stream) {
    std::string res;
    std::getline(stream, res, '\0');
    return res;
}

TEST_CASE("BigPacker Input Validation and Exceptions", "[big_pack][error]") {
    ScopedPackEnv env;

    SECTION("Negative scenario: Source directory does not exist") {
        std::filesystem::remove_all(env.src_dir);
        REQUIRE_THROWS_AS(BigPacker::pack_from_directory(env.src_dir, env.out_file), std::invalid_argument);
    }

    SECTION("Negative scenario: Source directory is actually a file") {
        std::filesystem::path fake_dir = env.root_dir / "fake_dir";
        std::ofstream(fake_dir) << "file data";
        REQUIRE_THROWS_AS(BigPacker::pack_from_directory(fake_dir, env.out_file), std::invalid_argument);
    }

    SECTION("Negative scenario: Output file path is invalid") {
        std::filesystem::path bad_out = env.root_dir / "non_existent_folder" / "out.big";
        REQUIRE_THROWS_AS(BigPacker::pack_from_directory(env.src_dir, bad_out), std::invalid_argument);
    }

    SECTION("Negative scenario: Output file resides inside source directory (self-inclusion)") {
        env.create_dummy_file("unit.ini", "Health=100");
        std::filesystem::path nested_out = env.src_dir / "nested_output.big";
        REQUIRE_THROWS_AS(BigPacker::pack_from_directory(env.src_dir, nested_out), std::invalid_argument);
    }
}

TEST_CASE("BigPacker Empty Directory Serialization", "[big_pack][empty]") {
    ScopedPackEnv env;

    SECTION("Positive scenario: Packing an empty directory yields a valid header-only archive") {
        REQUIRE_NOTHROW(BigPacker::pack_from_directory(env.src_dir, env.out_file));
        REQUIRE(std::filesystem::exists(env.out_file));

        std::ifstream in(env.out_file, std::ios::binary);
        char magic[5] = { 0 };
        in.read(magic, 4);
        REQUIRE(std::string_view(magic) == "BIG4");

        uint32_t total_size, num_files, header_size;
        in.read(reinterpret_cast<char*>(&total_size), 4);
        in.read(reinterpret_cast<char*>(&num_files), 4);
        in.read(reinterpret_cast<char*>(&header_size), 4);

        REQUIRE(lotm::core::from_little_endian(total_size) == 24); // 16 bytes base + 8 bytes padding
        REQUIRE(lotm::core::from_big_endian(num_files) == 0);
        REQUIRE(lotm::core::from_big_endian(header_size) == 24);

        // Verify EA padding tag L219\0\0\0\0 is present
        char padding[8] = { 0 };
        in.read(padding, 8);
        REQUIRE(std::string_view(padding, 8) == std::string_view("L219\0\0\0\0", 8));
    }
}

TEST_CASE("BigPacker Sorting and Path Normalization", "[big_pack][index]") {
    ScopedPackEnv env;

    SECTION("Positive scenario: Index is sorted alphabetically and slashes are normalized") {
        // Create files out of alphabetical order, including nested paths
        env.create_dummy_file("z_file.txt", "data");
        env.create_dummy_file("A_file.txt", "data");
        env.create_dummy_file("sub/folder/file.txt", "data");

        REQUIRE_NOTHROW(BigPacker::pack_from_directory(env.src_dir, env.out_file));

        std::ifstream in(env.out_file, std::ios::binary);
        in.seekg(8, std::ios::beg); // Skip magic and total_size

        uint32_t num_files, header_size;
        in.read(reinterpret_cast<char*>(&num_files), 4);
        in.read(reinterpret_cast<char*>(&header_size), 4);

        num_files = lotm::core::from_big_endian(num_files);
        REQUIRE(num_files == 3);

        // Read strings to verify alphabetical sorting
        std::vector<std::string> names;
        for (uint32_t i = 0; i < num_files; ++i) {
            in.seekg(8, std::ios::cur); // Skip offset and size
            names.push_back(read_null_terminated(in));
        }

        // Expected sorted order based on ASCII (A < s < z)
        // Also verify that forward slashes became backslashes
        REQUIRE(names[0] == "A_file.txt");
        REQUIRE(names[1] == "sub\\folder\\file.txt");
        REQUIRE(names[2] == "z_file.txt");
    }
}

TEST_CASE("BigPacker Payload Fidelity and Offset Alignment", "[big_pack][payload]") {
    ScopedPackEnv env;

    SECTION("Positive scenario: Payload bytes are packed accurately at their designated offsets") {
        std::string payload1 = "Hello World";
        std::string payload2(1500000, 'B'); // 1.5 MB payload spanning multiple 1 MB chunks

        env.create_dummy_file("file1.txt", payload1);
        env.create_dummy_file("file2.txt", payload2);

        REQUIRE_NOTHROW(BigPacker::pack_from_directory(env.src_dir, env.out_file));

        std::ifstream in(env.out_file, std::ios::binary);
        in.seekg(8, std::ios::beg);

        uint32_t num_files;
        in.read(reinterpret_cast<char*>(&num_files), 4);
        num_files = lotm::core::from_big_endian(num_files);
        in.seekg(4, std::ios::cur); // Skip header size

        struct ExpectedFile {
            uint32_t offset;
            uint32_t size;
            std::string name;
        };
        std::vector<ExpectedFile> index;

        for (uint32_t i = 0; i < num_files; ++i) {
            ExpectedFile f;
            in.read(reinterpret_cast<char*>(&f.offset), 4);
            in.read(reinterpret_cast<char*>(&f.size), 4);
            f.offset = lotm::core::from_big_endian(f.offset);
            f.size = lotm::core::from_big_endian(f.size);
            f.name = read_null_terminated(in);
            index.push_back(f);
        }

        // Verify payload 1 (file1.txt is alphabetically first)
        REQUIRE(index[0].name == "file1.txt");
        REQUIRE(index[0].size == payload1.size());
        in.seekg(index[0].offset, std::ios::beg);
        std::vector<char> buf1(index[0].size);
        in.read(buf1.data(), static_cast<std::streamsize>(buf1.size()));
        REQUIRE(std::string(buf1.begin(), buf1.end()) == payload1);

        // Verify payload 2 (file2.txt)
        REQUIRE(index[1].name == "file2.txt");
        REQUIRE(index[1].size == payload2.size());
        in.seekg(index[1].offset, std::ios::beg);
        std::vector<char> buf2(index[1].size);
        in.read(buf2.data(), static_cast<std::streamsize>(buf2.size()));
        REQUIRE(std::string(buf2.begin(), buf2.end()) == payload2);
    }
}

TEST_CASE("BigPacker Output Path Handling and Boundary Limits", "[big_pack][limits]") {
    ScopedPackEnv env;

    SECTION("Negative scenario: Archive payload exceeding 4GB format limits throws std::length_error") {
        std::filesystem::path huge_file = env.src_dir / "large_payload.dat";
        std::ofstream out(huge_file, std::ios::binary);
        out.write("X", 1);
        out.close();

        // Resize sparse allocation to 4.1 GB to trigger 32-bit format limit validation
        std::filesystem::resize_file(huge_file, 4402341478ULL);

        REQUIRE_THROWS_AS(BigPacker::pack_from_directory(env.src_dir, env.out_file), std::length_error);
    }
}

TEST_CASE("BigPacker Progress Callback Integration", "[big_pack][callback]") {
    ScopedPackEnv env;

    SECTION("Positive scenario: Callback is invoked for each file packed") {
        env.create_dummy_file("fileA.txt", "data");
        env.create_dummy_file("sub/fileB.txt", "data");

        std::vector<std::string> reported_files;
        auto cb = [&](std::string_view name) {
            reported_files.emplace_back(name);
            };

        REQUIRE_NOTHROW(BigPacker::pack_from_directory(env.src_dir, env.out_file, cb));

        REQUIRE(reported_files.size() == 2);
        // SAGE sorting puts fileA before sub\fileB
        REQUIRE(reported_files[0] == "fileA.txt");
        REQUIRE(reported_files[1] == "sub\\fileB.txt");
    }
}

TEST_CASE("BigPacker Case-Insensitive Deduplication", "[big_pack][dedup]") {
    SECTION("Negative scenario: Duplicate paths differing only by case throw std::invalid_argument") {
        std::vector<lotm::big::detail::PackSourceRecord> entries = {
            { "fake/path/unit.ini", "data\\unit.ini", 100, 0 },
            { "fake/path/UNIT.INI", "data\\UNIT.INI", 100, 0 }
        };

        REQUIRE_THROWS_AS(
            lotm::big::detail::sort_and_validate_entries(entries),
            std::invalid_argument
        );
    }

    SECTION("Positive scenario: Case-distinct unique paths pass validation") {
        std::vector<lotm::big::detail::PackSourceRecord> entries = {
            { "fake/path/armor.ini", "data\\armor.ini", 100, 0 },
            { "fake/path/weapon.ini", "data\\weapon.ini", 100, 0 }
        };

        REQUIRE_NOTHROW(lotm::big::detail::sort_and_validate_entries(entries));
    }
}

TEST_CASE("BigPacker Cumulative Limits and RAII Cleanup", "[big_pack][limits][raii]") {
    ScopedPackEnv env;

    SECTION("Negative scenario: Target output is an existing directory") {
        std::filesystem::create_directories(env.out_file);

        REQUIRE_THROWS_AS(
            BigPacker::pack_from_directory(env.src_dir, env.out_file),
            std::invalid_argument
        );
    }

    SECTION("Negative scenario: Exception in progress callback triggers RAII cleanup") {
        env.create_dummy_file("file.txt", "data");

        auto throwing_cb = [](std::string_view) {
            throw std::runtime_error("Simulated interrupt");
            };

        REQUIRE_THROWS_AS(
            BigPacker::pack_from_directory(env.src_dir, env.out_file, throwing_cb),
            std::runtime_error
        );

        // Verify the partial archive was deleted by the RAII guard during stack unwind
        REQUIRE_FALSE(std::filesystem::exists(env.out_file));
    }

    SECTION("Negative scenario: Cumulative archive size exceeds 4GB format limit") {
        std::filesystem::path huge1 = env.src_dir / "huge1.dat";
        std::filesystem::path huge2 = env.src_dir / "huge2.dat";

        std::ofstream(huge1).put('X');
        std::ofstream(huge2).put('X');

        // Resize each sparse file to ~2.1 GB. 
        // Individually they pass the single-file 32-bit limit, but their sum overflows 4GB.
        std::filesystem::resize_file(huge1, 2200000000ULL);
        std::filesystem::resize_file(huge2, 2200000000ULL);

        REQUIRE_THROWS_AS(
            BigPacker::pack_from_directory(env.src_dir, env.out_file),
            std::length_error
        );
    }
}


TEST_CASE("BigPacker File I/O Error Handling", "[big_pack][io]") {
    ScopedPackEnv env;

    SECTION("Negative scenario: Target output file cannot be created") {
        env.create_dummy_file("test.txt", "data");

        // Create target file as a regular file first
        {
            std::ofstream pre(env.out_file, std::ios::binary);
            pre << "lock placeholder";
        }

        // Lock output file exclusively (_SH_DENYRW = 0x10)
        // Passes is_directory() but causes std::ofstream to fail opening with BigArchiveError
        FILE* locked_out = _fsopen(env.out_file.string().c_str(), "rb", 0x10);
        if (locked_out) {
            REQUIRE_THROWS_AS(
                BigPacker::pack_from_directory(env.src_dir, env.out_file),
                BigArchiveError
            );
            fclose(locked_out);
        }
    }

    SECTION("Negative scenario: Source file cannot be read during packing") {
        env.create_dummy_file("locked.txt", "data");

        // Lock the file exclusively using Windows _fsopen (_SH_DENYRW = 0x10).
        // This guarantees std::ifstream inside BigPacker will fail to open it.
        std::string path_str = (env.src_dir / "locked.txt").string();
        FILE* locked_file = _fsopen(path_str.c_str(), "rb", 0x10);

        if (locked_file) {
            REQUIRE_THROWS_AS(
                BigPacker::pack_from_directory(env.src_dir, env.out_file),
                BigArchiveError
            );
            fclose(locked_file);
        }
    }
}
