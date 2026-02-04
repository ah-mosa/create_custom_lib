"""
إنشاء حزم مخصصة
"""
import os
import re
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List
import requests
from . import config
from .utils import setup_logger, get_safe_filename

logger = setup_logger(__name__)

class CustomBundler:
    def __init__(self, output_dir: str = "bundles"):
        self.cfg = config.get_config()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def create_bundle(self, dependencies: Dict, bundle_name: str) -> Dict:
        """إنشاء حزمة"""
        logger.info(f"إنشاء حزمة: {bundle_name}")
        
        bundle_path = self.output_dir / get_safe_filename(bundle_name)
        bundle_path.mkdir(exist_ok=True)
        
        results = {
            'bundle_name': bundle_name,
            'bundle_path': str(bundle_path),
            'successful': [],
            'failed': [],
            'files': []
        }
        
        # معالجة المكتبات
        if 'js_libraries' in dependencies:
            self._download_js_libs(dependencies['js_libraries'], bundle_path, results)
        
        if 'css_frameworks' in dependencies:
            self._download_css_frameworks(dependencies['css_frameworks'], bundle_path, results)
        
        # إنشاء ملف README
        self._create_readme(bundle_path, dependencies, results)
        
        # ضغط إذا لزم الأمر
        if self._get_size(bundle_path) > 10 * 1024 * 1024:
            self._create_zip(bundle_path)
        
        return results
    
    def _download_js_libs(self, libraries: List[str], output_path: Path, results: Dict):
        """تنزيل مكتبات JS"""
        lib_urls = {
            'jquery': 'https://code.jquery.com/jquery-3.6.0.min.js',
            'axios': 'https://cdnjs.cloudflare.com/ajax/libs/axios/1.6.0/axios.min.js'
        }
        
        js_dir = output_path / "js"
        js_dir.mkdir(exist_ok=True)
        
        for lib in libraries:
            if lib in lib_urls:
                try:
                    filename = self._download_file(lib_urls[lib], js_dir)
                    if filename:
                        results['successful'].append(lib)
                        results['files'].append(f"js/{filename}")
                        logger.info(f"تم تنزيل {lib}")
                except Exception as e:
                    results['failed'].append(lib)
                    logger.error(f"فشل تنزيل {lib}: {e}")
    
    def _download_css_frameworks(self, frameworks: List[str], output_path: Path, results: Dict):
        """تنزيل أطر العمل CSS"""
        framework_urls = {
            'bootstrap': {
                'css': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
                'js': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'
            },
            'tailwind': {
                'css': 'https://cdn.tailwindcss.com/3.3.0/tailwind.min.css'
            }
        }
        
        css_dir = output_path / "css"
        css_dir.mkdir(exist_ok=True)
        
        for fw in frameworks:
            if fw in framework_urls:
                urls = framework_urls[fw]
                for file_type, url in urls.items():
                    try:
                        filename = self._download_file(url, css_dir if file_type == 'css' else output_path / "js")
                        if filename:
                            results['successful'].append(f"{fw}_{file_type}")
                            results['files'].append(f"{'css' if file_type == 'css' else 'js'}/{filename}")
                    except Exception as e:
                        results['failed'].append(f"{fw}_{file_type}")
                        logger.error(f"فشل تنزيل {fw} {file_type}: {e}")
    
    def _download_file(self, url: str, output_dir: Path) -> str:
        """تنزيل ملف"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            filename = url.split('/')[-1]
            filepath = output_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return filename
        except Exception as e:
            logger.error(f"خطأ في التنزيل: {e}")
            raise
    
    def _create_readme(self, bundle_path: Path, dependencies: Dict, results: Dict):
        """إنشاء README"""
        readme_content = f"""# حزمة مخصصة - {results['bundle_name']}

## المكتبات المتضمنة
{chr(10).join(f"- {lib}" for lib in results['successful'])}

## التعليمات
أضف الملفات التالية إلى مشروعك:

"""
        
        for file in results['files']:
            if file.endswith('.js'):
                readme_content += f"""```html
<script src="{file}"></script>
"""
elif file.endswith('.css'):
readme_content += f"""```html
<link rel="stylesheet" href="{file}"> ``` """
    (bundle_path / "README.md").write_text(readme_content, encoding='utf-8')
    results['files'].append("README.md")

def _get_size(self, path: Path) -> int:
    """حساب الحجم"""
    total = 0
    for file in path.rglob("*"):
        if file.is_file():
            total += file.stat().st_size
    return total

def _create_zip(self, folder_path: Path):
    """إنشاء ZIP"""
    import zipfile
    
    zip_path = folder_path.parent / f"{folder_path.name}.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in folder_path.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(folder_path)
                zipf.write(file, arcname)
    
    logger.info(f"تم إنشاء الأرشيف: {zip_path}")

### **5. ملف `webui.py` محدث**

```python
"""
واجهة الويب باستخدام Flask
"""
from flask import Flask, render_template, request, jsonify, send_file
import os
from pathlib import Path
import json
from datetime import datetime
from scanner import WebProjectScanner
from bundler import CustomBundler
from utils import setup_logger, save_json
import config

app = Flask(__name__)
logger = setup_logger('webui')

# التحقق من المجلدات
cfg = config.get_config()
for path in cfg['paths'].values():
    Path(path).mkdir(exist_ok=True)

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan_project():
    """مسح مشروع"""
    try:
        data = request.get_json()
        project_path = data.get('project_path', '').strip()
        
        if not project_path:
            return jsonify({'error': 'مسار المشروع مطلوب'}), 400
        
        # المسح
        scanner = WebProjectScanner(project_path)
        results = scanner.scan()
        
        # حفظ النتائج
        report_file = Path(cfg['paths']['reports']) / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_json(results, report_file)
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"خطأ في المسح: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/bundle', methods=['POST'])
def create_bundle():
    """إنشاء حزمة"""
    try:
        data = request.get_json()
        bundle_name = data.get('bundle_name', 'custom_bundle').strip()
        dependencies = data.get('dependencies', {})
        
        if not bundle_name:
            return jsonify({'error': 'اسم الحزمة مطلوب'}), 400
        
        # الإنشاء
        bundler = CustomBundler(cfg['paths']['bundles'])
        results = bundler.create_bundle(dependencies, bundle_name)
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء الحزمة: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/reports')
def list_reports():
    """قائمة التقارير"""
    reports_dir = Path(cfg['paths']['reports'])
    reports = []
    
    for file in reports_dir.glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                reports.append({
                    'file': file.name,
                    'scan_id': data.get('scan_id', ''),
                    'project': data.get('project_path', ''),
                    'time': data.get('scan_time', ''),
                    'files': data.get('files_scanned', 0)
                })
        except:
            continue
    
    return jsonify({'reports': reports})

@app.route('/download/<path:filename>')
def download_file(filename):
    """تحميل ملف"""
    file_path = Path(cfg['paths']['bundles']) / filename
    
    if file_path.exists() and file_path.is_file():
        return send_file(str(file_path), as_attachment=True)
    
    return jsonify({'error': 'الملف غير موجود'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)