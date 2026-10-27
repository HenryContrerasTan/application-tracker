# Application Tracker

A full-stack web application for tracking full-time and internship
applications, built as a portfolio project.

## What it does

- Add applications with company, role, type (Full-time / Internship),
  status (Saved / Applied / Interview / Offer / Rejected), location,
  date applied, posting link, and notes.
- **Persistent storage:** every application is saved in a local SQLite
  database (`tracker.db`). Closing the server does not lose data.
- **Search and filter:** search by company, role, or notes, and filter by
  status and by type.
- Change an application's status inline, or delete it.
- See a count of total and currently shown applications.

## Tech used

- **Frontend:** HTML, CSS, JavaScript (`index.html`, `styles.css`, `app.js`)
- **Backend:** Python, standard library only — `http.server` and `sqlite3`
  (`app.py`). No third-party packages, so nothing needs installing.
- **Database:** SQLite (`tracker.db`, created automatically on first run)

## How to run it

```bash
cd job-application-tracker
python3 app.py
```

Then open **http://localhost:8000** in a browser.

To stop it, press `Ctrl+C` in the terminal. Your data stays in
`tracker.db`, so it is still there the next time you run it.

## How it works

1. The browser loads the page from the Python server.
2. The JavaScript frontend calls the JSON API on the same server:
   `GET /api/applications`, `POST /api/applications`,
   `PUT /api/applications/<id>`, `DELETE /api/applications/<id>`,
   and `GET /api/stats`.
3. The Python backend validates the input (company and role are
   required; type and status must be from the allowed lists) and stores
   it in SQLite with parameterized queries.

## What I built / learned

- A complete request flow: form → JavaScript `fetch` → Python API →
  SQLite → JSON response → updated UI.
- Server-side validation and parameterized SQL queries (no string
  concatenation of user input into SQL).
- Search with SQL `LIKE` and filtering by query parameters, plus
  sorting by date applied.
- Keeping a project dependency-free so it runs anywhere Python 3 is
  installed.

## Notes

- This is a personal project. It contains no real employer data:
  the database starts empty — add your own applications.
- The server listens only on `127.0.0.1` (your own computer), not on
  a public network.
