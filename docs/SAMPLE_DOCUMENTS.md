# Sample Document Examples

This document provides representative samples of the realistic test data used in our benchmarks. These samples demonstrate the nested document structures generated when using the `-rd` (realistic data) flag.

## Overview

The benchmark tool generates two types of documents:

1. **Standard documents**: Use flat binary payload blobs for the `data` field (not shown in JSON serialization)
2. **Realistic documents**: Use nested structures with mixed data types including strings, integers, decimals, binary data (base64-encoded), arrays, booleans, and subdocuments up to 5 levels deep

All documents include:
- `_id`: Unique document identifier
- `targets`: Array of link IDs used for multikey index query tests (10 links per document in indexed tests)
- `data`: Payload data (structure varies by test type)

## Document Categories

The benchmarks test documents across multiple payload sizes and attribute counts:

| Category | Payload Size | Attributes | Description |
|----------|--------------|------------|-------------|
| Small | 10B | 1 or 10 | Minimal nested structure |
| Small-Medium | 200B | 1 or 10 | Light nesting with mixed types |
| Medium | 1000B | 1 or 50 | Moderate nesting with subdocuments |
| Large | 2000B | 1 or 100 | Deep nesting with complex structures |
| Extra Large | 4000B | 1 or 200 | Maximum nesting with extensive data |

## Sample Documents

### 1. Small Multi-Attribute (10B, 10 attributes)

**Configuration**: `realistic_s10_n10000_a10_l10.json`
- Target size: ~10 bytes per document
- Attributes: 10
- Documents: 10,000
- Query links: 10

```json
{
  "data": {
    "field_0_0": [
      "SL47upfW3VLW/g==",
      true,
      true
    ]
  },
  "_id": "0",
  "targets": [
    "5519",
    "1248",
    "9970",
    "6918",
    "2763",
    "8884",
    "7525",
    "8093",
    "1130",
    "1505"
  ]
}
```

**Characteristics**:
- Single nested array with base64-encoded binary data and boolean values
- Minimal structure to achieve target payload size
- 10 target links for query testing

### 2. Small-Medium Multi-Attribute (200B, 10 attributes)

**Configuration**: `realistic_s200_n10000_a10_l10.json`
- Target size: ~200 bytes per document
- Attributes: 10
- Documents: 10,000
- Query links: 10

```json
{
  "data": {
    "field_0_1": [
      "SL47upfW3VI=",
      5067,
      849.0338903519045
    ],
    "field_0_0": [
      "AYRUq7AeMg9I5g==",
      false,
      false
    ],
    "field_0_3": "BICGk6Nf6VkxKILyuI6d7X3eEzusXf1CuUIbiEizY6bFKFvHLZMtT2Lm",
    "field_0_2": [
      "mKLDwDpptafDiS07ony55bh2",
      869.8123643005331,
      746.6058236447316
    ]
  },
  "_id": "0",
  "targets": [
    "5519",
    "1248",
    "9970",
    "6918",
    "2763",
    "8884",
    "7525",
    "8093",
    "1130",
    "1505"
  ]
}
```

**Characteristics**:
- Mix of arrays with different value types: base64 binary, integers, decimals, booleans
- String fields with base64-encoded data
- Multiple attributes distributed across the `data` subdocument
- Representative of small JSON documents in real applications

### 3. Medium Multi-Attribute (1000B, 50 attributes)

**Configuration**: `realistic_s1000_n10000_a50_l10.json`
- Target size: ~1000 bytes per document
- Attributes: 50
- Documents: 10,000
- Query links: 10

