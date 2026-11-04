/**
 * @file tests/cpp/ini/test_ini_parser.cpp
 * @brief Catch2 unit tests for the SAGE .ini, .inc, and .str structural parser.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <ini/parser.hpp>
#include <ini/types.hpp>

#include <catch2/catch_test_macros.hpp>

#include <filesystem>
#include <fstream>
#include <string>
#include <variant>
#include <vector>

using namespace lotm::ini;

namespace {
    // Utility to create a temporary file and return its path
    std::filesystem::path create_temp_file(const std::string& name, const std::string& content) {
        auto path = std::filesystem::temp_directory_path() / name;
        std::ofstream out(path, std::ios::binary);
        out << content;
        out.close();
        return path;
    }
} // namespace

TEST_CASE("IniParser: File loading and raw fallback", "[ini][load_file]") {
    SECTION("Empty path throws IniParseError") {
        REQUIRE_THROWS_AS(load_file(""), IniParseError);
    }

    SECTION("Non-existent file throws IniParseError") {
        REQUIRE_THROWS_AS(load_file("does_not_exist.ini"), IniParseError);
    }

    SECTION("Unsupported extension throws IniParseError") {
        auto p = create_temp_file("test.bin", "binary data");
        REQUIRE_THROWS_AS(load_file(p), IniParseError);
        std::filesystem::remove(p);
    }

    SECTION("Text file (.txt) falls back to raw text") {
        auto p = create_temp_file("test.txt", "Some raw text");
        auto [content, delims] = load_file(p);
        REQUIRE(content == "Some raw text\n");
        REQUIRE(delims.empty());
        std::filesystem::remove(p);
    }
}

TEST_CASE("IniParser: Basic INI Block Parsing", "[ini][ConstructFile]") {
    std::string ini_content =
        "Object GondorArcher\n"
        "    SelectPortrait = UPGondor_Archer\n"
        "    Draw = W3DScriptedModelDraw ModuleTag_01\n"
        "        OkToChangeModelColor = Yes\n"
        "    End\n"
        "End\n";

    auto p = create_temp_file("test_object.ini", ini_content);
    ConstructFile file(p, true);

    REQUIRE(file.name.ends_with("test_object.ini"));
    REQUIRE(file.start_level == 0);
    REQUIRE(file.items.size() == 1);
    REQUIRE(file.errors.empty());

    // Verify root block (Object)
    auto* root_block = std::get_if<ConstructLevel>(&file.items[0].value);
    REQUIRE(root_block != nullptr);
    REQUIRE(root_block->_class == "Object");
    REQUIRE(root_block->name == "GondorArcher");
    REQUIRE(root_block->end_token == "End");
    REQUIRE(root_block->items.size() == 2);

    // Verify Statement (SelectPortrait)
    auto* stmt = std::get_if<StatementNode>(&root_block->items[0].value);
    REQUIRE(stmt != nullptr);
    REQUIRE(stmt->text == "SelectPortrait = UPGondor_Archer");

    // Verify nested block (Draw)
    auto* draw_block = std::get_if<ConstructLevel>(&root_block->items[1].value);
    REQUIRE(draw_block != nullptr);
    REQUIRE(draw_block->_class == "Draw");
    REQUIRE(draw_block->name == "W3DScriptedModelDraw");
    REQUIRE(draw_block->identifier == "ModuleTag_01");
    REQUIRE(draw_block->items.size() == 1);

    // Verify nested Statement (OkToChangeModelColor)
    auto* inner_stmt = std::get_if<StatementNode>(&draw_block->items[0].value);
    REQUIRE(inner_stmt != nullptr);
    REQUIRE(inner_stmt->text == "OkToChangeModelColor = Yes");

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: ReplaceModule Level Shifting", "[ini][ReplaceModule]") {
    std::string ini_content =
        "Object GondorArcher\n"
        "    ReplaceModule ModuleTag_01\n"
        "        Draw = W3DScriptedModelDraw ModuleTag_01_New\n"
        "            OkToChangeModelColor = Yes\n"
        "        End\n"
        "    End\n"
        "End\n";

    auto p = create_temp_file("test_replace.ini", ini_content);
    ConstructFile file(p, true);

    REQUIRE(file.errors.empty());

    auto* root = std::get_if<ConstructLevel>(&file.items[0].value);
    REQUIRE(root != nullptr);

    auto* replace_mod = std::get_if<ConstructLevel>(&root->items[0].value);
    REQUIRE(replace_mod != nullptr);
    REQUIRE(replace_mod->_class == "ReplaceModule");
    REQUIRE(replace_mod->name == "ModuleTag_01");

    // Draw should be successfully nested inside ReplaceModule, despite both normally being Level 1
    auto* draw = std::get_if<ConstructLevel>(&replace_mod->items[0].value);
    REQUIRE(draw != nullptr);
    REQUIRE(draw->_class == "Draw");
    REQUIRE(draw->name == "W3DScriptedModelDraw");

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: Dynamic Schema Switching at Root", "[ini][ConstructFile]") {
    std::string ini_content =
        "Object GondorArcher\n"
        "End\n"
        "AudioEvent GondorArcherVoiceAttack\n"
        "End\n";

    auto p = create_temp_file("test_mixed.ini", ini_content);
    ConstructFile file(p, true);

    REQUIRE(file.items.size() == 2);
    REQUIRE(file.errors.empty());

    auto* obj_block = std::get_if<ConstructLevel>(&file.items[0].value);
    REQUIRE(obj_block != nullptr);
    REQUIRE(obj_block->_class == "Object");

    auto* audio_block = std::get_if<ConstructLevel>(&file.items[1].value);
    REQUIRE(audio_block != nullptr);
    REQUIRE(audio_block->_class == "AudioEvent");

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: Comments and Empty Lines", "[ini][Comments]") {
    std::string ini_content =
        "; Root comment\n"
        "\n"
        "Object GondorArcher // Inline comment\n"
        "    ; Block comment\n"
        "    ArmorSet = GondorArcherArmor\n"
        "End\n";

    auto p = create_temp_file("test_comments.ini", ini_content);
    ConstructFile file(p, true);

    REQUIRE(file.items.size() == 2);

    auto* root_comment = std::get_if<CommentNode>(&file.items[0].value);
    REQUIRE(root_comment != nullptr);
    REQUIRE(root_comment->text == "; Root comment");

    auto* obj = std::get_if<ConstructLevel>(&file.items[1].value);
    REQUIRE(obj != nullptr);
    REQUIRE(obj->comment == "// Inline comment");
    REQUIRE(obj->items.size() == 2);

    auto* block_comment = std::get_if<CommentNode>(&obj->items[0].value);
    REQUIRE(block_comment != nullptr);
    REQUIRE(block_comment->text == "; Block comment");

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: Preprocessor Directives", "[ini][Directives]") {
    std::string ini_content =
        "#define SOME_MACRO 1\n"
        "Object GondorArcher\n"
        "    #include \"some_file.inc\"\n"
        "End\n";

    auto p = create_temp_file("test_macros.ini", ini_content);
    ConstructFile file(p, true);

    REQUIRE(file.defines.size() == 1);
    REQUIRE(file.defines[0] == "#define SOME_MACRO 1");

    auto* obj = std::get_if<ConstructLevel>(&file.items[0].value);
    REQUIRE(obj != nullptr);

    auto* inc = std::get_if<IncludeNode>(&obj->items[0].value);
    REQUIRE(inc != nullptr);
    REQUIRE(inc->text == "#include \"some_file.inc\"");

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: Error Handling and Strict Mode", "[ini][Errors]") {
    std::string ini_content =
        "Object GondorArcher\n"
        "End\n"
        "End\n"; // Extraneous End

    auto p = create_temp_file("test_error.ini", ini_content);

    SECTION("Non-strict mode accumulates errors") {
        ConstructFile file(p, false);
        REQUIRE(file.errors.size() == 1);
        REQUIRE(file.errors[0].find("negative level reached") != std::string::npos);

        // Extraneous End is stored as a statement
        auto* end_stmt = std::get_if<StatementNode>(&file.items[1].value);
        REQUIRE(end_stmt != nullptr);
        REQUIRE(end_stmt->text == "End");
    }

    SECTION("Strict mode throws IniParseError") {
        REQUIRE_THROWS_AS(ConstructFile(p, true), IniParseError);
    }

    SECTION("scan_file_for_errors extracts diagnostic") {
        auto errors = scan_file_for_errors(p);
        REQUIRE(errors.size() == 1);
        REQUIRE(errors[0].find("negative level reached") != std::string::npos);
    }

    std::filesystem::remove(p);
}

TEST_CASE("StrParser: Flat Localization Files", "[str][StrParser]") {
    std::string str_content =
        "CONTROLBAR:ConstructGondorArcher\n"
        "    \"Train Gondor Archer\"\n"
        "End\n"
        "\n"
        "GUI:QuitGame\n"
        "    \"Quit\"\n"
        "End\n";

    auto p = create_temp_file("test.str", str_content);

    SECTION("StrDocument parsing") {
        auto doc = StrParser::parse_file(p);
        REQUIRE(doc.entries.size() == 2);

        auto* entry1 = std::get_if<StrEntry>(&doc.entries[0]);
        REQUIRE(entry1 != nullptr);
        REQUIRE(entry1->category == "CONTROLBAR");
        REQUIRE(entry1->identifier == "ConstructGondorArcher");
        REQUIRE(entry1->items.size() == 1);
        auto* stmt1 = std::get_if<StatementNode>(&entry1->items[0]);
        REQUIRE(stmt1->text == "\"Train Gondor Archer\"");

        auto* entry2 = std::get_if<StrEntry>(&doc.entries[1]);
        REQUIRE(entry2 != nullptr);
        REQUIRE(entry2->category == "GUI");
        REQUIRE(entry2->identifier == "QuitGame");
    }

    SECTION("ConstructFile delegates to StrParser") {
        ConstructFile file(p, true);
        REQUIRE(file.items.size() == 2);
        auto* entry1 = std::get_if<StrEntry>(&file.items[0].value);
        REQUIRE(entry1 != nullptr);
        REQUIRE(entry1->category == "CONTROLBAR");
    }

    std::filesystem::remove(p);
}
