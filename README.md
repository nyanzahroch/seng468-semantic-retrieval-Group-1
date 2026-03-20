# Version 1:
-Uses docker compose, PostgreSQL to store user data, has endpoints /signup and /login
-User data stored in PostgreSQL table called “users” which contains columns id, username, hashed_password
-This code also uses a session, but we can figure out later if we want to keep that
-/src/__init__.py creates the flask app and registers all the routers (where the endpoints are defined) and specifies running on port 8080
-/src/__main__.py is the first file that is run, calls the main() function from __init__.py
-/src/database/models.py sets up the database
-/src/router/auth.py contains the logic for the /signup and /login endpoints
-/src/router/ holds all the files for endpoints

## How to run:
1. you might need cp .env.example .env
2. Docker-compose build
3. Docker-compose up
4. In postman, test signup endpoint using POST http://localhost:8080/auth/signup with body (NOTE you need to choose a new unused username to test this, since userone already exists now in the postgreSQL database)
{
  "username": "userone",
  "password": "useronespassword"
}
5. Then click send, and should get response 200OK with JSON success message and the user’s id
6. Repeat with an existing username, like userone
7. When send, will get 409 conflict and JSON response saying the username already exists.
8. Test the login endpoint using POST http://localhost:8080/auth/login with body
{
  "username": "userone",
  "password": "useronespassword"
}
9. Then click send, and get response 200OK with JSON containing user’s token (which can be used for uploading the document, and should be stored in the PostgreSQL database), and the user id
10. If you enter the wrong password here, get response 401 UNAUTHORIZED with error “invalid credentials”
11. A placeholder for /documents endpoint was also created but not implemented, and its MinIO database is not made either. In postman, using GET http://localhost:8080/documents with authorization auth type Bearer Token and copying in the token from step 8, when you press send it responds (for now) 200OK with status “not implemented”



Notes
-not sure if this is correctly storing the JWT token

Checkpoint Requirements: 
-do we need a UI for the checkpoint?
1. Docker Compose Works (5 points) 
• docker-compose up starts all services 
• No manual setup steps required 
• All containers start without errors
 2. Basic API Functional (5 points) 
• POST /auth/signup works 
• POST /auth/login returns token 
• POST /documents accepts PDF upload 
• API responds on port 8080 
3. One PDF Upload & Search (5 points) 
• Can upload at least one PDF 
• PDF is stored (MinIO or local, doesn’t matter yet) 
• GET /search?q=test returns results 
• Results don’t have to be perfect (even random results OK for checkpoint)
