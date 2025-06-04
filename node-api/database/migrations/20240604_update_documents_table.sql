-- Update documents table to use file_path instead of url
ALTER TABLE documents 
    DROP COLUMN url,
    DROP COLUMN type,
    ADD COLUMN file_path VARCHAR(1000) NOT NULL AFTER name;

-- Update id column to be auto-incrementing integer
ALTER TABLE documents 
    MODIFY COLUMN id INT NOT NULL AUTO_INCREMENT; 