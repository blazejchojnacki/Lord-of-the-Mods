/**
 * @file tests/cpp/ini/test_ini_parser.cpp
 * @brief Exhaustive Catch2 unit and security test suite for lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>

#include "ini/lexer.hpp"
#include "ini/parser.hpp"
#include "ini/schema.hpp"
#include "ini/ast.hpp"

#include <atomic>
#include <chrono>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

#ifdef _WIN32
#include <share.h>
#endif

namespace fs = std::filesystem;
using namespace lotm::ini;

namespace {

    /**
     * @brief RAII temporary directory fixture for deterministic filesystem tests.
     */
    class TempDirFixture {
    public:
        TempDirFixture() {
            static std::atomic<std::uint64_t> counter{ 0 };
            const auto now = std::chrono::steady_clock::now().time_since_epoch().count();
            const std::string dir_name = "lotm_ini_test_" + std::to_string(now) + "_" + std::to_string(++counter);
            root_ = fs::temp_directory_path() / dir_name;
            fs::create_directories(root_);
        }

        ~TempDirFixture() {
            std::error_code ec;
            fs::remove_all(root_, ec);
        }

        TempDirFixture(const TempDirFixture&) = delete;
        TempDirFixture& operator=(const TempDirFixture&) = delete;

        [[nodiscard]] const fs::path& root() const noexcept { return root_; }

        [[nodiscard]] fs::path write_file(std::string_view rel_path, std::string_view content) const {
            const std::u8string_view u8_rel(
                reinterpret_cast<const char8_t*>(rel_path.data()),
                rel_path.size()
            );
            const fs::path full_path = root_ / fs::path(u8_rel);
            fs::create_directories(full_path.parent_path());
            std::ofstream out(full_path, std::ios::binary);
            out.write(content.data(), static_cast<std::streamsize>(content.size()));
            out.close();
            return full_path;
        }

    private:
        fs::path root_;
    };

#ifdef _WIN32
    /**
     * @brief RAII exclusive file lock using Windows _fsopen(_SH_DENYRW) to force deterministic I/O read failures.
     */
    class ScopedExclusiveFileLock {
    public:
        explicit ScopedExclusiveFileLock(const fs::path& path)
            : handle_(_fsopen(path.string().c_str(), "rb", _SH_DENYRW)) {
        }

        ~ScopedExclusiveFileLock() {
            if (handle_ != nullptr) {
                std::fclose(handle_);
            }
        }

        ScopedExclusiveFileLock(const ScopedExclusiveFileLock&) = delete;
        ScopedExclusiveFileLock& operator=(const ScopedExclusiveFileLock&) = delete;

        [[nodiscard]] bool is_locked() const noexcept { return handle_ != nullptr; }

    private:
        std::FILE* handle_{ nullptr };
    };
#endif

} // namespace

