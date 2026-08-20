# Prompt contract: metadata extraction

Extract source metadata only from the supplied source or explicit user input. Mark each value with provenance and confidence.

```yaml
title: {value: ..., provenance: extracted | inferred | user-provided | user-confirmed, confidence: high | medium | low}
author: {...}
source_type: ...
version: {...}
intended_audience: {...}
prerequisites: []
structure: []
warnings: []
needs_user_confirmation: []
```

Do not infer authority as fact. Preserve extraction warnings, especially OCR and missing page structure.
