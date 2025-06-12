-- Create team_tasks table
CREATE TABLE IF NOT EXISTS team_tasks (
    task_id VARCHAR(255) PRIMARY KEY,
    team_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    requirements JSON NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled'))
);

-- Create indexes
CREATE INDEX idx_team_tasks_team_id ON team_tasks(team_id);
CREATE INDEX idx_team_tasks_status ON team_tasks(status);
CREATE INDEX idx_team_tasks_created_at ON team_tasks(created_at);

-- Create trigger for update_team_tasks_updated_at
DELIMITER $$

CREATE TRIGGER update_team_tasks_updated_at
BEFORE UPDATE ON team_tasks
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END $$

DELIMITER ; 