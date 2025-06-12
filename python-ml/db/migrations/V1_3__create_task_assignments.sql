-- Create task_assignments table
CREATE TABLE IF NOT EXISTS task_assignments (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    assignments JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES team_tasks(task_id)
);

-- Create index on task_id for faster lookups
CREATE INDEX idx_task_assignments_task_id ON task_assignments(task_id);

-- Create trigger for update_task_assignments_updated_at
DELIMITER $$

CREATE TRIGGER update_task_assignments_updated_at
BEFORE UPDATE ON task_assignments
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END $$

DELIMITER ; 