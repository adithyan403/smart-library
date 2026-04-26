"""
E-Library Flask Backend
Lightweight backend optimized for low-spec systems (4GB RAM)
"""

import os
import json
import secrets
import pdfcrowd
import requests
import threading
import time
import random
import re
import io
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, send_file, redirect, url_for
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from ollama import Client

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Configuration
LIBRARY_ROOT = "D:/library/"
AI_LIBRARY_ROOT = "D:/ai_library/"
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB
ALLOWED_EXTENSION = {'pdf'}
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# AI Configuration
OPENAI_API_KEY = "ee3d6e51e3024a2b8c5f60fb3b9f9ed5.V6UJsXoqdXhud5bveICvuMqZ"
AI_GENERATOR_RUNNING = False
AI_TOPICS = ['Biology', 'Space', 'IT', 'Physics', 'Zoology', 'Circuits', 'Semiconductors', 'Automobiles', 'Power System', 'Chemistry', 'Geology', 'World History', 'Psychology', 'Economics', 'Astronomy', 'Literature', 'Machine Learning', 'Sociology', 'Mathematics', 'Philosophy', 'Art History', 'Architecture']
MINIMAX_API_URL = "https://api.minimax.chat/v1/chat/completions"
MINIMAX_MODEL = "minimax-text-01"
DRIVE_FOLDER_ID = "1xEzh5cOTZBQbQkdzmsG-fDjuX5gG4Wg0"
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_gdrive_service():
    # 1. Render Deployment (Headless Server-to-Server)
    if 'GOOGLE_CREDENTIALS_JSON' in os.environ:
        try:
            creds_info = json.loads(os.environ['GOOGLE_CREDENTIALS_JSON'])
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Service Account Auth Error: {e}")
            return None

    # 2. Local Environment Fallback (User Auth)
    creds = None
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception:
            pass
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Google Drive warning: credentials.json not found! Drive functions will fail.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    try:
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"GDrive Auth Error: {e}")
        return None

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSION

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def ensure_ai_library_exists():
    if not os.path.exists(AI_LIBRARY_ROOT):
        os.makedirs(AI_LIBRARY_ROOT)

def ensure_library_exists():
    """Ensure the main library directory exists"""
    if not os.path.exists(LIBRARY_ROOT):
        os.makedirs(LIBRARY_ROOT)
    ensure_ai_library_exists()

ORDER_FILE = os.path.join(LIBRARY_ROOT, "book_order.json")

