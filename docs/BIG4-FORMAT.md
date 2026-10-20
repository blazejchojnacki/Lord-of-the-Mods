# EA BIG4 Archive Specification

The SAGE engine utilizes the `BIG4` container format (FourCC: `BIG4`).

## Header Layout
| Field | Offset | Size | Endianness | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Magic | 0x00 | 4 B | Little-Endian | ASCII string `"BIG4"` |
| Total Size | 0x04 | 4 B | Little-Endian | Total archive byte count |
| File Count | 0x08 | 4 B | Big-Endian | Number of indexed files |
| Header Size | 0x0C | 4 B | Big-Endian | Offset where raw file data begins |

## Index Entry Layout
Repeated `File Count` times immediately following the header:
| Field | Size | Endianness | Notes |
| :--- | :--- | :--- | :--- |
| File Offset | 4 B | Big-Endian | Absolute byte offset of file data |
| File Size | 4 B | Big-Endian | Size of uncompressed file data |
| Path Name | Variable | ASCII | Null-terminated string (`\0`), backslash separated |

## Critical Format Quirks
1. **Alphabetical Sorting:** Entries in the index table MUST be sorted alphabetically using standard ASCII comparisons. The SAGE runtime performs a `bsearch` on the index; an unsorted index leads to file lookup failures or game crashes.
2. **Padding Block:** Original BFME archives contain an 8-byte padding tag (`"L219    "`) directly between the end of the last null-terminated file path and the start of the first file payload.
