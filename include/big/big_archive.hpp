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
#include <unordered_map>
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
            ProgressCallback progress_callback = {},
            std::string_view filter_pattern = {},
            bool create_directories = true
        ) const;

        // Reads a single archive entry into memory by its internal path
        [[nodiscard]] std::vector<uint8_t> read_entry(std::string_view entry_name) const;

        // Reads a single archive entry into memory using its metadata record
        [[nodiscard]] std::vector<uint8_t> read_entry(const BigEntry& entry) const;

        // Streams an entry's payload in chunks to the provided callback
        void stream_entry(std::string_view entry_name, ChunkCallback chunk_cb) const;

        // Streams an entry's payload in chunks to the provided callback using its metadata record
        void stream_entry(const BigEntry& entry, ChunkCallback chunk_cb) const;

        // Validates that the cumulative size of matching entries does not exceed the amplification ratio
        uintmax_t validate_extraction_quota(std::string_view filter_pattern = {}) const;

        // Returns the underlying archive file path
        [[nodiscard]] const std::filesystem::path& file_path() const noexcept;

        // Releases the in-memory index and marks the archive as closed
        void close() noexcept;

        [[nodiscard]] bool is_closed() const noexcept;

        [[nodiscard]] std::vector<BigEntry> get_entries(std::string_view filter_pattern = {}) const;

    private:
        std::filesystem::path file_path_;
        std::vector<BigEntry> entries_;
        std::unordered_map<std::string, std::size_t> index_map_;
        uintmax_t physical_size_{ 0 };
        uint32_t total_size_{ 0 };
        uint32_t header_size_{ 0 };
        bool is_closed_{ false };
    };

} // namespace lotm::big

template <>
struct std::hash<lotm::big::BigEntry> {
    std::size_t operator()(const lotm::big::BigEntry& e) const noexcept {
        std::size_t h1 = std::hash<uint32_t>{}(e.offset);
        std::size_t h2 = std::hash<uint32_t>{}(e.size);
        std::size_t h3 = std::hash<std::string>{}(e.name);
        return h1 ^ (h2 << 1) ^ (h3 << 2);
    }
};

template <>
struct std::hash<lotm::big::BigOverlayEntry> {
    std::size_t operator()(const lotm::big::BigOverlayEntry& e) const noexcept {
        std::size_t h1 = std::hash<lotm::big::BigEntry>{}(e.entry);
        std::size_t h2 = std::filesystem::hash_value(e.source_archive);
        std::size_t h3 = std::hash<uint32_t>{}(e.override_count);
        return h1 ^ (h2 << 1) ^ (h3 << 2);
    }
};
