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
#include <core/path_utils.hpp>
#include <core/string_utils.hpp>

#include <algorithm>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <unordered_set>
#include <utility>
#include <vector>

namespace lotm::big {

    namespace {
        using lotm::core::to_utf8;
        using lotm::core::to_lower_ascii;

        void validate_pack_rel_path(std::string_view rel_path) {
            if (rel_path.empty() ||
                rel_path.find('\0') != std::string_view::npos ||
                rel_path.front() == '\\' ||
                rel_path.front() == '/' ||
                rel_path.back() == '\\' ||
                rel_path.back() == '/') {
                throw std::invalid_argument("Invalid or unsafe archive entry path: " + std::string(rel_path));
            }

            std::size_t start = 0;
            while (start < rel_path.size()) {
                std::size_t end = rel_path.find_first_of("\\/", start);
                std::string_view segment = (end == std::string_view::npos)
                    ? rel_path.substr(start)
                    : rel_path.substr(start, end - start);

                if (lotm::core::is_unsafe_ntfs_component(segment)) {
                    throw std::invalid_argument("Invalid or unsafe archive entry path: " + std::string(rel_path));
                }

                if (end == std::string_view::npos) {
                    break;
                }
                start = end + 1;
            }
        }
    } // namespace

    namespace detail {
        void sort_and_validate_entries(std::vector<PackSourceRecord>& entries) {
            std::sort(entries.begin(), entries.end(), [](const PackSourceRecord& a, const PackSourceRecord& b) {
                return a.rel_path < b.rel_path;
                });

            std::unordered_set<std::string> seen_paths;
            for (const auto& f : entries) {
                validate_pack_rel_path(f.rel_path);

                std::string lower_path = to_lower_ascii(f.rel_path);

                if (!seen_paths.insert(lower_path).second) {
                    throw std::invalid_argument("Duplicate case-insensitive path detected: " + f.rel_path);
                }
            }
        }

        void collect_directory_files(
            const std::filesystem::path& source_dir,
            std::vector<PackSourceRecord>& file_list,
            uintmax_t& total_payload_size
        ) {
            total_payload_size = 0;
            for (const auto& entry : std::filesystem::recursive_directory_iterator(source_dir)) {
                if (entry.is_regular_file()) {
                    PackSourceRecord pack_entry;
                    pack_entry.full_path = entry.path();

                    auto rel_path = std::filesystem::relative(entry.path(), source_dir);
                    pack_entry.rel_path = to_utf8(rel_path);
                    for (char& c : pack_entry.rel_path) {
                        if (c == '/') c = '\\';
                    }

                    uintmax_t fsize = std::filesystem::file_size(entry.path());

                    // Guard against individual files exceeding 32-bit limits
                    if (fsize > std::numeric_limits<uint32_t>::max()) {
                        throw BigFormatError("File '" + pack_entry.rel_path + "' exceeds the 4GB format limit.");
                    }

                    pack_entry.size = static_cast<uint32_t>(fsize);
                    total_payload_size += fsize;
                    file_list.push_back(std::move(pack_entry));
                }
            }
        }

        ArchiveLayout finalize_archive_layout(
            std::vector<PackSourceRecord>& file_list,
            uintmax_t total_payload_size,
            std::vector<std::size_t>* out_original_indices
        ) {
            // Prevent case-insensitive overwrites in SAGE engine.
            sort_and_validate_entries(file_list);

            uint32_t num_files = static_cast<uint32_t>(file_list.size());
            uintmax_t header_size_calc = HEADER_BASE_SIZE;
            for (const auto& f : file_list) {
                header_size_calc += 4 + 4 + f.rel_path.length() + 1;
            }

            // + 8 for byte-for-byte alignment with the EA "L219" gap
            header_size_calc += EA_PADDING_SIZE;

            // Guard against total archive size exceeding 32-bit limits (4GB overflow)
            if (header_size_calc + total_payload_size > std::numeric_limits<uint32_t>::max()) {
                throw BigFormatError("Total archive size exceeds the 32-bit (4GB) BIG4 format limit.");
            }

            if (out_original_indices) {
                out_original_indices->reserve(file_list.size());
            }

            uint32_t header_size = static_cast<uint32_t>(header_size_calc);
            uint32_t current_offset = header_size;
            for (auto& f : file_list) {
                if (out_original_indices) {
                    out_original_indices->push_back(static_cast<std::size_t>(f.offset));
                }
                f.offset = current_offset;
                current_offset += f.size;
            }

            return ArchiveLayout{ num_files, header_size, current_offset };
        }

