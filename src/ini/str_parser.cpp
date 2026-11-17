/**
 * @file src/ini/str_parser.cpp
 * @brief Implementation of the dedicated single - level SAGE.str localization file parser.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "ini/parser.hpp"
#include <core/path_utils.hpp>

#include <filesystem>
#include <optional>
#include <span>
#include <stdexcept>

// Windows specific. Change for POSIX
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>

namespace lotm::ini {

    namespace {

        using lotm::core::utf8_to_path;

        [[nodiscard]] bool ends_with_ci(std::string_view str, std::string_view suffix) noexcept {
            if (str.size() < suffix.size()) {
                return false;
            }
            return detail::iequals_ascii(str.substr(str.size() - suffix.size()), suffix);
        }

        [[nodiscard]] std::string join_views(std::span<const std::string_view> tokens, std::string_view sep = " ") {
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

        /**
         * @brief RAII Memory Mapped File for zero-copy file reading on Windows.
         */
        class MMapFile {
        public:
            explicit MMapFile(const std::filesystem::path& path) {
                // Windows specific. Change for POSIX
                file_handle_ = CreateFileW(
                    path.c_str(),
                    GENERIC_READ,
                    FILE_SHARE_READ,
                    nullptr,
                    OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL,
                    nullptr
                );
                if (file_handle_ == INVALID_HANDLE_VALUE) {
                    throw IniParseError("Failed to open file for mapping: " + lotm::core::to_utf8(path));
                }

                LARGE_INTEGER size;
                if (!GetFileSizeEx(file_handle_, &size)) {
                    CloseHandle(file_handle_);
                    throw IniParseError("Failed to get file size: " + lotm::core::to_utf8(path));
                }
                if (size.QuadPart < 0 || static_cast<std::uintmax_t>(size.QuadPart) > MAX_INI_FILE_SIZE) {
                    CloseHandle(file_handle_);
                    throw IniParseError("Security abort: File size exceeds maximum allowed INI size: " + lotm::core::to_utf8(path));
                }
                size_ = static_cast<std::size_t>(size.QuadPart);

                if (size_ > 0) {
                    map_handle_ = CreateFileMappingW(
                        file_handle_,
                        nullptr,
                        PAGE_READONLY,
                        0,
                        0,
                        nullptr
                    );
                    if (map_handle_ == nullptr) {
                        CloseHandle(file_handle_);
                        throw IniParseError("Failed to create file mapping: " + lotm::core::to_utf8(path));
                    }

                    data_ = static_cast<const char*>(MapViewOfFile(
                        map_handle_,
                        FILE_MAP_READ,
                        0,
                        0,
                        0
                    ));
                    if (data_ == nullptr) {
                        CloseHandle(map_handle_);
                        CloseHandle(file_handle_);
                        throw IniParseError("Failed to map view of file: " + lotm::core::to_utf8(path));
                    }
                }
            }

            ~MMapFile() {
                // Windows specific. Change for POSIX
                if (data_) UnmapViewOfFile(data_);
                if (map_handle_) CloseHandle(map_handle_);
                if (file_handle_ != INVALID_HANDLE_VALUE) CloseHandle(file_handle_);
            }

            MMapFile(const MMapFile&) = delete;
            MMapFile& operator=(const MMapFile&) = delete;

            [[nodiscard]] std::string_view view() const noexcept {
                return { data_ ? data_ : "", size_ };
            }

        private:
            std::size_t size_{ 0 };
            const char* data_{ nullptr };
            // Windows specific. Change for POSIX
            HANDLE file_handle_{ INVALID_HANDLE_VALUE };
            HANDLE map_handle_{ nullptr };
        };

    } // namespace

    StrDocument StrParser::parse_file(
        std::string_view file_path,
        bool strict,
        std::optional<std::string_view> file_content
    ) {
        const std::filesystem::path fs_path = utf8_to_path(file_path);
        if (!ends_with_ci(file_path, ".str") ||
            (!file_content.has_value() && !std::filesystem::is_regular_file(fs_path))) {
            throw IniParseError("file " + std::string{ file_path } + " invalid.");
        }

        std::optional<MMapFile> mmap;
        std::string transcoded_buffer;
        std::string_view raw_view;
        if (file_content.has_value()) {
            raw_view = *file_content;
        }
        else {
            mmap.emplace(fs_path);
            raw_view = mmap->view();
        }
        const std::string_view content_view = prepare_utf8_view(raw_view, transcoded_buffer);

        StrDocument doc;
        doc.name = std::string{ file_path };

        std::optional<StrEntry> active_entry = std::nullopt;
        std::string last_comment;
        LexedLine lexed;

        struct OrphanSpan {
            std::size_t start_line{ 0 };
            std::size_t end_line{ 0 };
            std::string first_line_text{};
        };
        std::optional<OrphanSpan> orphan_span = std::nullopt;

        auto flush_orphan_span = [&]() {
            if (!orphan_span.has_value()) {
                return;
            }
            if (orphan_span->start_line == orphan_span->end_line) {
                doc.errors.push_back(
                    "Unexpected statement outside entry at " + std::string{ file_path } + ":" +
                    std::to_string(orphan_span->start_line) + ": " + orphan_span->first_line_text
                );
            }
            else {
                doc.errors.push_back(
                    "Unexpected statement outside entry at " + std::string{ file_path } + ":" +
                    std::to_string(orphan_span->start_line) + "-" + std::to_string(orphan_span->end_line) +
                    " (starting with: " + orphan_span->first_line_text + ")"
                );
            }
            orphan_span.reset();
            };

        for_each_line_view(content_view, [&](std::string_view raw_line, std::size_t line_num) {
            lex_line_into(raw_line, lexed);

            if (lexed.words.empty()) {
                if (!lexed.comment.empty()) {
                    if (!last_comment.empty()) {
                        last_comment.push_back('\\n');
                    }
                    last_comment.append(lexed.comment);
                }
                if (!last_comment.empty() && detail::trim_view(raw_line).empty()) {
                    if (active_entry.has_value()) {
                        active_entry->items.emplace_back(CommentNode{ std::move(last_comment) });
                    }
                    else {
                        doc.entries.emplace_back(CommentNode{ std::move(last_comment) });
                    }
                    last_comment.clear();
                }
                return;
            }

            const DelimiterRule* matched_rule = match_delimiter_rule(lexed.line_tokens, STR_DELIMITER_RULES);
            if (matched_rule != nullptr) {
                flush_orphan_span();

                if (active_entry.has_value()) {
                    const std::string active_id = active_entry->identifier.empty()
                        ? active_entry->category
                        : (active_entry->category + ":" + active_entry->identifier);
                    std::string err_msg = "Delimiter mismatch: unclosed entry '" + active_id +
                        "' before starting new entry at " + std::string{ file_path } + ":" + std::to_string(line_num);
                    doc.errors.push_back(err_msg);
                    if (strict) {
                        throw IniParseError(err_msg);
                    }
                    doc.entries.emplace_back(std::move(*active_entry));
                    active_entry.reset();
                }

                const auto remaining = std::span<const std::string_view>{ lexed.words }.subspan(
                    std::min(matched_rule->word_count, lexed.words.size())
                );

                std::string cat{ matched_rule->raw };
                std::string ident = join_views(remaining);
                validate_sage_bounds(cat, ident);

                active_entry = StrEntry{
                    std::move(cat),
                    std::move(ident),
                    std::move(last_comment),
                    lexed.comment,
                    "End",
                    "",
                    {}
                };
                last_comment.clear();
                return;
            }

            if (!last_comment.empty()) {
                if (active_entry.has_value()) {
                    active_entry->items.emplace_back(CommentNode{ std::move(last_comment) });
                }
                else {
                    doc.entries.emplace_back(CommentNode{ std::move(last_comment) });
                }
                last_comment.clear();
            }

            if (is_ini_end(lexed.words[0])) {
                if (!active_entry.has_value()) {
                    if (orphan_span.has_value() && orphan_span->end_line > orphan_span->start_line) {
                        orphan_span->end_line = line_num;
                        flush_orphan_span();
                        doc.entries.emplace_back(StatementNode{ join_views(lexed.words), lexed.comment });
                        return;
                    }
                    flush_orphan_span();

                    std::string err_msg = "Delimiter mismatch: negative level reached at " +
                        std::string{ file_path } + ":" + std::to_string(line_num) +
                        " on closing keyword '" + std::string{ lexed.words[0] } + "': " +
                        std::string{ detail::trim_view(raw_line) };
                    doc.errors.push_back(err_msg);
                    if (strict) {
                        throw IniParseError(err_msg);
                    }
                    doc.entries.emplace_back(StatementNode{ join_views(lexed.words), lexed.comment });
                }
                else {
                    active_entry->end_token = join_views(lexed.words);
                    active_entry->end_comment = lexed.comment;
                    doc.entries.emplace_back(std::move(*active_entry));
                    active_entry.reset();
                }
                return;
            }

            StatementNode stmt{ join_views(lexed.words_signs), lexed.comment };
            if (active_entry.has_value()) {
                active_entry->items.emplace_back(std::move(stmt));
            }
            else {
                if (strict) {
                    throw IniParseError(
                        "Unexpected statement outside entry at " + std::string{ file_path } + ":" +
                        std::to_string(line_num) + ": " + std::string{ detail::trim_view(raw_line) }
                    );
                }
                if (!orphan_span.has_value()) {
                    orphan_span = OrphanSpan{
                        line_num,
                        line_num,
                        std::string{ detail::trim_view(raw_line) }
                    };
                }
                else {
                    orphan_span->end_line = line_num;
                }
                doc.entries.emplace_back(std::move(stmt));
            }
            });

        flush_orphan_span();

        if (!last_comment.empty()) {
            if (active_entry.has_value()) {
                active_entry->items.emplace_back(CommentNode{ std::move(last_comment) });
            }
            else {
                doc.entries.emplace_back(CommentNode{ std::move(last_comment) });
            }
            last_comment.clear();
        }

        if (active_entry.has_value()) {
            const std::string active_id = active_entry->identifier.empty()
                ? active_entry->category
                : (active_entry->category + ":" + active_entry->identifier);
            std::string err_msg = "Unexpected EOF in " + std::string{ file_path } +
                ": unclosed entry '" + active_id + "' remains.";
            doc.errors.push_back(err_msg);
            if (strict) {
                throw IniParseError(err_msg);
            }
            doc.entries.emplace_back(std::move(*active_entry));
        }

        return doc;
    }

} // namespace lotm::ini
