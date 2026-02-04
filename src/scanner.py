"""
ماسح مشاريع الويب المتخصص في HTML, CSS, JS, jQuery, Bootstrap, Tailwind, PHP
"""
import os
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
import mimetypes

# استيراد الأدوات المساعدة
try:
    from utils import (
        setup_logger, safe_read_file, validate_path,
        clean_dependency_name, get_project_stats,
        is_web_file, extract_version, format_file_size
    )
    from config import get_config, Config
except ImportError:
    # استيراد بديل للتوافق
    import sys
    sys.path.append('.')
    from utils import (
        setup_logger, safe_read_file, validate_path,
        clean_dependency_name, get_project_stats,
        is_web_file, extract_version, format_file_size
    )
    from config import get_config, Config

logger = setup_logger('scanner')

class WebProjectScanner:
    """ماسح مشاريع الويب المتخصص"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.config = get_config()
        self.scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(project_path).encode()).hexdigest()[:6]}"
        
        # نتائج المسح
        self.results = {
            'scan_id': self.scan_id,
            'project_path': str(self.project_path),
            'scan_start': datetime.now().isoformat(),
            'technologies': {
                'html': {'files': 0, 'lines': 0, 'features': []},
                'css': {'files': 0, 'lines': 0, 'frameworks': []},
                'javascript': {'files': 0, 'lines': 0, 'libraries': []},
                'php': {'files': 0, 'lines': 0, 'features': []}
            },
            'dependencies': {
                'html': [],
                'css': [],
                'javascript': [],
                'php': []
            },
            'files': {
                'total': 0,
                'scanned': 0,
                'skipped': 0
            },
            'size': {
                'total': 0,
                'formatted': '0 B'
            },
            'detected_libraries': {
                'jquery': {'version': None, 'files': []},
                'bootstrap': {'version': None, 'files': []},
                'tailwind': {'version': None, 'files': []}
            },
            'cdn_links': [],
            'local_libraries': [],
            'warnings': [],
            'errors': []
        }
        
        # إحصائيات
        self.stats = get_project_stats(self.project_path)
        
    def scan(self) -> Dict:
        """إجراء مسح شامل للمشروع"""
        logger.info(f"بدء المسح {self.scan_id} للمشروع: {self.project_path}")
        
        try:
            # التحقق من صحة المسار
            is_valid, message = validate_path(str(self.project_path))
            if not is_valid:
                self.results['errors'].append(f"مسار غير صالح: {message}")
                logger.error(f"مسار غير صالح: {message}")
                return self.results
            
            # المسح حسب نوع الملف
            if self.config['focus_technologies']['html']:
                self._scan_html_files()
            
            if self.config['focus_technologies']['css']:
                self._scan_css_files()
            
            if self.config['focus_technologies']['javascript']:
                self._scan_js_files()
            
            if self.config['focus_technologies']['php']:
                self._scan_php_files()
            
            # تحليل إضافي
            self._detect_special_libraries()
            self._analyze_project_structure()
            
            # تحديث النتائج
            self._update_results()
            
        except Exception as e:
            error_msg = f"خطأ غير متوقع: {str(e)}"
            self.results['errors'].append(error_msg)
            logger.exception(error_msg)
        
        # إضافة وقت الانتهاء
        self.results['scan_end'] = datetime.now().isoformat()
        scan_duration = datetime.fromisoformat(self.results['scan_end']) - \
                       datetime.fromisoformat(self.results['scan_start'])
        self.results['scan_duration'] = str(scan_duration)
        
        logger.info(f"تم المسح {self.scan_id}: {self.results['files']['scanned']} ملف")
        return self.results
    
    def _scan_html_files(self):
        """مسح ملفات HTML"""
        logger.info("جاري مسح ملفات HTML...")
        
        html_files = list(self.project_path.rglob("*.html")) + \
                    list(self.project_path.rglob("*.htm"))
        
        for file_path in html_files:
            if self._should_skip(file_path):
                self.results['files']['skipped'] += 1
                continue
            
            try:
                content = safe_read_file(file_path, self.config['limits']['max_file_size'])
                if not content:
                    continue
                
                self.results['technologies']['html']['files'] += 1
                self.results['technologies']['html']['lines'] += content.count('\n')
                self.results['files']['scanned'] += 1
                self.results['size']['total'] += file_path.stat().st_size
                
                # اكتشاف المكتبات في HTML
                self._analyze_html_content(content, file_path)
                
            except Exception as e:
                self._add_warning(f"خطأ في معالجة {file_path.name}: {str(e)}")
    
    def _scan_css_files(self):
        """مسح ملفات CSS"""
        logger.info("جاري مسح ملفات CSS...")
        
        css_files = list(self.project_path.rglob("*.css")) + \
                   list(self.project_path.rglob("*.scss")) + \
                   list(self.project_path.rglob("*.less"))
        
        for file_path in css_files:
            if self._should_skip(file_path):
                self.results['files']['skipped'] += 1
                continue
            
            try:
                content = safe_read_file(file_path, self.config['limits']['max_file_size'])
                if not content:
                    continue
                
                self.results['technologies']['css']['files'] += 1
                self.results['technologies']['css']['lines'] += content.count('\n')
                self.results['files']['scanned'] += 1
                self.results['size']['total'] += file_path.stat().st_size
                
                # اكتشاف أطر العمل CSS
                self._analyze_css_content(content, file_path)
                
            except Exception as e:
                self._add_warning(f"خطأ في معالجة {file_path.name}: {str(e)}")
    
    def _scan_js_files(self):
        """مسح ملفات JavaScript"""
        logger.info("جاري مسح ملفات JavaScript...")
        
        js_files = list(self.project_path.rglob("*.js"))
        
        for file_path in js_files:
            # تخطي الملفات المضغوطة
            if file_path.name.endswith('.min.js'):
                self.results['files']['skipped'] += 1
                continue
            
            if self._should_skip(file_path):
                self.results['files']['skipped'] += 1
                continue
            
            try:
                content = safe_read_file(file_path, self.config['limits']['max_file_size'])
                if not content:
                    continue
                
                self.results['technologies']['javascript']['files'] += 1
                self.results['technologies']['javascript']['lines'] += content.count('\n')
                self.results['files']['scanned'] += 1
                self.results['size']['total'] += file_path.stat().st_size
                
                # اكتشاف المكتبات JavaScript
                self._analyze_js_content(content, file_path)
                
            except Exception as e:
                self._add_warning(f"خطأ في معالجة {file_path.name}: {str(e)}")
    
    def _scan_php_files(self):
        """مسح ملفات PHP"""
        logger.info("جاري مسح ملفات PHP...")
        
        php_files = list(self.project_path.rglob("*.php")) + \
                   list(self.project_path.rglob("*.phtml"))
        
        for file_path in php_files:
            if self._should_skip(file_path):
                self.results['files']['skipped'] += 1
                continue
            
            try:
                content = safe_read_file(file_path, self.config['limits']['max_file_size'])
                if not content:
                    continue
                
                self.results['technologies']['php']['files'] += 1
                self.results['technologies']['php']['lines'] += content.count('\n')
                self.results['files']['scanned'] += 1
                self.results['size']['total'] += file_path.stat().st_size
                
                # اكتشاف ميزات PHP
                self._analyze_php_content(content, file_path)
                
            except Exception as e:
                self._add_warning(f"خطأ في معالجة {file_path.name}: {str(e)}")
    
    def _analyze_html_content(self, content: str, file_path: Path):
        """تحليل محتوى HTML"""
        # اكتشاف jQuery
        jquery_patterns = [
            r'src=["\'][^"\']*jquery[^"\']*["\']',
            r'\$\.|\$\(|jQuery\(',
            r'cdn\.jquery|code\.jquery'
        ]
        
        for pattern in jquery_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.results['detected_libraries']['jquery']['files'].append(str(file_path))
                
                # استخراج الإصدار
                version_match = re.search(r'jquery[.-]?(\d+\.\d+\.\d+)', content, re.IGNORECASE)
                if version_match and not self.results['detected_libraries']['jquery']['version']:
                    self.results['detected_libraries']['jquery']['version'] = version_match.group(1)
                break
        
        # اكتشاف Bootstrap
        bootstrap_patterns = [
            r'bootstrap(?:\.min)?\.(?:js|css)',
            r'data-bs-|data-toggle',
            r'cdn\.bootstrap|bootstrapcdn\.com'
        ]
        
        for pattern in bootstrap_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.results['detected_libraries']['bootstrap']['files'].append(str(file_path))
                
                # استخراج الإصدار
                version_match = re.search(r'bootstrap[.-]?(\d+\.\d+\.\d+)', content, re.IGNORECASE)
                if version_match and not self.results['detected_libraries']['bootstrap']['version']:
                    self.results['detected_libraries']['bootstrap']['version'] = version_match.group(1)
                break
        
        # استخراج روابط CDN
        cdn_patterns = [
            r'src=["\'](https?://[^"\']+\.js)["\']',
            r'href=["\'](https?://[^"\']+\.css)["\']',
            r'url\(["\']?(https?://[^"\']+)["\']?\)'
        ]
        
        for pattern in cdn_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                url = match.group(1)
                if any(cdn in url for cdn in self.config['known_cdns']):
                    if url not in self.results['cdn_links']:
                        self.results['cdn_links'].append(url)
    
    def _analyze_css_content(self, content: str, file_path: Path):
        """تحليل محتوى CSS"""
        # اكتشاف Tailwind
        tailwind_patterns = [
            r'@tailwind\s',
            r'tailwind\s{',
            r'tw-|\.tw-'
        ]
        
        for pattern in tailwind_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.results['detected_libraries']['tailwind']['files'].append(str(file_path))
                
                # استخراج الإصدار
                version_match = re.search(r'tailwindcss@(\d+\.\d+\.\d+)', content)
                if version_match and not self.results['detected_libraries']['tailwind']['version']:
                    self.results['detected_libraries']['tailwind']['version'] = version_match.group(1)
                break
        
        # استخراج الاستيرادات
        imports = re.findall(r'@import\s+(?:url\()?["\']?([^"\';\)]+)["\']?', content)
        for imp in imports:
            if imp.startswith('http'):
                if any(cdn in imp for cdn in self.config['known_cdns']):
                    if imp not in self.results['cdn_links']:
                        self.results['cdn_links'].append(imp)
    
    def _analyze_js_content(self, content: str, file_path: Path):
        """تحليل محتوى JavaScript"""
        # اكتشاف مكتبات JS
        library_patterns = {
            'jquery': [r'\$\.|\$\(|jQuery\(|\.ajax\(|\.get\('],
            'axios': [r'axios\.|import axios'],
            'lodash': [r'_\.|import.*lodash'],
            'moment': [r'moment\.|import moment']
        }
        
        for lib_name, patterns in library_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    if lib_name not in self.results['dependencies']['javascript']:
                        self.results['dependencies']['javascript'].append(lib_name)
                    break
        
        # استخراج الواردات
        imports = re.findall(r'import\s+.*from\s+["\']([^"\']+)["\']', content)
        requires = re.findall(r'require\(["\']([^"\']+)["\']\)', content)
        
        for imp in imports + requires:
            if not imp.startswith(('.', '/')):
                cleaned = clean_dependency_name(imp)
                if cleaned and cleaned not in self.results['dependencies']['javascript']:
                    self.results['dependencies']['javascript'].append(cleaned)
    
    def _analyze_php_content(self, content: str, file_path: Path):
        """تحليل محتوى PHP"""
        # اكتشاف Composer
        if 'composer.json' in str(file_path):
            try:
                data = json.loads(content)
                if 'require' in data:
                    for package, version in data['require'].items():
                        dep = f"{package}:{version}"
                        if dep not in self.results['dependencies']['php']:
                            self.results['dependencies']['php'].append(dep)
            except:
                pass
        
        # اكتشاف WordPress
        wp_patterns = [
            r'wp_enqueue_script',
            r'wp_enqueue_style',
            r'add_action',
            r'get_template_directory'
        ]
        
        for pattern in wp_patterns:
            if re.search(pattern, content):
                if 'wordpress' not in self.results['technologies']['php']['features']:
                    self.results['technologies']['php']['features'].append('wordpress')
                break
    
    def _detect_special_libraries(self):
        """اكتشاف المكتبات الخاصة المطلوبة"""
        # اكتشاف Bootstrap من الملفات
        bootstrap_files = list(self.project_path.rglob("*bootstrap*"))
        for bfile in bootstrap_files:
            if bfile.suffix.lower() in ['.css', '.js', '.min.css', '.min.js']:
                if 'bootstrap' not in self.results['dependencies']['css']:
                    self.results['dependencies']['css'].append('bootstrap')
                
                # إضافة إلى الملفات المكتشفة
                if str(bfile) not in self.results['detected_libraries']['bootstrap']['files']:
                    self.results['detected_libraries']['bootstrap']['files'].append(str(bfile))
        
        # اكتشاف jQuery من الملفات
        jquery_files = list(self.project_path.rglob("*jquery*"))
        for jfile in jquery_files:
            if jfile.suffix.lower() in ['.js', '.min.js']:
                if 'jquery' not in self.results['dependencies']['javascript']:
                    self.results['dependencies']['javascript'].append('jquery')
                
                # إضافة إلى الملفات المكتشفة
                if str(jfile) not in self.results['detected_libraries']['jquery']['files']:
                    self.results['detected_libraries']['jquery']['files'].append(str(jfile))
        
        # اكتشاف Tailwind من الملفات
        tailwind_config = self.project_path / 'tailwind.config.js'
        if tailwind_config.exists():
            if 'tailwind' not in self.results['dependencies']['css']:
                self.results['dependencies']['css'].append('tailwind')
            
            if str(tailwind_config) not in self.results['detected_libraries']['tailwind']['files']:
                self.results['detected_libraries']['tailwind']['files'].append(str(tailwind_config))
    
    def _analyze_project_structure(self):
        """تحليل بنية المشروع"""
        # اكتشاف ملفات مهمة
        important_files = {
            'package.json': 'Node.js',
            'composer.json': 'PHP/Composer',
            'webpack.config.js': 'Webpack',
            'gulpfile.js': 'Gulp',
            'gruntfile.js': 'Grunt',
            '.gitignore': 'Git'
        }
        
        for filename, tech in important_files.items():
            if (self.project_path / filename).exists():
                if 'project_tools' not in self.results:
                    self.results['project_tools'] = []
                self.results['project_tools'].append(tech)
    
    def _update_results(self):
        """تحديث النتائج النهائية"""
        # تحديث إحصائيات الملفات
        self.results['files']['total'] = self.stats['total_files']
        
        # تحديث الحجم المنسق
        self.results['size']['formatted'] = format_file_size(self.results['size']['total'])
        
        # تحويل القوائم إلى مجموعات ثم إلى قوائم لإزالة التكرارات
        for key in ['html', 'css', 'javascript', 'php']:
            if key in self.results['dependencies']:
                self.results['dependencies'][key] = list(set(self.results['dependencies'][key]))
        
        # إضافة ملخص
        self.results['summary'] = {
            'total_dependencies': sum(len(deps) for deps in self.results['dependencies'].values()),
            'total_files_scanned': self.results['files']['scanned'],
            'project_size': self.results['size']['formatted'],
            'detected_frameworks': [
                lib for lib, data in self.results['detected_libraries'].items()
                if data['files']
            ]
        }
    
    def _should_skip(self, file_path: Path) -> bool:
        """تحديد ما إذا كان يجب تخطي الملف"""
        # التحقق من المجلدات المستبعدة
        for excluded in self.config['exclusions']['dirs']:
            if excluded in str(file_path):
                return True
        
        # التحقق من الملفات المستبعدة
        for pattern in self.config['exclusions']['files']:
            if file_path.match(pattern):
                return True
        
        # التحقق من حجم الملف
        try:
            if file_path.stat().st_size > self.config['limits']['max_file_size']:
                return True
        except:
            return True
        
        return False
    
    def _add_warning(self, message: str):
        """إضافة تحذير"""
        self.results['warnings'].append(message)
        logger.warning(message)


# ==================== واجهة مبسطة ====================
def scan_project(project_path: str) -> Dict:
    """
    واجهة مبسطة لمسح المشروع
    
    Args:
        project_path: مسار المشروع المراد مسحه
    
    Returns:
        نتائج المسح كقاموس
    """
    scanner = WebProjectScanner(project_path)
    return scanner.scan()


# ==================== اختبار ====================
if __name__ == "__main__":
    # اختبار المسح
    import sys
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
        results = scan_project(project_path)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("الرجاء تقديم مسار المشروع: python scanner.py /path/to/project")