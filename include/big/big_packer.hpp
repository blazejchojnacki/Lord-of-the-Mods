/**
 * @file include/big/big_packer.hpp
 * @brief Declaration of BIG packing object
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <big/types.hpp>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace lotm::big {

    namespace detail {
        struct PackSourceRecord {
            std::filesystem::path full_path;
            std::string rel_path;
            uint32_t size{ 0 };
            uint32_t offset{ 0 };
        };

        // Sorts alphabetically and validates case-insensitive uniqueness
        void sort_and_validate_entries(std::vector<PackSourceRecord>& entries);
    }

    class BigPacker {
    public:
        static void pack_from_directory(
            const std::filesystem::path& source_dir,
            const std::filesystem::path& output_file,
            ProgressCallback progress_callback = {}
        );

        [[nodiscard]] static std::vector<uint8_t> pack_to_memory(
            const std::filesystem::path& source_dir,
            ProgressCallback progress_callback = {}
        );

        [[nodiscard]] static std::vector<uint8_t> pack_to_memory(
            std::span<const std::pair<std::string, std::span<const uint8_t>>> files,
            ProgressCallback progress_callback = {}
        );

        [[nodiscard]] static std::vector<uint8_t> pack_to_memory(
            const std::vector<std::pair<std::string, std::vector<uint8_t>>>& files,
            ProgressCallback progress_callback = {}
        );
    };

} // namespace lotm::big
