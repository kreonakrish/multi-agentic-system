-- Create knowledge_retrieval_metrics table
CREATE TABLE IF NOT EXISTS knowledge_retrieval_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id INT NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    description TEXT,
    requirements JSON,
    memory_count INT NOT NULL DEFAULT 0,
    source_counts JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (task_id) REFERENCES team_tasks(task_id),
    INDEX idx_agent_task (agent_id, task_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci; 