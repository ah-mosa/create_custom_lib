"""
واجهة الويب الرئيسية - الإدارة الكاملة
"""

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename

import uvicorn
import asyncio
import json
import shutil
from pathlib import Path
import zipfile
from typing import List, Dict, Any, Optional
import logging
import os
import time
import tempfile
from datetime import datetime
import threading
import hashlib


from .utils.file_manager import FileManager
from .utils.background_worker import (
    get_worker, start_worker, stop_worker,
    submit_task, get_task_status, cancel_task,
    get_all_tasks, cleanup_old_tasks
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB حد أقصى لرفع الملفات
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'zip'}

# إنشاء مجلد الرفع إذا لم يكن موجوداً
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

def allowed_file(filename):
    """التحقق من صيغة الملف المسموح بها"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ==================== نقاط النهاية الجديدة لملفات ZIP ====================

@app.route('/api/upload-zip', methods=['POST'])
def upload_zip():
    """رفع ملف ZIP واستخراجه"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'لا يوجد ملف مرفوع'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'لم يتم اختيار ملف'}), 400
        
        if file and allowed_file(file.filename):
            # إنشاء اسم آمن للملف
            filename = secure_filename(file.filename)
            
            # إنشاء مجلد مؤقت للمشروع
            temp_dir = tempfile.mkdtemp(prefix='web_scanner_')
            zip_path = os.path.join(temp_dir, filename)
            
            # حفظ ملف ZIP
            file.save(zip_path)
            
            # استخراج ملف ZIP
            extract_dir = os.path.join(temp_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # التحقق من أمان الملفات داخل ZIP
                for file_info in zip_ref.infolist():
                    # منع هجمات Directory Traversal
                    file_path = os.path.normpath(file_info.filename)
                    if file_path.startswith('..') or os.path.isabs(file_path):
                        return jsonify({'error': 'الملف ZIP يحتوي على مسارات غير آمنة'}), 400
                
                # استخراج الملفات
                zip_ref.extractall(extract_dir)
            
            # البحث عن مجلد المشروع الرئيسي (قد يكون الملفات مباشرة أو داخل مجلد)
            project_root = find_project_root(extract_dir)
            
            # حذف ملف ZIP الأصلي بعد الاستخراج
            os.remove(zip_path)
            
            # حفظ معلومات المشروع المؤقت
            project_id = os.path.basename(temp_dir)
            
            # إضافة إلى المشاريع المؤقتة
            temp_projects[project_id] = {
                'id': project_id,
                'path': project_root,
                'temp_dir': temp_dir,
                'created_at': datetime.now().isoformat()
            }
            
            # تنظيف المشاريع القديمة
            cleanup_old_temp_projects()
            
            return jsonify({
                'success': True,
                'project_id': project_id,
                'project_path': project_root,
                'temp_dir': temp_dir,
                'message': 'تم رفع واستخراج المشروع بنجاح'
            })
        
        return jsonify({'error': 'صيغة الملف غير مدعومة. الرجاء رفع ملف ZIP فقط'}), 400
        
    except zipfile.BadZipFile:
        return jsonify({'error': 'ملف ZIP تالف أو غير صالح'}), 400
    except Exception as e:
        logger.error(f"خطأ في رفع ملف ZIP: {e}")
        return jsonify({'error': f'خطأ في معالجة الملف: {str(e)}'}), 500

def find_project_root(extracted_path):
    """البحث عن مجلد المشروع الرئيسي داخل الملفات المستخرجة"""
    # قائمة بملفات مشروع شائعة
    project_files = ['index.html', 'package.json', 'composer.json', '.gitignore']
    
    # البحث عن هذه الملفات في المستويات المختلفة
    for root, dirs, files in os.walk(extracted_path):
        for project_file in project_files:
            if project_file in files:
                return root
        
        # إذا لم نجد، نتحقق من وجود ملفات ويب
        web_extensions = ['.html', '.htm', '.php', '.js', '.css']
        for file in files:
            if any(file.endswith(ext) for ext in web_extensions):
                return root
    
    # إذا لم نجد أي شيء، نعيد المجلد المستخرج
    return extracted_path

@app.route('/api/temp-projects', methods=['GET'])
def get_temp_projects():
    """الحصول على قائمة المشاريع المؤقتة"""
    projects = []
    for project_id, project_info in temp_projects.items():
        projects.append({
            'id': project_id,
            'path': project_info['path'],
            'created_at': project_info['created_at']
        })
    
    return jsonify({'projects': projects})

@app.route('/api/cleanup-temp/<project_id>', methods=['DELETE'])
def cleanup_temp_project(project_id):
    """حذف مشروع مؤقت"""
    try:
        if project_id in temp_projects:
            project_info = temp_projects[project_id]
            temp_dir = project_info.get('temp_dir')
            
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            del temp_projects[project_id]
            
            return jsonify({
                'success': True,
                'message': f'تم حذف المشروع المؤقت {project_id}'
            })
        
        return jsonify({'error': 'المشروع غير موجود'}), 404
        
    except Exception as e:
        logger.error(f"خطأ في حذف المشروع المؤقت: {e}")
        return jsonify({'error': str(e)}), 500

def cleanup_old_temp_projects():
    """تنظيف المشاريع المؤقتة القديمة (أقدم من 24 ساعة)"""
    try:
        now = datetime.now()
        to_delete = []
        
        for project_id, project_info in temp_projects.items():
            created_at = datetime.fromisoformat(project_info['created_at'])
            age_hours = (now - created_at).total_seconds() / 3600
            
            if age_hours > 24:  # حذف المشاريع الأقدم من 24 ساعة
                to_delete.append(project_id)
        
        for project_id in to_delete:
            cleanup_temp_project(project_id)
            
    except Exception as e:
        logger.error(f"خطأ في تنظيف المشاريع القديمة: {e}")

# ==================== تحديث نقطة نهاية المسح لدعم المشاريع المؤقتة ====================

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """نقطة نهاية المسح - محدثة لدعم المشاريع المؤقتة"""
    try:
        data = request.json
        project_path = data.get('project_path')
        project_id = data.get('project_id')  # الجديد: معرف المشروع المؤقت
        
        # إذا كان هناك project_id، استخدم المسار المؤقت
        if project_id and project_id in temp_projects:
            project_path = temp_projects[project_id]['path']
        
        if not project_path:
            return jsonify({'error': 'مسار المشروع مطلوب'}), 400
        
        # التحقق من صحة المسار
        is_valid, message = validate_path(project_path)
        if not is_valid:
            return jsonify({'error': f'مسار غير صالح: {message}'}), 400
        
        # إنشاء معرف للمسح
        scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # بدء المسح في خيط منفصل
        thread = threading.Thread(
            target=run_scan,
            args=(scan_id, project_path, project_id),  # تمرير project_id
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'success': True,
            'scan_id': scan_id,
            'message': 'بدأ المسح بنجاح'
        })
        
    except Exception as e:
        logger.error(f"خطأ في نقطة نهاية المسح: {e}")
        return jsonify({'error': str(e)}), 500

