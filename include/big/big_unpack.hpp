/**
 * @file include/big/big_unpack.hpp
 * @brief Declaration of BIG unpacking object
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
