-- First, modify conversation_settings table
ALTER TABLE conversation_settings
  DROP COLUMN started_at,
  DROP COLUMN ended_at,
  DROP COLUMN title,
  ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  DROP FOREIGN KEY conversation_settings_ibfk_1,
  ADD CONSTRAINT conversation_settings_ibfk_1 FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL;

-- Then, modify conversations table
ALTER TABLE conversations
  DROP COLUMN temperature,
  DROP COLUMN token_limit,
  DROP COLUMN start_prompt,
  DROP COLUMN end_prompt,
  DROP COLUMN style,
  MODIFY conversation_data LONGTEXT,
  ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP; 