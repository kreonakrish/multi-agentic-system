CREATE TABLE IF NOT EXISTS team_conversation_settings (
    team_id INT NOT NULL,
    max_turns INT DEFAULT 10,
    response_timeout INT DEFAULT 30,
    auto_summarize BOOLEAN DEFAULT FALSE,
    language_model VARCHAR(50) DEFAULT 'gpt-3.5-turbo',
    temperature DECIMAL(3,2) DEFAULT 0.7,
    max_tokens INT DEFAULT 2000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);

CREATE TABLE messages (
    id INT NOT NULL AUTO_INCREMENT,
    content TEXT NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    team_id INT,
    role ENUM('user', 'assistant', 'system') NOT NULL DEFAULT 'user',
    parent_message_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL,
    INDEX idx_session (session_id),
    INDEX idx_team (team_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci; 