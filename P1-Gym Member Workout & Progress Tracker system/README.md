.

# 🏋️‍♂️ Gym Member Workout & Progress Tracker System

A Full-Stack Python Project using FastAPI + MySQL + Streamlit

### 📌 Overview

This project is a complete gym member management and workout tracking system built using:

Backend: FastAPI

Database: MySQL

Frontend: Streamlit

Authentication: Simple username/password (no tokens)

Analytics: Weekly workout volume, workout duration, body measurement progress

Charts: Streamlit bar charts & line charts

Exports: Download analytics graphs & tables

This system allows gym admins and members to track workouts, body progress, and member-related data.

### 🎯 Features

#### 👨‍💼 For Admin

Login with username/password

View all members

Add new members

Add/update/delete exercises

Add sessions/logs/measurements for any member

View all analytics

Manage gym data completely

#### 🧑‍🤝‍🧑 For Members

Login using their own account

View only their personal profile and workout details

Log their own:

Workout sessions

Workout logs

Body measurements

View their analytics:

Weekly workout volume (bar chart)

Average workout duration (bar chart)

Body measurement progress (line chart)

Download analytics reports as files

### 🛠 Technologies Used

Component	Technology
Backend	FastAPI
Frontend	Streamlit
Database	MySQL
Charts	Streamlit Bar & Line Charts
Auth	Simple username/password
Testing	REST endpoints via Postman
Logging	Python logging module
🗄 Database Schema

#### The project uses the following tables:

members

exercises

workout_sessions

workout_logs

body_measurements

Everything is created using the included schema.sql.

## 🚀 How to Run the Project

#### 1️⃣ Install MySQL & Create Database

The schema for database is given


Then import schema.sql.

#### 2️⃣ Install Backend Dependencies

cd backend
pip install -r requirements.txt


Run backend:

uvicorn server:app --reload


##### Backend will be available at:

👉 http://localhost:8000/docs

👉 http://localhost:8000/health

#### 3️⃣ Create Admin User

Use this endpoint:

POST http://localhost:8000/register_admin


Body example:

{
  "username": "admin",
  "password": "admin123",
  "name": "Gym Owner",
  "email": "admin@example.com",
  "phone": "9999999999"
}

#### 4️⃣ Install Frontend

cd frontend
pip install -r requirements.txt


Run Streamlit UI:

streamlit run app.py


Frontend opens at:

👉 http://localhost:8501/

🖥 How Authentication Works (Simple)

User enters username and password

Frontend stores them in session_state

Every request adds:

X-Username: <username>
X-Password: <password>


Backend validates them every time

No tokens, no JWT, no expiration

Lightweight & easy to debug

### 🧮 Analytics Provided

#### 1️⃣ Weekly Workout Volume

Bar graph

Total weight lifted per week

Downloadable  table

#### 2️⃣ Average Workout Duration

Bar graph

Computed per week/month

#### 3️⃣ Body Measurements Progress

Line chart

Tracks:

Weight

Chest

Arms

Waist




### 🧪 Testing Guide (Postman)

Test endpoints in this order:

/register_admin

/login

/add_members

/sessions

/logs

/measurements

/analytics/*
