/**
 * @file src/ini/file_io.cpp
 * @brief Implementation of OS-level memory mapping, UTF-8/CP1252 normalization, and file loading for lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "parser_utils.hpp"
#include "ini/parser.hpp"
#include <core/path_utils.hpp>

#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <utility>

// Windows specific. Change for POSIX
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>

namespace lotm::ini {
namespace detail {

    bool ends_with_ci(std::string_view str, std::string_view suffix) noexcept {
        if (str.size() < suffix.size()) {
            return false;
        }
        return lotm::ini::detail::iequals_ascii(str.substr(str.size() - suffix.size()), suffix);
    }

    bool is_supported_config_ext(std::string_view path) noexcept {
        return ends_with_ci(path, ".ini") || ends_with_ci(path, ".inc") || ends_with_ci(path, ".str");
    }

    std::string join_views(std::span<const std::string_view> tokens, std::string_view sep) {
        if (tokens.empty()) {
            return {};
        }
        std::size_t total_len = sep.size() * (tokens.size() - 1);
        for (const auto tok : tokens) {
            total_len += tok.size();
        }
        std::string result;
        result.reserve(total_len);
        for (std::size_t i = 0; i < tokens.size(); ++i) {
            if (i > 0) {
                result.append(sep);
            }
            result.append(tokens[i]);
        }
        return result;
    }

    std::string combine_text_and_comment(std::string_view text, std::string_view comment) {
        if (!text.empty() && !comment.empty()) {
            std::string combined;
            combined.reserve(text.size() + 1 + comment.size());
            combined.append(text);
            combined.push_back(' ');
            combined.append(comment);
            return combined;
        }
        if (!text.empty()) {
            return std::string{ text };
        }
        return std::string{ comment };
    }

    namespace {

        // Windows-1252 code page mapping for bytes 0x80..0x9F to Unicode code points.
        inline constexpr std::array<std::uint16_t, 32> CP1252_80_9F_TABLE = {
            0x20AC, 0x0081, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021,
            0x02C6, 0x2030, 0x0160, 0x2039, 0x0152, 0x008D, 0x017D, 0x008F,
            0x0090, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014,
            0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0x009D, 0x017E, 0x0178
        };

        /**
         * @brief Strips a leading UTF-8 Byte Order Mark (EF BB BF) if present.
         */
        [[nodiscard]] constexpr std::string_view strip_utf8_bom(std::string_view sv) noexcept {
            if (sv.size() >= 3 &&
                static_cast<unsigned char>(sv[0]) == 0xEF &&
                static_cast<unsigned char>(sv[1]) == 0xBB &&
                static_cast<unsigned char>(sv[2]) == 0xBF) {
                return sv.substr(3);
            }
            return sv;
        }

        /**
         * @brief Validates whether a byte view is well-formed UTF-8 in a single zero-allocation pass.
         */
        [[nodiscard]] constexpr bool is_valid_utf8(std::string_view sv) noexcept {
            std::size_t i = 0;
            const std::size_t len = sv.size();

            while (i < len) {
                const auto b0 = static_cast<unsigned char>(sv[i]);
                if (b0 <= 0x7F) {
                    ++i;
                }
                else if (b0 >= 0xC2 && b0 <= 0xDF) {
                    if (i + 1 >= len) {
                        return false;
                    }
                    const auto b1 = static_cast<unsigned char>(sv[i + 1]);
                    if ((b1 & 0xC0) != 0x80) {
                        return false;
                    }
                    i += 2;
                }
                else if (b0 >= 0xE0 && b0 <= 0xEF) {
                    if (i + 2 >= len) {
                        return false;
                    }
                    const auto b1 = static_cast<unsigned char>(sv[i + 1]);
                    const auto b2 = static_cast<unsigned char>(sv[i + 2]);
                    if ((b0 == 0xE0 && (b1 < 0xA0 || b1 > 0xBF)) ||
                        (b0 == 0xED && (b1 < 0x80 || b1 > 0x9F)) ||
                        (b1 & 0xC0) != 0x80 ||
                        (b2 & 0xC0) != 0x80) {
                        return false;
                    }
                    i += 3;
                }
                else if (b0 >= 0xF0 && b0 <= 0xF4) {
                    if (i + 3 >= len) {
                        return false;
                    }
                    const auto b1 = static_cast<unsigned char>(sv[i + 1]);
                    const auto b2 = static_cast<unsigned char>(sv[i + 2]);
                    const auto b3 = static_cast<unsigned char>(sv[i + 3]);
                    if ((b0 == 0xF0 && (b1 < 0x90 || b1 > 0xBF)) ||
                        (b0 == 0xF4 && (b1 < 0x80 || b1 > 0x8F)) ||
                        (b1 & 0xC0) != 0x80 ||
                        (b2 & 0xC0) != 0x80 ||
                        (b3 & 0xC0) != 0x80) {
                        return false;
                    }
                    i += 4;
                }
                else {
                    return false;
                }
            }
            return true;
        }

        /**
         * @brief Transcodes a Windows-1252 / Latin-1 byte view into a valid UTF-8 std::string.
         */
        [[nodiscard]] std::string cp1252_to_utf8(std::string_view sv) {
            std::string out;
            out.reserve(sv.size() + (sv.size() / 4));

            for (const char ch : sv) {
                const auto b = static_cast<unsigned char>(ch);
                if (b <= 0x7F) {
                    out.push_back(ch);
                }
                else if (b >= 0xA0) {
                    out.push_back(static_cast<char>(0xC0 | (b >> 6)));
                    out.push_back(static_cast<char>(0x80 | (b & 0x3F)));
                }
                else {
                    const std::uint16_t cp = CP1252_80_9F_TABLE[b - 0x80];
                    if (cp <= 0x07FF) {
                        out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
                        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
                    }
                    else {
                        out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
                        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
                        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
                    }
                }
            }
            return out;
        }

    } // namespace

    std::string_view prepare_utf8_view(
        std::string_view raw_view,
        std::string& transcoded_storage
    ) {
        if (raw_view.size() > MAX_INI_FILE_SIZE) {
            throw IniParseError(
                "Security abort: Buffer size (" + std::to_string(raw_view.size()) +
                ") exceeds maximum allowed INI size (" + std::to_string(MAX_INI_FILE_SIZE) + ")."
            );
        }
        const std::string_view stripped = strip_utf8_bom(raw_view);
        if (is_valid_utf8(stripped)) {
            return stripped;
        }
        transcoded_storage = cp1252_to_utf8(stripped);
        return transcoded_storage;
    }

    MMapFile::MMapFile(const std::filesystem::path& path) {
        // Windows specific. Change for POSIX
        HANDLE hFile = CreateFileW(
            path.c_str(),
            GENERIC_READ,
            FILE_SHARE_READ,
            nullptr,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            nullptr
        );
        if (hFile == INVALID_HANDLE_VALUE) {
            throw IniParseError("Failed to open file for mapping: " + lotm::core::to_utf8(path));
        }
        file_handle_ = hFile;

        LARGE_INTEGER size;
        if (!GetFileSizeEx(hFile, &size)) {
            CloseHandle(hFile);
            throw IniParseError("Failed to get file size: " + lotm::core::to_utf8(path));
        }
        if (size.QuadPart < 0 || static_cast<std::uintmax_t>(size.QuadPart) > MAX_INI_FILE_SIZE) {
            CloseHandle(hFile);
            throw IniParseError("Security abort: File size exceeds maximum allowed INI size: " + lotm::core::to_utf8(path));
        }
        size_ = static_cast<std::size_t>(size.QuadPart);

        if (size_ > 0) {
            HANDLE hMap = CreateFileMappingW(
                hFile,
                nullptr,
                PAGE_READONLY,
                0,
                0,
                nullptr
            );
            if (hMap == nullptr) {
                CloseHandle(hFile);
                throw IniParseError("Failed to create file mapping: " + lotm::core::to_utf8(path));
            }
            map_handle_ = hMap;

            data_ = static_cast<const char*>(MapViewOfFile(
                hMap,
                FILE_MAP_READ,
                0,
                0,
                0
            ));
            if (data_ == nullptr) {
                CloseHandle(hMap);
                CloseHandle(hFile);
                throw IniParseError("Failed to map view of file: " + lotm::core::to_utf8(path));
            }
        }
    }

    MMapFile::~MMapFile() {
        // Windows specific. Change for POSIX
        if (data_) UnmapViewOfFile(const_cast<char*>(data_));
        if (map_handle_) CloseHandle(static_cast<HANDLE>(map_handle_));
        if (file_handle_ && file_handle_ != INVALID_HANDLE_VALUE) CloseHandle(static_cast<HANDLE>(file_handle_));
    }

    MMapFile::MMapFile(MMapFile&& other) noexcept 
        : size_(std::exchange(other.size_, 0)),
          data_(std::exchange(other.data_, nullptr)),
          file_handle_(std::exchange(other.file_handle_, nullptr)),
          map_handle_(std::exchange(other.map_handle_, nullptr)) {}

    MMapFile& MMapFile::operator=(MMapFile&& other) noexcept {
        if (this != &other) {
            // Windows specific. Change for POSIX
            if (data_) UnmapViewOfFile(const_cast<char*>(data_));
            if (map_handle_) CloseHandle(static_cast<HANDLE>(map_handle_));
            if (file_handle_ && file_handle_ != INVALID_HANDLE_VALUE) CloseHandle(static_cast<HANDLE>(file_handle_));
            
            size_ = std::exchange(other.size_, 0);
            data_ = std::exchange(other.data_, nullptr);
            file_handle_ = std::exchange(other.file_handle_, nullptr);
            map_handle_ = std::exchange(other.map_handle_, nullptr);
        }
        return *this;
    }

} // namespace detail

    namespace {
        [[nodiscard]] std::string read_normalized_utf8_file(const std::filesystem::path& path) {
            detail::MMapFile mmap{ path };
            std::string transcoded;
            const std::string_view utf8_view = detail::prepare_utf8_view(mmap.view(), transcoded);
            if (!transcoded.empty()) {
                return transcoded;
            }
            return std::string{ utf8_view };
        }
    } // namespace

    std::pair<std::string, std::vector<std::vector<std::string>>> load_file(std::string_view full_path) {
        if (full_path.empty()) {
            throw IniParseError("empty path.");
        }
        const std::filesystem::path fs_path = lotm::core::utf8_to_path(full_path);
        if (!std::filesystem::is_regular_file(fs_path)) {
            throw IniParseError("wrong path: " + std::string{ full_path });
        }

        if (detail::is_supported_config_ext(full_path)) {
            ConstructFile file_object{ std::string{ full_path }, false };
            std::string printed = file_object.print();
            if (printed.empty()) {
                return { read_normalized_utf8_file(fs_path),{} };
            }
            return { std::move(printed), std::move(file_object.delimiters) };
        }

        if (detail::ends_with_ci(full_path, ".txt")) {
            return { read_normalized_utf8_file(fs_path),{} };
        }

        throw IniParseError("wrong path or unsupported file type: " + std::string{ full_path });
    }

} // namespace lotm::ini
