/**
 * @file tests/cpp/ini/test_serializer.cpp
 * @brief Unit tests for iterative serialization covering all AST and STR node variations in lotm::ini.
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
