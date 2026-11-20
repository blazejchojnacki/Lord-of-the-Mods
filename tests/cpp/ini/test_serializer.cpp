/**
 * @file tests/cpp/ini/test_serializer.cpp
 * @brief Unit tests for iterative serialization and FormatOptions rules in lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include "ini/parser.hpp"

using namespace lotm::ini;

TEST_CASE("Iterative serialization covers all AST and STR node variations", "[ini][serializer]") {
    SECTION("ConstructLevel, ScriptNode, IncludeNode, DefineNode, StatementNode, and CommentNode serialization") {
        ConstructLevel root_block{ "Object", "GondorTower", "", "; line 1\n  ; line 2", "; root hdr", "End", "; root end" };
        root_block.append(CommentNode{ "; inner standalone" });
        root_block.append(IncludeNode{ "\"..\\common.inc\"", "; inc cmt" });
        root_block.append(DefineNode{ "#define INNER_VAL 10", "; def cmt" });
        root_block.append(DefineNode{ "BARE_MACRO 20", "" });
        root_block.append(StatementNode{ "ArmorSet = TowerArmor", "; stmt cmt" });

        ScriptNode script{ "BeginScript", "OnInit", "; scr pre", "; scr hdr", "EndScript", "; scr end",{
            "CurDrawableShowSubObject(\"TORCH\")",
            "",
            "if true then return end"
        } };
        root_block.append(std::move(script));

        ConstructLevel unclosed_child{ "Body", "ActiveBody", "ModTag_Body", "", "", "", "" };
        unclosed_child.append(StatementNode{ "MaxHealth = 2000", "" });
        root_block.append(std::move(unclosed_child));

        ConstructLevel empty_header_child{ "", "", "", "", "", "End", "" };
        root_block.append(std::move(empty_header_child));

        const std::string printed = root_block.print(0, ".ini");
        const std::string expected =
            "; line 1\n"
            "; line 2\n"
            "Object GondorTower ; root hdr\n"
            "    ; inner standalone\n"
            "    #include \"..\\common.inc\" ; inc cmt\n"
            "    #define INNER_VAL 10 ; def cmt\n"
            "    #define BARE_MACRO 20\n"
            "    ArmorSet = TowerArmor ; stmt cmt\n"
            "    ; scr pre\n"
            "    BeginScript OnInit ; scr hdr\n"
            "        CurDrawableShowSubObject(\"TORCH\")\n"
            "\n"
            "        if true then return end\n"
            "    EndScript ; scr end\n"
            "    Body ActiveBody ModTag_Body\n"
            "        MaxHealth = 2000\n"
            "    End\n"
            "End ; root end\n";
        CHECK(printed == expected);

        const ScriptNode standalone_scr{ "BeginScript", "", "", "", "", "",{ "x = 1" } };
        CHECK(standalone_scr.print(1, ".ini") == "    BeginScript\n        x = 1\n");
    }

    SECTION("StrEntry and StrDocument serialization") {
        StrEntry e1{ "OBJECT", "GondorArcher", "; lead cmt", "; hdr cmt", "End", "; end cmt",{
            CommentNode{ "; inside str" },
            StatementNode{ "\"Gondor Archer\"", "; text cmt" }
        } };
        CHECK(e1.print() ==
            "; lead cmt\n"
            "OBJECT:GondorArcher ; hdr cmt\n"
            "    ; inside str\n"
            "    \"Gondor Archer\" ; text cmt\n"
            "End ; end cmt\n"
        );

        StrEntry e2_unclosed{ "GUI", "", "", "", "", "",{
            StatementNode{ "\"No Identifier\"", "" }
        } };
        CHECK(e2_unclosed.print() ==
            "GUI\n"
            "    \"No Identifier\"\n"
        );

        StrDocument doc{ "test.str",{ e1, CommentNode{ "; doc cmt" } },{} };
        CHECK(doc.print() == e1.print() + "\n; doc cmt\n\n");
    }
}

TEST_CASE("FormatOptions rules normalize indentation, headers, equals, comments, ends, and blank lines", "[ini][serializer][format_options]") {
    SECTION("Default FormatOptions equals lossless serialization") {
        const FormatOptions defaults{};
        const FormatOptions copy = defaults;
        CHECK(defaults == copy);
        CHECK(defaults.indent == LEVEL_INDENT);
        CHECK_FALSE(defaults.normalize_end_tokens);
        CHECK_FALSE(defaults.normalize_header_spacing);
        CHECK_FALSE(defaults.normalize_statement_equals);
        CHECK_FALSE(defaults.normalize_comments);
        CHECK_FALSE(defaults.coalesce_blank_lines);
    }

    SECTION("Full canonical FormatOptions across ConstructFile, ConstructLevel, ScriptNode, and statements") {
        const std::string raw_ini =
            "//   leading line 1\n"
            ";   leading line 2\n"
            "Object   GondorHero    ModTag_01 // header comment\n"
            "    //inner comment\n"
            "    ;\n"
            "    Damage=100 // inline slash\n"
            "    EmptyRhs   =   \n"
            "    QuotedEq = \"A=B\\\"=C\" ; keep inside quotes\n"
            "    BareFlagStatement\n"
            "    #include \"common.inc\" // inc comment\n"
            "    #define MACRO_X 1 // def comment\n"
            "    beginscript   InitTag // scr hdr\n"
            "        x = 1\n"
            "    endscript // scr end\n"
            "ENd // root end\n";

        ConstructFile doc{ "canonical.ini", true, raw_ini };

        FormatOptions opts;
        opts.indent = "\t";
        opts.normalize_end_tokens = true;
        opts.normalize_header_spacing = true;
        opts.normalize_statement_equals = true;
        opts.normalize_comments = true;
        opts.coalesce_blank_lines = true;

        const std::string formatted = doc.print(opts);
        const std::string expected =
            "; leading line 1\n"
            "; leading line 2\n"
            "Object GondorHero ModTag_01 ; header comment\n"
            "\t; inner comment\n"
            "\t;\n"
            "\tDamage = 100 ; inline slash\n"
            "\tEmptyRhs =\n"
            "\tQuotedEq = \"A=B\\\"=C\" ; keep inside quotes\n"
            "\tBareFlagStatement\n"
            "\t#include \"common.inc\" ; inc comment\n"
            "\t#define MACRO_X 1 ; def comment\n"
            "\tBeginScript InitTag ; scr hdr\n"
            "\t\tx = 1\n"
            "\tEndScript ; scr end\n"
            "End ; root end\n\n";
        CHECK(formatted == expected);
    }

    SECTION("FormatOptions applies to StrEntry and StrDocument including blank line coalescing") {
        StrEntry e1{ "OBJECT", "GondorSword", "// lead", "// hdr", "END", "// end",{
            CommentNode{ "//   inner" },
            StatementNode{ "\"Sword\"", "// text" }
        } };
        StrDocument doc{ "test.str",{ e1, CommentNode{ "// tail" } },{} };

        FormatOptions opts;
        opts.normalize_end_tokens = true;
        opts.normalize_header_spacing = true;
        opts.normalize_comments = true;
        opts.coalesce_blank_lines = true;

        const std::string expected =
            "; lead\n"
            "OBJECT:GondorSword ; hdr\n"
            "    ; inner\n"
            "    \"Sword\" ; text\n"
            "End ; end\n\n"
            "; tail\n\n";
        CHECK(doc.print(opts) == expected);
    }
}