        uint8_t* allocate_and_write_header(
            const std::vector<PackSourceRecord>& file_list,
            const ArchiveLayout& layout,
            const BufferAllocator& allocator
        ) {
            uint8_t* buffer = allocator(layout.total_size);
            if (!buffer) throw std::bad_alloc();

            std::size_t write_pos = 0;

            auto append_bytes = [buffer, &write_pos](const void* data, std::size_t len) {
                std::memcpy(buffer + write_pos, data, len);
                write_pos += len;
                };

            append_bytes(BIG4_MAGIC.data(), 4);

            uint32_t le_total_size = lotm::core::to_little_endian(layout.total_size);
            append_bytes(&le_total_size, sizeof(le_total_size));

            uint32_t be_num_files = lotm::core::to_big_endian(layout.num_files);
            append_bytes(&be_num_files, sizeof(be_num_files));

            uint32_t be_header_size = lotm::core::to_big_endian(layout.header_size);
            append_bytes(&be_header_size, sizeof(be_header_size));

            for (const auto& f : file_list) {
                uint32_t be_offset = lotm::core::to_big_endian(f.offset);
                append_bytes(&be_offset, sizeof(be_offset));

                uint32_t be_size = lotm::core::to_big_endian(f.size);
                append_bytes(&be_size, sizeof(be_size));

                append_bytes(f.rel_path.c_str(), f.rel_path.length() + 1);
            }

            // for byte-for-byte alignment with the EA "L219" gap
            append_bytes(EA_PADDING_TAG.data(), EA_PADDING_SIZE);

            return buffer;
        }

        void validate_output_file_target(const std::filesystem::path& output_file) {
            if (std::filesystem::is_directory(output_file)) {
                throw std::invalid_argument("Target output path cannot be a directory: " + to_utf8(output_file));
            }

            if (auto parent = output_file.parent_path(); !parent.empty() && !std::filesystem::exists(parent)) {
                throw std::invalid_argument("Target output directory does not exist: " + to_utf8(parent));
            }
        }

        void probe_output_file_writable(const std::filesystem::path& output_file) {
            if (std::filesystem::exists(output_file)) {
                std::fstream probe(output_file, std::ios::in | std::ios::out | std::ios::binary);
                if (!probe.is_open()) {
                    throw BigArchiveError("Cannot create output file: " + to_utf8(output_file));
                }
            }
        }

        AtomicArchiveWriter::AtomicArchiveWriter(const std::filesystem::path& output_file)
            : output_file_(output_file),
            temp_file_(output_file) {
            temp_file_ += ".lotm_tmp";
            out_.open(temp_file_, std::ios::binary);
            if (!out_.is_open()) {
                throw BigArchiveError("Cannot create output file: " + to_utf8(output_file_));
            }
        }

        AtomicArchiveWriter::~AtomicArchiveWriter() noexcept {
            if (!committed_) {
                out_.close();
                std::error_code ec;
                std::filesystem::remove(temp_file_, ec);
            }
        }

        void AtomicArchiveWriter::write_header(
            const std::vector<PackSourceRecord>& file_list,
            const ArchiveLayout& layout
        ) {
            out_.write(BIG4_MAGIC.data(), 4);

            uint32_t le_total_size = lotm::core::to_little_endian(layout.total_size);
            out_.write(reinterpret_cast<const char*>(&le_total_size), sizeof(le_total_size));

            uint32_t be_num_files = lotm::core::to_big_endian(layout.num_files);
            out_.write(reinterpret_cast<const char*>(&be_num_files), sizeof(be_num_files));

            uint32_t be_header_size = lotm::core::to_big_endian(layout.header_size);
            out_.write(reinterpret_cast<const char*>(&be_header_size), sizeof(be_header_size));

            for (const auto& f : file_list) {
                uint32_t be_offset = lotm::core::to_big_endian(f.offset);
                out_.write(reinterpret_cast<const char*>(&be_offset), sizeof(be_offset));

                uint32_t be_size = lotm::core::to_big_endian(f.size);
                out_.write(reinterpret_cast<const char*>(&be_size), sizeof(be_size));

                out_.write(f.rel_path.c_str(), static_cast<std::streamsize>(f.rel_path.length()));
                out_.write("\0", 1);
            }

            // for byte-for-byte alignment with the EA "L219" gap
            out_.write(EA_PADDING_TAG.data(), EA_PADDING_SIZE);
        }

        void AtomicArchiveWriter::write_chunk(
            const char* data,
            std::streamsize size,
            std::string_view write_error_prefix
        ) {
            out_.write(data, size);
            if (!out_) {
                throw BigArchiveError(std::string(write_error_prefix) + to_utf8(output_file_));
            }
        }

