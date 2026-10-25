/**
 * @file include/core/endian.hpp
 * @brief helper function templates to switch between Endian types
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <bit>
#include <concepts>
#include <cstdint>

namespace lotm::core {

    template <std::integral T>
    [[nodiscard]] constexpr T byteswap(T value) noexcept {
        if constexpr (sizeof(T) == 1) {
            return value;
        }
        else if constexpr (sizeof(T) == 2) {
            auto unsigned_val = static_cast<uint16_t>(value);
            return static_cast<T>((unsigned_val << 8) | (unsigned_val >> 8));
        }
        else if constexpr (sizeof(T) == 4) {
            auto unsigned_val = static_cast<uint32_t>(value);
            return static_cast<T>(
                ((unsigned_val & 0x000000FFu) << 24) |
                ((unsigned_val & 0x0000FF00u) << 8) |
                ((unsigned_val & 0x00FF0000u) >> 8) |
                ((unsigned_val & 0xFF000000u) >> 24)
                );
        }
        else if constexpr (sizeof(T) == 8) {
            auto unsigned_val = static_cast<uint64_t>(value);
            return static_cast<T>(
                ((unsigned_val & 0x00000000000000FFull) << 56) |
                ((unsigned_val & 0x000000000000FF00ull) << 40) |
                ((unsigned_val & 0x0000000000FF0000ull) << 24) |
                ((unsigned_val & 0x00000000FF000000ull) << 8) |
                ((unsigned_val & 0x000000FF00000000ull) >> 8) |
                ((unsigned_val & 0x0000FF0000000000ull) >> 24) |
                ((unsigned_val & 0x00FF000000000000ull) >> 40) |
                ((unsigned_val & 0xFF00000000000000ull) >> 56)
                );
        }
    }

    template <std::integral T>
    [[nodiscard]] constexpr T from_big_endian(T value) noexcept {
        if constexpr (std::endian::native == std::endian::little) {
            return byteswap(value);
        }
        else {
            return value;
        }
    }

    template <std::integral T>
    [[nodiscard]] constexpr T to_big_endian(T value) noexcept {
        return from_big_endian(value);
    }

} // namespace lotm::core
