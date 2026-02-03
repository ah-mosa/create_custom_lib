"""
مدير الملفات - التعامل مع الملفات والمجلدات
"""

import os
import json
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import aiofiles
import asyncio
from datetime import datetime
import hashlib

class FileManager:
    """فئة إدارة الملفات والمجلدات"""
    
    def __init__(self):
        self.base_dir = Path.cwd()
        self.uploads_dir = self.base_dir / 'uploads'
        self.projects_dir = self.base_dir / 'projects'
        self.bundles_dir = self.base_dir / 'bundles'
        self.reports_dir = self.base_dir / 'reports'
        
        # إنشاء المجلدات
        for directory in [self.uploads_dir, self.projects_dir, 
                         self.bundles_dir, self.reports_dir]:
            directory.mkdir(exist_ok=True)
    
    def validate_path(self, path: str) -> bool:
        """التحقق من أمان المسار"""
        try:
            resolved = Path(path).resolve()
            # التحقق من أن المسار داخل مجلد المشروع
            return resolved.is_relative_to(self.base_dir)
        except:
            return False
    
    async def save_uploaded_file(self, file, filename: str) -> Path:
        """حفظ ملف مرفوع"""
        file_path = self.uploads_dir / filename
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        return file_path
    
    async def extract_zip(self, zip_path: Path, extract_to: Optional[Path] = None) -> Path:
        """استخراج ملف ZIP"""
        if extract_to is None:
            extract_to = self.projects_dir / zip_path.stem
        
        extract_to.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        return extract_to
    
    def create_project_structure(self, project_name: str) -> Path:
        """إنشاء هيكل مشروع جديد"""
        project_path = self.projects_dir / project_name
        project_path.mkdir(exist_ok=True)
        
        # إنشاء مجلدات فرعية
        (project_path / 'src').mkdir(exist_ok=True)
        (project_path / 'bundles').mkdir(exist_ok=True)
        (project_path / 'reports').mkdir(exist_ok=True)
        
        return project_path
    
    def scan_project_files(self, project_path: Path, extensions: List[str] = None) -> List[Path]:
        """مسح ملفات المشروع"""
        if extensions is None:
            extensions = ['.js', '.ts', '.jsx', '.tsx', '.json', '.html']
        
        files = []
        
        for ext in extensions:
            files.extend(project_path.rglob(f'*{ext}'))
        
        # استبعاد node_modules والمجلدات الأخرى
        excluded_dirs = {'node_modules', '.git', 'dist', 'build', '.cache'}
        files = [
            f for f in files 
            if not any(excluded in f.parts for excluded in excluded_dirs)
        ]
        
        return files
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """الحصول على معلومات الملف"""
        stat = file_path.stat()
        
        return {
            'name': file_path.name,
            'path': str(file_path.relative_to(self.base_dir)),
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'extension': file_path.suffix,
            'is_dir': file_path.is_dir()
        }
    
    def get_directory_tree(self, directory: Path, max_depth: int = 3) -> Dict[str, Any]:
        """الحصول على هيكل المجلد"""
        if not directory.is_dir():
            return {}
        
        tree = {
            'name': directory.name,
            'path': str(directory.relative_to(self.base_dir)),
            'type': 'directory',
            'children': []
        }
        
        if max_depth > 0:
            try:
                for item in directory.iterdir():
                    if item.is_dir():
                        tree['children'].append(
                            self.get_directory_tree(item, max_depth - 1)
                        )
                    else:
                        tree['children'].append({
                            'name': item.name,
                            'path': str(item.relative_to(self.base_dir)),
                            'type': 'file',
                            'size': item.stat().st_size,
                            'extension': item.suffix
                        })
            except PermissionError:
                pass
        
        return tree
    
    async def read_file_content(self, file_path: Path, max_size: int = 1024 * 1024) -> str:
        """قراءة محتوى الملف"""
        if not file_path.exists() or file_path.stat().st_size > max_size:
            return ""
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return await f.read()
    
    def delete_project(self, project_id: str) -> bool:
        """حذف مشروع"""
        project_path = self.projects_dir / project_id
        if project_path.exists() and project_path.is_dir():
            shutil.rmtree(project_path)
            return True
        return False
    
    def get_project_size(self, project_id: str) -> int:
        """الحصول على حجم المشروع"""
        project_path = self.projects_dir / project_id
        if not project_path.exists():
            return 0
        
        total_size = 0
        for file in project_path.rglob('*'):
            if file.is_file():
                total_size += file.stat().st_size
        
        return total_size
    
    def create_bundle_zip(self, project_id: str, bundles: Dict[str, str]) -> Path:
        """إنشاء ملف ZIP للحزم"""
        zip_path = self.bundles_dir / f'{project_id}_bundles.zip'
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for lib_name, bundle_path in bundles.items():
                bundle_file = Path(bundle_path)
                if bundle_file.exists():
                    zipf.write(bundle_file, f'bundles/{bundle_file.name}')
        
        return zip_path