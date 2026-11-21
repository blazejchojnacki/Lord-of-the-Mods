/**
 * @file src/big/big_diff.cpp
 * @brief Implementation of BIG archive comparison engine
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <big/big_diff.hpp>
#include <big/big_packer.hpp>
#include <big/exceptions.hpp>
#include <big/types.hpp>
#include <core/endian.hpp>
#include <core/path_utils.hpp>
#include <core/string_utils.hpp>

#include <algorithm>
#include <cstddef>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace lotm::big {

    namespace {
        constexpr std::size_t DIFF_CHUNK_SIZE = 1024 * 1024;

        using lotm::core::to_utf8;
        using lotm::core::to_lower_ascii;

        struct IndexedEntry {
            std::string lower_name;
            BigEntry entry;
        };

        std::vector<IndexedEntry> build_sorted_index(const std::vector<BigEntry>& entries) {
            std::vector<IndexedEntry> indexed;
            indexed.reserve(entries.size());

            for (const auto& e : entries) {
                indexed.push_back(IndexedEntry{ to_lower_ascii(e.name), e });
            }

            std::sort(indexed.begin(), indexed.end(),
                [](const IndexedEntry& a, const IndexedEntry& b) {
                    return a.lower_name < b.lower_name;
                });

            return indexed;
        }

        struct PatchPlan {
            std::vector<detail::PackSourceRecord> file_list;
            std::vector<uint32_t> source_offsets;
            uintmax_t total_payload_size{ 0 };
            detail::ArchiveLayout layout{};
        };

        PatchPlan build_patch_plan(
            const BigArchive& base_archive,
            const BigArchive& target_archive,
            std::string_view filter_pattern
        ) {
            const BigDiffResult diff_result = BigDiff::compare(base_archive, target_archive, filter_pattern);

            std::vector<BigEntry> source_entries;
            source_entries.reserve(diff_result.added.size() + diff_result.modified.size());
            source_entries.insert(source_entries.end(), diff_result.added.begin(), diff_result.added.end());
            source_entries.insert(source_entries.end(), diff_result.modified.begin(), diff_result.modified.end());

            PatchPlan plan;
            plan.file_list.reserve(source_entries.size());

            for (std::size_t i = 0; i < source_entries.size(); ++i) {
                detail::PackSourceRecord rec;
                rec.rel_path = source_entries[i].name;
                for (char& c : rec.rel_path) {
                    if (c == '/') c = '\\';
                }
                rec.size = source_entries[i].size;
                rec.offset = static_cast<uint32_t>(i);
                plan.total_payload_size += rec.size;
                plan.file_list.push_back(std::move(rec));
            }

            std::vector<std::size_t> sorted_indices;
            plan.layout = detail::finalize_archive_layout(
                plan.file_list, plan.total_payload_size, &sorted_indices
            );

            plan.source_offsets.reserve(plan.file_list.size());
            for (const std::size_t orig_idx : sorted_indices) {
                plan.source_offsets.push_back(source_entries[orig_idx].offset);
            }

            return plan;
        }
    } // namespace

    BigDiffResult BigDiff::compare(
        const BigArchive& base_archive,
        const BigArchive& target_archive,
        std::string_view filter_pattern
    ) {
        const auto base_entries = base_archive.get_entries(filter_pattern);
        const auto target_entries = target_archive.get_entries(filter_pattern);

        const uintmax_t base_physical_size = base_archive.validate_extraction_quota(filter_pattern);
        const uintmax_t target_physical_size = target_archive.validate_extraction_quota(filter_pattern);

        const auto base_sorted = build_sorted_index(base_entries);
        const auto target_sorted = build_sorted_index(target_entries);

        BigDiffResult result;
        std::size_t i = 0;
        std::size_t j = 0;

        std::ifstream base_stream;
        std::ifstream target_stream;
        std::vector<char> base_buf;
        std::vector<char> target_buf;

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
                    if (static_cast<uintmax_t>(base_entry.offset) + base_entry.size > base_physical_size ||
                        static_cast<uintmax_t>(target_entry.offset) + target_entry.size > target_physical_size) {
                        throw BigFormatError("Extraction bounds exceeded for file: " + target_entry.name);
                    }

                    if (!base_stream.is_open()) {
                        base_stream.open(base_archive.file_path(), std::ios::binary);
                        target_stream.open(target_archive.file_path(), std::ios::binary);
                        if (!base_stream.is_open() || !target_stream.is_open()) {
                            throw BigArchiveError("Cannot open file for reading during diff comparison.");
                        }
                        base_buf.resize(DIFF_CHUNK_SIZE);
                        target_buf.resize(DIFF_CHUNK_SIZE);
                    }

                    base_stream.seekg(base_entry.offset, std::ios::beg);
                    target_stream.seekg(target_entry.offset, std::ios::beg);

                    uint32_t remaining = base_entry.size;
                    bool is_identical = true;
                    while (remaining > 0) {
                        const auto chunk_size = static_cast<std::streamsize>(
                            std::min<std::size_t>(remaining, base_buf.size()));
                        base_stream.read(base_buf.data(), chunk_size);
                        target_stream.read(target_buf.data(), chunk_size);
                        if (!base_stream || !target_stream ||
                            base_stream.gcount() != chunk_size || target_stream.gcount() != chunk_size) {
                            throw BigArchiveError("Failed to read payload for file: " + target_entry.name);
                        }
                        if (std::memcmp(base_buf.data(), target_buf.data(), static_cast<std::size_t>(chunk_size)) != 0) {
                            is_identical = false;
                            break;
                        }
                        remaining -= static_cast<uint32_t>(chunk_size);
                    }

                    if (is_identical) {
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

    std::vector<uint8_t> BigDiff::create_patch_to_memory(
        const BigArchive& base_archive,
        const BigArchive& target_archive,
        std::string_view filter_pattern,
        ProgressCallback progress_callback
    ) {
        std::vector<uint8_t> result;
        create_patch_to_memory(base_archive, target_archive, [&](std::size_t size) {
            result.resize(size);
            return result.data();
            }, filter_pattern, std::move(progress_callback));
        return result;
    }

    void BigDiff::create_patch_to_memory(
        const BigArchive& base_archive,
        const BigArchive& target_archive,
        const BufferAllocator& allocator,
        std::string_view filter_pattern,
        ProgressCallback progress_callback
    ) {
        const PatchPlan plan = build_patch_plan(base_archive, target_archive, filter_pattern);
        uint8_t* buffer = detail::allocate_and_write_header(plan.file_list, plan.layout, allocator);

        if (!plan.file_list.empty()) {
            std::ifstream src(target_archive.file_path(), std::ios::binary);
            if (!src.is_open()) {
                throw BigArchiveError("Cannot open file for reading: " + to_utf8(target_archive.file_path()));
            }

            uint64_t total_bytes_transferred = 0;

            for (std::size_t i = 0; i < plan.file_list.size(); ++i) {
                const auto& f = plan.file_list[i];
                if (f.size > 0) {
                    src.seekg(plan.source_offsets[i], std::ios::beg);
                    if (!src) {
                        throw BigArchiveError("Failed to seek to offset for file: " + f.rel_path);
                    }

                    uint32_t remaining = f.size;
                    uint64_t file_bytes_transferred = 0;
                    while (remaining > 0) {
                        const auto chunk_size = static_cast<std::streamsize>(
                            std::min<std::size_t>(remaining, DIFF_CHUNK_SIZE));
                        char* dest_ptr = reinterpret_cast<char*>(buffer + f.offset + file_bytes_transferred);
                        src.read(dest_ptr, chunk_size);
                        if (!src || src.gcount() != chunk_size) {
                            throw BigArchiveError("Failed to read payload for file: " + f.rel_path);
                        }

                        remaining -= static_cast<uint32_t>(chunk_size);
                        file_bytes_transferred += static_cast<uint64_t>(chunk_size);
                        total_bytes_transferred += static_cast<uint64_t>(chunk_size);

                        if (progress_callback) {
                            const ProgressReport report{
                                f.rel_path,
                                file_bytes_transferred,
                                f.size,
                                total_bytes_transferred,
                                static_cast<uint64_t>(plan.total_payload_size)
                            };
                            if (!progress_callback(report)) {
                                throw BigArchiveError("Operation cancelled by progress callback.");
                            }
                        }
                    }
                }
                else if (progress_callback) {
                    const ProgressReport report{
                        f.rel_path,
                        0,
                        0,
                        total_bytes_transferred,
                        static_cast<uint64_t>(plan.total_payload_size)
                    };
                    if (!progress_callback(report)) {
                        throw BigArchiveError("Operation cancelled by progress callback.");
                    }
                }
            }
        }
    }

    std::vector<uint8_t> BigDiff::create_patch_to_memory(
        const std::filesystem::path& base_path,
        const std::filesystem::path& target_path,
        std::string_view filter_pattern,
        ProgressCallback progress_callback
    ) {
        std::vector<uint8_t> result;
        create_patch_to_memory(base_path, target_path, [&](std::size_t size) {
            result.resize(size);
            return result.data();
            }, filter_pattern, std::move(progress_callback));
        return result;
    }

    void BigDiff::create_patch_to_memory(
        const std::filesystem::path& base_path,
        const std::filesystem::path& target_path,
        const BufferAllocator& allocator,
        std::string_view filter_pattern,
        ProgressCallback progress_callback
    ) {
        const BigArchive base_archive(base_path);
        const BigArchive target_archive(target_path);
        create_patch_to_memory(base_archive, target_archive, allocator, filter_pattern, std::move(progress_callback));
    }

    void BigDiff::create_patch(
        const BigArchive& base_archive,
        const BigArchive& target_archive,
        const std::filesystem::path& output_file,
        std::string_view filter_pattern,
        ProgressCallback progress_callback
    ) {
        detail::validate_output_file_target(output_file);

        const auto canonical_out = std::filesystem::weakly_canonical(output_file);
        if (canonical_out == std::filesystem::weakly_canonical(base_archive.file_path()) ||
            canonical_out == std::filesystem::weakly_canonical(target_archive.file_path())) {
            throw std::invalid_argument("Target output path cannot overwrite an input archive: " + to_utf8(output_file));
        }

        detail::probe_output_file_writable(output_file);

        const PatchPlan plan = build_patch_plan(base_archive, target_archive, filter_pattern);

        detail::AtomicArchiveWriter writer(output_file);
        writer.write_header(plan.file_list, plan.layout);

        if (!plan.file_list.empty()) {
            std::ifstream src(target_archive.file_path(), std::ios::binary);
            if (!src.is_open()) {
                throw BigArchiveError("Cannot open file for reading: " + to_utf8(target_archive.file_path()));
            }

            std::vector<char> chunk(DIFF_CHUNK_SIZE);
            uint64_t total_bytes_transferred = 0;

            for (std::size_t i = 0; i < plan.file_list.size(); ++i) {
                const auto& f = plan.file_list[i];
                if (f.size > 0) {
                    src.seekg(plan.source_offsets[i], std::ios::beg);
                    if (!src) {
                        throw BigArchiveError("Failed to seek to offset for file: " + f.rel_path);
                    }

                    uint32_t remaining = f.size;
                    uint64_t file_bytes_transferred = 0;
                    while (remaining > 0) {
                        const auto chunk_size = static_cast<std::streamsize>(
                            std::min<std::size_t>(remaining, chunk.size()));
                        src.read(chunk.data(), chunk_size);
                        if (!src || src.gcount() != chunk_size) {
                            throw BigArchiveError("Failed to read payload for file: " + f.rel_path);
                        }

                        writer.write_chunk(chunk.data(), chunk_size, "Failed writing patch data to archive: ");

                        remaining -= static_cast<uint32_t>(chunk_size);
                        file_bytes_transferred += static_cast<uint64_t>(chunk_size);
                        total_bytes_transferred += static_cast<uint64_t>(chunk_size);

                        if (progress_callback) {
                            const ProgressReport report{
                                f.rel_path,
                                file_bytes_transferred,
                                f.size,
                                total_bytes_transferred,
                                static_cast<uint64_t>(plan.total_payload_size)
                            };
                            if (!progress_callback(report)) {
                                throw BigArchiveError("Operation cancelled by progress callback.");
                            }
                        }
                    }
                }
                else if (progress_callback) {
                    const ProgressReport report{
                        f.rel_path,
                        0,
                        0,
                        total_bytes_transferred,
                        static_cast<uint64_t>(plan.total_payload_size)
                    };
                    if (!progress_callback(report)) {
                        throw BigArchiveError("Operation cancelled by progress callback.");
                    }
                }
            }
        }

        writer.commit("Failed writing patch data to archive: ");
    }

    void BigDiff::create_patch(
        const std::filesystem::path& base_path,
        const std::filesystem::path& target_path,
        const std::filesystem::path& output_file,
        std::string_view filter_pattern,
        ProgressCallback progress_callback
    ) {
        const BigArchive base_archive(base_path);
        const BigArchive target_archive(target_path);
        create_patch(base_archive, target_archive, output_file, filter_pattern, std::move(progress_callback));
    }

} // namespace lotm::big
