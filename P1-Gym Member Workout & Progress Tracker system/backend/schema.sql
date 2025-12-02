CREATE DATABASE IF  gym_member;
USE gym_member;

CREATE TABLE IF  members (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  age INT,
  gender ENUM('male','female','other'),
  joined_date DATE,
  phone VARCHAR(20),
  email VARCHAR(100),
  username VARCHAR(80) UNIQUE,
  password VARCHAR(255),
  role ENUM('admin','member') DEFAULT 'member',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE  exercises (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  muscle_group VARCHAR(100),
  equipment VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE  workout_sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  member_id INT NOT NULL,
  session_date DATE NOT NULL,
  total_duration INT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE  workout_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  exercise_id INT NOT NULL,
  sets INT NOT NULL,
  reps INT NOT NULL,
  weight DECIMAL(6,2),
  calories_burned DECIMAL(8,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);

CREATE TABLE  body_measurements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  member_id INT NOT NULL,
  measure_date DATE NOT NULL,
  weight DECIMAL(5,2),
  chest DECIMAL(5,2),
  arms DECIMAL(5,2),
  waist DECIMAL(5,2),
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);
