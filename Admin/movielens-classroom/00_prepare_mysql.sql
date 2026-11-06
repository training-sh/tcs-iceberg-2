-- One-time administrator preparation. Existing application user; dedicated course database only.
CREATE DATABASE IF NOT EXISTS movielens_classroom_s01;
GRANT SELECT, INSERT, CREATE, DROP, ALTER, INDEX
ON movielens_classroom_s01.* TO 'team'@'%';
