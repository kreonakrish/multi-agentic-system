-- Drop and recreate messages table with correct schema
DROP TABLE IF EXISTS messages;

CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NULL,  -- Allow NULL for system/user messages
    receiver_id INT NOT NULL,
    content TEXT NOT NULL,
    processed_message TEXT,
    model_response TEXT,
    interaction_type VARCHAR(50) DEFAULT 'direct',
    conversation_id VARCHAR(36),
    team_id INT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (receiver_id) REFERENCES agents(id),
    FOREIGN KEY (sender_id) REFERENCES agents(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci; 