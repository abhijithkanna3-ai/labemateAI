# LabMate AI

## Overview

LabMate AI is a virtual laboratory assistant designed to transform laboratory operations by providing intelligent tools for chemical calculations, safety data access, and automated documentation. The application serves as a centralized platform for scientists and technicians, offering features like reagent calculators, MSDS (Material Safety Data Sheet) lookups, safety protocol access, and lab report generation. The system emphasizes safety, accuracy, and efficiency while providing a hands-free, voice-activated interface for laboratory work.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
The application uses a traditional server-side rendered web interface built with Flask templates and Bootstrap 5 for responsive design. The frontend consists of:

- **Template System**: Jinja2 templates with a base template providing consistent navigation and layout
- **Static Assets**: CSS, JavaScript, and client-side functionality organized in static directory
- **Interactive Features**: Voice command system using Web Speech API, real-time dashboard updates, and AJAX-based calculations
- **Responsive Design**: Bootstrap-based UI components with custom CSS for laboratory-specific styling

### Backend Architecture
The backend follows a Flask-based MVC pattern with the following components:

- **Flask Application**: Core web framework handling routing, session management, and HTTP requests
- **Database Layer**: SQLAlchemy ORM with support for both SQLite (development) and PostgreSQL (production)
- **Models**: Three main entities - ActivityLog (user actions tracking), Calculation (reagent calculations), and LabReport (documentation)
- **Utilities**: Chemical database management, PDF report generation using ReportLab, and calculation functions
- **Session Management**: UUID-based session tracking for user activity isolation

### Data Storage Solutions
The application uses SQLAlchemy ORM with a flexible database configuration:

- **Primary Database**: SQLite for local development, PostgreSQL for production
- **Static Data**: JSON files for chemical properties, safety protocols, and reference data
- **Session Storage**: Flask sessions with configurable secret keys
- **Connection Management**: Connection pooling and health checks for database reliability

### Safety and Chemical Data Management
The system maintains comprehensive safety and chemical information:

- **Chemical Database**: JSON-based storage of molecular weights, hazard information, and safety notes
- **Safety Protocols**: Structured emergency procedures and first-aid instructions
- **MSDS Integration**: Quick access to Material Safety Data Sheets and chemical properties
- **Activity Logging**: Comprehensive tracking of all user actions for audit trails

### Authentication and Session Management
The application uses session-based authentication with user profiles:

- **User Authentication**: Simple form-based login with name, role, and institution
- **Session Management**: UUID-generated session IDs with user profile storage
- **User Roles**: Support for researcher, technician, student, supervisor, and other roles
- **Activity Tracking**: All user actions logged with session and user correlation
- **Profile Management**: Users can update their profile information during sessions
- **Session Security**: Protected routes requiring authentication before access

## External Dependencies

### Python Libraries
- **Flask**: Web framework for routing and request handling
- **SQLAlchemy**: Database ORM and connection management
- **ReportLab**: PDF generation for laboratory reports
- **UUID**: Session identifier generation

### Frontend Dependencies
- **Bootstrap 5**: CSS framework for responsive design and UI components
- **Font Awesome 6**: Icon library for user interface elements
- **Web Speech API**: Browser-native voice recognition for hands-free operation

### Data Sources
- **Chemical Database**: Local JSON file containing molecular weights, hazard classifications, and safety information
- **Safety Protocols**: JSON-structured emergency procedures and laboratory safety guidelines

### Development Tools
- **SQLite**: Local development database
- **Environment Variables**: Configuration for database URLs and session secrets
- **Static File Serving**: Flask's built-in static file handling for CSS, JavaScript, and assets

### Production Considerations
- **PostgreSQL**: Recommended production database with connection pooling
- **Environment Configuration**: Support for DATABASE_URL and SESSION_SECRET environment variables
- **Logging**: Debug-level logging configured for development and monitoring