        void AtomicArchiveWriter::commit(std::string_view write_error_prefix) {
            out_.flush();
            if (!out_.good()) {
                throw BigArchiveError(std::string(write_error_prefix) + to_utf8(output_file_));
            }
            out_.close();

            std::error_code rename_ec;
            std::filesystem::rename(temp_file_, output_file_, rename_ec);
            if (rename_ec) {
                throw BigArchiveError("Cannot commit output file: " + to_utf8(output_file_));
            }

            committed_ = true;
        }
    } // namespace detail

    void BigPacker::pack_from_directory(
        const std::filesystem::path& source_dir,
        const std::filesystem::path& output_file,
        ProgressCallback progress_callback
    ) {
        if (!std::filesystem::exists(source_dir) || !std::filesystem::is_directory(source_dir)) {
            throw std::invalid_argument("Source directory does not exist or is not a directory.");
        }

        detail::validate_output_file_target(output_file);

        // Guard against output_file residing inside source_dir (self-inclusion)
        const std::filesystem::path canonical_source = std::filesystem::weakly_canonical(source_dir);
        const std::filesystem::path canonical_output = std::filesystem::weakly_canonical(output_file);
        auto mismatch_pair = std::mismatch(
            canonical_source.begin(), canonical_source.end(),
            canonical_output.begin(), canonical_output.end());
        if (mismatch_pair.first == canonical_source.end()) {
            throw std::invalid_argument(
                "Target output archive cannot reside inside the source directory: " + to_utf8(output_file));
        }

        detail::probe_output_file_writable(output_file);

        std::vector<detail::PackSourceRecord> file_list;
        uintmax_t total_payload_size = 0;
        detail::collect_directory_files(source_dir, file_list, total_payload_size);

        const detail::ArchiveLayout layout = detail::finalize_archive_layout(file_list, total_payload_size);

        detail::AtomicArchiveWriter writer(output_file);
        writer.write_header(file_list, layout);

        std::vector<char> chunk(1024 * 1024);
        uint64_t total_bytes_transferred = 0;

        for (const auto& f : file_list) {
            std::ifstream src(f.full_path, std::ios::binary);
            if (!src.is_open()) {
                throw BigArchiveError("Cannot read source file: " + to_utf8(f.full_path));
            }

            uintmax_t bytes_copied = 0;
            while (src) {
                src.read(chunk.data(), static_cast<std::streamsize>(chunk.size()));
                std::streamsize bytes_read = src.gcount();
                if (bytes_read > 0) {
                    writer.write_chunk(chunk.data(), bytes_read, "Failed writing data to archive: ");
                    bytes_copied += static_cast<uintmax_t>(bytes_read);
                    total_bytes_transferred += static_cast<uint64_t>(bytes_read);

                    if (progress_callback) {
                        const ProgressReport report{
                            f.rel_path,
                            static_cast<uint64_t>(bytes_copied),
                            f.size,
                            total_bytes_transferred,
                            static_cast<uint64_t>(total_payload_size)
                        };
                        if (!progress_callback(report)) {
                            throw BigArchiveError("Operation cancelled by progress callback.");
                        }
                    }
                }
            }

            if (src.bad() || bytes_copied != f.size) {
                throw BigArchiveError("Byte count mismatch while packing file: " + f.rel_path);
            }

            if (f.size == 0 && progress_callback) {
                const ProgressReport report{
                    f.rel_path,
                    0,
                    0,
                    total_bytes_transferred,
                    static_cast<uint64_t>(total_payload_size)
                };
                if (!progress_callback(report)) {
                    throw BigArchiveError("Operation cancelled by progress callback.");
                }
            }
        }

        writer.commit("Failed writing data to archive: ");
    }

    std::vector<uint8_t> BigPacker::pack_to_memory(
        const std::filesystem::path& source_dir,
        ProgressCallback progress_callback
    ) {
        std::vector<uint8_t> result;
        pack_to_memory(source_dir, [&](std::size_t size) {
            result.resize(size);
            return result.data();
            }, std::move(progress_callback));
        return result;
    }