TEST_CASE("AST types, node operations, and SerializableNodeRef conversions", "[ini][types]") {
    SECTION("is_ini_end recognizes exact SAGE closing tokens") {
        STATIC_REQUIRE(is_ini_end("End"));
        STATIC_REQUIRE(is_ini_end("END"));
        STATIC_REQUIRE(is_ini_end("end"));
        STATIC_REQUIRE_FALSE(is_ini_end("EnD"));
        STATIC_REQUIRE_FALSE(is_ini_end("EndScript"));
        STATIC_REQUIRE_FALSE(is_ini_end(""));
    }

    SECTION("CommentNode and StatementNode equality") {
        const CommentNode c1{ "; comment A" };
        const CommentNode c2{ "; comment A" };
        const CommentNode c3{ "; comment B" };
        CHECK(c1 == c2);
        CHECK_FALSE(c1 == c3);

        const StatementNode s1{ "Damage = 100", "; inline" };
        const StatementNode s2{ "Damage = 100", "; inline" };
        const StatementNode s3{ "Damage = 200", "; inline" };
        CHECK(s1 == s2);
        CHECK_FALSE(s1 == s3);
    }

    SECTION("IncludeNode::clean_path normalizes slashes and strips quotes/whitespace") {
        const IncludeNode empty_inc{ "   \t \"\" '' \t " };
        CHECK(empty_inc.clean_path().empty());

        const IncludeNode win_inc{ " \t \"..\\data\\ini\\includes\\weapon.inc\"  " };
        CHECK(win_inc.clean_path() == "../data/ini/includes/weapon.inc");

        const IncludeNode single_quote_inc{ "'sub\\path\\macros.inc'" };
        CHECK(single_quote_inc.clean_path() == "sub/path/macros.inc");

        CHECK(win_inc == IncludeNode{ " \t \"..\\data\\ini\\includes\\weapon.inc\"  " });
    }

    SECTION("ConstructLevel constructors, rule-of-five, iterators, and indexing") {
        ConstructLevel lvl{ "Object", "GondorArcher", "ModTag_01", "; lead", "; hdr", "End", "; tail" };
        CHECK(lvl.empty());
        CHECK(lvl.size() == 0);

        lvl.append(CommentNode{ "; inner comment" });
        lvl.append(StatementNode{ "Health = 100", "" });
        REQUIRE(lvl.size() == 2);
        CHECK_FALSE(lvl.empty());

        CHECK(std::holds_alternative<CommentNode>(lvl[0]));
        lvl[1] = StatementNode{ "Health = 150", "; buffed" };

        const ConstructLevel& const_lvl = lvl;
        CHECK(std::get<StatementNode>(const_lvl[1]).text == "Health = 150");

        std::size_t count = 0;
        for (auto it = lvl.begin(); it != lvl.end(); ++it) {
            ++count;
        }
        CHECK(count == 2);

        std::size_t const_count = 0;
        for (auto it = const_lvl.begin(); it != const_lvl.end(); ++it) {
            ++const_count;
        }
        CHECK(const_count == 2);

        std::size_t cbegin_count = 0;
        for (auto it = const_lvl.cbegin(); it != const_lvl.cend(); ++it) {
            ++cbegin_count;
        }
        CHECK(cbegin_count == 2);

        ConstructLevel copy_constructed{ lvl };
        CHECK(copy_constructed == lvl);

        ConstructLevel copy_assigned;
        copy_assigned = lvl;
        CHECK(copy_assigned == lvl);

        ConstructLevel move_constructed{ std::move(copy_constructed) };
        CHECK(move_constructed == lvl);

        ConstructLevel move_assigned;
        move_assigned = std::move(copy_assigned);
        CHECK(move_assigned == lvl);
    }

    SECTION("StrEntry and StrDocument container protocols and equality") {
        StrEntry entry{ "OBJECT", "GondorSoldier" };
        CHECK(entry.empty());
        CHECK(entry.size() == 0);

        entry.append(CommentNode{ "; localized cmt" });
        entry.append(StatementNode{ "\"Gondor Soldier\"", "" });
        REQUIRE(entry.size() == 2);
        CHECK_FALSE(entry.empty());

        entry[1] = StatementNode{ "\"Gondor Infantry\"", "; updated" };
        const StrEntry& const_entry = entry;
        CHECK(std::get<StatementNode>(const_entry[1]).text == "\"Gondor Infantry\"");

        std::size_t entry_iter_count = 0;
        for (auto it = entry.begin(); it != entry.end(); ++it) { ++entry_iter_count; }
        for (auto it = const_entry.begin(); it != const_entry.end(); ++it) { ++entry_iter_count; }
        for (auto it = const_entry.cbegin(); it != const_entry.cend(); ++it) { ++entry_iter_count; }
        CHECK(entry_iter_count == 6);

        StrDocument doc{ "lotr.str" };
        CHECK(doc.empty());
        CHECK(doc.size() == 0);

        doc.append(CommentNode{ "; doc header" });
        doc.append(entry);
        REQUIRE(doc.size() == 2);
        CHECK_FALSE(doc.empty());

        doc[0] = CommentNode{ "; updated doc header" };
        const StrDocument& const_doc = doc;
        CHECK(std::get<CommentNode>(const_doc[0]).text == "; updated doc header");

        std::size_t doc_iter_count = 0;
        for (auto it = doc.begin(); it != doc.end(); ++it) { ++doc_iter_count; }
        for (auto it = const_doc.begin(); it != const_doc.end(); ++it) { ++doc_iter_count; }
        for (auto it = const_doc.cbegin(); it != const_doc.cend(); ++it) { ++doc_iter_count; }
        CHECK(doc_iter_count == 6);

        StrDocument doc_copy = doc;
        CHECK(doc_copy == doc);
        doc_copy.name = "other.str";
        CHECK_FALSE(doc_copy == doc);
    }

    SECTION("to_serializable_ref conversion overloads") {
        const AstNode ast_cmt = CommentNode{ "; c" };
        const AstNode ast_stmt = StatementNode{ "x = 1" };
        const AstNode ast_inc = IncludeNode{ "\"a.inc\"" };
        const AstNode ast_scr = ScriptNode{};
        const AstNode ast_lvl = ConstructLevel{ "Object", "Test" };

        CHECK(std::holds_alternative<const CommentNode*>(to_serializable_ref(ast_cmt)));
        CHECK(std::holds_alternative<const StatementNode*>(to_serializable_ref(ast_stmt)));
        CHECK(std::holds_alternative<const IncludeNode*>(to_serializable_ref(ast_inc)));
        CHECK(std::holds_alternative<const ScriptNode*>(to_serializable_ref(ast_scr)));
        CHECK(std::holds_alternative<const ConstructLevel*>(to_serializable_ref(ast_lvl)));

        const StrChildNode str_child_cmt = CommentNode{ "; sc" };
        const StrChildNode str_child_stmt = StatementNode{ "\"Localized\"" };
        CHECK(std::holds_alternative<const CommentNode*>(to_serializable_ref(str_child_cmt)));
        CHECK(std::holds_alternative<const StatementNode*>(to_serializable_ref(str_child_stmt)));

        const StrDocEntry doc_entry_str = StrEntry{ "OBJECT", "GondorFighter" };
        const StrDocEntry doc_entry_cmt = CommentNode{ "; dc" };
        const StrDocEntry doc_entry_stmt = StatementNode{ "orphan" };
        CHECK(std::holds_alternative<const StrEntry*>(to_serializable_ref(doc_entry_str)));
        CHECK(std::holds_alternative<const CommentNode*>(to_serializable_ref(doc_entry_cmt)));
        CHECK(std::holds_alternative<const StatementNode*>(to_serializable_ref(doc_entry_stmt)));

        const RootItem root_ast = ast_stmt;
        const RootItem root_str = StrEntry{ "GUI", "Start" };
        CHECK(std::holds_alternative<const StatementNode*>(to_serializable_ref(root_ast)));
        CHECK(std::holds_alternative<const StrEntry*>(to_serializable_ref(root_str)));
    }
}

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

        STATIC_REQUIRE(detail::iequals_ascii("BeginScript", "bEgInScRiPt"));
        STATIC_REQUIRE_FALSE(detail::iequals_ascii("Begin", "BeginScript"));
        STATIC_REQUIRE_FALSE(detail::iequals_ascii("End", "Enx"));

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

    SECTION("lex_line preserves ';' and '//' inside quotes and URL schemes like http://") {
        const LexedLine quoted_semi = lex_line("    \" Soldier ; Archer // Cavalry \" ; real trailing comment");
        REQUIRE(quoted_semi.words_signs.size() == 7);
        CHECK(quoted_semi.comment == "; real trailing comment");

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

TEST_CASE("Compile-time and runtime delimiter schema rules", "[ini][schema]") {
    SECTION("compile_delimiter_rule handles operators, whitespace, and MAX_RULE_TOKENS cap") {
        constexpr auto eq_rule = compile_delimiter_rule("AddEmotion = OVERRIDE");
        STATIC_REQUIRE(eq_rule.token_count == 3);
        STATIC_REQUIRE(eq_rule.word_count == 2);
        STATIC_REQUIRE(eq_rule.tokens().size() == 3);
        STATIC_REQUIRE(eq_rule.tokens()[0] == "AddEmotion");
        STATIC_REQUIRE(eq_rule.tokens()[1] == "=");
        STATIC_REQUIRE(eq_rule.tokens()[2] == "OVERRIDE");

        constexpr auto colon_rule = compile_delimiter_rule("  CONTROLBAR : Button  ");
        STATIC_REQUIRE(colon_rule.token_count == 3);
        STATIC_REQUIRE(colon_rule.word_count == 2);
        STATIC_REQUIRE(colon_rule.tokens()[1] == ":");

        constexpr auto empty_rule = compile_delimiter_rule("   \t\r\n ");
        STATIC_REQUIRE(empty_rule.token_count == 0);
        STATIC_REQUIRE(empty_rule.word_count == 0);

        constexpr auto overflow_rule = compile_delimiter_rule("A = B : C = D : E = F");
        STATIC_REQUIRE(overflow_rule.token_count == MAX_RULE_TOKENS);
        STATIC_REQUIRE(overflow_rule.word_count == 6);
    }

    SECTION("compile_delimiter_rules sorts descending by token count and skips empty rules") {
        const std::vector<std::string> raw_list = {
            "SingleToken",
            "   ",
            "Three = Tokens",
            "Two Tokens"
        };
        const auto compiled = compile_delimiter_rules(raw_list);
        REQUIRE(compiled.size() == 3);
        CHECK(compiled[0].raw == "Three = Tokens");
        CHECK(compiled[1].raw == "Two Tokens");
        CHECK(compiled[2].raw == "SingleToken");
    }

    SECTION("match_delimiter_rule matches case-insensitively and rejects partial tokens") {
        const std::vector<std::string> raw_list = { "AddEmotion = OVERRIDE", "Behavior" };
        const auto rules = compile_delimiter_rules(raw_list);

        const auto lex1 = lex_line("addemotion = override ModuleTag_01");
        const DelimiterRule* m1 = match_delimiter_rule(lex1.line_tokens, rules);
        REQUIRE(m1 != nullptr);
        CHECK(m1->raw == "AddEmotion = OVERRIDE");

        const auto lex2 = lex_line("AddEmotion = DIFFERENT");
        CHECK(match_delimiter_rule(lex2.line_tokens, rules) == nullptr);

        const auto lex3 = lex_line("");
        CHECK(match_delimiter_rule(lex3.line_tokens, rules) == nullptr);
    }
}

TEST_CASE("Iterative serialization covers all AST and STR node variations", "[ini][serializer]") {
    SECTION("ConstructLevel, ScriptNode, IncludeNode, StatementNode, and CommentNode serialization") {
        ConstructLevel root_block{ "Object", "GondorTower", "", "; line 1\n  ; line 2", "; root hdr", "End", "; root end" };
        root_block.append(CommentNode{ "; inner standalone" });
        root_block.append(IncludeNode{ "\"..\\common.inc\"", "; inc cmt" });
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
        const fs::path inc_file = temp.write_file("sub/draw.inc", "LodOptions\n    AllowMultipleModels = YES\nEnd\n");
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

TEST_CASE("Virtual chroot #include path validation and traversal defense", "[ini][security][include]") {
    TempDirFixture temp;
    const fs::path vroot = temp.root() / "data" / "ini";
    const fs::path current_ini = temp.write_file("data/ini/object/gondor/archer.ini", "");
    const fs::path local_inc = temp.write_file("data/ini/object/gondor/local_macros.inc", "");
    const fs::path root_inc = temp.write_file("data/ini/includes/global.inc", "");
    const fs::path outside_secret = temp.write_file("data/secret.ini", "");
    fs::create_directories(vroot / "includes" / "subdir");

    SECTION("Resolves relative to current_file parent first, then virtual_root") {
        const IncludeNode local_node{ "\"local_macros.inc\"" };
        CHECK(validate_include(local_node, current_ini, vroot) == fs::weakly_canonical(local_inc));

        const IncludeNode root_node{ "\"includes\\global.inc\"" };
        CHECK(validate_include(root_node, current_ini, vroot) == fs::weakly_canonical(root_inc));
    }

    SECTION("Blocks path traversal escaping virtual_root") {
        const IncludeNode escape_rel{ "\"..\\..\\..\\secret.ini\"" };
        CHECK_THROWS_AS(validate_include(escape_rel, current_ini, vroot), IniParseError);

        const IncludeNode escape_root{ "\"..\\secret.ini\"" };
        CHECK_THROWS_AS(validate_include(escape_root, current_ini, vroot), IniParseError);

        const IncludeNode escape_to_fs_root{ "\"..\\..\\..\\..\\..\\..\\..\"" };
        CHECK_THROWS_AS(validate_include(escape_to_fs_root, current_ini, vroot), IniParseError);
    }

    SECTION("Throws when target file does not exist or is a directory") {
        const IncludeNode missing_node{ "\"includes/nonexistent.inc\"" };
        CHECK_THROWS_AS(validate_include(missing_node, current_ini, vroot), IniParseError);

        const IncludeNode dir_node{ "\"includes/subdir\"" };
        CHECK_THROWS_AS(validate_include(dir_node, current_ini, vroot), IniParseError);
    }

#ifdef _WIN32
    SECTION("Handles case-insensitive drive/folder matching on Windows") {
        std::string upper_root_str = vroot.string();
        std::ranges::transform(upper_root_str, upper_root_str.begin(), [](unsigned char c) {
            return static_cast<char>(std::toupper(c));
            });
        const IncludeNode local_node{ "\"local_macros.inc\"" };
        CHECK_NOTHROW(validate_include(local_node, current_ini, fs::path{ upper_root_str }));
    }
#endif
}

TEST_CASE("StrParser happy paths, comment coalescing, and strict/non-strict error diagnostics", "[ini][str]") {
    TempDirFixture temp;

    SECTION("Rejects invalid file extensions or missing files") {
        CHECK_THROWS_AS(StrParser::parse_file("bad.ini", false, "OBJECT:Foo\nEnd\n"), IniParseError);
        CHECK_THROWS_AS(StrParser::parse_file((temp.root() / "missing.str").string(), false), IniParseError);
    }

    SECTION("Parses valid .str from disk with comments in all positions") {
        const std::string content =
            "; file header line 1\n"
            "; file header line 2\n"
            "\n"
            "; entry lead comment\n"
            "OBJECT:GondorFighter ; hdr cmt\n"
            "    ; inner block comment\n"
            "    \n"
            "    ; pre-text comment\n"
            "    \"Gondor Soldiers\" ; text cmt\n"
            "    ; trailing inside entry\n"
            "End ; end cmt\n"
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
}

TEST_CASE("ConstructFile INI/INC parser features, special blocks, and depth security limits", "[ini][parser][security]") {
    TempDirFixture temp;

    SECTION("Default ConstructFile, container interface, equality, and short filename print") {
        ConstructFile empty_cf;
        CHECK(empty_cf.empty());
        CHECK(empty_cf.size() == 0);

        empty_cf.name = "a";
        empty_cf.append(AstNode{ StatementNode{ "Key = 1", "" } });
        empty_cf.append(RootItem{ AstNode{ CommentNode{ "; cmt" } } });
        empty_cf.append(StrEntry{ "GUI", "Btn" });
        REQUIRE(empty_cf.size() == 3);
        CHECK_FALSE(empty_cf.empty());

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
        CHECK(cnt == 9);
        CHECK_FALSE(empty_cf.print().empty());

        ConstructFile no_name{ "", false };
        CHECK(no_name.empty());

        CHECK_THROWS_AS(ConstructFile("bad.ext", false, ""), IniParseError);
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

    SECTION("Handles #define, #include, ReplaceModule depth shift, FCurve, BeginScript, multi-flag headers, and schema switching") {
        const std::string ini_content =
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
            "End\n"
            "; trailing file comment\n";

        ConstructFile cf{ "hero.ini", true, ini_content };
        CHECK(cf.errors.empty());
        REQUIRE(cf.defines.size() == 1);
        CHECK(cf.defines[0] == "#define DAMAGE_MACRO 100 ; macro cmt");

        const std::string printed = cf.print();
        ConstructFile reparsed{ "hero.ini", true, printed };
        CHECK(reparsed.print() == printed);
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

TEST_CASE("File loading, error scanning, UTF-8 paths, and deterministic I/O lock handling", "[ini][io]") {
    TempDirFixture temp;

    SECTION("load_file handles .ini, empty .ini fallback, .txt, and error conditions") {
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
