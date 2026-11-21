/**
 * @file tests/cpp/ini/test_memory.cpp
 * @brief Unit tests for lotm::ini::StableVector memory safety and iterator stability.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include "ini/ast.hpp"

using namespace lotm::ini;

TEST_CASE("StableVector preserves element addresses across reallocations and replacements", "[ini][memory_safety]") {
    ConstructLevel block{ "Object", "GondorHero" };
    block.append(StatementNode{ "Health = 1000", "; initial" });

    const StatementNode* initial_ptr = &std::get<StatementNode>(block[0]);

    // Trigger multiple internal vector reallocations
    for (int i = 0; i < 512; ++i) {
        block.append(StatementNode{ "ExtraProp = " + std::to_string(i), "" });
    }

    // Address of element 0 must remain identical after reallocations
    CHECK(&std::get<StatementNode>(block[0]) == initial_ptr);
    CHECK(initial_ptr->text == "Health = 1000");

    // Replacing index 0 retires the old element without freeing its address while block lives
    block.items.replace_at(0, CommentNode{ "; replaced index 0" });
    CHECK(std::holds_alternative<CommentNode>(block[0]));
    CHECK(initial_ptr->text == "Health = 1000");

    // Random-access iterator arithmetic and reverse iteration
    const auto it_begin = block.begin();
    const auto it_end = block.end();
    CHECK((it_end - it_begin) == 513);
    CHECK(&(it_begin[0]) == &block[0]);
    CHECK(*((it_begin + 2) - 1) == block[1]);
    CHECK(*(1 + it_begin) == block[1]);
    CHECK(it_begin < it_end);
}
