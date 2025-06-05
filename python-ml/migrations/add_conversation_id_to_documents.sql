-- Add conversation_id column to documents table
ALTER TABLE documents
ADD COLUMN conversation_id int DEFAULT NULL,
ADD CONSTRAINT fk_documents_conversation_id 
FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL; 