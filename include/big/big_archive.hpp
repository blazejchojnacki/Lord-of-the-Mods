/**
 * @file include/big/big_archive.hpp
 * @brief Declaration of BIG unpacking object
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <big/types.hpp>
#include <filesystem>
#include <functional>
#include <string>
#include <string_view>
#include <vector>
#include <cstdint>

namespace lotm::big {

    class BigArchive {
    public:
        // Parses the header and file index immediately upon construction
        explicit BigArchive(std::filesystem::path file_path);

        // Extracts all files to the output directory
        void extract_all(
            const std::filesystem::path& output_dir,
            std::function<void(std::string_view)> progress_callback = {},
            std::string_view filter_pattern = {}
        ) const;

        // Reads a single archive entry into memory by its internal path
        [[nodiscard]] std::vector<uint8_t> read_entry(std::string_view entry_name) const;

        // Reads a single archive entry into memory using its metadata record
        [[nodiscard]] std::vector<uint8_t> read_entry(const BigEntry& entry) const;

        // Releases the in-memory index and marks the archive as closed
        void close() noexcept;

        [[nodiscard]] bool is_closed() const noexcept;

        [[nodiscard]] std::vector<BigEntry> get_entries(std::string_view filter_pattern = {}) const;

    private:
        std::filesystem::path file_path_;
        std::vector<BigEntry> entries_;
        uint32_t total_size_{ 0 };
        uint32_t header_size_{ 0 };
        bool is_closed_{ false };
    };

} // namespace lotm::big
