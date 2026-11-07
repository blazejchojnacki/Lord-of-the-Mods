/**
 * @file include/big/big_diff.hpp
 * @brief Declaration of BIG archive comparison engine
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <big/big_archive.hpp>
#include <big/types.hpp>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <string_view>
#include <vector>

namespace lotm::big {

    struct BigDiffResult {
        std::vector<BigEntry> added;
        std::vector<BigEntry> removed;
        std::vector<BigEntry> modified;
        std::vector<BigEntry> unchanged;

        [[nodiscard]] bool has_differences() const noexcept {
            return !added.empty() || !removed.empty() || !modified.empty();
        }
    };

    class BigDiff {
    public:
        // Compares two open BigArchive instances
        [[nodiscard]] static BigDiffResult compare(
            const BigArchive& base_archive,
            const BigArchive& target_archive,
            std::string_view filter_pattern = {}
        );

        // Opens and compares two BIG4 archive files from disk
        [[nodiscard]] static BigDiffResult compare(
            const std::filesystem::path& base_path,
            const std::filesystem::path& target_path,
            std::string_view filter_pattern = {}
        );

        // Packs only added and modified entries from target_archive into an in-memory BIG4 buffer
        [[nodiscard]] static std::vector<uint8_t> create_patch_to_memory(
            const BigArchive& base_archive,
            const BigArchive& target_archive,
            std::string_view filter_pattern = {},
            ProgressCallback progress_callback = {}
        );

        // Opens two BIG4 archives from disk and packs only added and modified entries into memory
        [[nodiscard]] static std::vector<uint8_t> create_patch_to_memory(
            const std::filesystem::path& base_path,
            const std::filesystem::path& target_path,
            std::string_view filter_pattern = {},
            ProgressCallback progress_callback = {}
        );

        // Packs only added and modified entries from target_archive into a standalone patch archive on disk
        static void create_patch(
            const BigArchive& base_archive,
            const BigArchive& target_archive,
            const std::filesystem::path& output_file,
            std::string_view filter_pattern = {},
            ProgressCallback progress_callback = {}
        );

        // Opens two BIG4 archives from disk and writes a standalone delta patch archive to output_file
        static void create_patch(
            const std::filesystem::path& base_path,
            const std::filesystem::path& target_path,
            const std::filesystem::path& output_file,
            std::string_view filter_pattern = {},
            ProgressCallback progress_callback = {}
        );
    };

} // namespace lotm::big
