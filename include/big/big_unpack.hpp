/**
 * @file include/big/big_unpack.hpp
 * @brief Declaration of BIG unpacking object
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <big/types.hpp>
#include <filesystem>
#include <string>
#include <vector>
#include <cstdint>

namespace lotm::big {

    class BigArchive {
    public:
        explicit BigArchive(std::filesystem::path file_path);

        // Parses the header and file index
        void read_header();

        // Extracts all files to the output directory (equivalent to read_big4)
        void extract_all(const std::filesystem::path& output_dir);

        [[nodiscard]] const std::vector<BigEntry>& get_entries() const noexcept { return entries_; }

    private:
        std::filesystem::path file_path_;
        std::vector<BigEntry> entries_;
        uint32_t total_size_{ 0 };
        uint32_t header_size_{ 0 };
    };

} // namespace lotm::big