```json
{
  "data": {
    "field_0_9": "SL47upfW3VLW/k7a/Eha2eo/B+EBhFSrsB4y",
    "field_0_8": "SObjP1aKJwmVbUEFBICGk6Nf6VkxKILyuI6d7X3e",
    "field_0_5": [
      261.67855458953915,
      5908,
      true
    ],
    "field_0_4": "LZMtT2LmogqYosPAOmm1p8OJLTui",
    "field_0_7": {
      "field_1_0": {},
      "field_1_1": 5944.589804084951
    },
    "field_0_6": {
      "field_1_0": {},
      "field_1_1": "xBRPqQmPIb/5ozqum4uAZlyO1FuTJ+LDr3Q="
    },
    "field_0_1": [
      "lXiJW/lCR9c=",
      9776,
      767.7000306677488
    ],
    "field_0_0": [
      "6K4+LeUDnHQ9zA==",
      true,
      false
    ],
    "field_0_10": {
      "field_1_0": 8388.086700733438
    },
    "field_0_3": "E9Pgiv4eg0BEaUb1NYM8Avy4OqlxRdgPw+nXxdt5VVwUshoQ2GI8ZS1d",
    "field_0_2": [
      "rRpNfett09VJlv+erNoXII2A",
      754.0064834020652,
      245.51351689005995
    ],
    "field_0_13": "7cub1uft2lBmvAtaum55l649sOfzPJ2YxyI5Q9FCguACKOhUT40ECg==",
    "field_0_14": {
      "field_1_0": "cnJYg1MYZ+/oFrjUXLPTbBqP8u1/VhrBn/rZMeoFOQbm8qhtTjIXZVjk"
    },
    "field_0_11": 7485.417699085951,
    "field_0_12": "s+mwqyxazRQEYgPH64Re",
    "field_0_17": [
      401,
      "UHazI1reBkxa",
      495.3580793833843,
      123.38050580599646
    ],
    "field_0_18": "T6uoUtYYKVBv1Kg9Yw6QFpoIXCd9voq+WS3RgLU2eq7UqVPqJtYlhM7XKeel",
    "field_0_15": 641912,
    "field_0_16": {
      "field_1_0": 7218.430232452083
    },
    "field_0_19": [
      "sQyjPbfgwist",
      false,
      false
    ]
  },
  "_id": "0",
  "targets": [
    "5519",
    "1248",
    "9970",
    "6918",
    "2763",
    "8884",
    "7525",
    "8093",
    "1130",
    "1505"
  ]
}
```

**Characteristics**:
- 50 attributes spread across the `data` subdocument
- Nested subdocuments up to 2 levels deep (field_0_N → field_1_N)
- Mix of all data types: strings, integers, decimals, arrays, subdocuments, booleans
- Empty subdocuments (`{}`) demonstrating sparse data patterns
- Representative of medium-complexity JSON documents in document databases

### 4. Large Multi-Attribute (2000B, 100 attributes)

**Configuration**: `realistic_s2000_n10000_a100_l10.json`
- Target size: ~2000 bytes per document
- Attributes: 100
- Documents: 10,000
- Query links: 10

Documents at this size contain approximately 100 attributes distributed across multiple nesting levels. The structure includes:
- Primary `data` subdocument with 100+ top-level fields
- Nested subdocuments up to 3-4 levels deep
- Mix of scalar values, arrays, and complex nested structures
- Larger base64-encoded binary blobs (up to 50 bytes)
- Arrays with 3-4 mixed-type elements

### 5. Extra Large Multi-Attribute (4000B, 200 attributes)

**Configuration**: `realistic_s4000_n10000_a200_l10.json`
- Target size: ~4000 bytes per document
- Attributes: 200
- Documents: 10,000
- Query links: 10

Documents at this size represent the maximum complexity tested:
- 200+ attributes distributed across the `data` subdocument
- Nested subdocuments up to 5 levels deep (field_0_N → field_1_N → field_2_N → field_3_N → field_4_N)
- Extensive use of all supported data types
- Large binary blobs (up to 50 bytes base64-encoded)
- Complex array structures with heterogeneous element types
- Representative of large, complex JSON documents in production document databases

## Document Generation Details

Documents are generated using:
- **Deterministic random seed**: 42 (ensures reproducible results across runs)
- **Payload distribution**: Split across N attributes based on `-n` parameter
- **Nesting depth**: Up to 5 levels for realistic data
- **Data types**: Random mix of:
  - Strings (base64-encoded binary data)
  - Integers (positive and negative)
  - Decimals (floating-point numbers)
  - Binary data (1-50 bytes, base64-encoded)
  - Arrays (3-4 elements, mixed types)
  - Booleans
  - Subdocuments (nested up to 5 levels)

## Usage in Benchmarks

These documents are cached in the `document_cache/` directory and reused across multiple benchmark runs to ensure consistency. The cache file naming convention is:

```
{type}_s{size}_n{numDocs}_a{attrs}_l{links}.json
```

Where:
- `type`: "realistic" or "standard"
- `size`: Target payload size in bytes (10, 200, 1000, 2000, 4000)
- `numDocs`: Number of documents (typically 10000)
- `attrs`: Number of attributes for multi-attribute tests (1, 10, 50, 100, 200)
- `links`: Number of query links in `targets` array (0 or 10)

## Performance Implications

Document structure significantly impacts database performance:

1. **Single-attribute documents**: Simpler for databases to parse but less realistic
2. **Multi-attribute documents**: More realistic but increase parsing overhead
3. **Nested structures**: Test query performance on paths like `data.field_0_5[2]`
4. **Large documents**: Test memory allocation and buffer management
5. **Mixed data types**: Test type conversion and validation overhead

The benchmarks compare MongoDB (BSON) and Oracle (JSON Collection Tables with OSON) performance across these varying document structures to provide realistic performance metrics for production workloads.
