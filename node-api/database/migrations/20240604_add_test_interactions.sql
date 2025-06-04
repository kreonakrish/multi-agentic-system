-- Add test agent interactions
INSERT INTO agent_interactions 
(team_id, source_agent_id, target_agent_id, interaction_type, success_rate, details)
SELECT 
    t.id as team_id,
    a1.id as source_agent_id,
    a2.id as target_agent_id,
    'query' as interaction_type,
    0.85 as success_rate,
    '{"query": "What is the status?", "response": "Processing completed successfully"}' as details
FROM teams t
CROSS JOIN agents a1
CROSS JOIN agents a2
WHERE a1.id != a2.id
AND a1.team_id = t.id
AND a2.team_id = t.id
LIMIT 10; 