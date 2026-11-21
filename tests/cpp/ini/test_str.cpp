/**
 * @file tests/cpp/ini/test_str.cpp
 * @brief Unit tests for StrParser happy paths, comment coalescing, and diagnostics in lotm::ini.
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
namespace fs = std::filesystem;

TEST_CASE("StrParser happy paths, comment coalescing, and strict/non-strict error diagnostics", "[ini][str]") {
    TempDirFixture temp;

    SECTION("Rejects invalid file extensions or missing files") {
        CHECK_THROWS_AS(StrParser::parse_file("bad.ini", false, "OBJECT:Foo\nEnd\n"), IniParseError);
        CHECK_THROWS_AS(StrParser::parse_file((temp.root() / "missing.str").string(), false), IniParseError);
    }

    SECTION("Parses valid .str from disk with comments in all positions and mixed-case ENd") {
        const std::string content =
            "; file header line 1\n"
            "; file header line 2\n"
            "\n"
            "; entry lead comment\n"
            "OBJECT:GondorFighter ; hdr cmt\n"
            "    ; inner block comment\n"
            "    \n"
            "    ; pre-text comment\n"
            "    \"Gondor \\\"Soldiers ; Elite\\\"\" ; text cmt\n"
            "    ; trailing inside entry\n"
            "ENd ; end cmt\n"
            "; trailing file comment\n";
        const fs::path str_path = temp.write_file("lotr.str", content);

        const StrDocument doc = StrParser::parse_file(str_path.string(), true);
        CHECK(doc.errors.empty());
        REQUIRE(doc.entries.size() == 3);
        CHECK(std::holds_alternative<CommentNode>(doc.entries[0]));
        CHECK(std::holds_alternative<StrEntry>(doc.entries[1]));
        CHECK(std::holds_alternative<CommentNode>(doc.entries[2]));

        const StrEntry& entry = std::get<StrEntry>(doc.entries[1]);
        CHECK(entry.category == "OBJECT");
        CHECK(entry.identifier == "GondorFighter");
        CHECK(entry.comment == "; entry lead comment");
        CHECK(entry.header_comment == "; hdr cmt");
        CHECK(entry.end_token == "ENd");
        CHECK(entry.end_comment == "; end cmt");
        REQUIRE(entry.items.size() == 4);
    }

    SECTION("Detects unclosed entry before new entry, negative level End, orphaned statement, and unclosed EOF") {
        const std::string malformed =
            "OrphanedLine = 1\n"
            "End\n"
            "OBJECT:UnclosedOne\n"
            "    \"Text 1\"\n"
            "GUI\n"
            "    \"Text 2\"\n"
            "TOOLTIP:UnclosedEOF\n"
            "    \"Text 3\"\n"
            "    ; trailing comment inside unclosed\n";

        const StrDocument doc = StrParser::parse_file("broken.str", false, malformed);
        REQUIRE(doc.errors.size() == 5);
        CHECK(doc.errors[0].find("Unexpected statement outside entry") != std::string::npos);
        CHECK(doc.errors[1].find("negative level reached") != std::string::npos);
        CHECK(doc.errors[2].find("unclosed entry 'OBJECT:UnclosedOne'") != std::string::npos);
        CHECK(doc.errors[3].find("unclosed entry 'GUI'") != std::string::npos);
        CHECK(doc.errors[4].find("unclosed entry 'TOOLTIP:UnclosedEOF'") != std::string::npos);

        CHECK_THROWS_AS(StrParser::parse_file("broken.str", true, "OrphanedLine\n"), IniParseError);
        CHECK_THROWS_AS(StrParser::parse_file("broken.str", true, "End\n"), IniParseError);
        CHECK_THROWS_AS(StrParser::parse_file("broken.str", true, "OBJECT:A\nOBJECT:B\nEnd\n"), IniParseError);
        CHECK_THROWS_AS(StrParser::parse_file("broken.str", true, "GUI\n\"Unclosed\"\n"), IniParseError);
    }

    SECTION("Panic-mode error recovery coalesces cascading orphan lines into a single line-span diagnostic") {
        const std::string unknown_cat_str =
            "UNKNOWN_CATEGORY:GondorUnit\n"
            "    \"Line 1 of unknown category\"\n"
            "    \"Line 2 of unknown category\"\n"
            "End\n"
            "OBJECT:ValidUnit\n"
            "    \"Valid Unit\"\n"
            "End\n"
            "ANOTHER_BAD:Trailing\n"
            "    \"Trailing orphan at EOF\"\n";

        const StrDocument doc = StrParser::parse_file("panic.str", false, unknown_cat_str);
        REQUIRE(doc.errors.size() == 2);
        CHECK(doc.errors[0].find("panic.str:1-4 (starting with: UNKNOWN_CATEGORY:GondorUnit)") != std::string::npos);
        CHECK(doc.errors[1].find("panic.str:8-9 (starting with: ANOTHER_BAD:Trailing)") != std::string::npos);
    }
}
