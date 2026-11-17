/**
 * @file tests/cpp/ini/test_include.cpp
 * @brief Unit tests for virtual chroot #include path validation and traversal defense in lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include "ini/parser.hpp"
#include "test_utils.hpp"
#include <algorithm>

using namespace lotm::ini;
using namespace lotm::ini::testing;
namespace fs = std::filesystem;

TEST_CASE("Virtual chroot #include path validation and traversal defense", "[ini][security][include]") {
    TempDirFixture temp;
    const fs::path vroot = temp.root() / "data" / "ini";
    const fs::path current_ini = temp.write_file("data/ini/object/gondor/archer.ini", "");
    const fs::path local_inc = temp.write_file("data/ini/object/gondor/local_macros.inc", "");
    const fs::path root_inc = temp.write_file("data/ini/includes/global.inc", "");
    const fs::path outside_secret = temp.write_file("data/secret.ini", "");
    fs::create_directories(vroot / "includes" / "subdir");

    SECTION("Resolves relative to current_file parent first, then virtual_root") {
        const IncludeNode local_node{ "\"local_macros.inc\"" };
        CHECK(validate_include(local_node, current_ini, vroot) == fs::weakly_canonical(local_inc));

        const IncludeNode root_node{ "\"includes\\global.inc\"" };
        CHECK(validate_include(root_node, current_ini, vroot) == fs::weakly_canonical(root_inc));
    }

    SECTION("Blocks path traversal escaping virtual_root") {
        const IncludeNode escape_rel{ "\"..\\..\\..\\secret.ini\"" };
        CHECK_THROWS_AS(validate_include(escape_rel, current_ini, vroot), IniParseError);

        const IncludeNode escape_root{ "\"..\\secret.ini\"" };
        CHECK_THROWS_AS(validate_include(escape_root, current_ini, vroot), IniParseError);

        const IncludeNode escape_to_fs_root{ "\"..\\..\\..\\..\\..\\..\\..\"" };
        CHECK_THROWS_AS(validate_include(escape_to_fs_root, current_ini, vroot), IniParseError);
    }

    SECTION("Distinguishes missing relative files inside virtual_root from traversal escapes") {
        const IncludeNode missing_rel_in_root{ "\"..\\missing_common.inc\"" };
        try {
            (void)validate_include(missing_rel_in_root, current_ini, vroot);
            FAIL("Expected IniParseError for missing relative include");
        }
        catch (const IniParseError& ex) {
            CHECK(std::string{ ex.what() }.find("Include file not found") != std::string::npos);
        }

        const IncludeNode missing_node{ "\"includes/nonexistent.inc\"" };
        CHECK_THROWS_AS(validate_include(missing_node, current_ini, vroot), IniParseError);

        const IncludeNode dir_node{ "\"includes/subdir\"" };
        CHECK_THROWS_AS(validate_include(dir_node, current_ini, vroot), IniParseError);
    }

#ifdef _WIN32
    SECTION("Handles case-insensitive drive/folder matching on Windows") {
        std::string upper_root_str = vroot.string();
        std::ranges::transform(upper_root_str, upper_root_str.begin(), [](unsigned char c) {
            return static_cast<char>(std::toupper(c));
            });
        const IncludeNode local_node{ "\"local_macros.inc\"" };
        CHECK_NOTHROW(validate_include(local_node, current_ini, fs::path{ upper_root_str }));
    }
#endif
}
