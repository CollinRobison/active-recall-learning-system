# Source record

Path: `sources/<source-id>/source.md`

```markdown
---
id: source-20260820-example
kind: source
title: Example source
author: Unknown
source_type: markdown | text | pdf | webpage | repository | transcript | image
original_location: /path/or/url
checksum: sha256:...
ingested_at: 2026-08-20T00:00:00Z
updated_at: 2026-08-20T00:00:00Z
authority: user-marked | reference | unverified
authority_scope: []
topic_ids: []
path_ids: []
extraction_status: pending | complete | partial | failed
index_status: disabled | stale | current | failed
metadata_confidence: {}
warnings: []
---

# Example source

## Why this source is being used

User-provided purpose.

## Extraction notes

Describe parser, OCR, structure retention, and limitations.

## Citation policy

Use page, chapter, section, line, or URL locations. See `protocol/citation-policy.md`.
```

Keep extracted content in `extracted.md`, structural metadata in `structure.md`, and assets only when they are learning-relevant.
