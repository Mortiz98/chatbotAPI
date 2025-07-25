# 🤖 ChatBot API with OpenAI Integration

An API for a chatbot integrated with OpenAI, built using FastAPI and SQLAlchemy.

## 🚀 Features

* 💬 Natural Language Processing with OpenAI
* 🔐 Full JWT-based authentication system
* 📜 Persistent conversation history
* 🔄 Chat session management
* 🛡️ Secure implementation using bcrypt and safe cookies

## 📋 Prerequisites

* Python 3.8 or higher
* PostgreSQL (or SQLite for development)
* Environment variables configured (see Configuration section)

## 🛠️ Installation

1. Clone the repository:

```bash
git clone <https://github.com/Mortiz98/chatbotAPI.git>
cd chatbot
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment variables:

```bash
# Create .env file
# Edit .env with your credentials
```

## ⚙️ Configuration

Create a `.env` file in the project root with the following content:

```env
# JWT
SECRET_KEY="your-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=1440

# Database
SQLALCHEMY_DATABASE_URL="postgresql://user:password@localhost/dbname"
# For SQLite:
# SQLALCHEMY_DATABASE_URL="sqlite:///./sql_app.db"

# OpenAI
OPENAI_API_KEY="your-openai-api-key"
```

## 🚀 Running the Project

Start the development server:

```bash
uvicorn main:app --reload
```

Access:

* API: [http://localhost:8000](http://localhost:8000)
* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 📌 Main Endpoints

### Authentication

* `POST /auth/register`: Register a new user
* `POST /auth/login`: Log in
* `POST /auth/logout`: Log out
* `GET /auth/me`: Get current user
* `POST /auth/refresh`: Refresh access token

### Chat

* `POST /chat/start`: Start a new chat session
* `POST /chat/message`: Send a message
* `GET /chat/history`: Get chat history
* `GET /chat/session/{session_id}`: Get a specific session

## 💄 Database Structure

### Users

* `id`: Integer (Primary Key)
* `email`: String (Unique)
* `username`: String (Unique)
* `hashed_password`: String
* `is_active`: Boolean
* `created_at`: DateTime
* `updated_at`: DateTime

### Messages

* `id`: Integer (Primary Key)
* `content`: String
* `is_bot`: Boolean
* `created_at`: DateTime
* `user_id`: Integer (Foreign Key)
* `session_id`: Integer (Foreign Key)

### ChatSessions

* `id`: Integer (Primary Key)
* `user_id`: Integer (Foreign Key)
* `started_at`: DateTime
* `ended_at`: DateTime

## 🔒 Security

* Passwords hashed with bcrypt
* JWT-based authentication
* Secure cookies (`httponly`, `samesite`)
* Configurable CORS policy

## 🛠️ Technologies Used

* [FastAPI](https://fastapi.tiangolo.com/) – Web framework
* [SQLAlchemy](https://www.sqlalchemy.org/) – ORM for Python
* [Pydantic](https://docs.pydantic.dev/) – Data validation
* [OpenAI API](https://platform.openai.com/) – NLP processing
* [Python-Jose](https://python-jose.readthedocs.io/) – JWT implementation
* [Passlib](https://passlib.readthedocs.io/) – Password hashing

## 📜 Upcoming Features

* [ ] Rate limiting
* [ ] Unit and integration testing
* [ ] Improved API documentation
* [ ] CI/CD configuration
* [ ] Caching for frequent responses
* [ ] Support for multiple AI models

## 👥 Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to your branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License – see the [LICENSE.md](LICENSE.md) file for details.
