/**
 * @file tests/cpp/core/test_path_utils.cpp
 * @brief Unit tests for lotm::core UTF-8 path conversion and NTFS security helpers.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include <core/path_utils.hpp>
#include <filesystem>
#include <string>

using namespace lotm::core;

TEST_CASE("UTF-8 path conversion roundtrip preserves non-ASCII characters", "[core][path_utils]") {
    const std::string utf8_input = "gda\xC5\x84sk/\xC5\xBC\xC3\xB3\xC5\x82\xC4\x87/weapon.ini";
    const std::filesystem::path fs_path = utf8_to_path(utf8_input);
    const std::string roundtrip = to_utf8(fs_path.generic_u8string());

    REQUIRE(roundtrip == utf8_input);
}

TEST_CASE("Win32 namespace prefix and drive-relative path detection", "[core][path_utils][security]") {
    SECTION("Win32 and NT namespace prefixes") {
        REQUIRE(has_win32_namespace_prefix("\\\\?\\C:\\file.txt"));
        REQUIRE(has_win32_namespace_prefix("\\\\.\\PhysicalDrive0"));
        REQUIRE(has_win32_namespace_prefix("\\??\\C:\\file.txt"));
        REQUIRE_FALSE(has_win32_namespace_prefix("data\\ini\\weapon.ini"));
        REQUIRE_FALSE(has_win32_namespace_prefix(""));
    }

    SECTION("Drive-relative paths") {
        REQUIRE(is_drive_relative_path("C:file.txt"));
        REQUIRE(is_drive_relative_path("D:..\\escaped.ini"));
        REQUIRE(is_drive_relative_path("C:"));
        REQUIRE_FALSE(is_drive_relative_path("C:\\absolute\\path.txt"));
        REQUIRE_FALSE(is_drive_relative_path("data\\weapon.ini"));
        REQUIRE_FALSE(is_drive_relative_path("a"));
    }
}

TEST_CASE("NTFS component and reserved DOS device validation", "[core][path_utils][security]") {
    SECTION("Rejects empty, dot, trailing space/dot, control chars, and reserved characters") {
        REQUIRE(is_unsafe_ntfs_component(""));
        REQUIRE(is_unsafe_ntfs_component("."));
        REQUIRE(is_unsafe_ntfs_component(".."));
        REQUIRE(is_unsafe_ntfs_component("folder "));
        REQUIRE(is_unsafe_ntfs_component("folder."));
        REQUIRE(is_unsafe_ntfs_component("stream:ads"));
        REQUIRE(is_unsafe_ntfs_component("bad<char>.ini"));
        REQUIRE(is_unsafe_ntfs_component(std::string("ctrl\x07.ini")));
    }

    SECTION("Rejects DOS device names including extensions and superscript digits") {
        REQUIRE(is_unsafe_ntfs_component("CON"));
        REQUIRE(is_unsafe_ntfs_component("con.txt"));
        REQUIRE(is_unsafe_ntfs_component("NUL .ini"));
        REQUIRE(is_unsafe_ntfs_component("CLOCK$.ini"));
        REQUIRE(is_unsafe_ntfs_component("COM1.txt"));
        REQUIRE(is_unsafe_ntfs_component("LPT9"));
        REQUIRE(is_unsafe_ntfs_component("COM\xB2.ini"));
        REQUIRE(is_unsafe_ntfs_component("LPT\xC2\xB3.ini"));
    }

    SECTION("Accepts safe path components") {
        REQUIRE_FALSE(is_unsafe_ntfs_component("weapon.ini"));
        REQUIRE_FALSE(is_unsafe_ntfs_component("COMMON_MACROS.INC"));
        REQUIRE_FALSE(is_unsafe_ntfs_component("COM10.ini"));
    }
}
