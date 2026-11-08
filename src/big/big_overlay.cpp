/**
 * @file src/big/big_overlay.cpp
 * @brief Implementation of SAGE load-order archive overlay engine
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <big/big_overlay.hpp>
#include <big/exceptions.hpp>

#include <algorithm>
#include <cctype>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace lotm::big {

    namespace {
        inline std::string to_utf8(const std::filesystem::path& p) {
            auto u8 = p.u8string();
            return std::string(reinterpret_cast<const char*>(u8.data()), u8.size());
        }

        std::string to_lower_ascii(std::string_view sv) {
            std::string res(sv);
            std::transform(res.begin(), res.end(), res.begin(),
                [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
            return res;
        }

        std::string normalize_lookup_key(std::string_view entry_name) {
            std::string key(entry_name);
            for (char& c : key) {
                if (c == '\\' || c == '/') {
                    c = static_cast<char>(std::filesystem::path::preferred_separator);
                }
                else {
                    c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
                }
            }
            return key;
        }
    } // namespace

    void BigOverlay::close() noexcept {
        is_closed_ = true;
        archives_.clear();
        index_map_.clear();
    }

    bool BigOverlay::is_closed() const noexcept {
        return is_closed_;
    }

    BigOverlay BigOverlay::from_directory(const std::filesystem::path& dir_path) {
        if (!std::filesystem::exists(dir_path) || !std::filesystem::is_directory(dir_path)) {
            throw std::invalid_argument("Overlay directory does not exist or is not a directory.");
        }

        std::vector<std::pair<std::string, std::filesystem::path>> discovered;
        for (const auto& item : std::filesystem::directory_iterator(dir_path)) {
            if (!item.is_regular_file()) {
                continue;
            }

            std::string ext = to_lower_ascii(to_utf8(item.path().extension()));
            if (ext != ".big") {
                continue;
            }

            std::string lower_filename = to_lower_ascii(to_utf8(item.path().filename()));
            discovered.emplace_back(std::move(lower_filename), item.path());
        }

        std::sort(discovered.begin(), discovered.end(),
            [](const auto& a, const auto& b) {
                return a.first < b.first;
            });

        BigOverlay overlay;
        for (const auto& [_, path] : discovered) {
            overlay.mount(path);
        }
        return overlay;
    }

    BigOverlay BigOverlay::from_archives(const std::vector<std::filesystem::path>& archive_paths) {
        BigOverlay overlay;
        for (const auto& path : archive_paths) {
            overlay.mount(path);
        }
        return overlay;
    }

    void BigOverlay::mount(const std::filesystem::path& archive_path) {
        if (is_closed_) throw BigArchiveError("Cannot mount to a closed overlay.");
        BigArchive archive(archive_path);
        const std::size_t current_idx = archives_.size();

        for (const auto& entry : archive.get_entries()) {
            std::string key = to_lower_ascii(entry.name);
            auto it = index_map_.find(key);
            if (it != index_map_.end()) {
                it->second.entry = entry;
                it->second.archive_index = current_idx;
                ++it->second.override_count;
            }
            else {
                index_map_.emplace(std::move(key), OverlayRecord{ entry, current_idx, 0 });
            }
        }

        archives_.emplace_back(archive_path, std::move(archive));
    }

    std::vector<std::filesystem::path> BigOverlay::get_mounted_archives() const {
        if (is_closed_) throw BigArchiveError("Cannot access closed overlay.");
        std::vector<std::filesystem::path> result;
        result.reserve(archives_.size());
        for (const auto& [path, _] : archives_) {
            result.push_back(path);
        }
        return result;
    }

    std::vector<BigOverlayEntry> BigOverlay::get_entries(std::string_view filter_pattern) const {
        if (is_closed_) throw BigArchiveError("Cannot access closed overlay.");
        std::vector<BigOverlayEntry> result;

        for (std::size_t idx = 0; idx < archives_.size(); ++idx) {
            const auto& [arc_path, arc] = archives_[idx];
            for (const auto& entry : arc.get_entries(filter_pattern)) {
                std::string key = to_lower_ascii(entry.name);
                auto it = index_map_.find(key);
                if (it != index_map_.end() && it->second.archive_index == idx) {
                    result.push_back(BigOverlayEntry{
                        it->second.entry,
                        arc_path,
                        it->second.override_count
                        });
                }
            }
        }

        std::sort(result.begin(), result.end(),
            [](const BigOverlayEntry& a, const BigOverlayEntry& b) {
                return std::lexicographical_compare(
                    a.entry.name.begin(), a.entry.name.end(),
                    b.entry.name.begin(), b.entry.name.end(),
                    [](unsigned char c1, unsigned char c2) {
                        return std::tolower(c1) < std::tolower(c2);
                    }
                );
            });

        return result;
    }

    BigOverlayEntry BigOverlay::resolve(std::string_view entry_name) const {
        if (is_closed_) throw BigArchiveError("Cannot resolve on a closed overlay.");
        const std::string key = normalize_lookup_key(entry_name);
        auto it = index_map_.find(key);
        if (it == index_map_.end()) {
            throw BigArchiveError("Entry not found in overlay: " + std::string(entry_name));
        }

        const auto& rec = it->second;
        return BigOverlayEntry{
            rec.entry,
            archives_[rec.archive_index].first,
            rec.override_count
        };
    }

    std::vector<uint8_t> BigOverlay::read_entry(std::string_view entry_name) const {
        if (is_closed_) throw BigArchiveError("Cannot read from a closed overlay.");
        const std::string key = normalize_lookup_key(entry_name);
        auto it = index_map_.find(key);
        if (it == index_map_.end()) {
            throw BigArchiveError("Entry not found in overlay: " + std::string(entry_name));
        }

        const auto& rec = it->second;
        return archives_[rec.archive_index].second.read_entry(rec.entry);
    }

    void BigOverlay::stream_entry(std::string_view entry_name, ChunkCallback chunk_cb) const {
        if (is_closed_) throw BigArchiveError("Cannot read from a closed overlay.");
        const std::string key = normalize_lookup_key(entry_name);
        auto it = index_map_.find(key);
        if (it == index_map_.end()) {
            throw BigArchiveError("Entry not found in overlay: " + std::string(entry_name));
        }

        const auto& rec = it->second;
        archives_[rec.archive_index].second.stream_entry(rec.entry, std::move(chunk_cb));
    }

} // namespace lotm::big
