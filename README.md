# MedTracker - Medication Management System

MedTracker is a comprehensive web application designed to help users manage their medications, track consumption, monitor inventory, and maintain prescription records. The system provides detailed analytics and reporting features to ensure medication adherence and efficient inventory management.

## Features

- **User Authentication**
  - Secure login and registration
  - Password protection and session management
  - User-specific medication tracking

- **Medication Management**
  - Add and update medications
  - Track dosage and frequency
  - Set scheduled times for medication
  - Monitor current stock levels
  - Low stock alerts

- **Prescription Management**
  - Upload and store prescription files (PDF, JPG, PNG)
  - Track prescription expiry dates
  - Add notes to prescriptions
  - Secure file storage

- **Consumption Tracking**
  - Log medication doses
  - Record consumption status (taken, missed, skipped)
  - Track adherence to scheduled times
  - Historical consumption records

- **Analytics and Reporting**
  - Detailed consumption reports
  - Date range filtering
  - Medication-specific analytics
  - Adherence rate tracking
  - Interactive charts and visualizations
  - Export functionality

## Tech Stack

- **Backend**
  - Python 3.11
  - Flask Framework
  - PostgreSQL Database
  - SQLAlchemy ORM
  - Flask-Login for authentication
  - Flask-WTF for forms

- **Frontend**
  - HTML5/CSS3
  - Bootstrap 5.3
  - JavaScript
  - Chart.js for visualizations
  - Responsive design

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
DATABASE_URL=postgresql://[user]:[password]@[host]:[port]/[database]
FLASK_SECRET_KEY=[your-secret-key]
```

4. Initialize the database:
```bash
flask db upgrade
```

5. Run the application:
```bash
python run.py
```

## Project Structure

```
medtracker/
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── main.js
│   │   └── chart_config.js
│   └── uploads/
│       └── prescriptions/
├── templates/
│   ├── layout.html
│   ├── dashboard.html
│   ├── inventory.html
│   ├── reports.html
│   └── ...
├── app.py
├── models.py
├── routes.py
├── forms.py
└── README.md
```

## Usage Guide

1. **Registration and Login**
   - Create a new account with email and password
   - Login with your credentials
   - Use "Remember Me" for convenience

2. **Adding Medications**
   - Navigate to Inventory
   - Click "Add New Medication"
   - Fill in medication details
   - Set dosage and schedule

3. **Tracking Consumption**
   - Use the Dashboard for daily tracking
   - Log doses as taken, missed, or skipped
   - Monitor adherence through reports

4. **Managing Prescriptions**
   - Upload prescriptions in the Inventory section
   - Add expiry dates and notes
   - View prescription history

5. **Generating Reports**
   - Access the Reports section
   - Select date range and medication
   - View consumption trends
   - Export data as needed

## Deployment

The application is designed to be deployed on Replit:

1. Create a new Repl
2. Import the project
3. Set up environment variables in Replit Secrets
4. Install dependencies using the package manager
5. Use the run button to start the application

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security

- All passwords are hashed using secure methods
- File uploads are validated and sanitized
- SQL injection protection through SQLAlchemy
- CSRF protection on all forms
- Secure session management

## Support

For support, please open an issue in the repository or contact the maintainers.