# تحديث دالة run_scan لقبول project_id
def run_scan(scan_id, project_path, project_id=None):
    """تشغيل المسح في خيط منفصل - محدثة"""
    try:
        # تسجيل بدء المسح
        scans[scan_id] = {
            'id': scan_id,
            'project_path': project_path,
            'project_id': project_id,  # حفظ معرف المشروع المؤقت
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'progress': 0
        }
        
        # تنفيذ المسح
        results = scan_project(project_path)
        
        # تحديث حالة المسح
        scans[scan_id].update({
            'status': 'completed',
            'end_time': datetime.now().isoformat(),
            'results': results,
            'progress': 100
        })
        
        logger.info(f"تم اكتمال المسح {scan_id}")
        
        # إذا كان مشروعاً مؤقتاً، يمكن تحديث معلوماته
        if project_id and project_id in temp_projects:
            temp_projects[project_id]['last_scan'] = scan_id
        
    except Exception as e:
        logger.error(f"خطأ في المسح {scan_id}: {e}")
        scans[scan_id].update({
            'status': 'failed',
            'end_time': datetime.now().isoformat(),
            'error': str(e),
            'progress': 100
        })
        
# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إنشاء تطبيق FastAPI
app = FastAPI(
    title="JS Custom Bundler - الإدارة الكاملة",
    description="أداة تحليل وإنشاء مكتبات JavaScript مخصصة من واجهة ويب متكاملة",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # في الإنتاج، حدد النطاقات المسموحة
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# إعداد المجلدات
BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"

# إنشاء المجلدات
for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR]:
    directory.mkdir(exist_ok=True)

# تحميل القوالب
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# تحميل الملفات الثابتة
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# تهيئة المديرين
file_manager = FileManager()

