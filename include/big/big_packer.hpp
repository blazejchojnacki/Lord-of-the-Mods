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
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
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

        struct ArchiveLayout {
            uint32_t num_files{ 0 };
            uint32_t header_size{ 0 };
            uint32_t total_size{ 0 };
        };

        // Sorts alphabetically and validates case-insensitive uniqueness
        void sort_and_validate_entries(std::vector<PackSourceRecord>& entries);

        // Scans a directory recursively for regular files and validates 32-bit single-file size limits
        void collect_directory_files(
            const std::filesystem::path& source_dir,
            std::vector<PackSourceRecord>& file_list,
            uintmax_t& total_payload_size
        );

        // Sorts entries, validates 32-bit archive bounds, and assigns final byte offsets
        [[nodiscard]] ArchiveLayout finalize_archive_layout(
            std::vector<PackSourceRecord>& file_list,
            uintmax_t total_payload_size,
            std::vector<std::size_t>* out_original_indices = nullptr
        );

        // Allocates a buffer of layout.total_size and serializes the BIG4 header and index table
        [[nodiscard]] uint8_t* allocate_and_write_header(
            const std::vector<PackSourceRecord>& file_list,
            const ArchiveLayout& layout,
            const BufferAllocator& allocator
        );

        // Validates that output_file is not a directory and its parent directory exists
        void validate_output_file_target(const std::filesystem::path& output_file);

        // Probes whether an existing output file is writable before expensive work begins
        void probe_output_file_writable(const std::filesystem::path& output_file);

        // RAII helper managing atomic .lotm_tmp sibling file serialization and rename commit
        class AtomicArchiveWriter {
        public:
            explicit AtomicArchiveWriter(const std::filesystem::path& output_file);
            ~AtomicArchiveWriter() noexcept;

            AtomicArchiveWriter(const AtomicArchiveWriter&) = delete;
            AtomicArchiveWriter& operator=(const AtomicArchiveWriter&) = delete;

            void write_header(
                const std::vector<PackSourceRecord>& file_list,
                const ArchiveLayout& layout
            );

            void write_chunk(const char* data, std::streamsize size, std::string_view write_error_prefix);

            void commit(std::string_view write_error_prefix);

        private:
            std::filesystem::path output_file_;
            std::filesystem::path temp_file_;
            std::ofstream out_;
            bool committed_{ false };
        };
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

        static void pack_to_memory(
            const std::filesystem::path& source_dir,
            const BufferAllocator& allocator,
            ProgressCallback progress_callback = {}
        );

        [[nodiscard]] static std::vector<uint8_t> pack_to_memory(
            std::span<const std::pair<std::string, std::span<const uint8_t>>> files,
            ProgressCallback progress_callback = {}
        );

        static void pack_to_memory(
            std::span<const std::pair<std::string, std::span<const uint8_t>>> files,
            const BufferAllocator& allocator,
            ProgressCallback progress_callback = {}
        );

        [[nodiscard]] static std::vector<uint8_t> pack_to_memory(
            const std::vector<std::pair<std::string, std::vector<uint8_t>>>& files,
            ProgressCallback progress_callback = {}
        );
    };

} // namespace lotm::big
