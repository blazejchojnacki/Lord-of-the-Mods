// Gemini Pro 3.1

#include <nanobind/nanobind.h>
#include "register.hpp"

NB_MODULE(lotm, m) {
    for (const auto& init_fn : lotm::python::get_registry()) {
        init_fn(m);
    }
}
