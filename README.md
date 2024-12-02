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

## Deployment and Infrastructure

### Automated Deployment Process
- Comprehensive deployment pipeline with health checks
- Automated database initialization and verification
- SSL certificate generation and configuration
- Environment validation and configuration
- Upload directory structure creation
- Automatic service dependency verification

### Infrastructure Features
- Health monitoring system with detailed status reporting
- Connection pool management for database optimization
- Automatic recovery mechanisms for failed deployments
- Detailed logging system with debug capabilities
- Port availability checking and management

### Deployment Steps
1. Create a new Repl
2. Import the project
3. Set up environment variables in Replit Secrets:
   - `DATABASE_URL`: PostgreSQL connection string
   - `FLASK_SECRET_KEY`: Application secret key
4. The deployment script will automatically:
   - Install dependencies
   - Set up SSL certificates
   - Initialize the database
   - Create necessary directories
   - Start the application with health checks

### Health Monitoring
- Real-time application health monitoring
- Database connection status verification
- SSL certificate validation
- Resource availability checking
- Detailed error reporting and logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security

### Authentication and Data Protection
- All passwords are hashed using secure methods
- File uploads are validated and sanitized
- SQL injection protection through SQLAlchemy
- CSRF protection on all forms
- Secure session management

### Database Security
- SSL-enforced database connections with certificate verification
- Connection pooling with automatic health checks
- Keepalive settings for connection stability
- Statement timeout limits for query protection
- Automated SSL certificate generation and management

### Infrastructure Security
- Environment variable validation and protection
- Secure file system permissions management
- Automated security configuration validation
- Protected upload directories with access control
- Detailed error logging with debug capabilities
- Automatic service dependency verification
- Enhanced error recovery mechanisms
- Comprehensive system health monitoring

## API Documentation

### Authentication Endpoints

#### Register User
- **URL**: `/auth/register`
- **Method**: `POST`
- **Parameters**:
  - `username` (required): User's username
  - `email` (required): User's email address
  - `password` (required): User's password
  - `confirm_password` (required): Password confirmation
- **Response**:
  - Success: Redirects to login page
  - Error: Returns form with validation errors

#### Login
- **URL**: `/auth/login`
- **Method**: `POST`
- **Parameters**:
  - `email` (required): User's email address
  - `password` (required): User's password
- **Response**:
  - Success: Redirects to dashboard
  - Error: Returns form with validation errors

### Medication Management

#### Get Dashboard
- **URL**: `/dashboard`
- **Method**: `GET`
- **Authentication**: Required
- **Response**: Dashboard page with medication list and consumption form

#### Get Inventory
- **URL**: `/inventory`
- **Method**: `GET`
- **Authentication**: Required
- **Response**: Inventory page with medication list and forms

#### Add Medication
- **URL**: `/inventory`
- **Method**: `POST`
- **Authentication**: Required
- **Parameters**:
  - `name` (required): Medication name
  - `dosage` (required): Dosage amount
  - `frequency`: Frequency of doses
  - `current_stock` (required): Initial stock quantity
  - `scheduled_time`: Scheduled administration time
  - `max_daily_doses`: Maximum doses per day
- **Response**:
  - Success: Redirects to inventory page
  - Error: Returns form with validation errors

#### Update Stock
- **URL**: `/update_stock/<med_id>`
- **Method**: `POST`
- **Authentication**: Required
- **Parameters**:
  - `quantity` (required): Stock quantity change (positive or negative)
- **Response**:
  - Success: Redirects to inventory page
  - Error: Returns error message

#### Delete Medication
- **URL**: `/medication/<med_id>/delete`
- **Method**: `POST`
- **Authentication**: Required
- **Response**:
  - Success: Redirects to inventory page
  - Error: Returns error message

### Consumption Tracking

#### Log Consumption
- **URL**: `/log_consumption/<med_id>`
- **Method**: `POST`
- **Authentication**: Required
- **Parameters**:
  - `quantity` (required): Amount consumed
- **Response**:
  - Success: Redirects to dashboard
  - Error: Returns error message

#### View History
- **URL**: `/history`
- **Method**: `GET`
- **Authentication**: Required
- **Response**: History page with consumption records

### Prescription Management

#### Upload Prescription
- **URL**: `/upload_prescription/<med_id>`
- **Method**: `POST`
- **Authentication**: Required
- **Parameters**:
  - `prescription_file` (required): PDF or image file
  - `expiry_date`: Prescription expiry date
  - `notes`: Additional notes
- **Response**:
  - Success: Redirects to inventory page
  - Error: Returns form with validation errors

### Reports and Analytics

#### Generate Reports
- **URL**: `/reports`
- **Method**: `GET`
- **Authentication**: Required
- **Query Parameters**:
  - `date_range`: Number of days (7, 30, or 90)
  - `medication_id`: Specific medication ID
- **Response**: Reports page with consumption analytics

### System Health

#### Health Check
- **URL**: `/health`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "status": "healthy",
    "timestamp": "ISO-8601 timestamp",
    "database": {
      "connected": true,
      "ssl_mode": "verify-full",
      "ssl_in_use": true,
      "server_version": "PostgreSQL version",
      "connection_pool": {
        "size": 5,
        "timeout": 30,
        "max_overflow": 10
      }
    }
  }
  ```

## Support

For support, please open an issue in the repository or contact the maintainers.