def create_default_templates():
    """إنشاء قوالب HTML افتراضية"""
    
    # الصفحة الرئيسية
    index_html = TEMPLATES_DIR / "index.html"
    
    html_content = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JS Custom Bundler - الإدارة الكاملة</title>
    <style>
        /* أنماط CSS الرئيسية */
        :root {
            --primary-color: #4361ee;
            --secondary-color: #3a0ca3;
            --success-color: #4cc9f0;
            --warning-color: #f72585;
            --danger-color: #7209b7;
            --light-color: #f8f9fa;
            --dark-color: #212529;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', 'Cairo', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 1000px;
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        h1 {
            font-size: 2.5rem;
            margin-bottom: 15px;
        }
        
        .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 20px;
        }
        
        .content {
            padding: 40px;
        }
        
        .card {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid #e9ecef;
        }
        
        h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.8rem;
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .status-icon {
            width: 50px;
            height: 50px;
            background: #4CAF50;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: white;
        }
        
        .status-info h3 {
            color: #333;
            margin-bottom: 5px;
        }
        
        .status-info p {
            color: #666;
            font-size: 0.9rem;
        }
        
        .actions {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-top: 30px;
        }
        
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        .btn-primary {
            background: var(--primary-color);
            color: white;
        }
        
        .btn-primary:hover {
            background: var(--secondary-color);
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-success {
            background: var(--success-color);
            color: white;
        }
        
        .btn-warning {
            background: var(--warning-color);
            color: white;
        }
        
        .btn-danger {
            background: var(--danger-color);
            color: white;
        }
        
        .upload-area {
            border: 3px dashed var(--primary-color);
            border-radius: 10px;
            padding: 60px 20px;
            text-align: center;
            margin: 20px 0;
            cursor: pointer;
            transition: all 0.3s;
            background: rgba(67, 97, 238, 0.05);
        }
        
        .upload-area:hover {
            background: rgba(67, 97, 238, 0.1);
            border-color: var(--secondary-color);
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .stat {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: 5px;
        }
        
        .stat-label {
            color: #666;
            font-size: 0.9rem;
        }
        
        footer {
            background: #343a40;
            color: white;
            text-align: center;
            padding: 20px;
            margin-top: 40px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .hidden {
            display: none;
        }
        
        .notification {
            position: fixed;
            bottom: 30px;
            left: 30px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
            padding: 20px;
            max-width: 400px;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 3000;
        }
        
        .notification.show {
            transform: translateY(0);
            opacity: 1;
        }
        
        .notification.success {
            background: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
        }
        
        .notification.error {
            background: #f8d7da;
            color: #721c24;
            border-left: 4px solid #dc3545;
        }
        
        .notification.info {
            background: #d1ecf1;
            color: #0c5460;
            border-left: 4px solid #17a2b8;
        }
        
        .notification.warning {
            background: #fff3cd;
            color: #856404;
            border-left: 4px solid #ffc107;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: bold;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1rem;
        }
        
        .analysis-results {
            max-height: 500px;
            overflow-y: auto;
            margin: 20px 0;
            padding: 20px;
            background: white;
            border-radius: 10px;
        }
        
        .library-item {
            background: #f8f9fa;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid var(--primary-color);
        }
        
        .library-name {
            color: var(--primary-color);
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .library-stats {
            display: flex;
            gap: 15px;
            margin-top: 10px;
            font-size: 0.9rem;
        }
        
        .library-stat {
            background: white;
            padding: 5px 10px;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        
        .functions-list {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 10px;
        }
        
        .function-tag {
            background: #e3f2fd;
            color: #1976d2;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
        }
        
        .progress-container {
            margin: 20px 0;
        }
        
        .progress-bar {
            height: 10px;
            background: #e9ecef;
            border-radius: 5px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: var(--primary-color);
            width: 0%;
            transition: width 0.3s;
        }
        
        .quick-actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .quick-btn {
            padding: 10px 20px;
            background: var(--light-color);
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .quick-btn:hover {
            background: var(--primary-color);
            color: white;
        }
        
        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 10px;
            }
            
            .content {
                padding: 20px;
            }
            
            .stats {
                grid-template-columns: 1fr;
            }
            
            .actions {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
            }
            
            .quick-actions {
                flex-direction: column;
            }
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1><i class="fas fa-code"></i> JS Custom Bundler</h1>
            <p class="subtitle">الإدارة الكاملة من واجهة الويب</p>
        </header>
        
        <div class="content">
            <div class="status">
                <div class="status-icon"><i class="fas fa-check"></i></div>
                <div class="status-info">
                    <h3>النظام يعمل بنجاح</h3>
                    <p>الخادم يعمل وجاهز للاستخدام</p>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="projectsCount">0</div>
                    <div class="stat-label">المشاريع</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="bundlesCount">0</div>
                    <div class="stat-label">الحزم</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="reportsCount">0</div>
                    <div class="stat-label">التقارير</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="tasksCount">0</div>
                    <div class="stat-label">المهام</div>
                </div>
            </div>
            
            <div class="card">
                <h2><i class="fas fa-upload"></i> رفع مشروع جديد</h2>
                <div class="upload-area" id="uploadArea">
                    <i class="fas fa-cloud-upload-alt fa-3x" style="color: var(--primary-color); margin-bottom: 15px;"></i>
                    <p>اسحب وأفلت ملف ZIP للمشروع هنا</p>
                    <p style="color: #666; margin-top: 10px; font-size: 0.9rem;">أو انقر لاختيار الملف</p>
                </div>
                <input type="file" id="fileInput" accept=".zip" style="display: none;">
                
                <div class="form-group">
                    <label for="projectName"><i class="fas fa-folder"></i> اسم المشروع:</label>
                    <input type="text" id="projectName" placeholder="أدخل اسم المشروع...">
                </div>
                
                <div class="actions">
                    <button class="btn btn-primary" onclick="uploadProject()">
                        <i class="fas fa-upload"></i> رفع وتحليل
                    </button>
                    <button class="btn btn-secondary" onclick="debugCurrentProject()">
                        <i class="fas fa-bug"></i> تشخيص
                    </button>
                </div>
            </div>
            
            <div class="card">
                <h2><i class="fas fa-bolt"></i> إجراءات سريعة</h2>
                <div class="quick-actions">
                    <button class="quick-btn" onclick="listAllProjects()">
                        <i class="fas fa-list"></i> عرض المشاريع
                    </button>
                    <button class="quick-btn" onclick="checkSystemHealth()">
                        <i class="fas fa-heartbeat"></i> فحص النظام
                    </button>
                    <button class="quick-btn" onclick="cleanupSystem()">
                        <i class="fas fa-broom"></i> تنظيف النظام
                    </button>
                    <button class="quick-btn" onclick="showRecentTasks()">
                        <i class="fas fa-tasks"></i> المهام الحديثة
                    </button>
                </div>
            </div>
            
            <div id="loading" class="loading hidden">
                <div class="spinner"></div>
                <p id="loadingText">جاري المعالجة...</p>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="loadingProgress"></div>
                    </div>
                </div>
            </div>
            
            <div id="results" class="card hidden">
                <h2><i class="fas fa-chart-bar"></i> نتائج التحليل</h2>
                <div id="resultsContent"></div>
            </div>
            
            <div id="debugInfo" class="card hidden">
                <h2><i class="fas fa-bug"></i> معلومات التشخيص</h2>
                <div id="debugContent"></div>
            </div>
        </div>
        
        <footer>
            <p>JS Custom Bundler &copy; 2024 | الإدارة الكاملة من الويب</p>
            <p style="font-size: 0.9rem; opacity: 0.8; margin-top: 5px;">الإصدار 2.0.0</p>
        </footer>
    </div>
    
    <div id="notification" class="notification">
        <div id="notificationMessage"></div>
    </div>
    
    <script>
        // حالات التطبيق
        let currentProject = null;
        let currentAnalysis = null;
        
        // تهيئة الصفحة
        document.addEventListener('DOMContentLoaded', function() {
            console.log('✅ الصفحة محملة بنجاح');
            loadStats();
            setupUpload();
            setupNotification();
            
            // تحميل الإحصائيات كل 30 ثانية
            setInterval(loadStats, 30000);
            
            // تحميل المهام النشطة كل 10 ثواني
            setInterval(loadActiveTasks, 10000);
        });
        
        // إعداد الإشعارات
        function setupNotification() {
            const notification = document.getElementById('notification');
            notification.addEventListener('click', function() {
                this.classList.remove('show');
            });
        }
        
        // عرض إشعار
        function showNotification(message, type = 'info', duration = 5000) {
            const notification = document.getElementById('notification');
            const messageEl = document.getElementById('notificationMessage');
            
            if (!notification || !messageEl) return;
            
            // تعيين النص واللون
            messageEl.textContent = message;
            notification.className = `notification show ${type}`;
            
            // إخفاء تلقائي بعد المدة المحددة
            setTimeout(() => {
                notification.classList.remove('show');
            }, duration);
        }
        
        // إعداد التحميل
        function setupUpload() {
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            
            uploadArea.addEventListener('click', () => fileInput.click());
            
            // سحب وإفلات
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.style.background = 'rgba(67, 97, 238, 0.1)';
                uploadArea.style.borderColor = '#3a0ca3';
            });
            
            uploadArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                uploadArea.style.background = '';
                uploadArea.style.borderColor = '';
            });
            
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.style.background = '';
                uploadArea.style.borderColor = '';
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFileUpload(files[0]);
                }
            });
            
            fileInput.addEventListener('change', (e) => {
                if (fileInput.files.length > 0) {
                    handleFileUpload(fileInput.files[0]);
                }
            });
        }
        
        // تحميل الإحصائيات
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('projectsCount').textContent = data.projects_count;
                    document.getElementById('bundlesCount').textContent = data.bundles_count;
                    document.getElementById('reportsCount').textContent = data.analysis_count;
                    
                    // تحميل عدد المهام النشطة
                    const tasks = await fetch('/api/tasks').then(r => r.json());
                    if (tasks) {
                        const activeTasks = tasks.filter(t => 
                            t.status === 'running' || t.status === 'pending'
                        ).length;
                        document.getElementById('tasksCount').textContent = activeTasks;
                    }
                }
            } catch (error) {
                console.error('❌ خطأ في تحميل الإحصائيات:', error);
            }
        }
        
        // تحميل المهام النشطة
        async function loadActiveTasks() {
            try {
                const response = await fetch('/api/tasks');
                const tasks = await response.json();
                
                if (tasks && tasks.length > 0) {
                    const activeTasks = tasks.filter(t => 
                        t.status === 'running' || t.status === 'pending'
                    );
                    
                    if (activeTasks.length > 0) {
                        // تحديث العداد
                        document.getElementById('tasksCount').textContent = activeTasks.length;
                        
                        // إذا كان هناك مهمة نشطة للتحميل الحالي، تحديث التقدم
                        if (currentProject) {
                            const projectTask = activeTasks.find(t => 
                                t.task_type === 'analyze_project' && 
                                t.result && 
                                t.result.analysis_id && 
                                t.result.analysis_id.includes(currentProject)
                            );
                            
                            if (projectTask && projectTask.status === 'running') {
                                updateLoading(projectTask.message, projectTask.progress);
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('❌ خطأ في تحميل المهام:', error);
            }
        }
        
        // معالجة تحميل الملف
        async function handleFileUpload(file) {
            if (!file.name.endsWith('.zip')) {
                showNotification('⚠️ يجب أن يكون الملف بصيغة ZIP', 'warning');
                return;
            }
            
            const projectName = document.getElementById('projectName').value || 
                               file.name.replace('.zip', '');
            
            if (!projectName.trim()) {
                showNotification('⚠️ يرجى إدخال اسم المشروع', 'warning');
                return;
            }
            
            showLoading('جاري رفع المشروع...');
            
            const formData = new FormData();
            formData.append('project_name', projectName);
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/projects', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ تم رفع المشروع بنجاح', 'success');
                    currentProject = projectName;
                    loadStats();
                    
                    // بدء التحليل تلقائياً
                    setTimeout(() => {
                        analyzeProject(projectName);
                    }, 1000);
                } else {
                    throw new Error(result.detail || 'حدث خطأ أثناء الرفع');
                }
            } catch (error) {
                showNotification(`❌ ${error.message}`, 'error');
            } finally {
                hideLoading();
            }
        }
        
        // رفع المشروع
        function uploadProject() {
            const fileInput = document.getElementById('fileInput');
            if (fileInput.files.length > 0) {
                handleFileUpload(fileInput.files[0]);
            } else {
                showNotification('⚠️ يرجى اختيار ملف أولاً', 'warning');
            }
        }
        
        // تحليل المشروع
        async function analyzeProject(projectId) {
            showLoading('جاري تحليل المشروع...');
            
            try {
                const response = await fetch(`/api/projects/${projectId}/analyze`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ تم بدء تحليل المشروع', 'success');
                    
                    // مراقبة المهمة
                    monitorTask(result.task_id, projectId, 'analysis');
                } else {
                    throw new Error(result.detail || 'حدث خطأ أثناء التحليل');
                }
            } catch (error) {
                showNotification(`❌ ${error.message}`, 'error');
                hideLoading();
            }
        }
        
        // مراقبة المهمة
        async function monitorTask(taskId, projectId, taskType) {
            const checkInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/tasks/${taskId}`);
                    const task = await response.json();
                    
                    if (response.ok) {
                        // تحديث التقدم
                        updateLoading(task.message, task.progress);
                        
                        // إذا اكتملت
                        if (task.status === 'completed') {
                            clearInterval(checkInterval);
                            showNotification('✅ اكتمل التحليل بنجاح', 'success');
                            hideLoading();
                            
                            if (taskType === 'analysis') {
                                currentAnalysis = task.result;
                                showAnalysisDetails(projectId);
                            } else if (taskType === 'bundles') {
                                showNotification('✅ تم إنشاء الحزم بنجاح', 'success');
                                showBundleResults(task.result);
                            }
                            
                            loadStats();
                        } else if (task.status === 'failed') {
                            clearInterval(checkInterval);
                            showNotification(`❌ فشل التحليل: ${task.error}`, 'error');
                            hideLoading();
                        }
                    }
                } catch (error) {
                    console.error('❌ خطأ في مراقبة المهمة:', error);
                }
            }, 1000);
        }
        
        // عرض تفاصيل التحليل
        async function showAnalysisDetails(projectId) {
            showLoading('جاري تحميل نتائج التحليل...');
            
            try {
                const response = await fetch(`/api/projects/${projectId}/analysis`);
                
                if (response.status === 404) {
                    throw new Error('لم يتم تحليل هذا المشروع بعد');
                }
                
                if (!response.ok) {
                    throw new Error(`خطأ ${response.status}: ${response.statusText}`);
                }
                
                const analysis = await response.json();
                
                if (!analysis || Object.keys(analysis).length === 0) {
                    throw new Error('ملف التحليل فارغ أو تالف');
                }
                
                displayDetailedAnalysis(analysis, projectId);
            } catch (error) {
                showNotification(`❌ ${error.message}`, 'error');
                showDebugInfo(error.message, projectId);
            } finally {
                hideLoading();
            }
        }
        
        // عرض التحليل التفصيلي
        function displayDetailedAnalysis(analysis, projectId) {
            const resultsDiv = document.getElementById('results');
            const contentDiv = document.getElementById('resultsContent');
            
            let html = `
                <div style="text-align: right;">
                    <h3 style="color: #333; border-bottom: 2px solid var(--primary-color); padding-bottom: 10px; margin-bottom: 20px;">
                        📊 نتائج التحليل - ${projectId}
                    </h3>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                            <div style="font-size: 2rem; color: var(--primary-color); font-weight: bold;">${analysis.total_files || 0}</div>
                            <div style="color: #666;">الملفات الممسوحة</div>
                        </div>
                        
                        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                            <div style="font-size: 2rem; color: var(--primary-color); font-weight: bold;">${analysis.libraries ? Object.keys(analysis.libraries).length : 0}</div>
                            <div style="color: #666;">المكتبات المكتشفة</div>
                        </div>
                        
                        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                            <div style="font-size: 2rem; color: var(--primary-color); font-weight: bold;">${analysis.total_functions || 0}</div>
                            <div style="color: #666;">الدوال المستخدمة</div>
                        </div>
                    </div>
            `;
            
            // عرض المكتبات المكتشفة
            if (analysis.libraries && Object.keys(analysis.libraries).length > 0) {
                html += `
                    <h4 style="color: #333; margin: 20px 0 10px 0;"><i class="fas fa-box"></i> المكتبات المكتشفة:</h4>
                    <div class="analysis-results">
                `;
                
                for (const [lib, data] of Object.entries(analysis.libraries)) {
                    const percentage = ((data.count / analysis.total_files) * 100).toFixed(1);
                    
                    html += `
                        <div class="library-item">
                            <div class="library-name">${lib}</div>
                            <div>تم استخدامها في ${data.count} ملف (${percentage}%)</div>
                            
                            ${data.functions_used && data.functions_used.length > 0 ? `
                            <div style="margin-top: 10px;">
                                <strong style="color: #666; font-size: 0.9rem;">الدوال المستخدمة:</strong>
                                <div class="functions-list">
                                    ${data.functions_used.slice(0, 10).map(func => `
                                        <span class="function-tag">${func}</span>
                                    `).join('')}
                                    ${data.functions_used.length > 10 ? `
                                        <span class="function-tag">+${data.functions_used.length - 10} أكثر</span>
                                    ` : ''}
                                </div>
                            </div>
                            ` : ''}
                            
                            <div class="library-stats">
                                <span class="library-stat">📁 ${data.count} ملف</span>
                                <span class="library-stat">🔧 ${data.functions_used ? data.functions_used.length : 0} دالة</span>
                            </div>
                        </div>
                    `;
                }
                
                html += `</div>`;
                
                // أزرار الإجراءات
                html += `
                    <div style="display: flex; gap: 15px; margin-top: 30px;">
                        <button class="btn btn-success" onclick="createBundlesForProject('${projectId}')" 
                                style="flex: 1; padding: 15px; font-size: 1.1rem;">
                            <i class="fas fa-box"></i> إنشاء حزم مخصصة
                        </button>
                        
                        <button class="btn btn-primary" onclick="downloadReport('${projectId}')" 
                                style="flex: 1; padding: 15px; font-size: 1.1rem;">
                            <i class="fas fa-file-pdf"></i> إنشاء تقرير
                        </button>
                    </div>
                    
                    <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                        <strong>📁 مسار المشروع:</strong> 
                        <code style="background: white; padding: 5px 10px; border-radius: 4px; margin-right: 10px;">
                            projects/${projectId}/
                        </code>
                    </div>
                `;
            } else {
                html += `
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-search fa-3x" style="margin-bottom: 20px;"></i>
                        <h3>لم يتم العثور على مكتبات</h3>
                        <p>المشروع لا يستخدم مكتبات JavaScript خارجية</p>
                    </div>
                `;
            }
            
            contentDiv.innerHTML = html;
            resultsDiv.classList.remove('hidden');
            document.getElementById('debugInfo').classList.add('hidden');
        }
        
        // إنشاء حزم للمشروع
        async function createBundlesForProject(projectId) {
            showLoading('جاري إنشاء الحزم المخصصة...');
            
            try {
                const response = await fetch(`/api/projects/${projectId}/bundles`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ تم بدء إنشاء الحزم', 'success');
                    monitorTask(result.task_id, projectId, 'bundles');
                } else {
                    throw new Error(result.detail || 'حدث خطأ أثناء إنشاء الحزم');
                }
            } catch (error) {
                showNotification(`❌ ${error.message}`, 'error');
                hideLoading();
            }
        }
        
        // عرض نتائج الحزم
        function showBundleResults(result) {
            if (!result || !result.bundles) return;
            
            let message = `تم إنشاء ${Object.keys(result.bundles).length} حزمة مخصصة:\n\n`;
            
            Object.entries(result.bundles).forEach(([lib, path]) => {
                message += `• ${lib}: ${path}\n`;
            });
            
            message += `\nيمكنك تنزيل جميع الحزم من: ${result.zip_path}`;
            
            Swal.fire({
                title: 'الحزم المنشأة',
                text: message,
                icon: 'success',
                confirmButtonText: 'تم',
                width: '600px'
            });
        }
        
        // تنزيل التقرير
        async function downloadReport(projectId) {
            try {
                const response = await fetch(`/api/projects/${projectId}/reports`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ تم بدء إنشاء التقرير', 'success');
                    
                    // مراقبة المهمة
                    const checkInterval = setInterval(async () => {
                        try {
                            const taskResponse = await fetch(`/api/tasks/${result.task_id}`);
                            const task = await taskResponse.json();
                            
                            if (taskResponse.ok && task.status === 'completed') {
                                clearInterval(checkInterval);
                                
                                if (task.result && task.result.report_url) {
                                    window.open(task.result.report_url, '_blank');
                                    showNotification('✅ تم إنشاء التقرير', 'success');
                                }
                            } else if (task.status === 'failed') {
                                clearInterval(checkInterval);
                                showNotification(`❌ فشل إنشاء التقرير: ${task.error}`, 'error');
                            }
                        } catch (error) {
                            console.error('❌ خطأ في مراقبة مهمة التقرير:', error);
                        }
                    }, 1000);
                } else {
                    throw new Error(result.detail || 'حدث خطأ أثناء إنشاء التقرير');
                }
            } catch (error) {
                showNotification(`❌ ${error.message}`, 'error');
            }
        }
        
        // تشخيص المشروع الحالي
        async function debugCurrentProject() {
            const projectName = document.getElementById('projectName').value;
            if (!projectName.trim()) {
                showNotification('⚠️ أدخل اسم مشروع أولاً', 'warning');
                return;
            }
            
            showLoading('جاري التشخيص...');
            
            try {
                const response = await fetch(`/api/projects/${projectName}/debug`);
                const debugInfo = await response.json();
                
                if (response.ok) {
                    displayDebugInfo(debugInfo);
                } else {
                    throw new Error('فشل في التشخيص');
                }
            } catch (error) {
                showNotification(`❌ ${error.message}`, 'error');
            } finally {
                hideLoading();
            }
        }
        
        // عرض معلومات التشخيص
        function displayDebugInfo(debugInfo) {
            const debugDiv = document.getElementById('debugInfo');
            const contentDiv = document.getElementById('debugContent');
            
            let html = `
                <h3 style="color: #333; border-bottom: 2px solid #ff9800; padding-bottom: 10px; margin-bottom: 20px;">
                    🐛 معلومات التشخيص - ${debugInfo.project_id}
                </h3>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <strong>المسار:</strong> ${debugInfo.project_path}<br>
                    <strong>المشروع موجود:</strong> ${debugInfo.project_exists ? '✅ نعم' : '❌ لا'}<br>
                    <strong>ملف التحليل موجود:</strong> ${debugInfo.analysis_file_exists ? '✅ نعم' : '❌ لا'}<br>
                    ${debugInfo.analysis_file_error ? `<strong>خطأ في ملف التحليل:</strong> ${debugInfo.analysis_file_error}<br>` : ''}
                </div>
            `;
            
            if (debugInfo.project_exists) {
                html += `
                    <h4 style="color: #333; margin: 20px 0 10px 0;">📁 الملفات في المشروع (${debugInfo.files_in_project.length}):</h4>
                    <div style="max-height: 300px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 5px;">
                `;
                
                if (debugInfo.files_in_project.length > 0) {
                    debugInfo.files_in_project.forEach(file => {
                        html += `
                            <div style="padding: 5px 10px; border-bottom: 1px solid #eee; font-family: monospace; font-size: 0.9rem;">
                                ${file.is_file ? '📄' : '📁'} ${file.path}
                                ${file.is_file ? `(${formatFileSize(file.size)})` : ''}
                            </div>
                        `;
                    });
                } else {
                    html += `<div style="color: #666; text-align: center; padding: 20px;">لا توجد ملفات</div>`;
                }
                
                html += `</div>`;
                
                // إجراءات
                html += `
                    <div style="margin-top: 20px;">
                        <button class="btn btn-primary" onclick="forceAnalyzeProject('${debugInfo.project_id}')" 
                                style="margin-right: 10px;">
                            <i class="fas fa-redo"></i> إعادة تحليل المشروع
                        </button>
                        ${debugInfo.analysis_file_exists ? `
                        <button class="btn btn-warning" onclick="showAnalysis('${debugInfo.project_id}')">
                            <i class="fas fa-chart-bar"></i> عرض نتائج التحليل
                        </button>
                        ` : ''}
                    </div>
                `;
            } else {
                html += `
                    <div style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin-top: 20px;">
                        ❌ المشروع غير موجود! تأكد من أن اسم المشروع صحيح.
                    </div>
                `;
            }
            
            contentDiv.innerHTML = html;
            debugDiv.classList.remove('hidden');
            document.getElementById('results').classList.add('hidden');
        }
        
        // إعادة تحليل المشروع
        async function forceAnalyzeProject(projectId) {
            showLoading('جاري إعادة تحليل المشروع...');
            
            try {
                const response = await fetch(`/api/projects/${projectId}/analyze`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ تم بدء إعادة التحليل', 'success');
                    monitorTask(result.task_id, projectId, 'analysis');
                } else {
                    throw new Error(result.detail || 'حدث خطأ أثناء التحليل');
                }
            } catch (error) {
                showNotification(`❌ ${error.message}`, 'error');
                hideLoading();
            }
        }
        
        // عرض جميع المشاريع
        async function listAllProjects() {
            showLoading('جاري تحميل المشاريع...');
            
            try {
                const response = await fetch('/api/projects');
                const projects = await response.json();
                
                if (response.ok) {
                    displayProjectsList(projects);
                } else {
                    throw new Error('فشل في تحميل المشاريع');
                }
            } catch (error) {
                showNotification(`❌ ${error.message}`, 'error');
            } finally {
                hideLoading();
            }
        }
        
        // عرض قائمة المشاريع
        function displayProjectsList(projects) {
            const resultsDiv = document.getElementById('results');
            const contentDiv = document.getElementById('resultsContent');
            
            let html = `
                <h3 style="color: #333; border-bottom: 2px solid var(--primary-color); padding-bottom: 10px; margin-bottom: 20px;">
                    📁 جميع المشاريع (${projects.length})
                </h3>
            `;
            
            if (projects.length > 0) {
                html += `<div style="max-height: 400px; overflow-y: auto;">`;
                
                projects.forEach(project => {
                    const hasAnalysis = project.has_analysis || false;
                    
                    html += `
                        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; 
                                    border: 1px solid ${hasAnalysis ? '#c3e6cb' : '#f5c6cb'};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="color: var(--primary-color); font-size: 1.1rem;">${project.name}</strong>
                                    <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">
                                        📏 ${formatFileSize(project.size)} • 📄 ${project.file_count} ملف
                                    </div>
                                    <div style="color: #888; font-size: 0.8rem; margin-top: 3px;">
                                        🕐 ${new Date(project.created_at).toLocaleString('ar')}
                                    </div>
                                </div>
                                <div>
                                    <span style="background: ${hasAnalysis ? '#d4edda' : '#f8d7da'}; 
                                              color: ${hasAnalysis ? '#155724' : '#721c24'}; 
                                              padding: 5px 10px; border-radius: 20px; font-size: 0.8rem;">
                                        ${hasAnalysis ? '✅ تم التحليل' : '❌ لم يحلل'}
                                    </span>
                                </div>
                            </div>
                            
                            <div style="display: flex; gap: 10px; margin-top: 15px;">
                                <button class="btn btn-primary" onclick="showAnalysis('${project.id}')" 
                                        style="padding: 8px 15px; font-size: 0.8rem;">
                                    <i class="fas fa-chart-bar"></i> تحليل
                                </button>
                                <button class="btn btn-secondary" onclick="debugProject('${project.id}')" 
                                        style="padding: 8px 15px; font-size: 0.8rem;">
                                    <i class="fas fa-bug"></i> تشخيص
                                </button>
                                <button class="btn btn-success" onclick="createBundlesForProject('${project.id}')" 
                                        style="padding: 8px 15px; font-size: 0.8rem;" 
                                        ${!hasAnalysis ? 'disabled' : ''}>
                                    <i class="fas fa-box"></i> حزم
                                </button>
                            </div>
                        </div>
                    `;
                });
                
                html += `</div>`;
            } else {
                html += `
                    <div style="text-align: center; padding: 40px; color: #666;">
                        📭 لا توجد مشاريع بعد
                        <p style="margin-top: 10px;">ابدأ برفع مشروع جديد 👆</p>
                    </div>
                `;
            }
            
            contentDiv.innerHTML = html;
            resultsDiv.classList.remove('hidden');
            document.getElementById('debugInfo').classList.add('hidden');
        }
        
        // فحص صحة النظام
        async function checkSystemHealth() {
            try {
                const response = await fetch('/api/health');
                const health = await response.json();
                
                if (response.ok) {
                    Swal.fire({
                        title: 'صحة النظام',
                        html: `
                            <div style="text-align: right;">
                                <p><strong>الحالة:</strong> ${health.status}</p>
                                <p><strong>الإصدار:</strong> ${health.version}</p>
                                <p><strong>الرسالة:</strong> ${health.message}</p>
                                <p><strong>الوقت:</strong> ${new Date(health.timestamp * 1000).toLocaleString('ar')}</p>
                            </div>
                        `,
                        icon: 'success',
                        confirmButtonText: 'تم'
                    });
                }
            } catch (error) {
                showNotification('❌ فشل في فحص النظام', 'error');
            }
        }
        
        // تنظيف النظام
        async function cleanupSystem() {
            try {
                const response = await fetch('/api/cleanup', {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ تم تنظيف النظام بنجاح', 'success');
                    loadStats();
                }
            } catch (error) {
                showNotification('❌ فشل في تنظيف النظام', 'error');
            }
        }
        
        // عرض المهام الحديثة
        async function showRecentTasks() {
            try {
                const response = await fetch('/api/tasks');
                const tasks = await response.json();
                
                if (tasks && tasks.length > 0) {
                    let message = `المهام الحديثة (${tasks.length}):\n\n`;
                    
                    tasks.slice(0, 5).forEach(task => {
                        const statusIcon = {
                            'pending': '⏳',
                            'running': '🔄',
                            'completed': '✅',
                            'failed': '❌',
                            'cancelled': '⛔'
                        }[task.status] || '❓';
                        
                        message += `${statusIcon} ${task.task_type}: ${task.status} (${task.progress}%)\n`;
                    });
                    
                    Swal.fire({
                        title: 'المهام الحديثة',
                        text: message,
                        icon: 'info',
                        confirmButtonText: 'تم'
                    });
                } else {
                    showNotification('📭 لا توجد مهام حالية', 'info');
                }
            } catch (error) {
                showNotification('❌ فشل في تحميل المهام', 'error');
            }
        }
        
        // وظائف مساعدة
        function showLoading(message) {
            const loading = document.getElementById('loading');
            const loadingText = document.getElementById('loadingText');
            
            if (loading && loadingText) {
                loadingText.textContent = message;
                loading.classList.remove('hidden');
            }
        }
        
        function hideLoading() {
            const loading = document.getElementById('loading');
            if (loading) {
                loading.classList.add('hidden');
            }
        }
        
        function updateLoading(message, progress) {
            const loadingText = document.getElementById('loadingText');
            const progressFill = document.getElementById('loadingProgress');
            
            if (loadingText && message) {
                loadingText.textContent = `${message} (${progress || 0}%)`;
            }
            
            if (progressFill) {
                progressFill.style.width = \`\${progress || 0}%\`;
            }
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 بايت';
            const k = 1024;
            const sizes = ['بايت', 'كيلوبايت', 'ميجابايت', 'جيجابايت'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        // وظائف إضافية
        function debugProject(projectId) {
            document.getElementById('projectName').value = projectId;
            debugCurrentProject();
        }
        
        function showAnalysis(projectId) {
            currentProject = projectId;
            showAnalysisDetails(projectId);
        }
    </script>
</body>
</html>"""
    
    try:
        with open(index_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"✅ تم إنشاء ملف HTML في: {index_html}")
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء ملف HTML: {e}")

def create_static_files():
    """إنشاء ملفات ثابتة افتراضية"""
    
    # مجلدات CSS و JS
    css_dir = STATIC_DIR / "css"
    js_dir = STATIC_DIR / "js"
    
    for directory in [css_dir, js_dir]:
        directory.mkdir(exist_ok=True)
    
    # ملف CSS مبسط
    css_file = css_dir / "style.css"
    if not css_file.exists():
        css_content = """/* أنماط إضافية */
.additional-styles {
    font-family: 'Arial', sans-serif;
    color: #333;
}

.alert {
    padding: 15px;
    border-radius: 5px;
    margin: 10px 0;
}

.alert-success {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.alert-error {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.alert-info {
    background-color: #d1ecf1;
    color: #0c5460;
    border: 1px solid #bee5eb;
}

.code-block {
    background: #272822;
    color: #f8f8f2;
    padding: 15px;
    border-radius: 5px;
    font-family: monospace;
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
}

.badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: bold;
    margin: 0 5px;
}

.badge-success {
    background: #c6f6d5;
    color: #22543d;
}

.badge-warning {
    background: #feebc8;
    color: #744210;
}

.badge-info {
    background: #bee3f8;
    color: #2a4365;
}

.badge-danger {
    background: #fed7d7;
    color: #742a2a;
}"""
        
        try:
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write(css_content)
            logger.info(f"✅ تم إنشاء ملف CSS")
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء ملف CSS: {e}")
    
    # ملف JS مبسط
    js_file = js_dir / "app.js"
    if not js_file.exists():
        js_content = """// JavaScript إضافي
console.log('JS Custom Bundler - الإصدار 2.0.0');

// وظائف إضافية
function showAdvancedUI() {
    console.log('جاري تحميل الواجهة المتقدمة...');
    // يمكن إضافة المزيد من الوظائف هنا
}

// تهيئة إضافية عند تحميل الصفحة
window.addEventListener('load', function() {
    console.log('✅ تم تحميل جميع الموارد');
    
    // التحقق من اتصال الخادم
    fetch('/api/health')
        .then(response => {
            if (response.ok) {
                console.log('✅ الخادم متصل ويعمل');
            } else {
                console.warn('⚠️ الخادم يرد برسالة خطأ');
            }
        })
        .catch(error => {
            console.error('❌ فشل الاتصال بالخادم:', error);
        });
});"""
        
        try:
            with open(js_file, 'w', encoding='utf-8') as f:
                f.write(js_content)
            logger.info(f"✅ تم إنشاء ملف JavaScript")
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء ملف JavaScript: {e}")

def initialize_web_app():
    """تهيئة تطبيق الويب"""
    logger.info("🔧 جاري تهيئة تطبيق الويب...")
    
    # طباعة معلومات المسارات
    logger.info(f"📁 المجلد الرئيسي: {BASE_DIR}")
    logger.info(f"📁 مجلد القوالب: {TEMPLATES_DIR}")
    logger.info(f"📁 مجلد الملفات الثابتة: {STATIC_DIR}")
    logger.info(f"📁 مجلد الرفع: {UPLOADS_DIR}")
    
    # إنشاء الملفات الأساسية
    create_default_templates()
    create_static_files()
    
    # بدء عامل الخلفية
    try:
        start_worker()
        logger.info("✅ عامل الخلفية يعمل")
    except Exception as e:
        logger.error(f"❌ خطأ في بدء عامل الخلفية: {e}")
    
    logger.info("✅ تم تهيئة تطبيق الويب بنجاح")

# نقاط النهاية API
@app.get("/")
async def home(request: Request):
    """الصفحة الرئيسية"""
    logger.info("📄 طلب الصفحة الرئيسية")
    
    # التحقق من وجود ملف HTML
    index_html = TEMPLATES_DIR / "index.html"
    if not index_html.exists():
        logger.error(f"❌ ملف HTML غير موجود: {index_html}")
        # إرجاع صفحة بسيطة في حالة الطوارئ
        return HTMLResponse("""
            <!DOCTYPE html>
            <html dir="rtl">
            <head><title>JS Custom Bundler</title></head>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h1>🚀 JS Custom Bundler</h1>
                <p>جاري تحضير التطبيق...</p>
                <p>إذا استمرت هذه المشكلة، يرجى التحقق من سجلات الخادم.</p>
            </body>
            </html>
        """)
    
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"❌ خطأ في عرض الصفحة: {e}")
        # قراءة الملف مباشرة كحل بديل
        with open(index_html, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)

@app.get("/api/stats")
async def get_stats():
    """الحصول على إحصائيات النظام"""
    try:
        # حساب الإحصائيات
        projects_count = len(list(file_manager.projects_dir.iterdir()))
        
        # حساب التقارير والحزم
        analysis_count = 0
        bundles_count = 0
        
        # التحقق من وجود مجلد التقارير
        if file_manager.reports_dir.exists():
            analysis_count = len(list(file_manager.reports_dir.glob("*.html")))
        
        # التحقق من وجود مجلد الحزم
        if file_manager.bundles_dir.exists():
            bundles_count = len(list(file_manager.bundles_dir.glob("*.zip")))
        
        # حساب المساحة المستخدمة
        total_size = 0
        for dir_path in [file_manager.projects_dir, file_manager.bundles_dir, 
                        file_manager.reports_dir, file_manager.uploads_dir]:
            if dir_path.exists():
                for file in dir_path.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size
        
        storage_used = f"{total_size / (1024*1024):.1f} MB"
        storage_percentage = min((total_size / (500 * 1024 * 1024)) * 100, 100)
        
        # الحصول على المهام النشطة
        active_tasks = 0
        try:
            tasks = get_all_tasks()
            active_tasks = len([t for t in tasks if t.get('status') in ['pending', 'running']])
        except:
            pass
        
        return {
            "projects_count": projects_count,
            "analysis_count": analysis_count,
            "bundles_count": bundles_count,
            "active_tasks": active_tasks,
            "storage_used": storage_used,
            "storage_percentage": storage_percentage,
            "system_status": "running",
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects")
async def get_projects():
    """الحصول على قائمة المشاريع"""
    try:
        projects = []
        
        for project_dir in file_manager.projects_dir.iterdir():
            if project_dir.is_dir():
                # حساب حجم المشروع
                size = file_manager.get_project_size(project_dir.name)
                
                # حساب عدد الملفات
                files = list(project_dir.rglob("*.*"))
                file_count = len([f for f in files if f.is_file()])
                
                # التحقق من وجود تحليل
                analysis_file = project_dir / "analysis_result.json"
                has_analysis = analysis_file.exists()
                
                projects.append({
                    "id": project_dir.name,
                    "name": project_dir.name,
                    "size": size,
                    "file_count": file_count,
                    "has_analysis": has_analysis,
                    "status": "active",
                    "created_at": project_dir.stat().st_ctime,
                    "updated_at": project_dir.stat().st_mtime
                })
        
        # ترتيب حسب تاريخ الإنشاء (الأحدث أولاً)
        projects.sort(key=lambda x: x["created_at"], reverse=True)
        
        return projects
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects")
async def create_project(
    project_name: str = Form(...),
    file: Optional[UploadFile] = None
):
    """إنشاء مشروع جديد"""
    try:
        logger.info(f"📤 رفع مشروع جديد: {project_name}")
        
        # إنشاء هيكل المشروع
        project_path = file_manager.create_project_structure(project_name)
        
        # إذا كان هناك ملف ZIP، استخراجه
        if file and file.filename and file.filename.endswith('.zip'):
            logger.info(f"📦 معالجة ملف ZIP: {file.filename}")
            
            # حفظ الملف المؤقت
            temp_path = file_manager.uploads_dir / file.filename
            with open(temp_path, 'wb') as f:
                content = await file.read()
                f.write(content)
            
            # استخراج ZIP
            await file_manager.extract_zip(temp_path, project_path)
            
            # حذف الملف المؤقت
            temp_path.unlink()
            
            logger.info(f"✅ تم استخراج الملف إلى: {project_path}")
        else:
            logger.info("ℹ️ لم يتم رفع ملف ZIP، سيتم إنشاء مشروع فارغ")
        
        return {
            "project_id": project_name,
            "message": "تم إنشاء المشروع بنجاح",
            "path": str(project_path)
        }
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """الحصول على تفاصيل مشروع"""
    try:
        project_path = file_manager.projects_dir / project_id
        
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="المشروع غير موجود")
        
        # معلومات المشروع
        stat = project_path.stat()
        size = file_manager.get_project_size(project_id)
        files = list(project_path.rglob("*.*"))
        file_count = len([f for f in files if f.is_file()])
        
        project_info = {
            "id": project_id,
            "name": project_id,
            "path": str(project_path),
            "size": size,
            "file_count": file_count,
            "status": "active",
            "created_at": stat.st_ctime,
            "updated_at": stat.st_mtime,
            "has_analysis": False
        }
        
        # التحقق من وجود تحليل
        analysis_file = project_path / "analysis_result.json"
        if analysis_file.exists():
            project_info["has_analysis"] = True
        
        return project_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/analysis")
async def get_project_analysis(project_id: str):
    """الحصول على نتائج تحليل المشروع"""
    try:
        project_path = file_manager.projects_dir / project_id
        analysis_file = project_path / "analysis_result.json"
        
        if not analysis_file.exists():
            raise HTTPException(status_code=404, detail="لم يتم تحليل المشروع بعد")
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        return analysis_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_id}/analyze")
async def analyze_project(project_id: str):
    """بدء تحليل مشروع"""
    try:
        project_path = file_manager.projects_dir / project_id
        
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="المشروع غير موجود")
        
        # مسح الملفات أولاً
        files = file_manager.scan_project_files(project_path)
        
        # إذا لم توجد ملفات، إرجاع خطأ
        if not files:
            raise HTTPException(
                status_code=400, 
                detail="لم يتم العثور على ملفات JavaScript/TypeScript في المشروع"
            )
        
        files_data = [
            {
                'path': str(f.relative_to(project_path)),
                'size': f.stat().st_size
            }
            for f in files[:50]  # تحليل أول 50 ملف فقط لأداء أفضل
        ]
        
        # إرسال مهمة التحليل
        task_id = submit_task('analyze_project', {
            'project_path': str(project_path),
            'files': files_data
        })
        
        return {
            "task_id": task_id,
            "message": "تم بدء تحليل المشروع",
            "analysis_id": f"analysis_{project_id}_{int(time.time())}"
        }
    except Exception as e:
        logger.error(f"Error analyzing project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/debug")
async def debug_project(project_id: str):
    """فحص مشروع للتشخيص"""
    try:
        project_path = file_manager.projects_dir / project_id
        
        debug_info = {
            "project_id": project_id,
            "project_path": str(project_path),
            "project_exists": project_path.exists(),
            "files_in_project": [],
            "analysis_file_exists": False,
            "analysis_file_path": str(project_path / "analysis_result.json"),
            "total_files": 0
        }
        
        if project_path.exists():
            # قائمة الملفات في المشروع
            files = list(project_path.rglob("*"))
            debug_info["total_files"] = len(files)
            
            # أول 20 ملف فقط
            debug_info["files_in_project"] = [
                {
                    "name": f.name,
                    "path": str(f.relative_to(project_path)),
                    "is_file": f.is_file(),
                    "size": f.stat().st_size if f.is_file() else 0
                }
                for f in files[:20]
            ]
            
            # التحقق من ملف التحليل
            analysis_file = project_path / "analysis_result.json"
            debug_info["analysis_file_exists"] = analysis_file.exists()
            
            if analysis_file.exists():
                try:
                    debug_info["analysis_file_size"] = analysis_file.stat().st_size
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    debug_info["analysis_keys"] = list(content.keys()) if isinstance(content, dict) else []
                except Exception as e:
                    debug_info["analysis_file_error"] = str(e)
        
        return debug_info
    except Exception as e:
        logger.error(f"Debug error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_id}/bundles")
async def create_project_bundles(project_id: str):
    """إنشاء حزم للمشروع"""
    try:
        project_path = file_manager.projects_dir / project_id
        
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="المشروع غير موجود")
        
        # التحقق من وجود تحليل
        analysis_file = project_path / "analysis_result.json"
        if not analysis_file.exists():
            raise HTTPException(
                status_code=400, 
                detail="يجب تحليل المشروع أولاً قبل إنشاء الحزم"
            )
        
        # قراءة التحليل
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        # إرسال مهمة إنشاء الحزم
        task_id = submit_task('create_bundles', {
            'project_path': str(project_path),
            'analysis': analysis
        })
        
        return {
            "task_id": task_id,
            "message": "تم بدء إنشاء الحزم"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bundles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_id}/reports")
async def create_project_report(project_id: str):
    """إنشاء تقرير للمشروع"""
    try:
        project_path = file_manager.projects_dir / project_id
        
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="المشروع غير موجود")
        
        # التحقق من وجود تحليل
        analysis_file = project_path / "analysis_result.json"
        if not analysis_file.exists():
            raise HTTPException(
                status_code=400, 
                detail="يجب تحليل المشروع أولاً قبل إنشاء التقرير"
            )
        
        # قراءة التحليل
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        # إرسال مهمة إنشاء التقرير
        task_id = submit_task('generate_report', {
            'project_path': str(project_path),
            'analysis': analysis
        })
        
        return {
            "task_id": task_id,
            "message": "تم بدء إنشاء التقرير"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/bundles/download")
async def download_bundles(project_id: str):
    """تنزيل حزم المشروع"""
    try:
        bundles_dir = file_manager.bundles_dir
        
        # إنشاء أرشيف ZIP
        zip_path = bundles_dir / f"{project_id}_bundles.zip"
        
        if not zip_path.exists():
            raise HTTPException(status_code=404, detail="لا توجد حزم للتنزيل")
        
        return FileResponse(
            zip_path,
            media_type='application/zip',
            filename=f"{project_id}_bundles.zip"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading bundles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
async def get_tasks():
    """الحصول على قائمة المهام"""
    try:
        tasks = get_all_tasks()
        return tasks
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """الحصول على حالة مهمة"""
    try:
        task = get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="المهمة غير موجود")
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task_api(task_id: str):
    """إلغاء مهمة"""
    try:
        if cancel_task(task_id):
            return {"message": "تم إلغاء المهمة"}
        else:
            raise HTTPException(status_code=400, detail="لا يمكن إلغاء المهمة")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """فحص صحة النظام"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": time.time(),
        "message": "✅ النظام يعمل بشكل طبيعي"
    }

@app.post("/api/cleanup")
async def cleanup_system():
    """تنظيف النظام"""
    try:
        # تنظيف الملفات المؤقتة
        for temp_file in file_manager.uploads_dir.glob("*"):
            if temp_file.is_file():
                temp_file.unlink()
        
        # تنظيف المهام القديمة
        cleanup_old_tasks(1)  # مهام أقدم من ساعة
        
        return {"message": "✅ تم تنظيف النظام بنجاح"}
    except Exception as e:
        logger.error(f"Error cleaning system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
async def reset_system():
    """إعادة تعيين النظام (للتطوير فقط)"""
    try:
        # حذف جميع المجلدات وإعادة إنشائها
        for dir_path in [file_manager.projects_dir, file_manager.bundles_dir, 
                        file_manager.reports_dir, file_manager.uploads_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
            dir_path.mkdir(exist_ok=True)
        
        # تنظيف المهام
        cleanup_old_tasks(0)  # حذف جميع المهام
        
        return {"message": "✅ تم إعادة تعيين النظام بنجاح"}
    except Exception as e:
        logger.error(f"Error resetting system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# تشغيل الخادم
if __name__ == "__main__":
    initialize_web_app()
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")