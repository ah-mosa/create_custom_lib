"""
أدوات مساعدة لوظائف متنوعة
"""
import os
import re
import json
import hashlib
import logging
import mimetypes
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# ==================== إعدادات التسجيل ====================
def setup_logger(name: str, log_file: str = "scanner.log", level: str = 'INFO') -> logging.Logger:
    """إعداد وتسجيل الأحداث"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # مستوى التسجيل
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # تنسيق الرسائل
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # معالج الملفات
        log_path = Path("logs") / log_file
        log_path.parent.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # معالج وحدة التحكم
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

# ==================== التعامل مع الملفات ====================
def safe_read_file(file_path: Path, max_size: int = 10 * 1024 * 1024) -> Optional[str]:
    """قراءة ملف بأمان مع التحقق من الحجم"""
    try:
        # التحقق من وجود الملف
        if not file_path.exists() or not file_path.is_file():
            return None
        
        # التحقق من حجم الملف
        file_size = file_path.stat().st_size
        if file_size > max_size:
            logger = setup_logger(__name__)
            logger.warning(f"تخطي ملف كبير: {file_path.name} ({file_size} bytes)")
            return None
        
        # محاولة قراءة بترميزات مختلفة
        encodings = ['utf-8', 'latin-1', 'windows-1256', 'cp1256', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # إذا فشلت جميع الترميزات، استخدام ثنائي مع تجاهل الأخطاء
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='ignore')
            
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"خطأ في قراءة الملف {file_path}: {e}")
        return None

def validate_path(path_str: str) -> Tuple[bool, str]:
    """التحقق من صحة وأمان المسار"""
    try:
        path = Path(path_str).resolve()
        
        # التحقق من وجود المسار
        if not path.exists():
            return False, "المسار غير موجود"
        
        # التحقق من أنه مجلد (مشروع)
        if not path.is_dir():
            return False, "المسار يجب أن يكون مجلد مشروع"
        
        # التحقق من الأنماط غير الآمنة
        unsafe_patterns = [
            r'\.\./', r'/etc/', r'/bin/', r'/sbin/', r'/usr/bin',
            r'C:\\Windows', r'C:\\System32', r'/passwd', r'/shadow',
            r'\.git$', r'\.env$'
        ]
        
        path_str_normalized = str(path).replace('\\', '/')
        for pattern in unsafe_patterns:
            if re.search(pattern, path_str_normalized, re.IGNORECASE):
                return False, f"مسار غير آمن"
        
        # التحقق من وجود ملفات مشروع
        project_files = ['index.html', 'package.json', 'composer.json', '.git']
        has_project_file = any((path / f).exists() for f in project_files)
        
        if not has_project_file:
            # التحقق من وجود ملفات برمجة
            code_files = list(path.rglob("*.html")) + list(path.rglob("*.php")) + \
                        list(path.rglob("*.js")) + list(path.rglob("*.css"))
            if len(code_files) == 0:
                return False, "لا يوجد ملفات مشروع"
        
        return True, "مسار صالح"
        
    except Exception as e:
        return False, f"خطأ في التحقق من المسار: {str(e)}"

def detect_file_type(file_path: Path) -> Dict[str, str]:
    """كشف نوع الملف والتفاصيل"""
    result = {
        'mime_type': 'application/octet-stream',
        'extension': file_path.suffix.lower(),
        'language': 'unknown',
        'is_text': False
    }
    
    # كشف MIME type
    mime_type, encoding = mimetypes.guess_type(str(file_path))
    if mime_type:
        result['mime_type'] = mime_type
    
    # تعيين لغة البرمجة
    extension_map = {
        '.html': 'html', '.htm': 'html',
        '.css': 'css', '.scss': 'scss', '.less': 'less',
        '.js': 'javascript', '.jsx': 'javascript',
        '.php': 'php', '.phtml': 'php',
        '.py': 'python', '.json': 'json',
        '.md': 'markdown', '.txt': 'text',
        '.xml': 'xml', '.yml': 'yaml', '.yaml': 'yaml'
    }
    
    if result['extension'] in extension_map:
        result['language'] = extension_map[result['extension']]
        result['is_text'] = True
    
    # التحقق من محتوى النص
    if result['is_text']:
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
                # محاولة فك الترميز
                try:
                    sample.decode('utf-8')
                    result['encoding'] = 'utf-8'
                except UnicodeDecodeError:
                    result['encoding'] = 'binary'
                    result['is_text'] = False
        except:
            result['is_text'] = False
    
    return result

# ==================== التعامل مع الشبكة ====================
def download_file(url: str, output_dir: Path, timeout: int = 30) -> Optional[Path]:
    """تنزيل ملف من URL بأمان"""
    try:
        # التحقق من URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        
        # إنشاء جلسة مع إعادة المحاولة
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # إعدادات الطلب
        headers = {
            'User-Agent': 'WebScanner/1.0'
        }
        
        # تنزيل الملف
        response = session.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # تحديد اسم الملف
        content_disposition = response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename = re.findall('filename=(.+)', content_disposition)[0].strip('"\'')
        else:
            filename = url.split('/')[-1].split('?')[0] or 'downloaded_file'
        
        # تنظيف اسم الملف
        filename = re.sub(r'[^\w\.\-]', '_', filename)
        
        # المسار الكامل للملف
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / filename
        
        # حفظ الملف
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # التحقق من صحة الملف
        if file_path.stat().st_size == 0:
            file_path.unlink()
            return None
        
        return file_path
        
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"خطأ في تنزيل {url}: {e}")
        return None

# ==================== معالجة النصوص ====================
def clean_dependency_name(dep: str) -> str:
    """تنظيف اسم المكتبة من الرموز الخاصة"""
    if not dep:
        return ""
    
    # إزالة الإصدار والرموز الخاصة
    dep = re.sub(r'[@#?].*$', '', dep)  # إزالة كل شيء بعد @ أو # أو ?
    dep = re.sub(r'[\^~<>=*]', '', dep)  # إزالة رموز الإصدار
    dep = dep.split('/')[-1]  # أخذ الجزء الأخير فقط
    dep = dep.strip('.-_ ')  # إزالة النقاط والشرطات من الأطراف
    
    return dep.lower()

def extract_version(text: str) -> Optional[str]:
    """استخراج رقم الإصدار من النص"""
    version_patterns = [
        r'(\d+\.\d+\.\d+)',  # x.x.x
        r'(\d+\.\d+)',       # x.x
        r'v(\d+\.\d+\.\d+)', # vx.x.x
        r'version[\s:]*(\d+\.\d+\.\d+)'
    ]
    
    for pattern in version_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

# ==================== أدوات مساعدة ====================
def format_file_size(bytes_size: int) -> str:
    """تنسيق حجم الملف بشكل مقروء"""
    if bytes_size == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    
    while bytes_size >= 1024 and unit_index < len(units) - 1:
        bytes_size /= 1024.0
        unit_index += 1
    
    return f"{bytes_size:.2f} {units[unit_index]}"

def create_hash(data: str, length: int = 8) -> str:
    """إنشاء تجزئة للبيانات"""
    return hashlib.md5(data.encode()).hexdigest()[:length]

def get_safe_filename(name: str) -> str:
    """تحويل الاسم إلى صيغة آمنة للملفات"""
    # إزالة الرموز غير الآمنة
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    
    # تقليل الشرطات المتكررة
    safe_name = re.sub(r'_+', '_', safe_name)
    
    # إزالة المسافات في البداية والنهاية
    safe_name = safe_name.strip('_-. ')
    
    # تحديد الطول
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    
    return safe_name

def save_json(data: Dict, file_path: Path) -> bool:
    """حفظ البيانات بصيغة JSON"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"خطأ في حفظ JSON: {e}")
        return False