def load_book_order():
    if os.path.exists(ORDER_FILE):
        try:
            with open(ORDER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_book_order(order_data):
    try:
        with open(ORDER_FILE, 'w', encoding='utf-8') as f:
            json.dump(order_data, f)
        return True
    except Exception:
        return False

# ============== AI Generator Logic ==============

def generate_ai_book():
    topic = random.choice(AI_TOPICS)
    prompt = f"""Write a beautifully formatted HTML article about a random interesting concept in the field of {topic}. 
REQUIREMENTS:
- The HTML should be highly colored and reader-friendly. 
- Use inline CSS to style different colored text for headings.
- Include topic-relevant images from the web using exactly this HTML format: <img src="https://image.pollinations.ai/prompt/[url-encoded-description]" alt="description" style="max-width:100%; border-radius:8px; margin:20px 0;">
- IMPORTANT: You MUST use the <img> HTML tag. Do NOT use markdown.
- IMPORTANT: Replace any spaces in the image URL prompt with %20. Example: https://image.pollinations.ai/prompt/biology%20cell%20diagram
- Greatly increase the depth of the content by adding helpful data tables, comparative analysis blocks, and real-world examples to explain the concepts.
- The very first element MUST be an <h1> tag containing the exact title of the article.
- Use simple language for easier understanding.
- Do NOT output ```html markdown blocks, just raw HTML string.
- Target a length of roughly 5 to 10 rich pages."""
    
    try:
        api_key = os.environ.get('OLLAMA_API_KEY', OPENAI_API_KEY)
        client = Client(
            host="https://ollama.com",
            headers={'Authorization': 'Bearer ' + str(api_key)}
        )
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt}
        ]
        
        print(f"Generating AI Book on '{topic}' using Ollama gpt-oss:120b...")
        html_content = ""
        for part in client.chat('gpt-oss:120b', messages=messages, stream=True):
            chunk = part['message']['content']
            html_content += chunk
            print(chunk, end='', flush=True)
            
        print("\n[AI Generation Complete]")
        html_content = html_content.strip()
        
        # Remove DeepSeek <think> reasoning chunks if any
        html_content = re.sub(r'<think>.*?</think>', '', html_content, flags=re.DOTALL).strip()
            
        if html_content.startswith('```html'):
            html_content = html_content[7:]
        if html_content.endswith('```'):
            html_content = html_content[:-3]
        html_content = html_content.strip()
            
        temp_html_path = os.path.join(AI_LIBRARY_ROOT, "temp_ai_book.html")
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        # Extract book title from H1 tag
        title_match = re.search(r'<h1.*?>(.*?)</h1>', html_content, re.IGNORECASE)
        if title_match:
            raw_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            book_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)
        else:
            book_title = f"{topic}_Concept_{int(time.time())}"
        if not book_title:
            book_title = f"{topic}_Concept_{int(time.time())}"
        
        client = pdfcrowd.HtmlToPdfClient('demo', 'demo')
        client.setContentViewportWidth('balanced')
        client.setJavascriptDelay(2000) # Maximum allowed by demo tier is 2000ms
        client.setUsePrintMedia(True)
        dept_path = os.path.join(AI_LIBRARY_ROOT, topic)
        os.makedirs(dept_path, exist_ok=True)
        
        filename = f"{book_title}.pdf"
        pdf_path = os.path.join(dept_path, filename)
        client.convertFileToFile(temp_html_path, pdf_path)
        
        # Upload to Google Drive immediately rather than persistent local storage
        service = get_gdrive_service()
        if service:
            file_metadata = {
                'name': filename,
                'parents': [DRIVE_FOLDER_ID],
                'description': topic # Using Drive's description to store the topic 
            }
            media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"Uploaded {filename} to Google Drive folder.")
            
            # Discard local file after upload
            try:
                os.remove(temp_html_path)
                os.remove(pdf_path)
            except:
                pass
    except Exception as e:
        print("AI Generation Error:", str(e))

def ai_scheduler_loop():
    global AI_GENERATOR_RUNNING
    while AI_GENERATOR_RUNNING:
        generate_ai_book()
        for _ in range(900):
            if not AI_GENERATOR_RUNNING:
                break
            time.sleep(1)

# ============== Routes ==============

@app.route('/')
def index():
    """Main entry point - redirects to 3D library"""
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    """Admin dashboard page"""
    if session.get('logged_in'):
        return render_template('dashboard.html')
    return render_template('login.html')

# ============== Authentication ==============

@app.route('/api/login', methods=['POST'])
def login():
    """Handle admin login"""
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['logged_in'] = True
        return jsonify({'success': True, 'message': 'Login successful'})
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """Handle admin logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'})

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    return jsonify({'logged_in': session.get('logged_in', False)})

# ============== Department Management ==============

@app.route('/api/departments', methods=['GET'])
def get_departments():
    """Get all departments"""
    ensure_library_exists()
    departments = []
    for name in os.listdir(LIBRARY_ROOT):
        path = os.path.join(LIBRARY_ROOT, name)
        if os.path.isdir(path):
            book_count = len([f for f in os.listdir(path) if f.endswith('.pdf')])
            departments.append({
                'name': name,
                'book_count': book_count
            })
    return jsonify({'departments': departments})

@app.route('/api/create_department', methods=['POST'])
@login_required
def create_department():
    """Create a new department (folder)"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'error': 'Department name required'}), 400
    
    # Sanitize folder name
    name = "".join(c for c in name if c.isalnum() or c in ' -_').strip()
    if not name:
        return jsonify({'error': 'Invalid department name'}), 400
    
    dept_path = os.path.join(LIBRARY_ROOT, name)
    if os.path.exists(dept_path):
        return jsonify({'error': 'Department already exists'}), 400
    
    os.makedirs(dept_path)
    return jsonify({'success': True, 'message': f'Department "{name}" created'})

