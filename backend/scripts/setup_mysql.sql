CREATE DATABASE IF NOT EXISTS chat_app
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'chat_user'@'localhost'
  IDENTIFIED BY 'chat_pass';

ALTER USER 'chat_user'@'localhost'
  IDENTIFIED BY 'chat_pass';

GRANT ALL PRIVILEGES ON chat_app.* TO 'chat_user'@'localhost';

FLUSH PRIVILEGES;
