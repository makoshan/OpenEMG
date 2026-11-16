#pragma once
#include <cstdlib>
#include <cstring>
#include <mach-o/getsect.h>
#include <mach-o/ldsyms.h>
#include "../hw_twin/v001_board.hpp"

struct SectSnap {
    const char   *sect_name;
    uint8_t      *seg;
    uint8_t      *snap;
    unsigned long sz;
};

inline void restore_sections(SectSnap *arr, int n) {
    for (int i = 0; i < n; i++) {
        if (!arr[i].snap) {
            arr[i].seg = getsectiondata(&_mh_dylib_header, "__DATA", arr[i].sect_name, &arr[i].sz);
            if (arr[i].seg && arr[i].sz > 0) {
                arr[i].snap = (uint8_t *)std::malloc(arr[i].sz);
                std::memcpy(arr[i].snap, arr[i].seg, arr[i].sz);
            }
        } else if (arr[i].seg && arr[i].sz > 0) {
            std::memcpy(arr[i].seg, arr[i].snap, arr[i].sz);
        }
    }
}

inline void register_sections_for_nrf_dma(SectSnap *arr, int n) {
    for (int i = 0; i < n; i++) {
        if (!arr[i].seg) {
            arr[i].seg = getsectiondata(&_mh_dylib_header, "__DATA", arr[i].sect_name, &arr[i].sz);
        }
        if (arr[i].seg && arr[i].sz > 0) {
            sim_register_nrf_ptr(arr[i].seg, (size_t)arr[i].sz);
        }
    }
}