@app.route('/api/delete_department', methods=['DELETE'])
@login_required
def delete_department():
    """Delete a department and all its contents"""
    data = request.get_json()
    name = data.get('name', '')
    
    if not name:
        return jsonify({'error': 'Department name required'}), 400
    
    dept_path = os.path.join(LIBRARY_ROOT, name)
    if not os.path.exists(dept_path):
        return jsonify({'error': 'Department not found'}), 404
    
    try:
        # Remove all files in department
        for file in os.listdir(dept_path):
            os.remove(os.path.join(dept_path, file))
        os.rmdir(dept_path)
        return jsonify({'success': True, 'message': f'Department "{name}" deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============== Book Management ==============

@app.route('/api/books/<department>', methods=['GET'])
def get_books(department):
    """Get all books in a department"""
    dept_path = os.path.join(LIBRARY_ROOT, department)
    if not os.path.exists(dept_path):
        return jsonify({'error': 'Department not found'}), 404
    
    books = []
    for filename in os.listdir(dept_path):
        if filename.endswith('.pdf'):
            # Extract book name from filename (remove .pdf extension)
            book_name = filename[:-4]
            filepath = os.path.join(dept_path, filename)
            books.append({
                'name': book_name,
                'filename': filename,
                'size': os.path.getsize(filepath)
            })
            
    order_data = load_book_order()
    if department in order_data:
        ordered_list = order_data[department]
        books.sort(key=lambda x: ordered_list.index(x['filename']) if x['filename'] in ordered_list else len(ordered_list))
        
    return jsonify({'books': books})

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_book():
    """Upload new books (PDFs)"""
    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    if 'files' in request.files:
        files = request.files.getlist('files')
    else:
        files = [request.files['file']]
        
    department = request.form.get('department', '').strip()
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not department:
        return jsonify({'error': 'Department required'}), 400
    
    dept_path = os.path.join(LIBRARY_ROOT, department)
    if not os.path.exists(dept_path):
        os.makedirs(dept_path)
        
    uploaded = 0
    errors = []
    last_filename = ""
    
    for file in files:
        if not allowed_file(file.filename):
            errors.append(f"{file.filename}: Only PDF allowed")
            continue
            
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
             errors.append(f"{file.filename}: Too large")
             continue
             
        book_name = file.filename.rsplit('.', 1)[0]
        if len(files) == 1 and request.form.get('book_name', '').strip():
            book_name = request.form.get('book_name', '').strip()
            
        safe_name = "".join(c for c in book_name if c.isalnum() or c in ' -_').strip()
        filename = f"{safe_name}.pdf"
        filepath = os.path.join(dept_path, filename)
        
        counter = 1
        while os.path.exists(filepath):
            filename = f"{safe_name}_{counter}.pdf"
            filepath = os.path.join(dept_path, filename)
            counter += 1
            
        try:
            file.save(filepath)
            uploaded += 1
            last_filename = filename
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            
    if uploaded > 0:
        return jsonify({
            'success': True,
            'message': f'Uploaded {uploaded} book(s).' + (f' {len(errors)} failed.' if errors else ''),
            'filename': last_filename
        })
    return jsonify({'error': '\n'.join(errors) if errors else 'Upload failed'}), 400

@app.route('/api/rename_book', methods=['POST'])
@login_required
def rename_book():
    """Rename a book"""
    data = request.get_json()
    department = data.get('department', '')
    old_name = data.get('old_name', '')
    new_name = data.get('new_name', '')
    
    if not all([department, old_name, new_name]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    dept_path = os.path.join(LIBRARY_ROOT, department)
    old_path = os.path.join(dept_path, old_name)
    
    if not os.path.exists(old_path):
        return jsonify({'error': 'File not found'}), 404
    
    safe_new_name = "".join(c for c in new_name if c.isalnum() or c in ' -_').strip()
    new_filename = f"{safe_new_name}.pdf"
    new_path = os.path.join(dept_path, new_filename)
    
    if os.path.exists(new_path):
        return jsonify({'error': 'A file with this name already exists'}), 400
    
    try:
        os.rename(old_path, new_path)
        return jsonify({
            'success': True,
            'message': 'Book renamed',
            'new_filename': new_filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_book', methods=['DELETE'])
@login_required
def delete_book():
    """Delete a book"""
    data = request.get_json()
    department = data.get('department', '')
    filename = data.get('filename', '')
    
    if not all([department, filename]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    filepath = os.path.join(LIBRARY_ROOT, department, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        os.remove(filepath)
        return jsonify({'success': True, 'message': 'Book deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============== File Serving & Ordering ==============

@app.route('/api/ai/start', methods=['POST'])
def start_ai_generator():
    global AI_GENERATOR_RUNNING
    if not AI_GENERATOR_RUNNING:
        AI_GENERATOR_RUNNING = True
        threading.Thread(target=ai_scheduler_loop, daemon=True).start()
        return jsonify({'success': True, 'message': 'AI Generator started'})
    return jsonify({'success': False, 'message': 'Already running'})

@app.route('/api/ai/stop', methods=['POST'])
def stop_ai_generator():
    global AI_GENERATOR_RUNNING
    AI_GENERATOR_RUNNING = False
    return jsonify({'success': True, 'message': 'AI Generator stopping...'})

@app.route('/api/ai/status', methods=['GET'])
def ai_status():
    global AI_GENERATOR_RUNNING
    return jsonify({'running': AI_GENERATOR_RUNNING})

@app.route('/api/ai/force_generate', methods=['POST'])
def force_generate():
    def task():
        generate_ai_book()
    threading.Thread(target=task, daemon=True).start()
    return jsonify({'success': True, 'message': 'Manual generation triggered'})

@app.route('/api/ai_books', methods=['GET'])
def get_ai_books():
    """Get all AI books directly from Google Drive"""
    service = get_gdrive_service()
    if not service:
        return jsonify({'books': []})
        
    all_books = []
    try:
        page_token = None
        while True:
            query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false"
            response = service.files().list(q=query, spaces='drive',
                                            fields='nextPageToken, files(id, name, size, description)',
                                            pageToken=page_token).execute()
            for file in response.get('files', []):
                filename = file.get('name')
                book_name = filename[:-4] if filename.endswith('.pdf') else filename
                
                all_books.append({
                    'name': book_name,
                    'filename': filename,
                    'department': file.get('description', 'AI_Generated'),
                    'size': int(file.get('size', 0)),
                    'drive_id': file.get('id')
                })
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
    except Exception as e:
        print(f"Drive API Fetch Error: {str(e)}")
            
    return jsonify({'books': all_books})

@app.route('/api/ai_read/<department>/<filename>')
def read_ai_book(department, filename):
    """Stream AI book direct from Google Drive"""
    service = get_gdrive_service()
    if not service:
        return jsonify({'error': 'Drive service not available'}), 500
        
    try:
        query = f"'{DRIVE_FOLDER_ID}' in parents and name='{filename}' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        if not files:
            return jsonify({'error': 'File not found in Drive'}), 404
            
        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        return send_file(fh, download_name=filename, as_attachment=False, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_order', methods=['POST'])
def save_order():
    """Save explicit book ordering"""
    data = request.get_json()
    department = data.get('department')
    order = data.get('order')
    
    if not department or not isinstance(order, list):
        return jsonify({'error': 'Invalid data'}), 400
        
    order_data = load_book_order()
    order_data[department] = order
    save_book_order(order_data)
    
    return jsonify({'success': True})

@app.route('/api/read/<department>/<filename>')
def read_book(department, filename):
    """Serve a PDF file for reading"""
    filepath = os.path.join(LIBRARY_ROOT, department, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filepath, mimetype='application/pdf')

@app.route('/api/all_books', methods=['GET'])
def get_all_books():
    """Get all books across all departments (for 3D view)"""
    ensure_library_exists()
    all_books = []
    order_data = load_book_order()
    
    for dept_name in os.listdir(LIBRARY_ROOT):
        dept_path = os.path.join(LIBRARY_ROOT, dept_name)
        if os.path.isdir(dept_path):
            dept_books = []
            for filename in os.listdir(dept_path):
                if filename.endswith('.pdf'):
                    book_name = filename[:-4]
                    dept_books.append({
                        'name': book_name,
                        'filename': filename,
                        'department': dept_name,
                        'size': os.path.getsize(os.path.join(dept_path, filename))
                    })
                    
            if dept_name in order_data:
                ordered_list = order_data[dept_name]
                dept_books.sort(key=lambda x: ordered_list.index(x['filename']) if x['filename'] in ordered_list else len(ordered_list))
                
            all_books.extend(dept_books)
            
    return jsonify({'books': all_books})

# ============== Error Handlers ==============

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    ensure_library_exists()
    print("=" * 50)
    print("E-Library Backend Starting...")
    print(f"Library root: {LIBRARY_ROOT}")
    print("Admin credentials: admin / admin123")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
