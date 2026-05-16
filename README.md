# Eventify - Event Management Platform

A Django-based event management platform for **clients** to book services, **vendors** to offer services, and **admins** to manage approvals and payments. Features include real-time chat, service booking with dynamic pricing, payment splitting between vendors, and role-based dashboards.

## Project Overview

### User Roles

- **Client**: Books events and services, makes payments, rates services, manages event details
- **Vendor**: Offers services, responds to booking requests, tracks earnings, manages availability
- **Admin**: Approves vendor sign-ups, manages system-wide transactions, views activity logs

### Core Features

1. **Authentication & Authorization**
   - Email-based registration with verification
   - Role-based access control (client/vendor/admin)
   - Password reset functionality
   - Admin approval workflow for vendors

2. **Event Management**
   - Clients create events with date, time, venue
   - Browse and book services for events
   - Approve/reject vendor bookings
   - Mark events complete with payment
   - View event history and status

3. **Service Management**
   - Vendors create and manage services
   - Set pricing and availability slots
   - Respond to booking requests (approve/reject/quote)
   - Track ratings and reviews

4. **Booking Lifecycle**
   - Client sends booking request (pending)
   - Vendor quotes, approves, or rejects
   - Client views requests and makes decisions
   - Event preparation with confirmed services

5. **Payment System**
   - Proportional payment split among multiple vendors
   - Support for partial payments with balance tracking
   - Per-vendor balance dashboard
   - Multi-role transaction history (client/vendor/admin)
   - Atomic transaction processing

6. **Chat System**
   - Real-time messaging between client and vendor
   - System notifications for booking decisions
   - Conversation history per client-vendor pair

7. **Admin Dashboard**
   - Approve vendor sign-ups
   - View all transactions and payouts
   - Monitor activity logs and system metrics
   - Manage user accounts

---

## Tech Stack

- **Backend**: Django 4.2+, PostgreSQL
- **Frontend**: HTML5, CSS3, vanilla JavaScript
- **Authentication**: Django built-in + email verification
- **Database**: PostgreSQL (local SQLite for development)

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- PostgreSQL (or SQLite for local development)
- Virtual environment tool (venv/virtualenv)

### 1. Clone and Install

```bash
# Clone the repository
git clone <repo-url>
cd eventify

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in required values:

```bash
cp .env.example .env
# Edit .env with your settings (see section below)
```

### 3. Database Setup

```bash
# Run migrations to set up schema
cd myproject
python manage.py migrate

# Create superuser (admin account)
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
cd myproject
python manage.py runserver

# Access at http://localhost:8000
```

---

## Environment Configuration

Copy `.env.example` to `.env` and configure these variables:

```env
# Django Settings
DEBUG=True                          # Set to False for production
DJANGO_SECRET_KEY=your-secret-key  # Generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
ALLOWED_HOSTS=localhost,127.0.0.1  # Production: set to your domain

# Database (choose ONE)
USE_SQLITE=1                        # Use SQLite for local development
# OR for PostgreSQL:
DATABASE_URL=postgresql://user:password@localhost:5432/eventify_db

# Email Configuration (Gmail example)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password  # Google App Password, not regular password
SENDER_ADDRESS=your-email@gmail.com

# Email Branding
EMAIL_BRAND_NAME=Eventify
EMAIL_BRAND_PRIMARY=#f97316
EMAIL_BRAND_SECONDARY=#10b981

# Features
REQUIRE_EMAIL_VERIFICATION=True     # Require users to verify email on signup

# OAuth (optional)
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# Production Security (when DEBUG=False)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

---

## Running Tests

```bash
cd myproject

# Run all tests
python manage.py test

# Run specific app tests
python manage.py test users         # User authentication tests
python manage.py test events        # Event booking tests
python manage.py test payment       # Payment and split tests
python manage.py test chat          # Chat messaging tests
python manage.py test services      # Service management tests

# Run with verbose output
python manage.py test --verbosity=2

# Stop on first failure
python manage.py test --failfast
```

### Test Coverage

- **users/tests.py**: Authentication flow, registration, password reset (20+ tests)
- **events/tests.py**: Event booking lifecycle, data validation
- **payment/tests.py**: Payment allocation, vendor splits, transaction recording
- **chat/tests.py**: Conversation creation, message history, system messages

---

## Database Migrations

Migrations are tracked in version control (git) for reproducibility:

```bash
cd myproject

# View pending migrations
python manage.py showmigrations

# Apply migrations
python manage.py migrate

# Create new migrations after model changes
python manage.py makemigrations

# See SQL for a migration
python manage.py sqlmigrate payment 0001

# Rollback a migration
python manage.py migrate payment 0001  # Go back to specific migration
```

---

## Project Structure

