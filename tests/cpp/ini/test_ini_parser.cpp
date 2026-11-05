/**
 * @file tests/cpp/ini/test_ini_parser.cpp
 * @brief Catch2 unit tests for the SAGE .ini, .inc, and .str structural parser.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <ini/delimiters.hpp>
#include <ini/exceptions.hpp>
#include <ini/parser.hpp>
#include <ini/types.hpp>

#include <catch2/catch_test_macros.hpp>

#include <filesystem>
#include <fstream>
#include <span>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

using namespace lotm::ini;

namespace {
    // Utility to create a temporary file and return its path
    std::filesystem::path create_temp_file(const std::string& name, const std::string& content) {
        auto path = std::filesystem::temp_directory_path() / name;
        std::ofstream out(path, std::ios::binary);
        out.write(content.data(), static_cast<std::streamsize>(content.size()));
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
        auto p = create_temp_file("test.txt", "Some raw text\n");
        auto [content, delims] = load_file(p);
        REQUIRE(content == "Some raw text\n");
        REQUIRE(delims.empty());
        std::filesystem::remove(p);
    }

    SECTION("Malformed INI falls back to raw text in load_file") {
        auto p = create_temp_file("unsupported.ini", "UnknownBlockWithNoDelimiters\n    Val = 1\n");
        auto [content, delims] = load_file(p);
        REQUIRE(!content.empty());
        std::filesystem::remove(p);
    }
}

TEST_CASE("IniParser: Lexer and Delimiter Compilation", "[ini][lexer]") {
    SECTION("lex_line handles both ; and // comments") {
        auto lexed1 = lex_line("Key = Value ; Semicolon comment");
        REQUIRE(lexed1.words.size() == 2);
        REQUIRE(lexed1.words[0] == "Key");
        REQUIRE(lexed1.words[1] == "Value");
        REQUIRE(lexed1.comment == "; Semicolon comment");

        auto lexed2 = lex_line("Key = Value // Slash comment");
        REQUIRE(lexed2.comment == "// Slash comment");

        auto lexed3 = lex_line("Key = Value // First ; Second");
        REQUIRE(lexed3.comment == "// First ; Second");

        auto lexed4 = lex_line("Key = Value ; First // Second");
        REQUIRE(lexed4.comment == "; First // Second");

        auto lexed5 = lex_line("NoComment = 123");
        REQUIRE(lexed5.comment.empty());
    }

    SECTION("compile_delimiter_rules and match_delimiter_rule") {
        std::vector<std::string_view> raw_delims = { "Draw", "DefaultModelConditionState", "AddEmotion = OVERRIDE" };
        auto rules = compile_delimiter_rules(std::span<const std::string_view>(raw_delims));
        REQUIRE(rules.size() == 3);

        std::vector<std::string> tokens1 = { "AddEmotion", "=", "OVERRIDE", "Extra" };
        const auto* match1 = match_delimiter_rule(tokens1, rules);
        REQUIRE(match1 != nullptr);
        REQUIRE(match1->raw == "AddEmotion = OVERRIDE");

        std::vector<std::string> tokens2 = { "Unrelated", "Token" };
        const auto* match2 = match_delimiter_rule(tokens2, rules);
        REQUIRE(match2 == nullptr);
    }

    SECTION("format_indented_text handles single and multi-line strings") {
        auto single = format_indented_text("SingleLine", 2);
        REQUIRE(single == "        SingleLine\n");

        auto multi = format_indented_text("Line1\nLine2", 1);
        REQUIRE(multi == "    Line1\n    Line2\n");
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

    std::string printed = file.print();
    REQUIRE(printed.find("Object GondorArcher") != std::string::npos);
    REQUIRE(printed.find("SelectPortrait = UPGondor_Archer") != std::string::npos);
    REQUIRE(printed.find("Draw W3DScriptedModelDraw ModuleTag_01") != std::string::npos);

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
        "\n"
        "    SelectPortrait = UPGondor_Archer\n"
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

    auto* stmt = std::get_if<StatementNode>(&obj->items[1].value);
    REQUIRE(stmt != nullptr);
    REQUIRE(stmt->text == "SelectPortrait = UPGondor_Archer");

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

    SECTION("scan_file_for_errors handles non-existent file cleanly") {
        auto errors = scan_file_for_errors("completely_missing.ini");
        REQUIRE(errors.size() == 1);
        REQUIRE(errors[0].find("Fatal error") != std::string::npos);
    }

    std::filesystem::remove(p);
}

TEST_CASE("StrParser: Flat Localization Files", "[str][StrParser]") {
    std::string str_content =
        "// File comment\n"
        "CONTROLBAR:ConstructGondorArcher\n"
        "    \"Train Gondor Archer\"\n"
        "End\n"
        "\n"
        "GUI:QuitGame\n"
        "    \"Quit\"\n"
        "End\n";

    auto p = create_temp_file("test.str", str_content);

    SECTION("StrDocument parsing and printing") {
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

        std::string printed = doc.print();
        REQUIRE(printed.find("CONTROLBAR:ConstructGondorArcher") != std::string::npos);
        REQUIRE(printed.find("\"Train Gondor Archer\"") != std::string::npos);
    }

    SECTION("ConstructFile delegates to StrParser") {
        ConstructFile file(p, true);
        REQUIRE(file.items.size() == 2);
        auto* entry1 = std::get_if<StrEntry>(&file.items[0].value);
        REQUIRE(entry1 != nullptr);
        REQUIRE(entry1->category == "CONTROLBAR");
    }

    SECTION("StrParser error handling") {
        REQUIRE_THROWS_AS(StrParser::parse_file("missing.str"), IniParseError);

        auto bad_str = create_temp_file("bad.str", "End\n");
        REQUIRE_THROWS_AS(StrParser::parse_file(bad_str, true), IniParseError);

        auto doc_lenient = StrParser::parse_file(bad_str, false);
        REQUIRE(doc_lenient.errors.size() == 1);
        std::filesystem::remove(bad_str);
    }

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: Windows-1252 Encoding Transcoding", "[ini][encoding]") {
    std::string win1252_data = "Object GondorArcher\n    DisplayName = \"";
    win1252_data.push_back(static_cast<char>(0x96)); // Windows-1252 en-dash (0x96)
    win1252_data += " Special\"\nEnd\n";

    auto p = create_temp_file("test_cp1252.ini", win1252_data);
    ConstructFile file(p, true);
    REQUIRE(file.errors.empty());

    auto* obj = std::get_if<ConstructLevel>(&file.items[0].value);
    REQUIRE(obj != nullptr);
    auto* stmt = std::get_if<StatementNode>(&obj->items[0].value);
    REQUIRE(stmt != nullptr);
    REQUIRE(stmt->text.find("Special") != std::string::npos);

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: .inc starting at non-zero level", "[ini][inc]") {
    std::string inc_content =
        "Draw = W3DScriptedModelDraw ModuleTag_Draw\n"
        "    OkToChangeModelColor = Yes\n"
        "End\n";

    auto p = create_temp_file("sub_module.inc", inc_content);
    ConstructFile file(p, true);

    REQUIRE(file.start_level == 1);
    REQUIRE(file.errors.empty());
    REQUIRE(file.items.size() == 1);

    auto* draw = std::get_if<ConstructLevel>(&file.items[0].value);
    REQUIRE(draw != nullptr);
    REQUIRE(draw->_class == "Draw");
    REQUIRE(draw->items.size() == 1);

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: Alternate Closing Keywords and Inner Scripts", "[ini][keywords]") {
    std::string ini_content =
        "Object GondorArcher\n"
        "    Draw = W3DScriptedModelDraw ModuleTag_01\n"
        "        AnimationState = IDLA\n"
        "            BeginScript\n"
        "                Prev = CurDrawablePrevAnimation()\n"
        "            EndScript\n"
        "        End\n"
        "    END\n"
        "End\n";

    auto p = create_temp_file("test_keywords.ini", ini_content);
    ConstructFile file(p, true);
    REQUIRE(file.errors.empty());

    auto* obj = std::get_if<ConstructLevel>(&file.items[0].value);
    REQUIRE(obj != nullptr);
    auto* draw = std::get_if<ConstructLevel>(&obj->items[0].value);
    REQUIRE(draw != nullptr);
    REQUIRE(draw->end_token == "END");

    auto* anim_state = std::get_if<ConstructLevel>(&draw->items[0].value);
    REQUIRE(anim_state != nullptr);
    REQUIRE(anim_state->_class == "AnimationState");

    auto* script = std::get_if<ConstructLevel>(&anim_state->items[0].value);
    REQUIRE(script != nullptr);
    REQUIRE(script->_class == "BeginScript");
    REQUIRE(script->end_token == "EndScript");

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: UTF-8 Validation Boundaries and Newline Normalization", "[ini][encoding_edge]") {
    SECTION("Valid multi-byte UTF-8 sequences (2-byte, 3-byte, 4-byte)") {
        std::string utf8_content =
            "Object GondorArcher\n"
            "    DisplayName = \"2-byte: \xC3\xA9\"\n"
            "    Description = \"3-byte: \xE2\x82\xAC\"\n"
            "    Symbol      = \"4-byte: \xF0\x9F\x94\xA5\"\n"
            "End\n";

        auto p = create_temp_file("test_valid_utf8.ini", utf8_content);
        ConstructFile file(p, true);
        REQUIRE(file.errors.empty());

        auto* obj = std::get_if<ConstructLevel>(&file.items[0].value);
        REQUIRE(obj != nullptr);
        REQUIRE(obj->items.size() == 3);

        std::filesystem::remove(p);
    }

    SECTION("Windows-1252 high table >= 0x800 and < 0x800 branches") {
        std::string win1252_data = "Object GondorArcher\n    Text = \"";
        win1252_data.push_back(static_cast<char>(0x80)); // 0x80 maps to U+20AC (>= 0x800, 3-byte UTF-8)
        win1252_data.push_back(static_cast<char>(0xE9)); // 0xE9 maps to U+00E9 (< 0x800, 2-byte UTF-8)
        win1252_data += "\"\nEnd\n";

        auto p = create_temp_file("test_cp1252_branches.ini", win1252_data);
        ConstructFile file(p, true);
        REQUIRE(file.errors.empty());

        auto* obj = std::get_if<ConstructLevel>(&file.items[0].value);
        REQUIRE(obj != nullptr);
        auto* stmt = std::get_if<StatementNode>(&obj->items[0].value);
        REQUIRE(stmt != nullptr);
        REQUIRE(stmt->text.find("\xE2\x82\xAC") != std::string::npos);

        std::filesystem::remove(p);
    }

    SECTION("Invalid UTF-8 sequences fallback to Windows-1252") {
        std::vector<std::string> invalid_patterns = {
            std::string("Object GondorArcher\n    Val = \"\xC2\x20\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xC2\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xE0\x80\x80\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xED\xA0\x80\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xE2\x82\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xE2\x20\x80\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xF5\x80\x80\x80\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xF0\x80\x80\x80\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xF4\x90\x80\x80\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xF0\x9F\x94\"\nEnd\n"),
            std::string("Object GondorArcher\n    Val = \"\xF0\x20\x80\x80\"\nEnd\n")
        };

        for (std::size_t i = 0; i < invalid_patterns.size(); ++i) {
            auto p = create_temp_file("test_invalid_utf8_" + std::to_string(i) + ".ini", invalid_patterns[i]);
            ConstructFile file(p, true);
            REQUIRE(file.errors.empty());
            std::filesystem::remove(p);
        }
    }

    SECTION("Universal newline handling (CRLF, bare CR, bare LF)") {
        std::string mixed_linebreaks = "Object GondorArcher\r\r    Prop1 = A\r\n    Prop2 = B\nEnd\r\n";
        auto p = create_temp_file("test_newlines.ini", mixed_linebreaks);
        ConstructFile file(p, true);
        REQUIRE(file.errors.empty());

        auto* obj = std::get_if<ConstructLevel>(&file.items[0].value);
        REQUIRE(obj != nullptr);
        REQUIRE(obj->items.size() == 2);

        std::filesystem::remove(p);
    }
}

TEST_CASE("StrParser: Advanced Branches and Unclosed Entries", "[str][edge]") {
    std::string str_content =
        "// Root comment\n"
        "\n"
        "CONTROLBAR:ConstructGondorArcher\n"
        "    ; Entry comment\n"
        "\n"
        "    \"Train Gondor Archer\"\n"
        "    // Trailing comment before End\n"
        "End\n"
        "TOOLTIP\n"
        "    \"Value without identifier\"\n";

    auto p = create_temp_file("test_advanced.str", str_content);
    auto doc = StrParser::parse_file(p);
    REQUIRE(doc.entries.size() == 3);

    auto* comment = std::get_if<CommentNode>(&doc.entries[0]);
    REQUIRE(comment != nullptr);
    REQUIRE(comment->text == "// Root comment");

    auto* entry1 = std::get_if<StrEntry>(&doc.entries[1]);
    REQUIRE(entry1 != nullptr);
    REQUIRE(entry1->category == "CONTROLBAR");
    REQUIRE(entry1->identifier == "ConstructGondorArcher");
    REQUIRE(entry1->items.size() == 3);

    auto* entry2 = std::get_if<StrEntry>(&doc.entries[2]);
    REQUIRE(entry2 != nullptr);
    REQUIRE(entry2->category == "TOOLTIP");
    REQUIRE(entry2->identifier.empty());
    REQUIRE(entry2->items.size() == 1);

    std::string printed = doc.print();
    REQUIRE(printed.find("TOOLTIP\n") != std::string::npos);

    auto [content, delims] = load_file(p);
    REQUIRE(!content.empty());
    REQUIRE(!delims.empty());

    std::filesystem::remove(p);
}

TEST_CASE("IniParser: ConstructLevel and AstNode Semantics", "[ini][types]") {
    ConstructLevel lvl1("Object", "GondorArcher", "Ident", "; Comment", "End");
    lvl1.append(StatementNode{ "Prop = 1" });

    SECTION("Copy constructor and assignment") {
        ConstructLevel copied = lvl1;
        REQUIRE(copied._class == "Object");
        REQUIRE(copied.name == "GondorArcher");
        REQUIRE(copied.items.size() == 1);

        ConstructLevel assigned;
        assigned = lvl1;
        REQUIRE(assigned.identifier == "Ident");
        REQUIRE(assigned.items.size() == 1);
    }

    SECTION("Move constructor and assignment") {
        ConstructLevel moved = std::move(lvl1);
        REQUIRE(moved._class == "Object");
        REQUIRE(moved.items.size() == 1);

        ConstructLevel move_assigned;
        move_assigned = std::move(moved);
        REQUIRE(move_assigned.name == "GondorArcher");
    }

    SECTION("AstNode variant wrapper accepts all node types") {
        AstNode n1(CommentNode{ "; c" });
        REQUIRE(std::holds_alternative<CommentNode>(n1.value));

        AstNode n2(StatementNode{ "s" });
        REQUIRE(std::holds_alternative<StatementNode>(n2.value));

        AstNode n3(IncludeNode{ "#inc" });
        REQUIRE(std::holds_alternative<IncludeNode>(n3.value));

        AstNode n4(StrEntry{ "CAT", "ID" });
        REQUIRE(std::holds_alternative<StrEntry>(n4.value));

        AstNode n5(ConstructLevel{ "CLS" });
        REQUIRE(std::holds_alternative<ConstructLevel>(n5.value));
    }

    SECTION("ConstructLevel print formatting variations") {
        ConstructLevel str_lvl("CONTROLBAR", "Id");
        std::string str_printed = str_lvl.print(0, ".str");
        REQUIRE(str_printed.find("CONTROLBAR:Id") != std::string::npos);

        ConstructLevel no_end("Object", "NoEnd");
        std::string no_end_printed = no_end.print(0, ".ini");
        REQUIRE(no_end_printed.find("Object NoEnd") != std::string::npos);

        ConstructLevel nested_parent("Parent");
        nested_parent.append(StrEntry{ "CAT", "ID", "; c", "End",{} });
        std::string nested_printed = nested_parent.print(0, ".ini");
        REQUIRE(nested_printed.find("CAT:ID") != std::string::npos);
    }

    SECTION("compile_delimiter_rules std::string overload") {
        std::vector<std::string> str_rules = { "Object", "Draw" };
        auto rules = compile_delimiter_rules(std::span<const std::string>(str_rules));
        REQUIRE(rules.size() == 2);
    }

    SECTION("load_file on valid .inc file") {
        std::string inc_content = "Draw = W3DScriptedModelDraw ModuleTag_01\nEnd\n";
        auto p = create_temp_file("test_valid.inc", inc_content);
        auto [content, delims] = load_file(p);
        REQUIRE(!content.empty());
        REQUIRE(!delims.empty());
        std::filesystem::remove(p);
    }
}

TEST_CASE("IniParser: Empty Lines and Comment Flushing Before End", "[ini][flushing]") {
    std::string ini_content =
        "Object GondorArcher\n"
        "    ; Block comment\n"
        "    // Another comment before end\n"
        "End\n";

    auto p = create_temp_file("test_flush.ini", ini_content);
    ConstructFile file(p, true);
    REQUIRE(file.errors.empty());

    auto* obj = std::get_if<ConstructLevel>(&file.items[0].value);
    REQUIRE(obj != nullptr);
    REQUIRE(obj->items.size() == 1);
    auto* comment = std::get_if<CommentNode>(&obj->items[0].value);
    REQUIRE(comment != nullptr);
    REQUIRE(comment->text.find("; Block comment") != std::string::npos);

    std::filesystem::remove(p);
}
