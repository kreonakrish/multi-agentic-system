@echo off
cd python-ml
mysql -u root -p < migrations/003_fix_messages_receiver_id.sql 