/**
 * @file include/big/big_overlay.hpp
 * @brief Declaration of SAGE load-order archive overlay engine
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <big/big_archive.hpp>
#include <big/types.hpp>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <compare>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

namespace lotm::big {

    struct BigOverlayEntry {
        BigEntry entry;
        std::filesystem::path source_archive;
        uint32_t override_count{ 0 };

        bool operator==(const BigOverlayEntry&) const = default;
        auto operator<=>(const BigOverlayEntry&) const = default;
    };

    class BigOverlay {

        // Scans a directory for .big files, sorts them in SAGE alphabetical order, and mounts them
        [[nodiscard]] static BigOverlay from_directory(const std::filesystem::path& dir_path);

        // Mounts an explicit sequence of .big archive files in the provided order
        [[nodiscard]] static BigOverlay from_archives(const std::vector<std::filesystem::path>& archive_paths);

        // Mounts a single .big archive on top of the current overlay state
        void mount(const std::filesystem::path& archive_path);

        // Returns the list of mounted archive paths in load order
        [[nodiscard]] std::vector<std::filesystem::path> get_mounted_archives() const;

        // Returns all effective entries in the overlay (optionally filtered by a glob pattern)
        [[nodiscard]] std::vector<BigOverlayEntry> get_entries(std::string_view filter_pattern = {}) const;

        // Resolves the winning entry and source archive for a specific internal file path
        [[nodiscard]] BigOverlayEntry resolve(std::string_view entry_name) const;

        // Reads the effective winning entry payload directly into memory
        [[nodiscard]] std::vector<uint8_t> read_entry(std::string_view entry_name) const;

        // Streams the effective winning entry payload in chunks to the provided callback
        void stream_entry(std::string_view entry_name, ChunkCallback chunk_cb) const;

        // Releases the in-memory index and marks the overlay as closed
        void close() noexcept;

        [[nodiscard]] bool is_closed() const noexcept;

    private:
        bool is_closed_{ false };

        struct OverlayRecord {
            BigEntry entry;
            std::size_t archive_index{ 0 };
            uint32_t override_count{ 0 };
        };

        std::vector<std::pair<std::filesystem::path, BigArchive>> archives_;
        std::unordered_map<std::string, OverlayRecord> index_map_;
    };

} // namespace lotm::big
