# Index interface

The runtime exposes these optional commands:

```text
learning vector-status WORKSPACE
learning vector-reindex WORKSPACE --embedding-provider sentence-transformers
learning vector-query WORKSPACE TEXT --embedding-provider sentence-transformers
learning reindex WORKSPACE
learning query WORKSPACE TEXT [--topic TOPIC] [--source SOURCE] [--path PATH] [--limit N]
```

## Contract

Use one Milvus Lite database per workspace under `index/milvus/workspace.db` when enabled. Store source ID, topic/path IDs, location, chunk order, content hash, authority, extraction method, workspace file, embedding provider/model/version/dimension. `REBUILD` reads manifests and canonical Markdown/extracted sources, reports failures, and never deletes those files. `QUERY` must return citation metadata with each result. If `pymilvus` is unavailable, vector commands return `status: unavailable`; the agent should use the dependency-free lexical manifest and report degraded retrieval. The hash embedding provider is deterministic for tests and local experiments, but is not presented as semantic-quality retrieval.
