/**
 * @file src/big/big_diff.cpp
 * @brief Implementation of BIG archive comparison engine
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <big/big_diff.hpp>

#include <algorithm>
#include <cctype>
#include <cstddef>
#include <string>
#include <utility>
#include <vector>

namespace lotm::big {

    namespace {
        struct IndexedEntry {
            std::string lower_name;
            BigEntry entry;
        };

        std::vector<IndexedEntry> build_sorted_index(const std::vector<BigEntry>& entries) {
            std::vector<IndexedEntry> indexed;
            indexed.reserve(entries.size());

            for (const auto& e : entries) {
                std::string lower = e.name;
                std::transform(lower.begin(), lower.end(), lower.begin(),
                    [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
                indexed.push_back(IndexedEntry{ std::move(lower), e });
            }

            std::sort(indexed.begin(), indexed.end(),
                [](const IndexedEntry& a, const IndexedEntry& b) {
                    return a.lower_name < b.lower_name;
                });

            return indexed;
        }
    } // namespace

    BigDiffResult BigDiff::compare(
        const BigArchive& base_archive,
        const BigArchive& target_archive,
        std::string_view filter_pattern
    ) {
        const auto base_sorted = build_sorted_index(base_archive.get_entries(filter_pattern));
        const auto target_sorted = build_sorted_index(target_archive.get_entries(filter_pattern));

        BigDiffResult result;
        std::size_t i = 0;
        std::size_t j = 0;

        while (i < base_sorted.size() && j < target_sorted.size()) {
            if (base_sorted[i].lower_name < target_sorted[j].lower_name) {
                result.removed.push_back(base_sorted[i].entry);
                ++i;
            }
            else if (target_sorted[j].lower_name < base_sorted[i].lower_name) {
                result.added.push_back(target_sorted[j].entry);
                ++j;
            }
            else {
                const auto& base_entry = base_sorted[i].entry;
                const auto& target_entry = target_sorted[j].entry;

                if (base_entry.size != target_entry.size) {
                    result.modified.push_back(target_entry);
                }
                else if (base_entry.size == 0) {
                    result.unchanged.push_back(target_entry);
                }
                else {
                    const auto base_payload = base_archive.read_entry(base_entry);
                    const auto target_payload = target_archive.read_entry(target_entry);
                    if (base_payload == target_payload) {
                        result.unchanged.push_back(target_entry);
                    }
                    else {
                        result.modified.push_back(target_entry);
                    }
                }

                ++i;
                ++j;
            }
        }

        while (i < base_sorted.size()) {
            result.removed.push_back(base_sorted[i].entry);
            ++i;
        }

        while (j < target_sorted.size()) {
            result.added.push_back(target_sorted[j].entry);
            ++j;
        }

        return result;
    }

    BigDiffResult BigDiff::compare(
        const std::filesystem::path& base_path,
        const std::filesystem::path& target_path,
        std::string_view filter_pattern
    ) {
        const BigArchive base_archive(base_path);
        const BigArchive target_archive(target_path);
        return compare(base_archive, target_archive, filter_pattern);
    }

} // namespace lotm::big
