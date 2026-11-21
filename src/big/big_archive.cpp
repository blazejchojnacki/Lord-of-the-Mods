/**
 * @file src/big/big_archive.cpp
 * @brief Implementation of BIG unpacking object
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <big/big_archive.hpp>
#include <big/exceptions.hpp>
#include <big/types.hpp>
#include <core/endian.hpp>
#include <core/path_utils.hpp>

#include <algorithm>
#include <cctype>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <functional>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>

namespace lotm::big {

    namespace {
        constexpr std::size_t MAX_ENTRY_PATH_LENGTH = 4096;
        constexpr std::size_t EXTRACT_CHUNK_SIZE = 1024 * 1024;
        constexpr uintmax_t MAX_AMPLIFICATION_RATIO = 20;

        using lotm::core::to_utf8;
        using lotm::core::matches_glob;
        using lotm::core::normalize_virtual_path;
        using lotm::core::has_win32_namespace_prefix;
        using lotm::core::is_drive_relative_path;

        inline std::filesystem::path from_utf8(std::string_view sv) {
            try {
                return lotm::core::utf8_to_path(sv);
            }
            catch (const std::exception&) {
                throw BigSecurityError("Invalid UTF-8 or unmappable characters in entry path: " + std::string(sv));
            }
        }

        // Internal helper for reading strings until null-terminator within a byte budget
        static std::string read_null_terminated_string(std::ifstream& stream, std::size_t max_bytes) {
            std::string result;
            char ch = '\0';
            for (std::size_t i = 0; i < max_bytes; ++i) {
                if (!stream.get(ch)) {
                    return result;
                }
                if (ch == '\0') {
                    return result;
                }
                result.push_back(ch);
            }
            stream.setstate(std::ios::failbit);
            return result;
        }
    } // namespace

    BigArchive::BigArchive(std::filesystem::path file_path)
        : file_path_(std::move(file_path)) {

        std::ifstream file(file_path_, std::ios::binary);
        if (!file.is_open()) {
            throw BigArchiveError("Cannot open file: " + to_utf8(file_path_));
        }

        // Header reading
        char magic[4] = { 0 };
        file.read(magic, 4);
        if (!file || std::string_view(magic, 4) != BIG4_MAGIC) {
            std::string safe_magic;
            safe_magic.reserve(4);
            for (unsigned char c : magic) {
                safe_magic.push_back((c >= 32 && c < 127) ? static_cast<char>(c) : '?');
            }
            throw BigFormatError("Not a valid BIG4 file! Found: " + safe_magic);
        }

        // Total size (Little Endian - '<I')
        file.read(reinterpret_cast<char*>(&total_size_), sizeof(total_size_));
        total_size_ = lotm::core::from_little_endian(total_size_);

        // Number of files and header size (Big Endian - hence swapping)
        uint32_t num_files = 0;
        file.read(reinterpret_cast<char*>(&num_files), sizeof(num_files));
        file.read(reinterpret_cast<char*>(&header_size_), sizeof(header_size_));

        if (!file) {
            throw BigFormatError("Truncated BIG4 header metadata.");
        }

        num_files = lotm::core::from_big_endian(num_files);
        header_size_ = lotm::core::from_big_endian(header_size_);

        // Prevent memory exhaustion from malicious/corrupted num_files claims
        std::error_code ec;
        physical_size_ = std::filesystem::file_size(file_path_, ec);
        if (ec) {
            throw BigArchiveError("Cannot read physical file size: " + to_utf8(file_path_));
        }

        if (header_size_ < HEADER_BASE_SIZE ||
            header_size_ > physical_size_ ||
            total_size_ < header_size_ ||
            static_cast<uintmax_t>(num_files) * 8 > header_size_ - HEADER_BASE_SIZE) {
            throw BigFormatError("Corrupted BIG4 index: Claims more files than physically possible.");
        }

        entries_.reserve(num_files);

        // Index reading
        for (uint32_t i = 0; i < num_files; ++i) {
            BigEntry entry;

            file.read(reinterpret_cast<char*>(&entry.offset), sizeof(entry.offset));
            file.read(reinterpret_cast<char*>(&entry.size), sizeof(entry.size));

            if (!file) {
                throw BigFormatError("Truncated BIG4 file index.");
            }

            entry.offset = lotm::core::from_big_endian(entry.offset);
            entry.size = lotm::core::from_big_endian(entry.size);

            auto current_pos = file.tellg();
            if (current_pos < 0 || static_cast<uintmax_t>(current_pos) >= header_size_) {
                throw BigFormatError("Truncated BIG4 string table.");
            }

            std::size_t remaining_header = static_cast<std::size_t>(
                std::min<uintmax_t>(header_size_ - static_cast<uintmax_t>(current_pos), MAX_ENTRY_PATH_LENGTH));

            // Read non-empty file name until null byte
            entry.name = read_null_terminated_string(file, remaining_header);

            if (!file || entry.name.empty()) {
                throw BigFormatError("Truncated BIG4 string table.");
            }

            // Replace backslashes and forward slashes with native directory separators
            for (char& c : entry.name) {
                if (c == '\\' || c == '/') {
                    c = static_cast<char>(std::filesystem::path::preferred_separator);
                }
            }

            std::string lower_name = normalize_virtual_path(entry.name);

            entries_.push_back(std::move(entry));
            index_map_.emplace(std::move(lower_name), entries_.size() - 1);
        }
    }

    const std::filesystem::path& BigArchive::file_path() const noexcept {
        return file_path_;
    }

    void BigArchive::close() noexcept {
        is_closed_ = true;
        entries_.clear();
        entries_.shrink_to_fit();
        index_map_.clear();
    }

    bool BigArchive::is_closed() const noexcept {
        return is_closed_;
    }

    std::vector<BigEntry> BigArchive::get_entries(std::string_view filter_pattern) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot access entries of a closed archive.");
        }
        if (filter_pattern.empty()) {
            return entries_;
        }

        std::vector<BigEntry> filtered;
        for (const auto& entry : entries_) {
            if (matches_glob(entry.name, filter_pattern)) {
                filtered.push_back(entry);
            }
        }
        return filtered;
    }

    const BigEntry& BigArchive::resolve(std::string_view entry_name) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot resolve on a closed archive.");
        }

        // Match normalized path case-insensitively to mirror SAGE engine lookup semantics
        const std::string key = normalize_virtual_path(entry_name);
        auto it = index_map_.find(key);
        if (it == index_map_.end()) {
            throw BigArchiveError("Entry not found in archive: " + std::string(entry_name));
        }

        return entries_[it->second];
    }

    std::vector<uint8_t> BigArchive::read_entry(std::string_view entry_name) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot read from a closed archive.");
        }

        return read_entry(resolve(entry_name));
    }

    std::vector<uint8_t> BigArchive::read_entry(const BigEntry& entry) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot read from a closed archive.");
        }

        std::error_code ec;
        const auto physical_size = std::filesystem::file_size(file_path_, ec);
        if (ec) {
            throw BigArchiveError("Cannot open file for reading: " + to_utf8(file_path_));
        }

        // Validate payload bounds before allocating memory
        if (static_cast<uintmax_t>(entry.offset) + entry.size > physical_size) {
            throw BigFormatError("Extraction bounds exceeded for file: " + entry.name);
        }

        std::ifstream file(file_path_, std::ios::binary);
        if (!file.is_open()) {
            throw BigArchiveError("Cannot open file for reading: " + to_utf8(file_path_));
        }

        std::vector<uint8_t> buffer(entry.size);
        if (entry.size > 0) {
            file.seekg(entry.offset, std::ios::beg);
            if (!file) {
                throw BigArchiveError("Failed to seek to offset for file: " + entry.name);
            }

            file.read(reinterpret_cast<char*>(buffer.data()), static_cast<std::streamsize>(entry.size));
            if (!file || file.gcount() != static_cast<std::streamsize>(entry.size)) {
                throw BigArchiveError("Failed to read payload for file: " + entry.name);
            }
        }

        return buffer;
    }

    void BigArchive::stream_entry(std::string_view entry_name, ChunkCallback chunk_cb) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot read from a closed archive.");
        }
        if (!chunk_cb) return;

        stream_entry(resolve(entry_name), std::move(chunk_cb));
    }

    void BigArchive::stream_entry(const BigEntry& entry, ChunkCallback chunk_cb) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot read from a closed archive.");
        }
        if (!chunk_cb) return;

        if (static_cast<uintmax_t>(entry.offset) + entry.size > physical_size_) {
            throw BigFormatError("Extraction bounds exceeded for file: " + entry.name);
        }

        std::ifstream file(file_path_, std::ios::binary);
        if (!file.is_open()) throw BigArchiveError("Cannot open file for reading: " + to_utf8(file_path_));

        if (entry.size > 0) {
            file.seekg(entry.offset, std::ios::beg);
            if (!file) throw BigArchiveError("Failed to seek to offset for file: " + entry.name);

            std::vector<uint8_t> buffer(EXTRACT_CHUNK_SIZE);
            uint32_t remaining = entry.size;
            while (remaining > 0) {
                const auto chunk_size = static_cast<std::streamsize>(
                    std::min<std::size_t>(remaining, buffer.size()));
                file.read(reinterpret_cast<char*>(buffer.data()), chunk_size);
                if (!file || file.gcount() != chunk_size) {
                    throw BigArchiveError("Failed to read payload for file: " + entry.name);
                }
                if (!chunk_cb(std::span<const uint8_t>(buffer.data(), static_cast<std::size_t>(chunk_size)))) {
                    break;
                }
                remaining -= static_cast<uint32_t>(chunk_size);
            }
        }
        else {
            chunk_cb(std::span<const uint8_t>());
        }
    }

    uintmax_t BigArchive::validate_extraction_quota(std::string_view filter_pattern) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot access closed archive.");
        }
        const uintmax_t max_extraction_quota = physical_size_ * MAX_AMPLIFICATION_RATIO;

        // Upfront quota evaluation across all entries to prevent amplification / zip-bomb attacks
        uintmax_t total_extracted_bytes = 0;
        for (const auto& entry : entries_) {
            if (!matches_glob(entry.name, filter_pattern)) {
                continue;
            }
            if (max_extraction_quota - total_extracted_bytes < entry.size) {
                throw BigSecurityError("Archive amplification (Zip Bomb) threshold exceeded.");
            }
            total_extracted_bytes += entry.size;
        }

        return physical_size_;
    }

    void BigArchive::extract_all(
        const std::filesystem::path& output_dir,
        ProgressCallback progress_callback,
        std::string_view filter_pattern,
        bool create_directories
    ) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot extract from a closed archive.");
        }

        if (!std::filesystem::exists(output_dir)) {
            if (create_directories) {
                std::filesystem::create_directories(output_dir);
            }
            else {
                throw std::invalid_argument("Target output directory does not exist: " + to_utf8(output_dir));
            }
        }

        const uintmax_t physical_size = validate_extraction_quota(filter_pattern);
        const std::filesystem::path canonical_output_dir = std::filesystem::weakly_canonical(output_dir);
        uint64_t total_archive_size = 0;

        // Pre-flight security and bounds validation pass
        // PRE-FLIGHT VALIDATION LOOP
        for (const auto& entry : entries_) {
            if (!matches_glob(entry.name, filter_pattern)) {
                continue;
            }

            // Check for malicious or corrupted bounds
            if (static_cast<uintmax_t>(entry.offset) + entry.size > physical_size) {
                throw BigFormatError("Extraction bounds exceeded for file: " + entry.name);
            }

            if (has_win32_namespace_prefix(entry.name)) {
                throw BigSecurityError("Extended Win32 namespace prefix detected in entry: " + entry.name);
            }

            if (is_drive_relative_path(entry.name)) {
                throw BigSecurityError("Directory traversal via Windows drive-relative path detected in entry: " + entry.name);
            }

            std::filesystem::path entry_rel_path = from_utf8(entry.name);
            if (entry_rel_path.empty() ||
                entry_rel_path.is_absolute() ||
                entry_rel_path.has_root_name() ||
                entry_rel_path.has_root_directory()) {
                throw BigSecurityError("Unsafe or rooted path in archive entry: " + entry.name);
            }

            // Verify path components against device names, alternate streams, and existing symlinks
            std::filesystem::path current_check = canonical_output_dir;
            for (const auto& part : entry_rel_path) {
                if (part.empty() || part == ".") continue;
                if (part == "..") {
                    throw BigSecurityError("Directory traversal (..) detected in entry: " + entry.name);
                }
                if (lotm::core::is_unsafe_ntfs_component(to_utf8(part))) {
                    throw BigSecurityError("Unsafe Windows device name or ADS stream in path: " + entry.name);
                }

                current_check /= part;
                std::error_code check_ec;
                auto st = std::filesystem::symlink_status(current_check, check_ec);
                if (!check_ec && std::filesystem::is_symlink(st)) {
                    throw BigSecurityError("Symlink detected in path (strict abort policy): " + entry.name);
                }
            }

            std::filesystem::path target_path = std::filesystem::weakly_canonical(canonical_output_dir / entry_rel_path);
            auto mismatch_pair = std::mismatch(
                canonical_output_dir.begin(), canonical_output_dir.end(),
                target_path.begin(), target_path.end());

            if (mismatch_pair.first != canonical_output_dir.end() || target_path == canonical_output_dir) {
                throw BigSecurityError("Path traversal attempt detected for file: " + entry.name);
            }

            total_archive_size += entry.size;
        }

        std::ifstream file(file_path_, std::ios::binary);
        if (!file.is_open()) {
            throw BigArchiveError("Cannot open file for extraction.");
        }

        std::vector<char> buffer(EXTRACT_CHUNK_SIZE);
        uint64_t total_bytes_transferred = 0;

        // SAFE EXTRACTION LOOP
        for (const auto& entry : entries_) {
            if (!matches_glob(entry.name, filter_pattern)) {
                continue;
            }

            std::filesystem::path entry_rel_path = from_utf8(entry.name);
            std::filesystem::path target_path = canonical_output_dir / entry_rel_path;
            std::filesystem::path target_subdir = target_path.parent_path();

            if (!std::filesystem::exists(target_subdir)) {
                std::filesystem::create_directories(target_subdir);
            }

            std::ofstream out_file(target_path, std::ios::binary);
            if (!out_file.is_open()) {
                throw BigArchiveError("Cannot create output file: " + to_utf8(target_path));
            }

            if (entry.size > 0) {
                file.seekg(entry.offset, std::ios::beg);
                if (!file) {
                    throw BigArchiveError("Failed to seek to offset for file: " + entry.name);
                }

                // Stream payload through reusable chunk buffer
                uint32_t remaining = entry.size;
                uint64_t file_bytes_transferred = 0;
                while (remaining > 0) {
                    const auto chunk_size = static_cast<std::streamsize>(
                        std::min<std::size_t>(remaining, buffer.size()));
                    file.read(buffer.data(), chunk_size);

                    if (!file || file.gcount() != chunk_size) {
                        throw BigArchiveError("Failed to read payload for file: " + entry.name);
                    }

                    out_file.write(buffer.data(), chunk_size);
                    if (!out_file) {
                        throw BigArchiveError("Failed to write extracted file: " + to_utf8(target_path));
                    }

                    remaining -= static_cast<uint32_t>(chunk_size);
                    file_bytes_transferred += static_cast<uint64_t>(chunk_size);
                    total_bytes_transferred += static_cast<uint64_t>(chunk_size);

                    if (progress_callback) {
                        const ProgressReport report{
                            entry.name,
                            file_bytes_transferred,
                            entry.size,
                            total_bytes_transferred,
                            total_archive_size
                        };
                        if (!progress_callback(report)) {
                            out_file.close();
                            std::error_code rm_ec;
                            std::filesystem::remove(target_path, rm_ec);
                            throw BigArchiveError("Operation cancelled by progress callback.");
                        }
                    }
                }
            }

            out_file.flush();
            if (!out_file) {
                throw BigArchiveError("Failed to flush extracted file: " + to_utf8(target_path));
            }

            if (entry.size == 0 && progress_callback) {
                const ProgressReport report{
                    entry.name,
                    0,
                    0,
                    total_bytes_transferred,
                    total_archive_size
                };
                if (!progress_callback(report)) {
                    out_file.close();
                    std::error_code rm_ec;
                    std::filesystem::remove(target_path, rm_ec);
                    throw BigArchiveError("Operation cancelled by progress callback.");
                }
            }
        }
    }

} // namespace lotm::big
