-- MySQL 数据库初始化脚本
-- 与 app/models 中的 User、Session 模型对应，库名与 config.yaml 中 database.dbname 一致

-- 创建数据库（若不存在）
CREATE DATABASE IF NOT EXISTS agent_platform
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE agent_platform;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_username (username),
  KEY ix_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT '用户表';

-- 会话表（依赖 users）
CREATE TABLE IF NOT EXISTS sessions (
  id INT NOT NULL AUTO_INCREMENT,
  user_id INT NOT NULL,
  session_uuid VARCHAR(64) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_session_uuid (session_uuid),
  KEY ix_user_id (user_id),
  KEY ix_session_uuid (session_uuid),
  CONSTRAINT fk_sessions_user_id FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT '用户会话表';

-- 聊天记录表（按 session_uuid，用于 recent history 与 summary）
CREATE TABLE IF NOT EXISTS chat_message (
  id BIGINT NOT NULL AUTO_INCREMENT,
  session_uuid VARCHAR(64) NOT NULL,
  role VARCHAR(32) NOT NULL,
  content TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_session_uuid (session_uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT '聊天记录';

-- 会话摘要表（按 session_uuid，避免上下文过长）
CREATE TABLE IF NOT EXISTS conversation_summary (
  session_uuid VARCHAR(64) NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (session_uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT '会话摘要';
