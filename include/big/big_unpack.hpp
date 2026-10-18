// Gemini Pro 3.1

#pragma once

#include <filesystem>
#include <string>
#include <vector>
#include <cstdint>

namespace lotm::big {

    struct BigEntry {
        uint32_t offset;
        uint32_t size;
        std::string name;
    };

    class BigArchive {
    public:
        explicit BigArchive(std::filesystem::path file_path);

        // Parses the header and file index
        void read_header();

        // Extracts all files to the output directory (equivalent to read_big4)
        void extract_all(const std::filesystem::path& output_dir);

        [[nodiscard]] const std::vector<BigEntry>& get_entries() const noexcept { return entries_; }

    private:
        std::filesystem::path file_path_;
        std::vector<BigEntry> entries_;
        uint32_t total_size_{ 0 };
        uint32_t header_size_{ 0 };

        // Helper for Big-Endian conversion (equivalent to struct.unpack('>I'))
        static uint32_t swap_endian(uint32_t val) noexcept;
    };

} // namespace lotm::big
