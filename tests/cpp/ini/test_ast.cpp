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
        CHECK(std::holds_alternative<const StrEntry*>(to_serializable_ref(root_str)));
    }
}
