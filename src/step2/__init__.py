"""Step 2: preprocessing/normalization + schema-based fact extraction.

- Preprocessing is deterministic (no AI): clean text, normalize units, chunk.
- Extraction uses an LLM carefully: one call per document, strict JSON schema.
"""
