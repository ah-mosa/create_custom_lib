"""
أداة مسح وتحليل مشاريع الويب لاكتشاف المكتبات المستخدمة
"""
import os
import json
import re
from pathlib import Path
import subprocess
from typing import Dict, List, Set, Optional
import ast

class ProjectScanner:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.dependencies = {
            'npm': set(),
            'pip': set(),
            'cdn': set(),
            'local': set()
        }
        self.files_scanned = 0
        
    def scan_project(self) -> Dict:
        """المسح الرئيسي للمشروع"""
        print(f"🔍 جاري مسح المشروع: {self.project_path}")
        
        if not self.project_path.exists():
            raise ValueError(f"المسار غير موجود: {self.project_path}")
        
        # تحليل الملفات الأساسية
        self._analyze_package_files()
        
        # مسح الملفات بناء على النوع
        self._scan_html_files()
        self._scan_js_files()
        self._scan_css_files()
        self._scan_python_files()
        
        return {
            'dependencies': {k: list(v) for k, v in self.dependencies.items()},
            'files_scanned': self.files_scanned,
            'project_size': self._get_project_size()
        }
    
    def _analyze_package_files(self):
        """تحليل ملفات إدارة الحزم"""
        # package.json للمشاريع Node.js
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # استخراج dependencies و devDependencies
                for dep_type in ['dependencies', 'devDependencies']:
                    if dep_type in data:
                        for dep, version in data[dep_type].items():
                            self.dependencies['npm'].add(f"{dep}@{version}")
            except Exception as e:
                print(f"⚠️ خطأ في تحليل package.json: {e}")
        
        # requirements.txt للمشاريع Python
        req_file = self.project_path / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.dependencies['pip'].add(line)
            except Exception as e:
                print(f"⚠️ خطأ في تحليل requirements.txt: {e}")
    
    def _scan_html_files(self):
        """مسح ملفات HTML للعثور على مكتبات CDN"""
        html_patterns = [
            r'src=["\'](https?://[^"\']+\.js)["\']',
            r'href=["\'](https?://[^"\']+\.css)["\']',
            r'from ["\'](https?://[^"\']+)["\']',
            r'import.*from ["\'](https?://[^"\']+)["\']'
        ]
        
        for file_path in self.project_path.rglob("*.html"):
            self._scan_file_for_patterns(file_path, html_patterns, 'cdn')
    
    def _scan_js_files(self):
        """مسح ملفات JavaScript"""
        js_patterns = [
            r'import.*from ["\']([^"\']+)["\']',
            r'require\(["\']([^"\']+)["\']\)',
            r'from ["\']([^"\']+)["\']'
        ]
        
        for file_path in self.project_path.rglob("*.js"):
            self._scan_file_for_patterns(file_path, js_patterns, 'npm')
            
        for file_path in self.project_path.rglob("*.jsx"):
            self._scan_file_for_patterns(file_path, js_patterns, 'npm')
            
        for file_path in self.project_path.rglob("*.ts"):
            self._scan_file_for_patterns(file_path, js_patterns, 'npm')
            
        for file_path in self.project_path.rglob("*.tsx"):
            self._scan_file_for_patterns(file_path, js_patterns, 'npm')
    
    def _scan_css_files(self):
        """مسح ملفات CSS"""
        css_patterns = [
            r'@import\s+["\']([^"\']+)["\']',
            r'url\(["\']?([^"\'\)]+)["\']?\)'
        ]
        
        for file_path in self.project_path.rglob("*.css"):
            self._scan_file_for_patterns(file_path, css_patterns, 'cdn')
            
        for file_path in self.project_path.rglob("*.scss"):
            self._scan_file_for_patterns(file_path, css_patterns, 'cdn')
            
        for file_path in self.project_path.rglob("*.less"):
            self._scan_file_for_patterns(file_path, css_patterns, 'cdn')
    
    def _scan_python_files(self):
        """مسح ملفات Python"""
        for file_path in self.project_path.rglob("*.py"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.files_scanned += 1
                    
                # تحليل imports في Python
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.dependencies['pip'].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self.dependencies['pip'].add(node.module)
            except Exception as e:
                print(f"⚠️ خطأ في تحليل ملف Python {file_path}: {e}")
    
    def _scan_file_for_patterns(self, file_path: Path, patterns: List[str], dep_type: str):
        """مسح ملف للعثور على أنماط محددة"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.files_scanned += 1
                
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # تصفية المطابقات المحلية
                    if not match.startswith(('.', '/', '\\')):
                        self.dependencies[dep_type].add(match)
        except Exception as e:
            print(f"⚠️ خطأ في قراءة الملف {file_path}: {e}")
    
    def _get_project_size(self) -> str:
        """حساب حجم المشروع"""
        total_size = 0
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        # تحويل إلى وحدة مناسبة
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total_size < 1024.0:
                return f"{total_size:.2f} {unit}"
            total_size /= 1024.0
        
        return f"{total_size:.2f} TB"