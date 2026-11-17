/**
 * @file tests/cpp/ini/test_recognize.cpp
 * @brief Unit tests for structure recognition across .ini, .inc, and .str files in lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include "ini/parser.hpp"
#include "test_utils.hpp"

using namespace lotm::ini;
using namespace lotm::ini::testing;

TEST_CASE("Structure recognition across .ini, .inc, and .str files", "[ini][recognize]") {
    TempDirFixture temp;

    SECTION(".str structure recognition returns STR_DELIMITERS at level 0") {
        const auto [delims, start_lvl] = recognize_structure("lotr.STR");
        REQUIRE(delims.size() == 2);
        CHECK(delims[0].size() == STR_DELIMITERS.size());
        CHECK(delims[1].empty());
        CHECK(start_lvl == 0);
    }

    SECTION(".ini recognition matches only level 0 and ignores level > 0 keywords") {
        const std::string content =
            "; comment\n"
            "\n"
            "Draw = W3DScriptedModelDraw ModuleTag_01\n"
            "Weapon GondorSword\n";
        const auto [delims, start_lvl] = recognize_structure("weapon.ini", content);
        REQUIRE_FALSE(delims.empty());
        CHECK(delims[0][0] == "Weapon");
        CHECK(start_lvl == 0);

        const auto [empty_delims, zero_lvl] = recognize_structure("unknown.ini", "RandomKey = 123\n");
        CHECK(empty_delims.empty());
        CHECK(zero_lvl == 0);
    }

    SECTION(".inc recognition detects inner nesting levels and reads from disk when content is nullopt") {
        const std::filesystem::path inc_file = temp.write_file("sub/draw.inc", "LodOptions\n    AllowMultipleModels = YES\nEnd\n");
        const auto [delims, start_lvl] = recognize_structure(inc_file.string());
        REQUIRE(delims.size() == 5);
        CHECK(start_lvl == 2);
    }

    SECTION("Unsupported extension returns empty structure and missing file throws") {
        const auto [delims, start_lvl] = recognize_structure("readme.txt", "Object Foo\nEnd\n");
        CHECK(delims.empty());
        CHECK(start_lvl == 0);

        CHECK_THROWS_AS(recognize_structure((temp.root() / "missing.ini").string()), IniParseError);
    }
}
