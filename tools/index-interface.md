# Index interface

A future optional helper may expose:

```text
learning-index STATUS --workspace WORKSPACE
learning-index REBUILD --workspace WORKSPACE [--collection source_chunks|approved_learning_notes]
learning-index QUERY --workspace WORKSPACE --text TEXT [--topic TOPIC] [--source SOURCE] [--path PATH] [--limit N]
```

## Contract

Use one Milvus Lite database per workspace under `index/milvus/workspace.db` when enabled. Store source ID, topic/path IDs, location, chunk order, content hash, authority, extraction method, workspace file, embedding provider/model/version/dimension. `REBUILD` reads manifests and canonical Markdown/extracted sources, reports failures, and never deletes those files. `QUERY` must return citation metadata with each result. If unavailable, status must say degraded and the agent should use direct file search.