```
eventify/
├── myproject/                 # Django project root
│   ├── manage.py              # Django CLI
│   ├── settings.py            # Project configuration
│   ├── urls.py                # URL routing
│   │
│   ├── users/                 # User management & authentication
│   │   ├── models.py          # EventUser, Notification models
│   │   ├── views.py           # Auth, dashboard views
│   │   ├── services.py        # Business logic (auth, notifications)
│   │   ├── templates/users/   # User-facing templates
│   │   └── tests.py           # Auth flow tests
│   │
│   ├── events/                # Event management
│   │   ├── models.py          # Event, EventServiceBooking models
│   │   ├── views.py           # Event CRUD and booking handling
│   │   ├── forms.py           # Event and payment forms
│   │   ├── templates/events/  # Event templates (client/vendor)
│   │   └── tests.py           # Booking lifecycle tests
│   │
│   ├── services/              # Service listings and booking
│   │   ├── models.py          # Service, ServiceRating, ApprovalRequest
│   │   ├── views.py           # Service browsing and requests
│   │   ├── forms.py           # Service creation form
│   │   ├── rating_utils.py    # Rating calculation helpers
│   │   └── templates/services/ # Service templates
│   │
│   ├── payment/               # Payment processing
│   │   ├── models.py          # Transaction, PaymentMethod, Payout
│   │   ├── views.py           # Checkout and transaction views
│   │   ├── forms.py           # Payment method form
│   │   └── tests.py           # Payment split and transaction tests
│   │
│   ├── chat/                  # Real-time messaging
│   │   ├── models.py          # Conversation, Message models
│   │   ├── views.py           # Chat endpoints
│   │   ├── templates/chat/    # Chat templates
│   │   └── tests.py           # Message and conversation tests
│   │
│   ├── templates/             # Project-wide templates
│   │   ├── base.html          # Base layout
│   │   ├── auth.html          # Registration page
│   │   ├── landing.html       # Marketing landing
│   │   └── emails/            # Email templates
│   │
│   └── static/                # CSS, JS, images
│       ├── lucide.min.js      # Icon library
│       └── {app}/             # App-specific assets
│
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git ignore patterns
└── README.md                  # This file
```

---

## Common Workflows

### 1. Client Booking Flow

1. **Client signs up** → Registration as client → Email verification
2. **Browse services** → View available services, filter by category
3. **Request booking** → Select service, check vendor availability
4. **Await response** → Vendor replies with approval/rejection/quote
5. **Create event** → Add event date and confirmed services
6. **Make payment** → Complete event and pay vendors
7. **Rate services** → Leave feedback for vendors after completion

### 2. Vendor Approval Flow

1. **Vendor signs up** → Registration as vendor → Admin approval
2. **Set up services** → Create services with pricing and description
3. **Add availability** → Set work availability slots
4. **Respond to requests** → Approve/reject booking requests or send quotes
5. **Track earnings** → View transaction history and available balance
6. **Receive payment** → Payouts released after client payment completion

### 3. Admin Workflow

1. **Review vendors** → Dashboard shows pending vendor approvals
2. **Approve/reject** → Admin interface to manage vendor sign-ups
3. **Monitor transactions** → View all payments, splits, and payouts
4. **View activity** → Activity log of system events and approvals

---

## Key Features Details

### Payment Splitting Algorithm

When a client pays for multiple services:

1. **Proportional allocation** based on each vendor's outstanding amount
2. **Decimal precision** (0.01 BDT) to avoid rounding errors
3. **Remainder distribution** ensures exact total match
4. **Atomic transaction** - all-or-nothing payment processing

Example: Client pays 5000 BDT for two services (3000 + 2000 due)
- Vendor A: 3000/5000 × 5000 = 3000 BDT
- Vendor B: 2000/5000 × 5000 = 2000 BDT

### Role-Based Access Control

- **Middleware** checks user role on each request
- **Decorators** restrict views to specific roles (@login_required, custom decorators)
- **Template tags** show/hide UI elements based on role

### Security Features

- **CSRF protection** on all forms
- **Email verification** for new accounts (configurable)
- **Password hashing** with Django's built-in system
- **Secure cookies** (HTTPOnly, Secure flags in production)
- **SQL injection prevention** via ORM

---

## Deployment

### Production Checklist

Before deploying:

```bash
# Create .env with production values
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True

# Run checks
python manage.py check --deploy

# Collect static files
python manage.py collectstatic --no-input

# Run migrations on production database
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Environment Setup

Use PostgreSQL for production (not SQLite):

```env
DATABASE_URL=postgresql://user:password@db-host:5432/eventify_db
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
```

---

## Troubleshooting

### Tests failing with 301/redirect errors
- This is due to ALLOWED_HOSTS defaults. Set DEBUG=True in test environment.

### Migrations not applying
- Clear old migration records: `python manage.py migrate --fake eventify 0001` then re-migrate

### Email not sending
- Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env
- Gmail requires "App Passwords" for 2FA accounts
- Check Django logs for SMTP errors

### Database connection errors
- Verify DATABASE_URL or PostgreSQL service is running
- Check user permissions on database
- Use SQLite for development: set USE_SQLITE=1

---

## Contributing & Development

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable/function names
- Add docstrings to functions and classes
- Keep functions focused (single responsibility)

### Adding New Features

1. Create new models in `{app}/models.py`
2. Run migrations: `python manage.py makemigrations {app}`
3. Create views in `{app}/views.py` with proper access control
4. Add URL routes in `{app}/urls.py`
5. Create templates in `{app}/templates/{app}/`
6. Add tests in `{app}/tests.py`
7. Test locally before committing

---

## Support & Contact

For issues or questions:
1. Check existing GitHub issues
2. Review this README for common solutions
3. Check Django documentation for general questions
4. File a new issue with:
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)

---

## License

This project is for educational purposes (CSE-314 Software Engineering Lab).

---

## Contributors
This project was developed by:
- [Onindo Dey Niloy x 23101092](https://github.com/niloy92-glitch)
- [Shakib Hossain Shawon x 23101101](https://github.com/shawon13101)
- [Mariam Sheikh x 22201225](https://github.com/mariamsheikh02)
- [Ashfiq Islam x 23101106](https://github.com/AshF000)

## Project Status

**Last Updated**: May 2026  
**Version**: 1.0  
**Status**: Production-ready for evaluation

### Recent Improvements (May 2026)

- ✓ Fixed test discovery and import paths
- ✓ Generated and committed migrations to Git
- ✓ Hardened security defaults (DEBUG, ALLOWED_HOSTS, HTTPS)
- ✓ Added comprehensive logging for error tracking
- ✓ Removed unreachable code and dead functions
- ✓ Added unit tests for critical paths (payments, bookings, chat)
- ✓ Complete documentation and setup guide

