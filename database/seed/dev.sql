-- Dev seed for the 007 chat schema. Run with: make seed
-- (PGPASSWORD=rag psql -h localhost -U rag -d rag_learning -f database/seed/dev.sql)

INSERT INTO conversations (id, title) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Digital garden notes'),
    ('00000000-0000-0000-0000-000000000002', 'RAG experiments') ON CONFLICT (id) DO NOTHING;

INSERT INTO messages (id, conversation_id, role, content, sources) VALUES
    ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'user',
     'How does chunking work in this platform?', NULL),
    ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'assistant',
     'Every strategy lives behind a common interface and is chosen by config — e.g. `chunking: recursive`.',
     '[{"document_id":"seed-doc","chunk_id":"seed-1","snippet":"strategy behind a common interface","score":0.9}]'),
    ('10000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000002', 'user',
     'Swapping strategies should not touch pipeline code.', NULL)
    ON CONFLICT (id) DO NOTHING;