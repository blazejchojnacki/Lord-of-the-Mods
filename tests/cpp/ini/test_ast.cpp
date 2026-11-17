/**
 * @file tests/cpp/ini/test_ast.cpp
 * @brief Unit tests for AST types, node operations, and conversions in lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include "ini/ast.hpp"
#include "ini/parser.hpp"
#include <stdexcept>

using namespace lotm::ini;

TEST_CASE("AST types, node operations, and SerializableNodeRef conversions", "[ini][types]") {
    SECTION("is_ini_end recognizes exact SAGE closing tokens") {
        STATIC_REQUIRE(is_ini_end("End"));
        STATIC_REQUIRE(is_ini_end("END"));
        STATIC_REQUIRE(is_ini_end("end"));
        STATIC_REQUIRE(is_ini_end("EnD"));
        STATIC_REQUIRE(is_ini_end("eNd"));
        STATIC_REQUIRE_FALSE(is_ini_end("Enx"));
        STATIC_REQUIRE_FALSE(is_ini_end("EndScript"));
        STATIC_REQUIRE_FALSE(is_ini_end(""));
    }

    SECTION("CommentNode, StatementNode, and DefineNode equality") {
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

        const DefineNode d1{ "#define MACRO 10", "; def cmt" };
        const DefineNode d2{ "#define MACRO 10", "; def cmt" };
        const DefineNode d3{ "#define MACRO 20", "; def cmt" };
        CHECK(d1 == d2);
        CHECK_FALSE(d1 == d3);
    }

    SECTION("IncludeNode::clean_path normalizes slashes and strips quotes/whitespace") {
        const IncludeNode empty_inc{ "   	 \"\" '' 	 " };
        CHECK(empty_inc.clean_path().empty());

        const IncludeNode win_inc{ " 	 \"..\\data\\ini\\includes\\weapon.inc\"  " };
        CHECK(win_inc.clean_path() == "../data/ini/includes/weapon.inc");

        const IncludeNode single_quote_inc{ "'sub\\path\\macros.inc'" };
        CHECK(single_quote_inc.clean_path() == "sub/path/macros.inc");

        CHECK(win_inc == IncludeNode{ " 	 \"..\\data\\ini\\includes\\weapon.inc\"  " });
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
        const AstNode ast_def = DefineNode{ "#define K 1" };
        const AstNode ast_scr = ScriptNode{};
        const AstNode ast_lvl = ConstructLevel{ "Object", "Test" };

        CHECK(std::holds_alternative<const CommentNode*>(to_serializable_ref(ast_cmt)));
        CHECK(std::holds_alternative<const StatementNode*>(to_serializable_ref(ast_stmt)));
        CHECK(std::holds_alternative<const IncludeNode*>(to_serializable_ref(ast_inc)));
        CHECK(std::holds_alternative<const DefineNode*>(to_serializable_ref(ast_def)));
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
        CHECK(std::holds_alternative<const StatementNode*>(to_serializable_ref(root_ast)));
        CHECK(std::holds_alternative<const StrEntry*>(to_serializable_ref(root_str)));
    }
}

TEST_CASE("ConstructLevel and ConstructFile AST query, mutation, and key/value validation", "[ini][ast][query]") {
    const std::string sample_ini =
        "TopKey = InitialTop\n"
        "TopKey = OverriddenTop\n"
        "Object GondorHero\n"
        "    Side = Men\n"
        "    Side = Gondor\n"
        "    EmptyEq =\n"
        "    SpaceSep   100\n"
        "    BareKey\n"
        "    Draw = W3DScriptedModelDraw ModuleTag_Draw01\n"
        "        DefaultModelConditionState\n"
        "            Model = GUHero_SKN\n"
        "        End\n"
        "    End\n"
        "    Behavior = AIUpdateInterface ModuleTag_AI\n"
        "        AutoAcquireEnemiesWhenIdle = YES\n"
        "    End\n"
        "End\n";

    ConstructFile doc{ "query_test.ini", true, sample_ini };

    SECTION("find_block and find_all support direct, recursive, and const queries") {
        const ConstructFile& const_doc = doc;
        REQUIRE(const_doc.find_block("Object", "GondorHero") != nullptr);
        CHECK(const_doc.find_block("Object", "MissingHero") == nullptr);
        CHECK(const_doc.find_block("DefaultModelConditionState", std::nullopt, std::nullopt, false) == nullptr);

        const ConstructLevel* nested_state = const_doc.find_block(
            "DefaultModelConditionState", std::nullopt, std::nullopt, true
        );
        REQUIRE(nested_state != nullptr);
        CHECK(nested_state->get_value("Model") == "GUHero_SKN");

        ConstructLevel* hero = doc.find_block("Object", "GondorHero");
        REQUIRE(hero != nullptr);
        const ConstructLevel& const_hero = *hero;

        CHECK(const_hero.find_block("Draw", "W3DScriptedModelDraw", "ModuleTag_Draw01") != nullptr);
        CHECK(const_hero.find_block("Draw =", "W3DScriptedModelDraw", "ModuleTag_Draw01") != nullptr);
        CHECK(const_hero.find_block("Draw", "W3DScriptedModelDraw", "WrongTag") == nullptr);

        CHECK(const_doc.find_all("Behavior", std::nullopt, std::nullopt, true).size() == 1);
        CHECK(const_hero.find_all("Behavior").size() == 1);
        CHECK(const_hero.find_all("DefaultModelConditionState", std::nullopt, std::nullopt, true).size() == 1);

        CHECK(hero->remove_block("Behavior", "AIUpdateInterface", "ModuleTag_AI"));
        CHECK_FALSE(hero->remove_block("Behavior", "AIUpdateInterface", "ModuleTag_AI"));
        CHECK(doc.remove_block("Object", "GondorHero"));
        CHECK_FALSE(doc.remove_block("Object", "GondorHero"));
    }

    SECTION("get_value, get_all_values, set_value, and remove_value preserve formatting and handle edge cases") {
        CHECK(doc.get_value("TopKey") == "OverriddenTop");
        CHECK(doc.get_value("   ").has_value() == false);
        CHECK(doc.get_all_values("TopKey") == std::vector<std::string>{ "InitialTop", "OverriddenTop" });
        CHECK(doc.get_all_values("").empty());

        doc.set_value("TopKey", "FinalTop");
        CHECK(doc.get_value("TopKey") == "FinalTop");
        doc.set_value("NewTopEmpty", "");
        CHECK(doc.get_value("NewTopEmpty") == "");
        doc.set_value("NewTopVal", "42");
        CHECK(doc.get_value("NewTopVal") == "42");

        CHECK(doc.remove_value("TopKey", false));
        CHECK(doc.get_value("TopKey") == "InitialTop");
        CHECK(doc.remove_value("TopKey", true));
        CHECK_FALSE(doc.get_value("TopKey").has_value());
        CHECK_FALSE(doc.remove_value(""));

        ConstructLevel* hero = doc.find_block("Object", "GondorHero");
        REQUIRE(hero != nullptr);
        CHECK(hero->get_value("Side") == "Gondor");
        CHECK(hero->get_value("") == std::nullopt);
        CHECK(hero->get_all_values("Side") == std::vector<std::string>{ "Men", "Gondor" });
        CHECK(hero->get_all_values("").empty());

        hero->set_value("EmptyEq", "Filled");
        CHECK(hero->get_value("EmptyEq") == "Filled");
        hero->set_value("SpaceSep", "200");
        CHECK(hero->get_value("SpaceSep") == "200");
        hero->set_value("BareKey", "300");
        CHECK(hero->get_value("BareKey") == "300");
        hero->set_value("AppendedEmpty", "");
        CHECK(hero->get_value("AppendedEmpty") == "");

        CHECK(hero->remove_value("Side", true));
        CHECK(hero->get_all_values("Side").empty());
        CHECK_FALSE(hero->remove_value("   "));
    }

    SECTION("set_value validates keys and values against separators, newlines, and 32-bit SAGE bounds") {
        ConstructLevel* hero = doc.find_block("Object", "GondorHero");
        REQUIRE(hero != nullptr);

        CHECK_THROWS_AS(hero->set_value("", "10"), std::invalid_argument);
        CHECK_THROWS_AS(hero->set_value("   ", "10"), std::invalid_argument);
        CHECK_THROWS_AS(hero->set_value("Bad Key", "10"), std::invalid_argument);
        CHECK_THROWS_AS(hero->set_value("Bad=Key", "10"), std::invalid_argument);
        CHECK_THROWS_AS(hero->set_value("Bad:Key", "10"), std::invalid_argument);
        CHECK_THROWS_AS(hero->set_value("ValidKey", "Line1\nLine2"), std::invalid_argument);
        CHECK_THROWS_AS(hero->set_value("ValidKey", "Line1\rLine2"), std::invalid_argument);

        const std::string overlong_key(SAGE_MAX_BLOCK_NAME_LEN + 1, 'K');
        const std::string overlong_val(SAGE_MAX_IDENTIFIER_LEN + 1, 'V');
        CHECK_THROWS_AS(hero->set_value(overlong_key, "10"), IniParseError);
        CHECK_THROWS_AS(hero->set_value("ValidKey", overlong_val), IniParseError);
        CHECK_THROWS_AS(doc.set_value(overlong_key, "10"), IniParseError);
        CHECK_THROWS_AS(doc.set_value("ValidKey", overlong_val), IniParseError);
    }
}
