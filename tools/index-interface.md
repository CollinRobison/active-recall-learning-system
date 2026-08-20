# Index interface

The runtime exposes these optional commands:

```text
learning vector-status WORKSPACE
learning vector-reindex WORKSPACE --embedding-provider sentence-transformers [--incremental]
learning vector-query WORKSPACE TEXT --embedding-provider sentence-transformers [--source SOURCE] [--topic TOPIC] [--path PATH]
learning reindex WORKSPACE
learning query WORKSPACE TEXT [--topic TOPIC] [--source SOURCE] [--path PATH] [--limit N]
```

## Contract

Use one Milvus Lite database per workspace under `index/milvus/workspace.db` when enabled. Each vector row stores source ID, topic/path IDs, section/location, content hash, and workspace file; vector status stores the embedding provider/model/version/dimension and a record-ID-to-content-hash map. A full rebuild creates a numbered collection generation and publishes it only after all rows are inserted, so a failed build cannot replace the previous published generation. `--incremental` upserts changed chunks and deletes stale record IDs from that published generation. `QUERY` applies source filtering in Milvus and topic/path filtering after decoding stored IDs, returning citation metadata with each result. Rebuilds never delete canonical Markdown/extracted sources. If `pymilvus` is unavailable, vector commands return `status: unavailable`; use the dependency-free lexical manifest and report degraded retrieval. The hash embedding provider is deterministic for tests and local experiments, but is not presented as semantic-quality retrieval.
