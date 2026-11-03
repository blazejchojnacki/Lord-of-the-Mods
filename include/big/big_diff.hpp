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
#include <filesystem>
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
    };

} // namespace lotm::big
