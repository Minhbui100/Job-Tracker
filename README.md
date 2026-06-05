# Job Tracker

A Flask web app for tracking job applications stored in a PostgreSQL database.

## Features

- View all applications in a card grid 
- Add applications with company, position, location, status, salary, level, date, notes, job description, posting link, and optional CV upload (PDF)
- View full details of any application
- Edit any application field
- Delete applications 

## Tech Stack

- **Backend**: Python / Flask
- **Database**: PostgreSQL (via psycopg2)
- **Frontend**: Jinja2 templates, CSS

## Setup

### Database

Create a PostgreSQL database named `job_tracker` and run the following to set up the schema:

```sql
CREATE TABLE status_table (
    id   SERIAL PRIMARY KEY,
    status TEXT UNIQUE NOT NULL
);

INSERT INTO status_table (status) VALUES
    ('not applied'), ('applied'), ('interview'), ('offer'), ('rejected');

CREATE TABLE level (
    id   SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

INSERT INTO level (name) VALUES
    ('internship'), ('entry'), ('mid'), ('senior'), ('lead');

CREATE TABLE job (
    id           SERIAL PRIMARY KEY,
    company      TEXT NOT NULL,
    position     TEXT NOT NULL,
    location     TEXT NOT NULL,
    status_id    INT REFERENCES status_table(id),
    salary       INT,
    date_applied DATE,
    note         TEXT,
    posting_link TEXT,
    description  TEXT,
    level        INT REFERENCES level(id),
    cv_path      TEXT,
    UNIQUE (company, position, location)
);
```

### Configuration

The app reads database credentials from environment variables with the following defaults:

| Variable   | Default      |
|------------|--------------|
| `host`     | `localhost`  |
| `name`     | `job_tracker`|
| `user`     | `postgres`   |
| `password` | `postgres`   |

### Run

```bash
python app.py
```

The app starts on `http://127.0.0.1:5000` by default.
