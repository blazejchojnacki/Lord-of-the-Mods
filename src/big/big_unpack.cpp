// Gemini Pro 3.1

#include <big/big_unpack.hpp>
#include <core/endian.hpp>
#include <fstream>
#include <stdexcept>
#include <iostream>
#include <string_view>

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
        if (std::string_view(magic) != BIG4_MAGIC) {
            throw std::invalid_argument(std::string("Not a BIG4 file! Found: ") + magic);
        }

        // Total size (Little Endian - '<I')
        file.read(reinterpret_cast<char*>(&total_size_), sizeof(total_size_));

        // Number of files and header size (Big Endian - hence swapping)
        uint32_t num_files = 0;
        file.read(reinterpret_cast<char*>(&num_files), sizeof(num_files));
        num_files = lotm::core::from_big_endian(num_files);

        file.read(reinterpret_cast<char*>(&header_size_), sizeof(header_size_));
        header_size_ = lotm::core::from_big_endian(header_size_);

        std::cout << "File: " << file_path_.string() << '\n';
        std::cout << "Number of files inside: " << num_files << '\n';

        entries_.reserve(num_files);

        // Index reading
        for (uint32_t i = 0; i < num_files; ++i) {
            BigEntry entry;

            file.read(reinterpret_cast<char*>(&entry.offset), sizeof(entry.offset));
            entry.offset = lotm::core::from_big_endian(entry.offset);

            file.read(reinterpret_cast<char*>(&entry.size), sizeof(entry.size));
            entry.size = lotm::core::from_big_endian(entry.size);

            // Read file name until null byte
            entry.name = read_null_terminated_string(file);

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

        // File extraction
        for (const auto& entry : entries_) {
            std::filesystem::path target_path = output_dir / entry.name;
            std::filesystem::path target_subdir = target_path.parent_path();

            if (!std::filesystem::exists(target_subdir)) {
                std::filesystem::create_directories(target_subdir);
            }

            file.seekg(entry.offset, std::ios::beg);

            // Read directly to a vector buffer
            std::vector<char> buffer(entry.size);
            file.read(buffer.data(), entry.size);

            std::ofstream out_file(target_path, std::ios::binary);
            out_file.write(buffer.data(), entry.size);

            std::cout << "Extracted: " << entry.name << '\n';
        }
    }

} // namespace lotm::big
