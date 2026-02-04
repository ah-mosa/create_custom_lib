"""
إعدادات وتكوين الأداة - إصدار Python
"""
import json
from pathlib import Path
from datetime import datetime

# ==================== المسارات ====================
BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
BUNDLES_DIR = BASE_DIR / "bundles"
LOGS_DIR = BASE_DIR / "logs"
UPLOAD_DIR = BASE_DIR / "uploads"
TEMP_DIR = BASE_DIR / "temp"

# إنشاء المجلدات إذا لم تكن موجودة
for directory in [REPORTS_DIR, BUNDLES_DIR, LOGS_DIR, UPLOAD_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ==================== الإعدادات العامة ====================
class Config:
    """فئة الإعدادات"""
    
    # إصدار التطبيق
    VERSION = "2.0.0"
    
    # التركيز التقني (كما طلبت)
    FOCUS_TECHNOLOGIES = {
        'html': True,
        'css': True,
        'javascript': True,
        'jquery': True,
        'bootstrap': True,
        'tailwind': True,
        'php': True,
        'python': False  # غير مفعل حسب طلبك
    }
    
    # حدود المسح
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_PROJECT_SIZE = 100 * 1024 * 1024  # 100MB
    SCAN_TIMEOUT = 30  # ثانية
    
    # المجلدات المستبعدة
    EXCLUDE_DIRS = [
        '.git', '.svn', '.hg',
        'node_modules', 'vendor',
        '__pycache__', '.idea',
        'dist', 'build', 'logs',
        'tmp', 'temp', 'cache'
    ]
    
    # الملفات المستبعدة
    EXCLUDE_FILES = [
        '*.min.js', '*.min.css',
        '*.log', '*.tmp', '*.temp',
        '*.map', '.DS_Store'
    ]
    
    # أنماط اكتشاف المكتبات
    LIBRARY_PATTERNS = {
        'jquery': [
            r'jquery[.-]?(\d+\.\d+\.\d+)?(\.min)?\.js',
            r'\$\.|\$\(|jQuery\(|\.ajax\(|\.get\(|\.post\(',
            r'cdn\.jquery|code\.jquery'
        ],
        'bootstrap': [
            r'bootstrap[.-]?(\d+\.\d+\.\d+)?(\.min)?\.(js|css)',
            r'data-bs-|data-toggle|modal|carousel',
            r'cdn\.bootstrap|bootstrapcdn\.com'
        ],
        'tailwind': [
            r'tailwindcss\.com|cdn\.tailwindcss',
            r'tailwind\.config\.js',
            r'@tailwind\s|tw-|tailwind\s{'
        ]
    }
    
    # CDNs معروفة
    KNOWN_CDNS = [
        'cdn.jsdelivr.net',
        'cdnjs.cloudflare.com',
        'code.jquery.com',
        'cdn.tailwindcss.com',
        'unpkg.com',
        'bootstrapcdn.com',
        'fonts.googleapis.com'
    ]
    
    # إعدادات الحزم
    BUNDLE_SETTINGS = {
        'output_dir': 'custom_builds',
        'minify_js': True,
        'minify_css': True,
        'create_zip': True,
        'include_readme': True
    }
    
    @classmethod
    def to_dict(cls):
        """تحويل الإعدادات إلى قاموس"""
        return {
            'version': cls.VERSION,
            'focus_technologies': cls.FOCUS_TECHNOLOGIES,
            'limits': {
                'max_file_size': cls.MAX_FILE_SIZE,
                'max_project_size': cls.MAX_PROJECT_SIZE,
                'scan_timeout': cls.SCAN_TIMEOUT
            },
            'exclusions': {
                'dirs': cls.EXCLUDE_DIRS,
                'files': cls.EXCLUDE_FILES
            },
            'library_patterns': cls.LIBRARY_PATTERNS,
            'known_cdns': cls.KNOWN_CDNS,
            'bundle_settings': cls.BUNDLE_SETTINGS,
            'paths': {
                'base': str(BASE_DIR),
                'reports': str(REPORTS_DIR),
                'bundles': str(BUNDLES_DIR),
                'logs': str(LOGS_DIR),
                'uploads': str(UPLOAD_DIR),
                'temp': str(TEMP_DIR)
            }
        }
    
    @classmethod
    def save_to_json(cls, file_path: Path = None):
        """حفظ الإعدادات إلى ملف JSON"""
        if file_path is None:
            file_path = BASE_DIR / "config.json"
        
        data = cls.to_dict()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return file_path

# إنشاء ملف config.json للتوافق
Config.save_to_json()

# دالة لتحميل الإعدادات
def get_config():
    """الحصول على الإعدادات الحالية"""
    return Config.to_dict()

def load_config_from_json(file_path: Path = None):
    """تحميل الإعدادات من ملف JSON"""
    if file_path is None:
        file_path = BASE_DIR / "config.json"
    
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    
    return Config.to_dict()