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

        inline std::string to_utf8(const std::filesystem::path& p) {
            auto u8 = p.u8string();
            return std::string(reinterpret_cast<const char*>(u8.data()), u8.size());
        }

        // Case-insensitive glob matcher supporting '*' and '?' with normalized path separators
        bool matches_glob(std::string_view text, std::string_view pattern) noexcept {
            if (pattern.empty() || pattern == "*") {
                return true;
            }

            auto norm = [](char c) noexcept -> char {
                if (c == '\\' || c == '/') {
                    return static_cast<char>(std::filesystem::path::preferred_separator);
                }
                return static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
                };

            std::size_t t_idx = 0;
            std::size_t p_idx = 0;
            std::size_t star_idx = std::string_view::npos;
            std::size_t match_idx = 0;

            while (t_idx < text.size()) {
                if (p_idx < pattern.size() && (pattern[p_idx] == '?' || norm(pattern[p_idx]) == norm(text[t_idx]))) {
                    ++t_idx;
                    ++p_idx;
                }
                else if (p_idx < pattern.size() && pattern[p_idx] == '*') {
                    star_idx = p_idx;
                    match_idx = t_idx;
                    ++p_idx;
                }
                else if (star_idx != std::string_view::npos) {
                    p_idx = star_idx + 1;
                    ++match_idx;
                    t_idx = match_idx;
                }
                else {
                    return false;
                }
            }

            while (p_idx < pattern.size() && pattern[p_idx] == '*') {
                ++p_idx;
            }

            return p_idx == pattern.size();
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

        // Checks for extended Win32 and NT namespace prefixes (\\?, \\., \?, \., \??)
        bool has_win32_namespace_prefix(std::string_view path) {
            constexpr char sep = static_cast<char>(std::filesystem::path::preferred_separator);
            std::size_t pos = 0;
            while (pos < path.size() && path[pos] == sep) {
                ++pos;
            }
            return pos > 0 && pos < path.size() && (path[pos] == '?' || path[pos] == '.');
        }

        // Checks for Windows drive-relative paths (e.g., C:file.txt, D:..\escaped.txt)
        bool is_drive_relative_path(std::string_view path) {
            constexpr char sep = static_cast<char>(std::filesystem::path::preferred_separator);
            return path.size() >= 2 &&
                std::isalpha(static_cast<unsigned char>(path[0])) != 0 &&
                path[1] == ':' &&
                (path.size() == 2 || path[2] != sep);
        }

        // Checks for Windows reserved device names and Alternate Data Streams (ADS)
        bool is_unsafe_filename(std::string_view name) {
            if (name.empty() || name.back() == ' ' || name.back() == '.') {
                return true;
            }

            std::string upper_name;
            upper_name.reserve(name.size());
            for (char c : name) {
                const auto uc = static_cast<unsigned char>(c);
                if (uc < 32 || c == ':' || c == '<' || c == '>' ||
                    c == '"' || c == '|' || c == '?' || c == '*') {
                    return true;
                }
                upper_name.push_back(static_cast<char>(std::toupper(uc)));
            }

            auto dot_pos = upper_name.find('.');
            std::string_view base = (dot_pos != std::string_view::npos)
                ? std::string_view(upper_name).substr(0, dot_pos)
                : upper_name;

            // Strip trailing spaces and dots (Win32 path normalization trims them before device check)
            while (!base.empty() && (base.back() == ' ' || base.back() == '.')) {
                base.remove_suffix(1);
            }

            if (base == "CON" || base == "PRN" || base == "AUX" || base == "NUL" ||
                base == "CONIN$" || base == "CONOUT$") {
                return true;
            }
            if (base.size() == 4 && (base.starts_with("COM") || base.starts_with("LPT"))) {
                if (base[3] >= '1' && base[3] <= '9') {
                    return true;
                }
            }
            return false;
        }
    } // namespace

    BigArchive::BigArchive(std::filesystem::path file_path)
        : file_path_(std::move(file_path)) {

        std::ifstream file(file_path_, std::ios::binary);
        if (!file.is_open()) {
            throw BigArchiveError("Cannot open file: " + to_utf8(file_path_));
        }

        // Header reading
        char magic[5] = { 0 };
        file.read(magic, 4);
        if (!file || std::string_view(magic) != BIG4_MAGIC) {
            throw BigFormatError(std::string("Not a valid BIG4 file! Found: ") + magic);
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
        auto physical_size = std::filesystem::file_size(file_path_, ec);
        if (ec) {
            throw BigArchiveError("Cannot read physical file size: " + to_utf8(file_path_));
        }

        if (header_size_ < HEADER_BASE_SIZE ||
            header_size_ > physical_size ||
            static_cast<uintmax_t>(num_files) * 8 > physical_size) {
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

            // Read file name until null byte
            entry.name = read_null_terminated_string(file, remaining_header);

            if (!file) {
                throw BigFormatError("Truncated BIG4 string table.");
            }

            // Replace backslashes and forward slashes with native directory separators
            for (char& c : entry.name) {
                if (c == '\\' || c == '/') {
                    c = static_cast<char>(std::filesystem::path::preferred_separator);
                }
            }

            entries_.push_back(std::move(entry));
        }
    }

    void BigArchive::close() noexcept {
        is_closed_ = true;
        entries_.clear();
        entries_.shrink_to_fit();
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

    std::vector<uint8_t> BigArchive::read_entry(std::string_view entry_name) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot read from a closed archive.");
        }

        std::string normalized_name(entry_name);
        for (char& c : normalized_name) {
            if (c == '\\' || c == '/') {
                c = static_cast<char>(std::filesystem::path::preferred_separator);
            }
        }

        // Match normalized path case-insensitively to mirror SAGE engine lookup semantics
        auto it = std::find_if(entries_.begin(), entries_.end(),
            [&normalized_name](const BigEntry& entry) {
                if (entry.name.size() != normalized_name.size()) {
                    return false;
                }
                return std::equal(entry.name.begin(), entry.name.end(), normalized_name.begin(),
                    [](unsigned char a, unsigned char b) {
                        return std::tolower(a) == std::tolower(b);
                    });
            });

        if (it == entries_.end()) {
            throw BigArchiveError("Entry not found in archive: " + std::string(entry_name));
        }

        return read_entry(*it);
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

    void BigArchive::extract_all(
        const std::filesystem::path& output_dir,
        std::function<void(std::string_view)> progress_callback,
        std::string_view filter_pattern
    ) const {
        if (is_closed_) {
            throw BigArchiveError("Cannot extract from a closed archive.");
        }

        std::error_code ec;
        const auto physical_size = std::filesystem::file_size(file_path_, ec);
        if (ec) {
            throw BigArchiveError("Cannot open file for extraction: " + to_utf8(file_path_));
        }

        const uintmax_t max_extraction_quota = physical_size * MAX_AMPLIFICATION_RATIO;

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

        if (!std::filesystem::exists(output_dir)) {
            std::filesystem::create_directories(output_dir);
        }

        const std::filesystem::path canonical_output_dir = std::filesystem::weakly_canonical(output_dir);

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

            std::filesystem::path entry_rel_path(entry.name);
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
                if (is_unsafe_filename(part.string())) {
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
        }

        std::ifstream file(file_path_, std::ios::binary);
        if (!file.is_open()) {
            throw BigArchiveError("Cannot open file for extraction.");
        }

        std::vector<char> buffer(EXTRACT_CHUNK_SIZE);

        // SAFE EXTRACTION LOOP
        for (const auto& entry : entries_) {
            if (!matches_glob(entry.name, filter_pattern)) {
                continue;
            }

            std::filesystem::path entry_rel_path(entry.name);
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
                }
            }

            out_file.flush();
            if (!out_file) {
                throw BigArchiveError("Failed to flush extracted file: " + to_utf8(target_path));
            }

            if (progress_callback) {
                progress_callback(entry.name);
            }
        }
    }

} // namespace lotm::big
