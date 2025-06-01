-- Allow NULL receiver_id in messages table
ALTER TABLE messages MODIFY COLUMN receiver_id int NULL;
ALTER TABLE messages DROP FOREIGN KEY messages_ibfk_2;
ALTER TABLE messages ADD CONSTRAINT messages_ibfk_2 FOREIGN KEY (receiver_id) REFERENCES agents(id) ON DELETE SET NULL; 