# S2T Gym Attendance & Membership Management System

A production-ready, full-stack application designed specifically for **S2T Fitness Studio** to manage gym memberships, track payments, generate QR codes, and log member attendance. 

The application is optimized for **lightning-fast response times** (~150ms-300ms) by utilizing a localized Mumbai database, omitting connection pre-pings, skipping transaction commits on GET requests, and executing consolidated single-round-trip database queries.

---

## 🚀 Key Features

### 👤 Member Portal
- **Self-Registration:** New members can register, select a plan (Monthly, Annually, Special PT), and receive a sequential member ID (e.g., `S2T101`).
- **Dashboard:** Displays real-time membership validity, plan details, and a visual attendance calendar.
- **Attendance Streak:** Live tracking of consecutive days attended to encourage gym engagement.
- **Declare Payments:** Members can notify the admin directly from the dashboard after making a payment ("I've Paid").

### 👑 Admin Dashboard
- **Consolidated Overview:** Live business KPIs including membership breakdowns, today's unique check-ins (FN/AN), pending approvals, and monthly revenue.
- **Member Management:** View and search members, activate/deactivate accounts, and edit profile details.
- **Payment Approvals Queue:** Fast approval or rejection of member-declared payments.
- **QR Code Generator:** Downloadable high-quality gym entrance QR codes linked directly to the checkout/check-in page.
- **Reports Export:** Instant Excel/CSV downloads of all attendance and revenue records.

### 🔒 Security & Optimization
- **Brute-Force Protection:** Automatically locks user accounts for 30 minutes after 5 consecutive failed login attempts.
- **Role-Based Routing:** Secured frontend pages and backend endpoints using role guards (`admin` vs. `member`).
- **Performance Optimizations:** Skip database transaction commits on read-only requests and combined multi-step fetches into single joined queries.

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy (Async), Alembic (migrations), Uvicorn.
- **Frontend:** React (Vite), TailwindCSS, React Router DOM, QRcode.js.
- **Database:** Supabase PostgreSQL (Mumbai Region `ap-south-1` for optimal latency).

---

## ⚙️ Setup & Installation

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**

### 1. Database Setup
1. Create a new **Supabase** project and select **Mumbai (ap-south-1)** as the region.
2. In Project Settings -> Database, copy the **Connection Pooler (Transaction Mode)** string.

### 2. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd S2T
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the root directory and configure it as follows:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT_ID]:[PASSWORD]@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0
   JWT_SECRET_KEY=generate-a-strong-64-character-hex-secret-key-here
   ENV=development
   ```
5. Run migrations to create tables and database triggers:
   ```bash
   python -m alembic upgrade head
   ```
6. Seed the starter admin account and plans:
   ```bash
   python scripts/seed_admin.py
   ```
7. Start the backend server:
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### 3. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd S2T/frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

---

## 🔑 Default Credentials

### Admin Login
- **Email:** `admin@s2tfitness.in`
- **Password:** `ChangeMe@Production1`

---

## 📁 Repository Structure
```
S2T/
├── alembic/              # Database migration versions
├── app/                  # FastAPI Application source code
│   ├── api/              # API Endpoints (v1)
│   ├── core/             # Configuration, Security, and Guards
│   ├── database/         # SQLAlchemy Engine & session pool
│   ├── models/           # SQLAlchemy Declarative Models
│   ├── repositories/     # Data Access layer (DAO)
│   ├── schemas/          # Pydantic validation schemas
│   └── services/         # Business logic layer
├── frontend/             # React (Vite) App
│   ├── src/
│   │   ├── api.js        # Central API fetch client
│   │   ├── components/   # Views and Admin Panel components
│   │   ├── context/      # Auth state provider
│   │   └── App.jsx       # Route registration
└── scripts/              # Data seeding scripts
```
