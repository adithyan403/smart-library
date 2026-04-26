# E-Library System

A lightweight, full-stack E-Library system optimized for low-spec systems (4GB RAM). Features a 3D interactive library interface, admin dashboard, and integrated PDF reader.

## Features

- **3D Library Interface** - Interactive Three.js-based library room with bookshelves
- **Admin Dashboard** - Manage departments, upload/delete books
- **PDF Reader** - Integrated PDF.js viewer with zoom and navigation
- **Lightweight** - Minimal dependencies, optimized for low-spec hardware

## Folder Structure

```
smart_library/
├── app.py              # Flask backend
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── templates/
│   ├── index.html      # 3D Library interface
│   ├── login.html      # Admin login page
│   └── dashboard.html  # Admin dashboard
└── static/
    ├── css/
    ├── js/
    └── models/
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- D: drive (or modify `LIBRARY_ROOT` in app.py for custom path)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Library Directory

The backend will automatically create `D:/library/` on first run. You can also create it manually:

```bash
mkdir D:\library
```

### 4. Run the Application

```bash
python app.py
```

The server will start at `http://localhost:5000`

## Usage

### Access Points

- **Library (3D View)**: http://localhost:5000/
- **Admin Dashboard**: http://localhost:5000/admin

### Default Admin Credentials

- Username: `admin`
- Password: `admin123`

### Admin Features

1. **Create Department** - Add new category folders
2. **Upload Book** - Upload PDF files (max 15MB)
3. **Delete Book/Department** - Remove files and folders
4. **View All Books** - See all departments and their contents

### Library Features

1. **3D Navigation** - View library as interactive 3D scene
2. **Browse Books** - Click on books to see details
3. **Read PDF** - Open books in integrated PDF reader
4. **Zoom/Navigate** - Use controls for PDF viewing

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/login | Admin login | No |
| POST | /api/logout | Admin logout | Yes |
| GET | /api/departments | List all departments | No |
| POST | /api/create_department | Create department | Yes |
| DELETE | /api/delete_department | Delete department | Yes |
| GET | /api/books/\<dept\> | List books in department | No |
| POST | /api/upload | Upload PDF book | Yes |
| DELETE | /api/delete_book | Delete a book | Yes |
| GET | /api/read/\<dept\>/\<file\> | Serve PDF file | No |
| GET | /api/all_books | List all books | No |

## Configuration

Edit `app.py` to modify:

```python
LIBRARY_ROOT = "D:/library/"      # Storage location
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB limit
ADMIN_USERNAME = "admin"          # Login username
ADMIN_PASSWORD = "admin123"       # Login password
```

## Keyboard Shortcuts (PDF Reader)

- `Escape` - Close PDF reader
- `Arrow Left` - Previous page
- `Arrow Right` - Next page

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: Tailwind CSS, Vanilla JS
- **3D**: Three.js, GSAP
- **PDF**: PDF.js

## Troubleshooting

### "Module not found" error
```bash
pip install flask
```

### Library folder not found
Ensure `D:/library/` exists or run the app as administrator

### 3D not loading
Make sure your browser supports WebGL

## Security Notes

- Change default admin credentials for production
- The app uses session-based authentication
- File uploads are restricted to PDF only
- File size is limited to 15MB
