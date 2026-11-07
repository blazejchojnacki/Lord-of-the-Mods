/**
 * @file include/big/types.hpp
 * @brief constants and structs for BIG features
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <string_view>

namespace lotm::big {

    inline constexpr std::string_view BIG4_MAGIC = "BIG4";
    inline constexpr uint32_t HEADER_BASE_SIZE = 16;
    inline constexpr uint32_t EA_PADDING_SIZE = 8;
    inline constexpr std::string_view EA_PADDING_TAG{ "L219\0\0\0\0", 8 };

    struct BigEntry {
        uint32_t offset{ 0 };
        uint32_t size{ 0 };
        std::string name;
    };

    struct ProgressReport {
        std::string_view entry_name;
        uint64_t bytes_transferred{ 0 };
        uint64_t file_size{ 0 };
        uint64_t total_bytes_transferred{ 0 };
        uint64_t total_archive_size{ 0 };
    };

    using ProgressCallback = std::function<bool(const ProgressReport&)>;

} // namespace lotm::big