def load_json(file_path: Path) -> Optional[Dict]:
    """تحميل البيانات من ملف JSON"""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"خطأ في تحميل JSON: {e}")
        return None

def get_project_stats(project_path: Path) -> Dict[str, Any]:
    """الحصول على إحصائيات المشروع"""
    stats = {
        'total_files': 0,
        'total_size': 0,
        'file_types': {},
        'scan_date': datetime.now().isoformat()
    }
    
    try:
        exclude_dirs = {'.git', 'node_modules', '__pycache__', 'vendor'}
        
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                # تخطي الملفات في مجلدات مستبعدة
                if any(excluded in str(file_path) for excluded in exclude_dirs):
                    continue
                
                stats['total_files'] += 1
                
                try:
                    file_size = file_path.stat().st_size
                    stats['total_size'] += file_size
                    
                    # نوع الملف
                    ext = file_path.suffix.lower()
                    if ext:
                        stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
                except:
                    continue
        
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"خطأ في حساب إحصائيات: {e}")
    
    return stats

def is_web_file(file_path: Path) -> bool:
    """التحقق مما إذا كان الملف من نوع ويب"""
    web_extensions = {'.html', '.htm', '.css', '.js', '.php', '.json', '.xml'}
    return file_path.suffix.lower() in web_extensions

def merge_dependencies(deps_list: List[List[str]]) -> List[str]:
    """دمج قوائم المكتبات مع إزالة التكرارات"""
    merged = set()
    for deps in deps_list:
        for dep in deps:
            cleaned = clean_dependency_name(dep)
            if cleaned:
                merged.add(cleaned)
    return sorted(list(merged))

def format_duration(seconds: float) -> str:
    """تنسيق المدة الزمنية"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"

def create_temp_dir() -> Path:
    """إنشاء مجلد مؤقت"""
    temp_dir = Path(tempfile.mkdtemp(prefix="webscanner_"))
    return temp_dir

def cleanup_temp_dir(temp_dir: Path):
    """تنظيف المجلد المؤقت"""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    except Exception as e:
        logger = setup_logger(__name__)
        logger.warning(f"خطأ في تنظيف مجلد مؤقت: {e}")