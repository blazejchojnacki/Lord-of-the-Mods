/**
 * @file include/big/types.hpp
 * @brief constants and structs for BIG features
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

#include <cstdint>
#include <string>
#include <string_view>

namespace lotm::big {

    inline constexpr std::string_view BIG4_MAGIC = "BIG4";
    inline constexpr uint32_t HEADER_BASE_SIZE = 16;
    inline constexpr uint32_t EA_PADDING_SIZE = 8;
    inline constexpr std::string_view EA_PADDING_TAG = "L219    ";

    struct BigEntry {
        uint32_t offset{ 0 };
        uint32_t size{ 0 };
        std::string name;
    };

} // namespace lotm::big
