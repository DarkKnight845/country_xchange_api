# Country Exchange Data API

This project is a RESTful API built with FastAPI that provides up-to-date data on world countries, including population, capital, region, and an estimated GDP calculated using currency exchange rates fetched from external APIs. The data is stored and served from a persistent PostgreSQL database.

## 🚀 Features

The API serves the following primary endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/countries` | `GET` | Retrieve a paginated and sortable list of all countries. |
| `/countries/{country_id}` | `GET` | Retrieve detailed information for a specific country by ID. |
| `/status` | `GET` | Check the last successful data refresh time. |

### Data Refresh Logic

Data persistence and updates are handled by the `refresh_logic.py` script, which:

1. Fetches fresh country data from `restcountries.com`.
2. Fetches the latest exchange rates from an external API.
3. Calculates an estimated GDP for each country based on population and exchange rate.
4. Updates or inserts records into the PostgreSQL database.

## 🛠️ Technology Stack

* **API Framework:** FastAPI
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy 2.0
* **Deployment:** Docker, Docker Compose, Railway

## 💻 Local Development Setup

The easiest way to run this project locally is using Docker Compose, which manages both the FastAPI application and the PostgreSQL database.

### Prerequisites

* Docker Desktop (Running)

### 1. Environment Variables

Create a file named `.env` in the root directory and populate it with the following connection details. These credentials are used by both the `api` service and the `postgres` service defined in `docker-compose.yml`.
```env
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=countries_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://your_username:your_password@postgres:5432/countries_db
```