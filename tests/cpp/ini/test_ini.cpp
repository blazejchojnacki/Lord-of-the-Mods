/**
 * @file tests/cpp/ini/test_ini.cpp
 * @brief Unit tests for ConstructFile INI/INC parser features, special blocks, and limits in lotm::ini.
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

TEST_CASE("ConstructFile INI/INC parser features, special blocks, and depth security limits", "[ini][parser][security]") {
    TempDirFixture temp;

    SECTION("Default ConstructFile, container interface, equality, and extensionless filename print") {
        ConstructFile empty_cf;
        CHECK(empty_cf.empty());
        CHECK(empty_cf.size() == 0);

        empty_cf.name = "virtual_buffer";
        empty_cf.append(AstNode{ DefineNode{ "#define LEGACY_DEF 1", "" } });
        empty_cf.append(AstNode{ ConstructLevel{ "Object", "GondorSoldier", "", "", "", "End", "" } });
        empty_cf.append(RootItem{ AstNode{ CommentNode{ "; cmt" } } });
        empty_cf.append(StrEntry{ "GUI", "Btn" });
        REQUIRE(empty_cf.size() == 4);
        CHECK_FALSE(empty_cf.empty());

        const std::string printed_extless = empty_cf.print();
        CHECK(printed_extless.find("#define LEGACY_DEF 1\n") != std::string::npos);
        CHECK(printed_extless.find("Object GondorSoldier\n") != std::string::npos);

        empty_cf[0] = AstNode{ StatementNode{ "Key = 2", "" } };
        const ConstructFile& const_cf = empty_cf;
        CHECK(std::get<StatementNode>(std::get<AstNode>(const_cf[0])).text == "Key = 2");

        ConstructFile copy_cf = empty_cf;
        CHECK(copy_cf == empty_cf);
        copy_cf.name = "b";
        CHECK_FALSE(copy_cf == empty_cf);

        std::size_t cnt = 0;
        for (auto it = empty_cf.begin(); it != empty_cf.end(); ++it) { ++cnt; }
        for (auto it = const_cf.begin(); it != const_cf.end(); ++it) { ++cnt; }
        for (auto it = const_cf.cbegin(); it != const_cf.cend(); ++it) { ++cnt; }
        CHECK(cnt == 12);
        CHECK_FALSE(empty_cf.print().empty());

        ConstructFile no_name{ "", false };
        CHECK(no_name.empty());

        CHECK_THROWS_AS(ConstructFile("bad.ext", false, ""), IniParseError);
    }

    SECTION("construct_with_metadata preserves caller-supplied delimiters and start_level") {
        ConstructFile meta_cf;
        meta_cf.name = "custom.inc";
        meta_cf.delimiters = { { "CustomRoot" },{ "CustomInner" },{} };
        meta_cf.start_level = 1;
        meta_cf.strict = true;
        meta_cf.file_content = "\xEF\xBB\xBF" "CustomInner MyBlock\n    Value = 42\nENd\n";

        meta_cf.construct_with_metadata();
        CHECK(meta_cf.start_level == 1);
        REQUIRE(meta_cf.size() == 1);
        const auto& blk = std::get<ConstructLevel>(std::get<AstNode>(meta_cf[0]));
        CHECK(blk._class == "CustomInner");
        CHECK(blk.name == "MyBlock");
        CHECK(blk.end_token == "ENd");

        // Disk-backed construct_with_metadata and .str construct_with_metadata
        const fs::path disk_inc = temp.write_file("disk_meta.inc", "CustomInner DiskBlock\nEnd\n");
        ConstructFile disk_meta;
        disk_meta.name = disk_inc.string();
        disk_meta.delimiters = { { "CustomRoot" },{ "CustomInner" },{} };
        disk_meta.start_level = 1;
        disk_meta.strict = true;
        disk_meta.construct_with_metadata();
        REQUIRE(disk_meta.size() == 1);

        ConstructFile str_meta;
        str_meta.name = "meta.str";
        str_meta.file_content = "OBJECT:Hero\n    \"Aragorn\"\nEnd\n";
        str_meta.construct_with_metadata();
        REQUIRE(str_meta.size() == 1);

        ConstructFile invalid_meta;
        invalid_meta.name = "invalid.ext";
        CHECK_THROWS_AS(invalid_meta.construct_with_metadata(), IniParseError);
    }

    SECTION("ConstructFile delegates .str files and preserves StrEntry, CommentNode, and StatementNode items") {
        const std::string str_content =
            "; top comment\n"
            "\n"
            "OrphanStmt\n"
            "OBJECT:Hero\n"
            "    \"Aragorn\"\n"
            "End\n";
        ConstructFile cf{ "lotr.str", false, str_content };
        CHECK(cf.errors.size() == 1);
        REQUIRE(cf.size() == 3);
        CHECK_FALSE(cf.print().empty());
    }

    SECTION("Handles #define ordering, #include, ReplaceModule depth shift, FCurve, BeginScript, multi-flag headers, and .inc schema switching") {
        const std::string ini_content =
            "#include \"..\\first_include.inc\" ; inc before define\n"
            "#define DAMAGE_MACRO 100 ; macro cmt\n"
            "#include \"..\\common.inc\" ; inc cmt\n"
            "#include\n"
            "; leading comment\n"
            "\n"
            "BeginScript TopLevelScript\n"
            "    if a == 1 then end\n"
            "EndScript ; top scr end\n"
            "Alpha = FCurve TopCurve\n"
            "    ControlPoint = 0 1\n"
            "End\n"
            "; pre-armor comment\n"
            "Armor HeroArmor\n"
            "    Armor = DEFAULT 50%\n"
            "End\n"
            "Object GondorHero\n"
            "    Draw = W3DScriptedModelDraw ModuleTag_Draw\n"
            "        DefaultModelConditionState\n"
            "            Model = GUHero_SKN\n"
            "        End\n"
            "        AnimationState = MOVING SPECIAL_ONE DAMAGED AFLAME\n"
            "            BeginScript\n"
            "                CurDrawableSetTransitionAnimState(\"TRANS_Move\")\n"
            "            EndScript\n"
            "        End\n"
            "    End\n"
            "    ReplaceModule ModuleTag_OldBody\n"
            "        Body = ActiveBody ModuleTag_NewBody\n"
            "            MaxHealth = 3000\n"
            "        End\n"
            "    End\n"
            "    Color = FCurve\n"
            "        InPadding = 1\n"
            "    End\n"
            "ENd\n"
            "; trailing file comment\n";

        ConstructFile cf{ "hero.ini", true, ini_content };
        CHECK(cf.errors.empty());
        REQUIRE(cf.size() >= 2);
        const auto& def_node = std::get<DefineNode>(std::get<AstNode>(cf[1]));
        CHECK(def_node.text == "#define DAMAGE_MACRO 100");
        CHECK(def_node.comment == "; macro cmt");

        const std::string printed = cf.print();
        // Verify #include before #define stays before #define in serialized output
        CHECK(printed.find("#include \"..\\first_include.inc\"") < printed.find("#define DAMAGE_MACRO 100"));

        ConstructFile reparsed{ "hero.ini", true, printed };
        CHECK(reparsed.print() == printed);

        // Verify .inc base-level schema switching at start_level > 0 (level 1 blocks across different schema groups)
        const std::string inc_switch_content =
            "Draw = W3DScriptedModelDraw ModuleTag_01\n"
            "    ExtraPublicBone = BONE01\n"
            "End\n"
            "DamageNugget\n"
            "    Damage = 50\n"
            "End\n";
        ConstructFile inc_cf{ "mixed_level1.inc", true, inc_switch_content };
        CHECK(inc_cf.start_level == 1);
        REQUIRE(inc_cf.size() == 2);
        CHECK(std::get<ConstructLevel>(std::get<AstNode>(inc_cf[0]))._class == "Draw =");
        CHECK(std::get<ConstructLevel>(std::get<AstNode>(inc_cf[1]))._class == "DamageNugget");
    }

    SECTION("Handles negative level End and unclosed EOF in strict and non-strict modes") {
        const std::string bad_ini =
            "Object TestUnit\n"
            "End\n"
            "End ; extra closing\n"
            "Object UnclosedUnit\n"
            "    Side = Men\n";

        ConstructFile non_strict{ "bad.ini", false, bad_ini };
        REQUIRE(non_strict.errors.size() == 2);
        CHECK(non_strict.errors[0].find("negative level reached") != std::string::npos);
        CHECK(non_strict.errors[1].find("unclosed block(s) remain") != std::string::npos);

        CHECK_THROWS_AS(ConstructFile("bad.ini", true, "End\n"), IniParseError);
        CHECK_THROWS_AS(ConstructFile("bad.ini", true, "Object Unclosed\n"), IniParseError);
    }

    SECTION("Enforces MAX_INI_DEPTH = 16 against stack exhaustion on blocks, FCurve, and BeginScript") {
        std::string deep_fcurve = "Object RootObj\n";
        for (std::size_t i = 0; i < MAX_INI_DEPTH - 1; ++i) {
            deep_fcurve += "Alpha = FCurve\n";
        }
        for (std::size_t i = 0; i < MAX_INI_DEPTH; ++i) {
            deep_fcurve += "End\n";
        }
        CHECK_NOTHROW(ConstructFile("ok_depth.ini", true, deep_fcurve));

        std::string overflow_fcurve = "Object RootObj\n";
        for (std::size_t i = 0; i < MAX_INI_DEPTH; ++i) {
            overflow_fcurve += "Alpha = FCurve\n";
        }
        CHECK_THROWS_AS(ConstructFile("overflow_fcurve.ini", true, overflow_fcurve), IniParseError);

        std::string overflow_script = "Object RootObj\n";
        for (std::size_t i = 0; i < MAX_INI_DEPTH - 1; ++i) {
            overflow_script += "Alpha = FCurve\n";
        }
        overflow_script += "BeginScript\n";
        CHECK_THROWS_AS(ConstructFile("overflow_script.ini", true, overflow_script), IniParseError);

        // Deep custom delimiter rules via .inc to hit MAX_INI_DEPTH in handle_block_start
        std::string overflow_block = "Object RootObj\n";
        for (std::size_t i = 0; i < MAX_INI_DEPTH - 1; ++i) {
            overflow_block += "Alpha = FCurve\n";
        }
        overflow_block += "ReplaceModule ModTag\n";
        for (std::size_t i = 0; i < MAX_INI_DEPTH - 2; ++i) {
            overflow_block += "ReplaceModule ModTag\n";
        }
        CHECK_THROWS_AS(ConstructFile("overflow_block.ini", true, overflow_block), IniParseError);
    }

    SECTION("Enforces legacy 32-bit SAGE Engine string buffer limits on classes, names, and identifiers") {
        const std::string valid_256(256, 'A');
        const std::string invalid_257(257, 'A');
        const std::string valid_512(512, 'B');
        const std::string invalid_513(513, 'B');

        // ConstructLevel
        CHECK_NOTHROW(ConstructLevel{ valid_256 + " =", valid_256, valid_512 });
        CHECK_THROWS_AS(ConstructLevel(invalid_257, "Name", ""), IniParseError);
        CHECK_THROWS_AS(ConstructLevel("Object", invalid_257, ""), IniParseError);
        CHECK_THROWS_AS(ConstructLevel("Object", "", invalid_513), IniParseError);

        // ScriptNode
        CHECK_NOTHROW(ScriptNode{ valid_256, valid_512 });
        CHECK_THROWS_AS(ScriptNode(invalid_257, ""), IniParseError);
        CHECK_THROWS_AS(ScriptNode("BeginScript", invalid_513), IniParseError);

        // StrEntry
        CHECK_NOTHROW(StrEntry{ valid_256, valid_512 });
        CHECK_THROWS_AS(StrEntry(invalid_257, ""), IniParseError);
        CHECK_THROWS_AS(StrEntry("GUI", invalid_513), IniParseError);

        // Parser enforcement on INI blocks, BeginScript, FCurve, and STR entries
        const std::string overlong_ini_block = "Object " + invalid_257 + "\nEnd\n";
        CHECK_THROWS_AS(ConstructFile("bounds_block.ini", true, overlong_ini_block), IniParseError);

        const std::string overlong_ini_ident = "Object ValidName " + invalid_513 + "\nEnd\n";
        CHECK_THROWS_AS(ConstructFile("bounds_ident.ini", true, overlong_ini_ident), IniParseError);

        const std::string overlong_script = "BeginScript " + invalid_513 + "\nEndScript\n";
        CHECK_THROWS_AS(ConstructFile("bounds_script.ini", true, overlong_script), IniParseError);

        const std::string overlong_fcurve = "Alpha = FCurve " + invalid_513 + "\nEnd\n";
        CHECK_THROWS_AS(ConstructFile("bounds_fcurve.ini", true, overlong_fcurve), IniParseError);

        const std::string overlong_fcurve_class = invalid_257 + " = FCurve\nEnd\n";
        CHECK_THROWS_AS(ConstructFile("bounds_fcurve_cls.ini", true, overlong_fcurve_class), IniParseError);

        const std::string overlong_str = "OBJECT:" + invalid_513 + "\n    \"Text\"\nEnd\n";
        CHECK_THROWS_AS(StrParser::parse_file("bounds.str", true, overlong_str), IniParseError);
    }
}
