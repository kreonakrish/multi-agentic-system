CREATE TABLE `agent_interactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `source_agent_id` int NOT NULL,
  `target_agent_id` int NOT NULL,
  `interaction_type` varchar(50) NOT NULL,
  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP,
  `success_rate` float DEFAULT '0',
  `details` text,
  PRIMARY KEY (`id`),
  KEY `team_id` (`team_id`),
  KEY `source_agent_id` (`source_agent_id`),
  KEY `idx_agent_interactions_target` (`target_agent_id`),
  CONSTRAINT `agent_interactions_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`) ON DELETE CASCADE,
  CONSTRAINT `agent_interactions_ibfk_2` FOREIGN KEY (`source_agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `agent_interactions_ibfk_3` FOREIGN KEY (`target_agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `agent_memory` (
  `id` int NOT NULL AUTO_INCREMENT,
  `agent_id` int NOT NULL,
  `memory_type` varchar(50) NOT NULL,
  `start_prompt` text,
  `end_prompt` text,
  `context` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `source_type` varchar(50) DEFAULT 'task',
  `confidence` float DEFAULT '0.8',
  PRIMARY KEY (`id`),
  KEY `idx_agent_memory_agent` (`agent_id`),
  CONSTRAINT `agent_memory_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=97 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `agent_tools` (
  `id` int NOT NULL AUTO_INCREMENT,
  `agent_id` int NOT NULL,
  `tool_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `agent_id` (`agent_id`),
  KEY `tool_id` (`tool_id`),
  CONSTRAINT `agent_tools_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `agent_tools_ibfk_2` FOREIGN KEY (`tool_id`) REFERENCES `tools` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=72 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `agents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` text,
  `memory_type` varchar(255) DEFAULT NULL,
  `foundation_model` varchar(255) DEFAULT NULL,
  `status` enum('active','inactive','busy') DEFAULT 'inactive',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `accuracy_rate` decimal(5,2) DEFAULT '0.00',
  `success_rate` decimal(5,2) DEFAULT '0.00',
  `priority` int DEFAULT '3',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=156 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `conversation_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int DEFAULT NULL,
  `temperature` float DEFAULT NULL,
  `token_limit` int DEFAULT NULL,
  `start_prompt` text,
  `end_prompt` text,
  `style` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_team_id` (`team_id`),
  CONSTRAINT `conversation_settings_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=271 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `conversation_steps` (
  `id` int NOT NULL AUTO_INCREMENT,
  `conversation_id` int NOT NULL,
  `role` enum('user','agent','tool','bot') DEFAULT NULL,
  `content` text,
  `agent_id` int DEFAULT NULL,
  `tool_id` int DEFAULT NULL,
  `parent_idx` int DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `conversation_id` (`conversation_id`),
  KEY `agent_id` (`agent_id`),
  KEY `tool_id` (`tool_id`),
  CONSTRAINT `conversation_steps_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE CASCADE,
  CONSTRAINT `conversation_steps_ibfk_2` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL,
  CONSTRAINT `conversation_steps_ibfk_3` FOREIGN KEY (`tool_id`) REFERENCES `tools` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `conversations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `settings_id` int DEFAULT NULL,
  `team_id` int DEFAULT NULL,
  `started_at` timestamp NULL DEFAULT NULL,
  `ended_at` timestamp NULL DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `conversation_data` longtext,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `temperature` float DEFAULT '0.7',
  `token_limit` int DEFAULT '512',
  `start_prompt` text,
  `end_prompt` text,
  `style` varchar(255) DEFAULT NULL,
  `conversation_id` varchar(255) DEFAULT NULL,
  `content` json DEFAULT NULL,
  `metadata` json DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_settings_id` (`settings_id`),
  KEY `idx_conversations_team_id` (`team_id`),
  CONSTRAINT `conversations_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_settings_id` FOREIGN KEY (`settings_id`) REFERENCES `conversation_settings` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=514 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `documents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int DEFAULT NULL,
  `conversation_id` int DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `type` varchar(100) DEFAULT 'unknown',
  `size` bigint DEFAULT '0',
  `file_type` varchar(100) DEFAULT 'unknown',
  `file_size` bigint DEFAULT '0',
  `file_path` varchar(1000) NOT NULL,
  `url` varchar(1000) DEFAULT NULL,
  `content` text,
  `metadata` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `uploaded_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `team_id` (`team_id`),
  KEY `conversation_id` (`conversation_id`),
  CONSTRAINT `documents_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`) ON DELETE CASCADE,
  CONSTRAINT `documents_ibfk_2` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sender_id` int DEFAULT NULL,
  `receiver_id` int DEFAULT NULL,
  `content` text NOT NULL,
  `processed_message` text,
  `model_response` text,
  `interaction_type` varchar(50) DEFAULT 'direct',
  `conversation_id` varchar(36) DEFAULT NULL,
  `team_id` int DEFAULT NULL,
  `status` varchar(20) DEFAULT 'pending',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `messages_ibfk_1` (`receiver_id`),
  KEY `messages_ibfk_2` (`sender_id`),
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`receiver_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL,
  CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`sender_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=89 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `task_assignments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `task_id` varchar(255) NOT NULL,
  `assignments` json NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`),
  KEY `idx_task_assignments_task_id` (`task_id`),
  CONSTRAINT `task_assignments_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `team_tasks` (`task_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `task_decompositions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_id` varchar(255) NOT NULL,
  `subtasks` json DEFAULT NULL,
  `dependencies` json DEFAULT NULL,
  `execution_plan` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `task_decompositions_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `team_tasks` (`task_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `team_agents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `agent_id` int NOT NULL,
  `accuracy` int DEFAULT NULL,
  `success` int DEFAULT NULL,
  `priority` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `team_id` (`team_id`),
  KEY `agent_id` (`agent_id`),
  CONSTRAINT `team_agents_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`) ON DELETE CASCADE,
  CONSTRAINT `team_agents_ibfk_2` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=356 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `team_configurations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `config_data` json NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `team_configurations_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `team_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` varchar(36) NOT NULL,
  `task_id` varchar(36) NOT NULL,
  `task_description` text NOT NULL,
  `task_requirements` json DEFAULT NULL,
  `team_config` json DEFAULT NULL,
  `status` varchar(20) DEFAULT 'pending',
  `result` json DEFAULT NULL,
  `error_message` text,
  `processing_time` int DEFAULT NULL,
  `agent_responses` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_team_id` (`team_id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=398 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `team_tasks` (
  `task_id` varchar(255) NOT NULL,
  `team_id` int NOT NULL,
  `task_type` varchar(100) DEFAULT NULL,
  `complexity` varchar(100) DEFAULT NULL,
  `description` text NOT NULL,
  `requirements` json NOT NULL,
  `status` varchar(50) NOT NULL DEFAULT 'pending',
  `priority` int NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`task_id`),
  KEY `idx_team_tasks_team_id` (`team_id`),
  KEY `idx_team_tasks_status` (`status`),
  KEY `idx_team_tasks_created_at` (`created_at`),
  CONSTRAINT `team_tasks_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`),
  CONSTRAINT `valid_status` CHECK ((`status` in (_utf8mb4'pending',_utf8mb4'in_progress',_utf8mb4'completed',_utf8mb4'failed',_utf8mb4'cancelled')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `team_tool_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `tool_id` int NOT NULL,
  `permission_level` enum('read','write','admin') DEFAULT 'read',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `team_id` (`team_id`),
  KEY `tool_id` (`tool_id`),
  CONSTRAINT `team_tool_permissions_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`),
  CONSTRAINT `team_tool_permissions_ibfk_2` FOREIGN KEY (`tool_id`) REFERENCES `tools` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=133 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `teams` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `configuration` json DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `tools` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tool_name` varchar(255) NOT NULL,
  `tool_type` varchar(255) DEFAULT NULL,
  `hostname` varchar(255) DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `auth_method` varchar(255) DEFAULT NULL,
  `description` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `workflow_steps` (
  `id` int NOT NULL AUTO_INCREMENT,
  `workflow_id` int NOT NULL,
  `agent_id` int NOT NULL,
  `step_order` int NOT NULL,
  `status` enum('pending','in_progress','completed','failed') DEFAULT 'pending',
  `tool_responses` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `start_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `end_time` timestamp NULL DEFAULT NULL,
  `execution_time` float DEFAULT NULL,
  `error_message` text,
  `tool_name` varchar(255) DEFAULT NULL,
  `tool_input` text,
  `tool_output` text,
  `llm_input` text,
  `llm_output` text,
  PRIMARY KEY (`id`),
  KEY `workflow_id` (`workflow_id`),
  KEY `agent_id` (`agent_id`),
  KEY `idx_workflow_step_status` (`status`),
  KEY `idx_workflow_step_time` (`start_time`,`end_time`),
  CONSTRAINT `workflow_steps_ibfk_1` FOREIGN KEY (`workflow_id`) REFERENCES `workflows` (`id`),
  CONSTRAINT `workflow_steps_ibfk_2` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=287 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `workflows` (
  `id` int NOT NULL AUTO_INCREMENT,
  `initiator_id` int NOT NULL,
  `type` enum('sequential','parallel','broadcast') NOT NULL,
  `status` enum('pending','in_progress','completed','failed') DEFAULT 'pending',
  `message` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `team_id` int DEFAULT NULL,
  `task_id` varchar(36) DEFAULT NULL,
  `correlation_id` varchar(255) DEFAULT NULL,
  `task_data` json DEFAULT NULL,
  `start_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `end_time` timestamp NULL DEFAULT NULL,
  `execution_time` float DEFAULT NULL,
  `successful_agents` int DEFAULT '0',
  `total_agents` int DEFAULT '0',
  `error_message` text,
  PRIMARY KEY (`id`),
  KEY `initiator_id` (`initiator_id`),
  KEY `team_id` (`team_id`),
  KEY `idx_workflow_status` (`status`),
  KEY `idx_workflow_time` (`start_time`,`end_time`),
  KEY `idx_workflow_task` (`task_id`),
  CONSTRAINT `workflows_ibfk_1` FOREIGN KEY (`initiator_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `workflows_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=194 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