    void BigPacker::pack_to_memory(
        const std::filesystem::path& source_dir,
        const BufferAllocator& allocator,
        ProgressCallback progress_callback
    ) {
        if (!std::filesystem::exists(source_dir) || !std::filesystem::is_directory(source_dir)) {
            throw std::invalid_argument("Source directory does not exist or is not a directory.");
        }

        std::vector<detail::PackSourceRecord> file_list;
        uintmax_t total_payload_size = 0;
        detail::collect_directory_files(source_dir, file_list, total_payload_size);

        const detail::ArchiveLayout layout = detail::finalize_archive_layout(file_list, total_payload_size);
        uint8_t* buffer = detail::allocate_and_write_header(file_list, layout, allocator);
        uint64_t total_bytes_transferred = 0;

        for (const auto& f : file_list) {
            std::ifstream src(f.full_path, std::ios::binary);
            if (!src.is_open()) {
                throw BigArchiveError("Cannot read source file: " + to_utf8(f.full_path));
            }

            if (f.size > 0) {
                src.read(reinterpret_cast<char*>(buffer + f.offset), static_cast<std::streamsize>(f.size));
                if (src.bad() || static_cast<uint32_t>(src.gcount()) != f.size) {
                    throw BigArchiveError("Byte count mismatch while packing file: " + f.rel_path);
                }
            }

            total_bytes_transferred += f.size;

            if (progress_callback) {
                const ProgressReport report{
                    f.rel_path,
                    f.size,
                    f.size,
                    total_bytes_transferred,
                    static_cast<uint64_t>(total_payload_size)
                };
                if (!progress_callback(report)) {
                    throw BigArchiveError("Operation cancelled by progress callback.");
                }
            }
        }
    }

    std::vector<uint8_t> BigPacker::pack_to_memory(
        std::span<const std::pair<std::string, std::span<const uint8_t>>> files,
        ProgressCallback progress_callback
    ) {
        std::vector<uint8_t> result;
        pack_to_memory(files, [&](std::size_t size) {
            result.resize(size);
            return result.data();
            }, std::move(progress_callback));
        return result;
    }

    void BigPacker::pack_to_memory(
        std::span<const std::pair<std::string, std::span<const uint8_t>>> files,
        const BufferAllocator& allocator,
        ProgressCallback progress_callback
    ) {
        std::vector<detail::PackSourceRecord> file_list;
        file_list.reserve(files.size());
        uintmax_t total_payload_size = 0;

        for (std::size_t i = 0; i < files.size(); ++i) {
            const auto& [raw_path, payload] = files[i];
            if (raw_path.empty()) {
                throw std::invalid_argument("Entry path cannot be empty.");
            }

            detail::PackSourceRecord pack_entry;
            pack_entry.rel_path = raw_path;
            for (char& c : pack_entry.rel_path) {
                if (c == '/') c = '\\';
            }

            if (payload.size() > std::numeric_limits<uint32_t>::max()) {
                throw BigFormatError("File '" + pack_entry.rel_path + "' exceeds the 4GB format limit.");
            }

            pack_entry.size = static_cast<uint32_t>(payload.size());
            // Store original index temporarily in offset prior to alphabetical sorting
            pack_entry.offset = static_cast<uint32_t>(i);
            total_payload_size += payload.size();
            file_list.push_back(std::move(pack_entry));
        }

        std::vector<std::size_t> sorted_indices;
        const detail::ArchiveLayout layout = detail::finalize_archive_layout(
            file_list, total_payload_size, &sorted_indices
        );
        uint8_t* buffer = detail::allocate_and_write_header(file_list, layout, allocator);
        uint64_t total_bytes_transferred = 0;

        for (std::size_t i = 0; i < file_list.size(); ++i) {
            const auto& f = file_list[i];
            const auto& payload = files[sorted_indices[i]].second;
            if (!payload.empty()) {
                std::memcpy(buffer + f.offset, payload.data(), payload.size());
            }

            total_bytes_transferred += f.size;

            if (progress_callback) {
                const ProgressReport report{
                    f.rel_path,
                    f.size,
                    f.size,
                    total_bytes_transferred,
                    static_cast<uint64_t>(total_payload_size)
                };
                if (!progress_callback(report)) {
                    throw BigArchiveError("Operation cancelled by progress callback.");
                }
            }
        }
    }

    std::vector<uint8_t> BigPacker::pack_to_memory(
        const std::vector<std::pair<std::string, std::vector<uint8_t>>>& files,
        ProgressCallback progress_callback
    ) {
        std::vector<std::pair<std::string, std::span<const uint8_t>>> span_files;
        span_files.reserve(files.size());
        for (const auto& [raw_path, payload] : files) {
            span_files.emplace_back(raw_path, std::span<const uint8_t>(payload.data(), payload.size()));
        }
        return pack_to_memory(
            std::span<const std::pair<std::string, std::span<const uint8_t>>>(span_files),
            std::move(progress_callback)
        );
    }

} // namespace lotm::big
