/**
 * @file tests/cpp/ini/test_lexer.cpp
 * @brief Unit tests for zero-copy lexer, whitespace helpers, and line view iterator in lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include "ini/lexer.hpp"
#include <vector>
#include <string_view>
#include <utility>

using namespace lotm::ini;

TEST_CASE("Zero-copy lexer, whitespace helpers, and line view iterator", "[ini][lexer]") {
    SECTION("Whitespace trimming, collapsing, and case-insensitive ASCII comparison") {
        STATIC_REQUIRE(detail::is_lex_space(' '));
        STATIC_REQUIRE(detail::is_lex_space('\t'));
        STATIC_REQUIRE(detail::is_lex_space('\r'));
        STATIC_REQUIRE(detail::is_lex_space('\n'));
        STATIC_REQUIRE(detail::is_lex_space('\v'));
        STATIC_REQUIRE(detail::is_lex_space('\f'));
        STATIC_REQUIRE_FALSE(detail::is_lex_space('X'));

        STATIC_REQUIRE(detail::lstrip_view(" \t\r\n\v\fHello ") == "Hello ");
        STATIC_REQUIRE(detail::rstrip_view(" Hello \t\r\n\v\f") == " Hello");
        STATIC_REQUIRE(detail::trim_view(" \t\v\f ") == "");
        STATIC_REQUIRE(detail::trim_view("") == "");

        CHECK(detail::collapse_whitespace("") == "");
        CHECK(detail::collapse_whitespace("   \t\r\n ") == "");
        CHECK(detail::collapse_whitespace("  ;  comment \t with \v multiple   spaces ") == "; comment with multiple spaces");
    }

    SECTION("lex_line tokenizes separators without mutation and extracts comments") {
        const LexedLine l1 = lex_line("  Draw = W3DScriptedModelDraw ModuleTag_01 ; inline   comment // second ");
        REQUIRE(l1.words == std::vector<std::string_view>{"Draw", "W3DScriptedModelDraw", "ModuleTag_01"});
        REQUIRE(l1.words_signs == std::vector<std::string_view>{"Draw", "=", "W3DScriptedModelDraw", "ModuleTag_01"});
        REQUIRE(l1.line_tokens == std::vector<std::string_view>{"Draw", "=", "W3DScriptedModelDraw", "ModuleTag_01"});
        CHECK(l1.comment == "; inline comment // second");

        const LexedLine l2 = lex_line("CONTROLBAR:GondorSwordman// slash comment ; semi after");
        REQUIRE(l2.words == std::vector<std::string_view>{"CONTROLBAR", "GondorSwordman"});
        REQUIRE(l2.words_signs == std::vector<std::string_view>{"CONTROLBAR:GondorSwordman"});
        REQUIRE(l2.line_tokens == std::vector<std::string_view>{"CONTROLBAR", ":", "GondorSwordman"});
        CHECK(l2.comment == "// slash comment ; semi after");

        const LexedLine l3 = lex_line("Key=Val1:Val2");
        REQUIRE(l3.words == std::vector<std::string_view>{"Key", "Val1", "Val2"});
        REQUIRE(l3.words_signs == std::vector<std::string_view>{"Key=Val1:Val2"});
        REQUIRE(l3.line_tokens == std::vector<std::string_view>{"Key", "=", "Val1", ":", "Val2"});
        CHECK(l3.comment.empty());
    }

    SECTION("lex_line preserves ';' and '//' inside quotes, escaped quotes, and URL schemes like http://") {
        const LexedLine quoted_semi = lex_line("    \" Soldier ; Archer // Cavalry \" ; real trailing comment");
        REQUIRE(quoted_semi.words_signs.size() == 7);
        CHECK(quoted_semi.comment == "; real trailing comment");

        const LexedLine escaped_quote_line = lex_line("    \"Quote \\\" ; still inside // quotes \\\" end\" ; outside comment");
        CHECK(escaped_quote_line.comment == "; outside comment");
        REQUIRE(escaped_quote_line.words_signs.size() == 9);

        const LexedLine url_line = lex_line("    URL = http://www.ea.com/lotr // official link");
        REQUIRE(url_line.words_signs == std::vector<std::string_view>{"URL", "=", "http://www.ea.com/lotr"});
        CHECK(url_line.comment == "// official link");

        const LexedLine leading_slash = lex_line("// full line slash comment");
        CHECK(leading_slash.words.empty());
        CHECK(leading_slash.comment == "// full line slash comment");
    }

    SECTION("for_each_line_view handles LF, CRLF, CR, and early termination") {
        const std::string_view mixed_buf = "Line1\nLine2\r\nLine3\rLine4";
        std::vector<std::pair<std::string_view, std::size_t>> collected;

        for_each_line_view(mixed_buf, [&](std::string_view line, std::size_t num) {
            collected.emplace_back(line, num);
            });

        REQUIRE(collected.size() == 4);
        CHECK(collected[0] == std::pair<std::string_view, std::size_t>{"Line1", 1});
        CHECK(collected[1] == std::pair<std::string_view, std::size_t>{"Line2", 2});
        CHECK(collected[2] == std::pair<std::string_view, std::size_t>{"Line3", 3});
        CHECK(collected[3] == std::pair<std::string_view, std::size_t>{"Line4", 4});

        std::size_t stopped_at = 0;
        for_each_line_view(mixed_buf, [&](std::string_view, std::size_t num) -> bool {
            stopped_at = num;
            return num < 2;
            });
        CHECK(stopped_at == 2);

        std::size_t empty_calls = 0;
        for_each_line_view("", [&](std::string_view, std::size_t) { ++empty_calls; });
        CHECK(empty_calls == 0);
    }
}
