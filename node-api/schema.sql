-- Create conversation_settings table if not exists
CREATE TABLE IF NOT EXISTS conversation_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT,
    temperature FLOAT DEFAULT 0.7,
    token_limit INT DEFAULT 512,
    start_prompt TEXT,
    end_prompt TEXT,
    style VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
);

-- Create conversations table if not exists
CREATE TABLE IF NOT EXISTS conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    settings_id INT,
    team_id INT,
    started_at DATETIME,
    ended_at DATETIME,
    title VARCHAR(255) NOT NULL DEFAULT 'Untitled',
    conversation_data LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (settings_id) REFERENCES conversation_settings(id) ON DELETE SET NULL,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
);

-- Create agent_memory table if not exists
CREATE TABLE IF NOT EXISTS agent_memory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id INT NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    start_prompt TEXT,
    end_prompt TEXT,
    context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
);

-- Create agent_interactions table if not exists
CREATE TABLE IF NOT EXISTS agent_interactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    source_agent_id INT NOT NULL,
    target_agent_id INT NOT NULL,
    interaction_type VARCHAR(50) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    success_rate FLOAT DEFAULT 0,
    details TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (source_agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    FOREIGN KEY (target_agent_id) REFERENCES agents(id) ON DELETE CASCADE
);

-- Add indexes for better performance
CREATE INDEX idx_team_id ON conversation_settings(team_id);
CREATE INDEX idx_settings_id ON conversations(settings_id);
CREATE INDEX idx_conversations_team_id ON conversations(team_id);
CREATE INDEX idx_agent_interactions_team ON agent_interactions(team_id);
CREATE INDEX idx_agent_interactions_source ON agent_interactions(source_agent_id);
CREATE INDEX idx_agent_interactions_target ON agent_interactions(target_agent_id);
CREATE INDEX idx_agent_memory_agent ON agent_memory(agent_id); 