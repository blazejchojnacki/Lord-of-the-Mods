/**
 * @file src/big/big_unpack.cpp
 * @brief Implementation of BIG unpacking object
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

#include <big/big_unpack.hpp>
#include <core/endian.hpp>
#include <fstream>
#include <stdexcept>
#include <iostream>
#include <string_view>
#include <filesystem>

namespace lotm::big {

    // Internal helper for reading strings until null-terminator
    static std::string read_null_terminated_string(std::ifstream& stream) {
        std::string result;
        std::getline(stream, result, '\0');
        return result;
    }

    BigArchive::BigArchive(std::filesystem::path file_path)
        : file_path_(std::move(file_path)) {
    }

    void BigArchive::read_header() {
        std::ifstream file(file_path_, std::ios::binary);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open file: " + file_path_.string());
        }

        // Header reading
        char magic[5] = { 0 };
        file.read(magic, 4);
        if (!file || std::string_view(magic) != BIG4_MAGIC) {
            throw std::invalid_argument(std::string("Not a valid BIG4 file! Found: ") + magic);
        }

        // Total size (Little Endian - '<I')
        file.read(reinterpret_cast<char*>(&total_size_), sizeof(total_size_));

        // Number of files and header size (Big Endian - hence swapping)
        uint32_t num_files = 0;
        file.read(reinterpret_cast<char*>(&num_files), sizeof(num_files));
        file.read(reinterpret_cast<char*>(&header_size_), sizeof(header_size_));

        if (!file) {
            throw std::runtime_error("Truncated BIG4 header metadata.");
        }

        num_files = lotm::core::from_big_endian(num_files);
        header_size_ = lotm::core::from_big_endian(header_size_);

        // Prevent memory exhaustion from malicious/corrupted num_files claims
        auto physical_size = std::filesystem::file_size(file_path_);
        if (header_size_ > physical_size || static_cast<uintmax_t>(num_files) * 8 > physical_size) {
            throw std::runtime_error("Corrupted BIG4 index: Claims more files than physically possible.");
        }

        std::cout << "File: " << file_path_.string() << '\n';
        std::cout << "Number of files inside: " << num_files << '\n';

        entries_.reserve(num_files);

        // Index reading
        for (uint32_t i = 0; i < num_files; ++i) {
            BigEntry entry;

            file.read(reinterpret_cast<char*>(&entry.offset), sizeof(entry.offset));
            file.read(reinterpret_cast<char*>(&entry.size), sizeof(entry.size));

            if (!file) {
                throw std::runtime_error("Truncated BIG4 file index.");
            }

            entry.offset = lotm::core::from_big_endian(entry.offset);
            entry.size = lotm::core::from_big_endian(entry.size);

            // Read file name until null byte
            entry.name = read_null_terminated_string(file);

            if (!file) {
                throw std::runtime_error("Truncated BIG4 string table.");
            }

            // Replace backslashes with native directory separators
            for (char& c : entry.name) {
                if (c == '\\') {
                    c = static_cast<char>(std::filesystem::path::preferred_separator);
                }
            }

            entries_.push_back(std::move(entry));
        }
    }

    void BigArchive::extract_all(const std::filesystem::path& output_dir) {
        if (!std::filesystem::exists(output_dir)) {
            std::filesystem::create_directories(output_dir);
        }

        std::ifstream file(file_path_, std::ios::binary);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open file for extraction.");
        }

        auto physical_size = std::filesystem::file_size(file_path_);

        // File extraction
        for (const auto& entry : entries_) {
            // Check for malicious or corrupted bounds
            if (static_cast<uintmax_t>(entry.offset) + entry.size > physical_size) {
                throw std::runtime_error("Extraction bounds exceeded for file: " + entry.name);
            }

            std::filesystem::path target_path = output_dir / entry.name;
            std::filesystem::path target_subdir = target_path.parent_path();

            if (!std::filesystem::exists(target_subdir)) {
                std::filesystem::create_directories(target_subdir);
            }

            std::ofstream out_file(target_path, std::ios::binary);
            if (!out_file.is_open()) {
                throw std::runtime_error("Cannot create output file: " + target_path.string());
            }

            if (entry.size > 0) {
                file.seekg(entry.offset, std::ios::beg);
                if (!file) {
                    throw std::runtime_error("Failed to seek to offset for file: " + entry.name);
                }

                // Read directly to a vector buffer
                std::vector<char> buffer(entry.size);
                file.read(buffer.data(), entry.size);

                if (!file) {
                    throw std::runtime_error("Failed to read payload for file: " + entry.name);
                }

                out_file.write(buffer.data(), entry.size);
            }

            std::cout << "Extracted: " << entry.name << '\n';
        }
    }

} // namespace lotm::big
