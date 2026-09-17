CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS zhiyin_vectors (
    namespace VARCHAR(32) NOT NULL,
    record_id VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    embedding vector(1024) NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    source_id VARCHAR(255) NOT NULL DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (namespace, record_id, model),
    CONSTRAINT ck_zhiyin_vectors_namespace CHECK (
        namespace IN ('theory', 'occupation', 'jd', 'report', 'memory', 'resume')
    )
);

CREATE INDEX IF NOT EXISTS ix_zhiyin_vectors_hnsw
    ON zhiyin_vectors USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS ix_zhiyin_vectors_metadata
    ON zhiyin_vectors USING gin (metadata);
