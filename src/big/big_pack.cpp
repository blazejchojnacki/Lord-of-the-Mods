// Gemini Pro 3.1

#include <big/big_pack.hpp>
#include <fstream>
#include <stdexcept>
#include <vector>
#include <iostream>
#include <string>

namespace lotm::big {

    // Local byte swap to avoid modifying big_unpack.cpp or requiring a core library dependency here
    static uint32_t swap_endian_pack(uint32_t val) noexcept {
        return ((val & 0xFF000000) >> 24) |
            ((val & 0x00FF0000) >> 8) |
            ((val & 0x0000FF00) << 8) |
            ((val & 0x000000FF) << 24);
    }

    void BigPacker::pack_from_directory(const std::filesystem::path& source_dir, const std::filesystem::path& output_file) {
        if (!std::filesystem::exists(source_dir) || !std::filesystem::is_directory(source_dir)) {
            throw std::invalid_argument("Source directory does not exist or is not a directory.");
        }

        struct PackEntry {
            std::filesystem::path full_path;
            std::string rel_path;
            uint32_t size{ 0 };
            uint32_t offset{ 0 };
        };

        std::vector<PackEntry> file_list;

        for (const auto& entry : std::filesystem::recursive_directory_iterator(source_dir)) {
            if (entry.is_regular_file()) {
                PackEntry pack_entry;
                pack_entry.full_path = entry.path();

                auto rel_path = std::filesystem::relative(entry.path(), source_dir);
                pack_entry.rel_path = rel_path.string();
                for (char& c : pack_entry.rel_path) {
                    if (c == '/') c = '\\';
                }

                pack_entry.size = static_cast<uint32_t>(std::filesystem::file_size(entry.path()));
                file_list.push_back(std::move(pack_entry));
            }
        }

        uint32_t num_files = static_cast<uint32_t>(file_list.size());
        uint32_t header_size = 16;
        for (const auto& f : file_list) {
            header_size += 4 + 4 + static_cast<uint32_t>(f.rel_path.length()) + 1;
        }

        uint32_t current_offset = header_size;
        for (auto& f : file_list) {
            f.offset = current_offset;
            current_offset += f.size;
        }

        uint32_t total_size = current_offset;

        std::cout << "Creating archive: " << output_file.string() << '\n';
        std::ofstream out(output_file, std::ios::binary);
        if (!out.is_open()) {
            throw std::runtime_error("Cannot create output file: " + output_file.string());
        }

        out.write("BIG4", 4);
        out.write(reinterpret_cast<const char*>(&total_size), sizeof(total_size));

        uint32_t be_num_files = swap_endian_pack(num_files);
        out.write(reinterpret_cast<const char*>(&be_num_files), sizeof(be_num_files));

        uint32_t be_header_size = swap_endian_pack(header_size);
        out.write(reinterpret_cast<const char*>(&be_header_size), sizeof(be_header_size));

        for (const auto& f : file_list) {
            uint32_t be_offset = swap_endian_pack(f.offset);
            out.write(reinterpret_cast<const char*>(&be_offset), sizeof(be_offset));

            uint32_t be_size = swap_endian_pack(f.size);
            out.write(reinterpret_cast<const char*>(&be_size), sizeof(be_size));

            out.write(f.rel_path.c_str(), f.rel_path.length());
            out.write("\0", 1);
        }

        std::vector<char> chunk(1024 * 1024);
        for (const auto& f : file_list) {
            std::cout << "Packing: " << f.rel_path << '\n';
            std::ifstream src(f.full_path, std::ios::binary);
            if (!src.is_open()) {
                throw std::runtime_error("Cannot read source file: " + f.full_path.string());
            }

            while (src) {
                src.read(chunk.data(), chunk.size());
                std::streamsize bytes_read = src.gcount();
                if (bytes_read > 0) {
                    out.write(chunk.data(), bytes_read);
                }
            }
        }

        std::cout << "\nSuccess! Created file: " << output_file.string() << '\n';
        std::cout << "Total size: " << total_size << " bytes\n";
    }

} // namespace lotm::big
