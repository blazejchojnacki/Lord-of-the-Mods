// Gemini Pro 3.1

#pragma once

#include <filesystem>

namespace lotm::big {

    class BigPacker {
    public:
        static void pack_from_directory(const std::filesystem::path& source_dir, const std::filesystem::path& output_file);
    };

} // namespace lotm::big
