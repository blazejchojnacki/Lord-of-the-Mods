/**
 * @file tests/cpp/ini/test_encoding.cpp
 * @brief Unit tests for UTF-8 BOM stripping, Windows-1252 fallback, and binary spans in lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include "ini/parser.hpp"
#include "test_utils.hpp"
#include <filesystem>
#include <span>

using namespace lotm::ini;
using namespace lotm::ini::testing;
namespace fs = std::filesystem;

TEST_CASE("UTF-8 BOM stripping, Windows-1252 fallback, and binary span constructor", "[ini][encoding]") {
    TempDirFixture temp;

    SECTION("Strips UTF-8 BOM in .ini, .inc, and .str files from memory and disk") {
        const std::string bom_ini = "\xEF\xBB\xBFWeapon GondorSword\n    Damage = 40\nEnd\n";
        const fs::path ini_path = temp.write_file("bom_weapon.ini", bom_ini);

        ConstructFile cf_disk{ ini_path.string(), true };
        REQUIRE(cf_disk.size() == 1);
        CHECK(std::get<ConstructLevel>(std::get<AstNode>(cf_disk[0]))._class == "Weapon");

        ConstructFile cf_mem{ "bom_mem.ini", true, bom_ini };
        REQUIRE(cf_mem.size() == 1);

        const std::string bom_str = "\xEF\xBB\xBFOBJECT:GondorSword\n    \"Sword\"\nEnd\n";
        const StrDocument str_doc = StrParser::parse_file("bom.str", true, bom_str);
        REQUIRE(str_doc.entries.size() == 1);
        CHECK(std::get<StrEntry>(str_doc.entries[0]).category == "OBJECT");
    }

    SECTION("ConstructFile std::span<const uint8_t> constructor handles valid UTF-8, Windows-1252, and empty buffers") {
        // 1. Valid multi-byte UTF-8 (2-byte é, 3-byte €, 4-byte 🗡️)
        const std::string valid_utf8 =
            "Weapon EowynSword ; \xC3\xA9 \xE2\x82\xAC \xF0\x9F\x97\xA1\n"
            "    Damage = 50\n"
            "End\n";
        const std::span<const std::uint8_t> utf8_span(
            reinterpret_cast<const std::uint8_t*>(valid_utf8.data()),
            valid_utf8.size()
        );
        ConstructFile cf_utf8{ "utf8.ini", true, utf8_span };
        REQUIRE(cf_utf8.size() == 1);
        CHECK(cf_utf8.print().find("\xC3\xA9 \xE2\x82\xAC \xF0\x9F\x97\xA1") != std::string::npos);

        // 2. Windows-1252 bytes: 0x80 (€, 3-byte UTF-8), 0x81 (C1 2-byte UTF-8),
        //    0x93/0x94 (“”, 3-byte UTF-8), 0xE9 (é, >= 0xA0 2-byte UTF-8)
        const std::string cp1252_str =
            "OBJECT:Hero\n"
            "    \"\x93H\xE9ro\x94 \x80\x81\"\n"
            "End\n";
        const std::span<const std::uint8_t> cp1252_span(
            reinterpret_cast<const std::uint8_t*>(cp1252_str.data()),
            cp1252_str.size()
        );
        ConstructFile cf_cp1252{ "cp1252.str", true, cp1252_span };
        REQUIRE(cf_cp1252.size() == 1);
        const std::string printed = cf_cp1252.print();
        CHECK(printed.find("\xE2\x80\x9C" "H\xC3\xA9ro" "\xE2\x80\x9D \xE2\x82\xAC\xC2\x81") != std::string::npos);

        // 3. Empty buffer span (unnamed, named valid extension, and invalid extension)
        const std::span<const std::uint8_t> empty_span{};
        ConstructFile cf_empty_span{ "", false, empty_span };
        CHECK(cf_empty_span.empty());

        ConstructFile cf_empty_named{ "virtual_empty.ini", true, empty_span };
        CHECK(cf_empty_named.empty());
        CHECK(cf_empty_named.errors.empty());

        CHECK_THROWS_AS(ConstructFile("unsupported.ext", true, empty_span), IniParseError);
    }

    SECTION("UTF-8 validator rejects malformed, overlong, surrogate, and truncated sequences via CP1252 fallback") {
        const std::vector<std::string> invalid_utf8_samples = {
            "Weapon W ; \xC2",                 // Truncated 2-byte sequence
            "Weapon W ; \xC2\x20",             // Invalid 2-byte continuation
            "Weapon W ; \xE0\xA0",             // Truncated 3-byte sequence
            "Weapon W ; \xE0\x80\x80",         // Overlong 3-byte sequence
            "Weapon W ; \xED\xA0\x80",         // UTF-16 surrogate half (U+D800)
            "Weapon W ; \xE1\x20\x80",         // Invalid 3-byte continuation
            "Weapon W ; \xF0\x90\x80",         // Truncated 4-byte sequence
            "Weapon W ; \xF0\x80\x80\x80",     // Overlong 4-byte sequence
            "Weapon W ; \xF4\x90\x80\x80",     // Above U+10FFFF 4-byte sequence
            "Weapon W ; \xF1\x20\x80\x80"      // Invalid 4-byte continuation
        };

        for (const auto& sample : invalid_utf8_samples) {
            const std::string payload = sample + "\nEnd\n";
            ConstructFile cf{ "fallback.ini", true, payload };
            REQUIRE(cf.size() == 1);
        }

        const fs::path cp1252_txt = temp.write_file("legacy.txt", "Price: \x80 100 - Cr\xE9" "dits");
        const auto [txt_out, txt_delims] = load_file(cp1252_txt.string());
        CHECK(txt_out == "Price: \xE2\x82\xAC 100 - Cr\xC3\xA9" "dits");
        CHECK(txt_delims.empty());
    }
}
