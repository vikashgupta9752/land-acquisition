# Real-Time National Land Acquisition & Management System (NLAMS)

A complete Django-based web application for managing the end-to-end government land acquisition workflow digitally across five role-based panels.

## Tech Stack
- **Backend:** Python 3.11+, Django 5.2
- **Frontend:** HTML5, CSS3, Bootstrap 5, Bootstrap Icons, JavaScript
- **Database:** SQLite (MySQL-compatible)
- **Charts & Maps:** Chart.js, Leaflet.js + Leaflet.Draw (OpenStreetMap)

## Five Role-Based Panels
1. **Admin Panel** (`/accounts/admin-panel/`): User management, departments, system statistics, audit logs.
2. **Government Officer Panel** (`/projects/officer-dashboard/`): Project creation, land records, survey assignment & verification, compensation calculator, official notifications, objection review, payments, and possession.
3. **Surveyor Panel** (`/surveys/dashboard/`): Assigned field surveys, inspection measurements, photo/document uploads, status updates.
4. **Landowner / Citizen Panel** (`/land-records/my-dashboard/`): Self-registration, personal land parcels, official notices, compensation/payment tracking, objection submission.
5. **Monitoring & Decision Support Panel** (`/monitoring/dashboard/`): Real-time KPIs, Chart.js analytics, GIS map, delayed projects, district/village summaries, and CSV/PDF report exports.

## Quick Start (Local Setup)

```bash
cd land_acquisition
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

## Demo Accounts (Seeded by `seed_demo_data`)
| Role | Username | Password |
| :--- | :--- | :--- |
| Administrator | `admin` | `Admin@123` |
| Government Officer | `officer1` | `Officer@123` |
| Surveyor | `surveyor1` | `Survey@123` |
| Landowner / Citizen | `citizen1` | `Citizen@123` |
| Monitoring Official | `monitor1` | `Monitor@123` |
