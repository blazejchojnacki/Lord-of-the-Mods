/**
 * @file tests/cpp/ini/test_io.cpp
 * @brief Unit tests for file loading, error scanning, UTF-8 paths, and I/O lock handling in lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include "ini/parser.hpp"
#include "test_utils.hpp"
#include <filesystem>

using namespace lotm::ini;
using namespace lotm::ini::testing;
namespace fs = std::filesystem;

TEST_CASE("File loading, error scanning, UTF-8 paths, and deterministic I/O lock handling", "[ini][io]") {
    TempDirFixture temp;

    SECTION("load_file handles .ini, empty .ini fallback, .txt, and propagates security exceptions") {
        CHECK_THROWS_AS(load_file(""), IniParseError);
        CHECK_THROWS_AS(load_file((temp.root() / "nonexistent.ini").string()), IniParseError);

        const fs::path valid_ini = temp.write_file("armor.ini", "Armor TestArmor\n  Armor = DEFAULT 10%\nEnd\n");
        const auto [ini_text, ini_delims] = load_file(valid_ini.string());
        CHECK(ini_text.find("Armor TestArmor") != std::string::npos);
        CHECK_FALSE(ini_delims.empty());

        const fs::path empty_ini = temp.write_file("empty.ini", "   \r\n  ");
        const auto [raw_fallback, empty_delims] = load_file(empty_ini.string());
        CHECK(raw_fallback == "   \r\n  ");
        CHECK(empty_delims.empty());

        const fs::path txt_file = temp.write_file("notes.txt", "Raw text file content");
        const auto [txt_content, txt_delims] = load_file(txt_file.string());
        CHECK(txt_content == "Raw text file content");
        CHECK(txt_delims.empty());

        const fs::path bad_ext = temp.write_file("archive.big", "BIG4");
        CHECK_THROWS_AS(load_file(bad_ext.string()), IniParseError);

        // Security violation in .ini must throw IniParseError instead of falling back to raw file text
        const fs::path exploit_ini = temp.write_file(
            "exploit.ini",
            "Object " + std::string(300, 'X') + "\nEnd\n"
        );
        CHECK_THROWS_AS(load_file(exploit_ini.string()), IniParseError);
    }

    SECTION("Handles non-ASCII UTF-8 filesystem paths across ConstructFile, StrParser, and validate_include") {
        const std::string rel_utf8_ini = "gda\xC5\x84sk_\xC5\xBC\xC3\xB3\xC5\x82\xC4\x87/bro\xC5\x84.ini";
        const std::string rel_utf8_inc = "gda\xC5\x84sk_\xC5\xBC\xC3\xB3\xC5\x82\xC4\x87/makra.inc";
        const std::string rel_utf8_str = "gda\xC5\x84sk_\xC5\xBC\xC3\xB3\xC5\x82\xC4\x87/tekst.str";

        const fs::path ini_path = temp.write_file(rel_utf8_ini, "Weapon Miecz\n    Damage = 30\nEnd\n");
        const fs::path inc_path = temp.write_file(rel_utf8_inc, "Damage = 30\n");
        const fs::path str_path = temp.write_file(rel_utf8_str, "OBJECT:Miecz\n    \"Miecz\"\nEnd\n");

        const auto u8_ini = ini_path.u8string();
        const std::string utf8_ini_str(reinterpret_cast<const char*>(u8_ini.data()), u8_ini.size());

        const auto u8_str = str_path.u8string();
        const std::string utf8_str_str(reinterpret_cast<const char*>(u8_str.data()), u8_str.size());

        ConstructFile cf{ utf8_ini_str, true };
        REQUIRE(cf.size() == 1);

        StrDocument sdoc = StrParser::parse_file(utf8_str_str, true);
        REQUIRE(sdoc.size() == 1);

        const IncludeNode inc_node{ "\"makra.inc\"" };
        CHECK(validate_include(inc_node, ini_path, temp.root()) == fs::weakly_canonical(inc_path));
    }

    SECTION("scan_file_for_errors returns warnings for broken files and catches fatal exceptions") {
        const fs::path clean_ini = temp.write_file("clean.ini", "Armor A\nEnd\n");
        CHECK(scan_file_for_errors(clean_ini.string()).empty());

        const fs::path broken_ini = temp.write_file("broken.ini", "Armor A\nEnd\nEnd\n");
        const auto errs = scan_file_for_errors(broken_ini.string());
        REQUIRE(errs.size() == 1);
        CHECK(errs[0].find("negative level reached") != std::string::npos);

        const auto fatal_errs = scan_file_for_errors((temp.root() / "missing.ini").string());
        REQUIRE(fatal_errs.size() == 1);
        CHECK(fatal_errs[0].find("Fatal error while processing") != std::string::npos);
    }

#ifdef _WIN32
    SECTION("Deterministic Windows _fsopen(_SH_DENYRW) lock triggers read_file_bytes failure paths") {
        const fs::path locked_ini = temp.write_file("locked.ini", "Weapon Sword\nEnd\n");
        ScopedExclusiveFileLock lock{ locked_ini };
        REQUIRE(lock.is_locked());

        CHECK_THROWS_AS(ConstructFile(locked_ini.string(), false), IniParseError);
        CHECK_THROWS_AS(load_file(locked_ini.string()), IniParseError);

        const fs::path locked_str = temp.write_file("locked.str", "OBJECT:Unit\nEnd\n");
        ScopedExclusiveFileLock str_lock{ locked_str };
        REQUIRE(str_lock.is_locked());

        CHECK_THROWS_AS(StrParser::parse_file(locked_str.string(), false), IniParseError);
    }
#endif
}
