# Exact context template

Manifest v1 fields: `v`, `sources`, `requirements`, `decisions`, `assumptions`, `proposals`.
Each source has exact `content` plus its SHA-256 `version`. Each requirement has a unique `id`, exact `text`, `global` boolean, `depends_on` requirement IDs, a `source` ID, and exact `acceptance` text. Decisions, assumptions, and proposals are separate string lists.

A host can create a version with `Manifest.create(data)`. Use `Engine.prepare_context(manifest, task, required_ids, output_contract)`. Global requirements and dependency closure are included in stable source order. The caller chooses relevant IDs; the engine does not prove relevance or completeness. Requirements are not extracted by a language model.

Referenced inputs are resolved only by a host-created `Access` scope and `ReferenceStore`. Retrieved documents/tools keep their role and `untrusted_data` marker. Do not turn embedded text into system instructions.
