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

#include <algorithm>
#include <cctype>
#include <cstddef>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <system_error>
#include <utility>
#include <vector>

namespace lotm::big {

    namespace {
        constexpr std::size_t DIFF_CHUNK_SIZE = 1024 * 1024;

        inline std::string to_utf8(const std::filesystem::path& p) {
            auto u8 = p.u8string();
            return std::string(reinterpret_cast<const char*>(u8.data()), u8.size());
        }

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

        struct PatchPlan {
            std::vector<detail::PackSourceRecord> file_list;
            std::vector<uint32_t> source_offsets;
            uintmax_t total_payload_size{ 0 };
            uint32_t num_files{ 0 };
            uint32_t header_size{ 0 };
            uint32_t total_size{ 0 };
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

            detail::sort_and_validate_entries(plan.file_list);

            plan.num_files = static_cast<uint32_t>(plan.file_list.size());
            uintmax_t header_size_calc = HEADER_BASE_SIZE;
            for (const auto& f : plan.file_list) {
                header_size_calc += 4 + 4 + f.rel_path.length() + 1;
            }
            header_size_calc += EA_PADDING_SIZE;

            if (header_size_calc + plan.total_payload_size > std::numeric_limits<uint32_t>::max()) {
                throw BigFormatError("Total archive size exceeds the 32-bit (4GB) BIG4 format limit.");
            }

            plan.source_offsets.reserve(plan.file_list.size());
            plan.header_size = static_cast<uint32_t>(header_size_calc);
            uint32_t current_offset = plan.header_size;
            for (auto& f : plan.file_list) {
                plan.source_offsets.push_back(source_entries[f.offset].offset);
                f.offset = current_offset;
                current_offset += f.size;
            }

            plan.total_size = current_offset;
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
        const PatchPlan plan = build_patch_plan(base_archive, target_archive, filter_pattern);

        std::vector<uint8_t> buffer(plan.total_size);
        std::size_t write_pos = 0;

        auto append_bytes = [&buffer, &write_pos](const void* data, std::size_t len) {
            std::memcpy(buffer.data() + write_pos, data, len);
            write_pos += len;
            };

        append_bytes(BIG4_MAGIC.data(), 4);

        uint32_t le_total_size = lotm::core::to_little_endian(plan.total_size);
        append_bytes(&le_total_size, sizeof(le_total_size));

        uint32_t be_num_files = lotm::core::to_big_endian(plan.num_files);
        append_bytes(&be_num_files, sizeof(be_num_files));

        uint32_t be_header_size = lotm::core::to_big_endian(plan.header_size);
        append_bytes(&be_header_size, sizeof(be_header_size));

        for (const auto& f : plan.file_list) {
            uint32_t be_offset = lotm::core::to_big_endian(f.offset);
            append_bytes(&be_offset, sizeof(be_offset));

            uint32_t be_size = lotm::core::to_big_endian(f.size);
            append_bytes(&be_size, sizeof(be_size));

            append_bytes(f.rel_path.c_str(), f.rel_path.length() + 1);
        }

        append_bytes(EA_PADDING_TAG.data(), EA_PADDING_SIZE);

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
                        char* dest_ptr = reinterpret_cast<char*>(buffer.data() + f.offset + file_bytes_transferred);
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

        return buffer;
    }

    std::vector<uint8_t> BigDiff::create_patch_to_memory(
        const std::filesystem::path& base_path,
        const std::filesystem::path& target_path,
        std::string_view filter_pattern,
        ProgressCallback progress_callback
    ) {
        const BigArchive base_archive(base_path);
        const BigArchive target_archive(target_path);
        return create_patch_to_memory(base_archive, target_archive, filter_pattern, std::move(progress_callback));
    }

    void BigDiff::create_patch(
        const BigArchive& base_archive,
        const BigArchive& target_archive,
        const std::filesystem::path& output_file,
        std::string_view filter_pattern,
        ProgressCallback progress_callback
    ) {
        if (std::filesystem::is_directory(output_file)) {
            throw std::invalid_argument("Target output path cannot be a directory: " + to_utf8(output_file));
        }

        if (auto parent = output_file.parent_path(); !parent.empty() && !std::filesystem::exists(parent)) {
            throw std::invalid_argument("Target output directory does not exist: " + to_utf8(parent));
        }

        const auto canonical_out = std::filesystem::weakly_canonical(output_file);
        if (canonical_out == std::filesystem::weakly_canonical(base_archive.file_path()) ||
            canonical_out == std::filesystem::weakly_canonical(target_archive.file_path())) {
            throw std::invalid_argument("Target output path cannot overwrite an input archive: " + to_utf8(output_file));
        }

        if (std::filesystem::exists(output_file)) {
            std::fstream probe(output_file, std::ios::in | std::ios::out | std::ios::binary);
            if (!probe.is_open()) {
                throw BigArchiveError("Cannot create output file: " + to_utf8(output_file));
            }
        }

        const PatchPlan plan = build_patch_plan(base_archive, target_archive, filter_pattern);

        std::filesystem::path temp_file = output_file;
        temp_file += ".lotm_tmp";

        std::ofstream out(temp_file, std::ios::binary);
        if (!out.is_open()) {
            throw BigArchiveError("Cannot create output file: " + to_utf8(output_file));
        }

        bool write_successful = false;
        struct CleanupGuard {
            std::ofstream& stream;
            std::filesystem::path path;
            bool& success;
            ~CleanupGuard() {
                if (!success) {
                    stream.close();
                    std::error_code ec;
                    std::filesystem::remove(path, ec);
                }
            }
        } guard{ out, temp_file, write_successful };

        out.write(BIG4_MAGIC.data(), 4);

        uint32_t le_total_size = lotm::core::to_little_endian(plan.total_size);
        out.write(reinterpret_cast<const char*>(&le_total_size), sizeof(le_total_size));

        uint32_t be_num_files = lotm::core::to_big_endian(plan.num_files);
        out.write(reinterpret_cast<const char*>(&be_num_files), sizeof(be_num_files));

        uint32_t be_header_size = lotm::core::to_big_endian(plan.header_size);
        out.write(reinterpret_cast<const char*>(&be_header_size), sizeof(be_header_size));

        for (const auto& f : plan.file_list) {
            uint32_t be_offset = lotm::core::to_big_endian(f.offset);
            out.write(reinterpret_cast<const char*>(&be_offset), sizeof(be_offset));

            uint32_t be_size = lotm::core::to_big_endian(f.size);
            out.write(reinterpret_cast<const char*>(&be_size), sizeof(be_size));

            out.write(f.rel_path.c_str(), static_cast<std::streamsize>(f.rel_path.length()));
            out.write("\0", 1);
        }

        out.write(EA_PADDING_TAG.data(), EA_PADDING_SIZE);

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

                        out.write(chunk.data(), chunk_size);
                        if (!out) {
                            throw BigArchiveError("Failed writing patch data to archive: " + to_utf8(output_file));
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

        out.flush();
        if (!out.good()) {
            throw BigArchiveError("Failed writing patch data to archive: " + to_utf8(output_file));
        }
        out.close();

        std::error_code rename_ec;
        std::filesystem::rename(temp_file, output_file, rename_ec);
        if (rename_ec) {
            throw BigArchiveError("Cannot commit output file: " + to_utf8(output_file));
        }

        write_successful = true;
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
