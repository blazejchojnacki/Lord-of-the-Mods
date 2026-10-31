/**
 * @file src/big/big_packer.cpp
 * @brief Implementation of BIG packing object
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <big/big_packer.hpp>
#include <big/exceptions.hpp>
#include <big/types.hpp>
#include <core/endian.hpp>
#include <fstream>
#include <functional>
#include <stdexcept>
#include <vector>
#include <string>
#include <string_view>
#include <algorithm>
#include <limits>

namespace lotm::big {

    void BigPacker::pack_from_directory(const std::filesystem::path& source_dir, const std::filesystem::path& output_file, std::function<void(std::string_view)> progress_callback) {
        if (!std::filesystem::exists(source_dir) || !std::filesystem::is_directory(source_dir)) {
            throw std::invalid_argument("Source directory does not exist or is not a directory.");
        }

        if (std::filesystem::is_directory(output_file)) {
            throw std::invalid_argument("Target output path cannot be a directory: " + output_file.string());
        }

        if (auto parent = output_file.parent_path(); !parent.empty() && !std::filesystem::exists(parent)) {
            throw std::invalid_argument("Target output directory does not exist: " + parent.string());
        }

        // Guard against output_file residing inside source_dir (self-inclusion)
        const std::filesystem::path canonical_source = std::filesystem::weakly_canonical(source_dir);
        const std::filesystem::path canonical_output = std::filesystem::weakly_canonical(output_file);
        auto mismatch_pair = std::mismatch(
            canonical_source.begin(), canonical_source.end(),
            canonical_output.begin(), canonical_output.end());
        if (mismatch_pair.first == canonical_source.end()) {
            throw std::invalid_argument(
                "Target output archive cannot reside inside the source directory: " + output_file.string());
        }

        struct PackEntry {
            std::filesystem::path full_path;
            std::string rel_path;
            uint32_t size{ 0 };
            uint32_t offset{ 0 };
        };

        std::vector<PackEntry> file_list;
        uintmax_t total_payload_size = 0;

        for (const auto& entry : std::filesystem::recursive_directory_iterator(source_dir)) {
            if (entry.is_regular_file()) {
                PackEntry pack_entry;
                pack_entry.full_path = entry.path();

                auto rel_path = std::filesystem::relative(entry.path(), source_dir);
                pack_entry.rel_path = rel_path.string();
                for (char& c : pack_entry.rel_path) {
                    if (c == '/') c = '\\';
                }

                uintmax_t fsize = std::filesystem::file_size(entry.path());

                // Guard against individual files exceeding 32-bit limits
                if (fsize > std::numeric_limits<uint32_t>::max()) {
                    throw std::length_error("File '" + pack_entry.rel_path + "' exceeds the 4GB format limit.");
                }

                pack_entry.size = static_cast<uint32_t>(fsize);
                total_payload_size += fsize;
                file_list.push_back(std::move(pack_entry));
            }
        }

        // CRITICAL FIX: Sort the index alphabetically.
        // SAGE engine uses bsearch on the archive index. An unsorted BIG file will crash the game.
        std::sort(file_list.begin(), file_list.end(), [](const PackEntry& a, const PackEntry& b) {
            return a.rel_path < b.rel_path;
            });

        uint32_t num_files = static_cast<uint32_t>(file_list.size());
        uintmax_t header_size_calc = HEADER_BASE_SIZE;
        for (const auto& f : file_list) {
            header_size_calc += 4 + 4 + f.rel_path.length() + 1;
        }

        // + 8 for byte-for-byte alignment with the EA "L219" gap
        header_size_calc += EA_PADDING_SIZE;

        // Guard against total archive size exceeding 32-bit limits (4GB overflow)
        if (header_size_calc + total_payload_size > std::numeric_limits<uint32_t>::max()) {
            throw std::length_error("Total archive size exceeds the 32-bit (4GB) BIG4 format limit.");
        }

        uint32_t header_size = static_cast<uint32_t>(header_size_calc);
        uint32_t current_offset = header_size;
        for (auto& f : file_list) {
            f.offset = current_offset;
            current_offset += f.size;
        }

        uint32_t total_size = current_offset;

        std::ofstream out(output_file, std::ios::binary);
        if (!out.is_open()) {
            throw BigArchiveError("Cannot create output file: " + output_file.string());
        }

        out.write(BIG4_MAGIC.data(), 4);
        out.write(reinterpret_cast<const char*>(&total_size), sizeof(total_size));

        uint32_t be_num_files = lotm::core::to_big_endian(num_files);
        out.write(reinterpret_cast<const char*>(&be_num_files), sizeof(be_num_files));

        uint32_t be_header_size = lotm::core::to_big_endian(header_size);
        out.write(reinterpret_cast<const char*>(&be_header_size), sizeof(be_header_size));

        for (const auto& f : file_list) {
            uint32_t be_offset = lotm::core::to_big_endian(f.offset);
            out.write(reinterpret_cast<const char*>(&be_offset), sizeof(be_offset));

            uint32_t be_size = lotm::core::to_big_endian(f.size);
            out.write(reinterpret_cast<const char*>(&be_size), sizeof(be_size));

            out.write(f.rel_path.c_str(), static_cast<std::streamsize>(f.rel_path.length()));
            out.write("\0", 1);
        }

        // for byte-for-byte alignment with the EA "L219" gap
        out.write(EA_PADDING_TAG.data(), EA_PADDING_SIZE);

        std::vector<char> chunk(1024 * 1024);
        for (const auto& f : file_list) {
            std::ifstream src(f.full_path, std::ios::binary);
            if (!src.is_open()) {
                out.close();
                std::filesystem::remove(output_file);
                throw BigArchiveError("Cannot read source file: " + f.full_path.string());
            }

            uintmax_t bytes_copied = 0;
            while (src) {
                src.read(chunk.data(), static_cast<std::streamsize>(chunk.size()));
                std::streamsize bytes_read = src.gcount();
                if (bytes_read > 0) {
                    out.write(chunk.data(), bytes_read);
                    if (!out) {
                        out.close();
                        std::filesystem::remove(output_file);
                        throw BigArchiveError("Failed writing data to archive: " + output_file.string());
                    }
                    bytes_copied += static_cast<uintmax_t>(bytes_read);
                }
            }

            if (src.bad() || bytes_copied != f.size) {
                out.close();
                std::filesystem::remove(output_file);
                throw BigArchiveError("Byte count mismatch while packing file: " + f.rel_path);
            }

            if (progress_callback) {
                progress_callback(f.rel_path);
            }
        }

        out.flush();
        if (!out.good()) {
            out.close();
            std::filesystem::remove(output_file);
            throw BigArchiveError("Failed writing data to archive: " + output_file.string());
        }
    }

} // namespace lotm::big
