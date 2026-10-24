/**
 * @file tests/cpp/core/test_endian.cpp
 * @brief Unit tests for lotm::core endianness utilities.
 *
 * Copyright (C) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include <core/endian.hpp>
#include <concepts>
#include <cstdint>
#include <limits>

using namespace lotm::core;

TEST_CASE("Compile-time constexpr evaluation", "[endian][constexpr]") {
    SECTION("Positive scenario: Constants evaluated at compile time") {
        STATIC_REQUIRE(byteswap<uint16_t>(0x1234) == 0x3412);
        STATIC_REQUIRE(byteswap<uint32_t>(0x12345678) == 0x78563412);
        STATIC_REQUIRE(byteswap<uint64_t>(0x1122334455667788ULL) == 0x8877665544332211ULL);
    }
}

TEST_CASE("Endianness byte swapping handles all standard widths", "[endian][byteswap]") {

    SECTION("Positive scenario: 8-bit width remains unchanged (no-op)") {
        REQUIRE(byteswap<uint8_t>(0xAB) == 0xAB);
        REQUIRE(byteswap<int8_t>(-1) == -1);
    }

    SECTION("Positive scenario: 16-bit width swaps properly") {
        REQUIRE(byteswap<uint16_t>(0xAABB) == 0xBBAA);
        REQUIRE(byteswap<uint16_t>(0x00FF) == 0xFF00);

        // Negative / Edge cases: Boundaries
        REQUIRE(byteswap<uint16_t>(0) == 0);
        REQUIRE(byteswap<uint16_t>(std::numeric_limits<uint16_t>::max()) == 0xFFFF);
    }

    SECTION("Positive scenario: 32-bit width swaps properly") {
        REQUIRE(byteswap<uint32_t>(0xDEADBEEF) == 0xEFBEADDE);
        REQUIRE(byteswap<uint32_t>(0x000000FF) == 0xFF000000);

        // Negative / Edge cases: Boundaries
        REQUIRE(byteswap<uint32_t>(0) == 0);
        REQUIRE(byteswap<uint32_t>(std::numeric_limits<uint32_t>::max()) == 0xFFFFFFFF);
    }

    SECTION("Positive scenario: 64-bit width swaps properly") {
        REQUIRE(byteswap<uint64_t>(0x0102030405060708ULL) == 0x0807060504030201ULL);
        REQUIRE(byteswap<uint64_t>(0x00000000000000FFULL) == 0xFF00000000000000ULL);

        // Negative / Edge cases: Boundaries
        REQUIRE(byteswap<uint64_t>(0) == 0);
        REQUIRE(byteswap<uint64_t>(std::numeric_limits<uint64_t>::max()) == 0xFFFFFFFFFFFFFFFFULL);
    }
}

TEST_CASE("Endianness operations handle signed integers safely", "[endian][signed]") {
    SECTION("Negative scenario: Negative signed values maintain bit representation without corruption") {
        // -2 in 16-bit is 0xFFFE. Swapped: 0xFEFF
        REQUIRE(byteswap<int16_t>(-2) == static_cast<int16_t>(0xFEFF));

        // -2 in 32-bit is 0xFFFFFFFE. Swapped: 0xFEFFFFFF
        REQUIRE(byteswap<int32_t>(-2) == static_cast<int32_t>(0xFEFFFFFF));
    }

    SECTION("Positive scenario: Positive signed values are preserved correctly") {
        REQUIRE(byteswap<int32_t>(0x12345678) == static_cast<int32_t>(0x78563412));
    }
}

TEST_CASE("Endianness idempotency and byte invariants", "[endian][identity]") {
    SECTION("Positive scenario: Double swap restores the original value") {
        uint16_t v16 = 0x1234;
        uint32_t v32 = 0xDEADBEEF;
        uint64_t v64 = 0x0123456789ABCDEFULL;

        REQUIRE(byteswap(byteswap(v16)) == v16);
        REQUIRE(byteswap(byteswap(v32)) == v32);
        REQUIRE(byteswap(byteswap(v64)) == v64);
    }

    SECTION("Positive scenario: Single-byte char types behave as identity") {
        REQUIRE(byteswap('A') == 'A');
        REQUIRE(byteswap(static_cast<unsigned char>(255)) == 255);
    }
}

TEST_CASE("System endianness routing to_big_endian and from_big_endian", "[endian][routing]") {
    uint16_t v16 = 0x1234;
    uint32_t v32 = 0xAABBCCDD;
    uint64_t v64 = 0x0102030405060708ULL;

    if constexpr (std::endian::native == std::endian::little) {
        SECTION("Positive scenario: Little Endian host swaps the bytes") {
            REQUIRE(to_big_endian(v16) == 0x3412);
            REQUIRE(from_big_endian(v16) == 0x3412);
            REQUIRE(to_big_endian(v32) == 0xDDCCBBAA);
            REQUIRE(from_big_endian(v32) == 0xDDCCBBAA);
            REQUIRE(to_big_endian(v64) == 0x0807060504030201ULL);
            REQUIRE(from_big_endian(v64) == 0x0807060504030201ULL);
        }
    }
    else {
        SECTION("Positive scenario: Big Endian host acts as a no-op") {
            REQUIRE(to_big_endian(v16) == 0x1234);
            REQUIRE(from_big_endian(v16) == 0x1234);
            REQUIRE(to_big_endian(v32) == 0xAABBCCDD);
            REQUIRE(from_big_endian(v32) == 0xAABBCCDD);
            REQUIRE(to_big_endian(v64) == 0x0102030405060708ULL);
            REQUIRE(from_big_endian(v64) == 0x0102030405060708ULL);
        }
    }
}

TEST_CASE("Concept constraint verification", "[endian][concept]") {
    SECTION("Positive scenario: Integrals satisfy function template constraints") {
        STATIC_REQUIRE(requires(uint8_t v) { byteswap(v); });
        STATIC_REQUIRE(requires(uint16_t v) { byteswap(v); });
        STATIC_REQUIRE(requires(uint32_t v) { byteswap(v); });
        STATIC_REQUIRE(requires(uint64_t v) { byteswap(v); });
        STATIC_REQUIRE(requires(int32_t v) { from_big_endian(v); });
        STATIC_REQUIRE(requires(uint32_t v) { to_big_endian(v); });
    }

    SECTION("Negative scenario: Non-integral types do not satisfy std::integral") {
        STATIC_REQUIRE_FALSE(std::integral<float>);
        STATIC_REQUIRE_FALSE(std::integral<double>);
        STATIC_REQUIRE_FALSE(std::integral<const char*>);
        STATIC_REQUIRE_FALSE(std::integral<std::nullptr_t>);
    }
}
