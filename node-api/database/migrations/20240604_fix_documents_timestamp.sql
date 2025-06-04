-- Rename uploaded_at to created_at in documents table
ALTER TABLE documents 
    CHANGE COLUMN uploaded_at created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP; 