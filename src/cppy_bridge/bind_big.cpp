// Gemini Pro 3.1

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/filesystem.h>
#include <nanobind/stl/vector.h>

#include "register.hpp"
#include <big/big_unpack.hpp>

namespace nb = nanobind;

namespace lotm::python {

    void register_big_bindings(nb::module_& m) {
        auto sub = m.def_submodule("big", "BIG archive handling");

        nb::class_<lotm::big::BigEntry>(sub, "BigEntry")
            .def_ro("offset", &lotm::big::BigEntry::offset)
            .def_ro("size", &lotm::big::BigEntry::size)
            .def_ro("name", &lotm::big::BigEntry::name);

        nb::class_<lotm::big::BigArchive>(sub, "BigArchive")
            .def(nb::init<std::filesystem::path>(), nb::arg("file_path"))
            .def("read_header", &lotm::big::BigArchive::read_header)
            .def("extract_all", &lotm::big::BigArchive::extract_all, nb::arg("output_dir"))
            .def("get_entries", &lotm::big::BigArchive::get_entries);
    }

    // Static instance registers this function before NB_MODULE executes
    static BindingRegistrar big_registrar(&register_big_bindings);

} // namespace lotm::python
