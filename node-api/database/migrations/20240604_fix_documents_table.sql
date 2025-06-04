-- Drop existing documents table
DROP TABLE IF EXISTS documents;

-- Create documents table with correct structure
CREATE TABLE documents (
    id INT NOT NULL AUTO_INCREMENT,
    team_id INT DEFAULT NULL,
    name VARCHAR(255) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY team_id (team_id),
    CONSTRAINT documents_ibfk_1 FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci; 