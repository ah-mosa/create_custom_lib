"""
عامل الخلفية - تنفيذ المهام الطويلة
"""

import asyncio
import threading
import queue
import time
import json
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import uuid

class TaskStatus:
    """حالة المهمة"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class BackgroundTask:
    """مهمة خلفية"""
    
    def __init__(self, task_id: str, task_type: str, data: Dict[str, Any]):
        self.task_id = task_id
        self.task_type = task_type
        self.data = data
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.message = ""
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.callback_url = None
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'error': self.error
        }
    
    def update_progress(self, progress: int, message: str = ""):
        """تحديث التقدم"""
        self.progress = progress
        if message:
            self.message = message
    
    def mark_running(self):
        """وضع علامة التشغيل"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
    
    def mark_completed(self, result: Any = None):
        """وضع علامة الإكمال"""
        self.status = TaskStatus.COMPLETED
        self.progress = 100
        self.result = result
        self.completed_at = datetime.now()
    
    def mark_failed(self, error: str):
        """وضع علامة الفشل"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
    
    def mark_cancelled(self):
        """وضع علامة الإلغاء"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()

class BackgroundWorker:
    """عامل الخلفية (نمط Singleton)"""
    
    _instance = None
    _tasks = {}
    
    def __new__(cls):
        """نمط Singleton"""
        if cls._instance is None:
            cls._instance = super(BackgroundWorker, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """تهيئة العامل (تعمل مرة واحدة فقط)"""
        if self._initialized:
            return
        
        self.task_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._initialized = True
    
    def start(self):
        """بدء العامل"""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            print("✅ عامل الخلفية يعمل")
    
    def stop(self):
        """إيقاف العامل"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        self.executor.shutdown(wait=False)
        print("🛑 عامل الخلفية توقف")
    
    def _worker_loop(self):
        """حلقة عمل العامل"""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                if task:
                    self._process_task(task)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ خطأ في عامل الخلفية: {e}")
    
    def _process_task(self, task: BackgroundTask):
        """معالجة المهمة"""
        try:
            task.mark_running()
            self._tasks[task.task_id] = task
            
            # تنفيذ المهمة حسب النوع
            if task.task_type == 'scan_project':
                self._execute_scan_project(task)
            elif task.task_type == 'analyze_project':
                self._execute_analyze_project(task)
            elif task.task_type == 'create_bundles':
                self._execute_create_bundles(task)
            elif task.task_type == 'generate_report':
                self._execute_generate_report(task)
            elif task.task_type == 'cleanup_project':
                self._execute_cleanup_project(task)
            else:
                raise ValueError(f"نوع مهمة غير معروف: {task.task_type}")
                
        except Exception as e:
            task.mark_failed(str(e))
            print(f"❌ فشلت المهمة {task.task_id}: {e}")
    
    def _execute_scan_project(self, task: BackgroundTask):
        """تنفيذ مسح المشروع"""
        from src.scanner import ProjectScanner
        
        project_path = Path(task.data['project_path'])
        
        task.update_progress(10, "جاري تهيئة الماسح...")
        scanner = ProjectScanner(str(project_path))
        
        task.update_progress(30, "جاري مسح الملفات...")
        files = scanner.scan()
        
        task.update_progress(70, "جاري تحليل التبعيات...")
        import_analysis = []
        
        for file_path in files[:100]:  # تحليل أول 100 ملف فقط لأداء أفضل
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # تحليل بسيط للواردات
                imports = self._extract_imports_simple(content)
                import_analysis.append({
                    'file': str(file_path.relative_to(project_path)),
                    'imports': imports,
                    'size': file_path.stat().st_size
                })
            except:
                continue
        
        task.update_progress(100, "اكتمل المسح")
        
        result = {
            'total_files': len(files),
            'analyzed_files': len(import_analysis),
            'files': [
                {
                    'name': f.name,
                    'path': str(f.relative_to(project_path)),
                    'size': f.stat().st_size,
                    'type': f.suffix
                } for f in files[:50]  # إرجاع أول 50 ملف فقط
            ],
            'import_analysis': import_analysis,
            'project_size': sum(f.stat().st_size for f in files)
        }
        
        task.mark_completed(result)

    def _execute_analyze_project(self, task: BackgroundTask):
        """تنفيذ تحليل المشروع"""
        try:
            from src.analyzer import DependencyAnalyzer
            
            project_path = Path(task.data['project_path'])
            files_data = task.data.get('files', [])
            
            print(f"🔍 بدء تحليل المشروع: {project_path}")
            print(f"📁 عدد الملفات للتحليل: {len(files_data)}")
            
            task.update_progress(10, "جاري تهيئة المحلل...")
            analyzer = DependencyAnalyzer()
            
            task.update_progress(30, "جاري تحليل الملفات...")
            files_analysis = []
            
            # تحليل الملفات
            for i, file_info in enumerate(files_data[:50]):  # تحليل أول 50 ملف فقط لأداء أفضل
                file_path = project_path / file_info['path']
                
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        analysis = analyzer.analyze_file(file_path, content)
                        analysis['file'] = str(file_path.relative_to(project_path))
                        files_analysis.append(analysis)
                        
                        print(f"✓ تم تحليل: {file_path.name}")
                    except Exception as e:
                        print(f"⚠️ خطأ في تحليل {file_path}: {e}")
                
                # تحديث التقدم
                progress = 30 + ((i + 1) / min(len(files_data), 50)) * 50
                task.update_progress(int(progress), f"جاري تحليل الملف {i+1}/{min(len(files_data), 50)}")
            
            print(f"📊 تم تحليل {len(files_analysis)} ملف")
            
            task.update_progress(90, "جاري تجميع النتائج...")
            aggregated = analyzer.aggregate_analysis(files_analysis)
            
            # إضافة معلومات إضافية
            aggregated['total_analyzed_files'] = len(files_analysis)
            aggregated['analysis_date'] = datetime.now().isoformat()
            
            # حفظ النتائج
            output_file = project_path / 'analysis_result.json'
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(aggregated, f, ensure_ascii=False, indent=2)
                print(f"💾 تم حفظ النتائج في: {output_file}")
                print(f"📏 حجم الملف: {output_file.stat().st_size} بايت")
            except Exception as e:
                print(f"❌ فشل في حفظ النتائج: {e}")
                raise
            
            task.update_progress(100, "اكتمل التحليل")
            
            result = {
                'analysis': aggregated,
                'output_file': str(output_file),
                'total_analyzed': len(files_analysis),
                'libraries_found': len(aggregated.get('libraries', {})),
                'success': True
            }
            
            task.mark_completed(result)
            print("✅ تحليل المشروع اكتمل بنجاح")
            
        except Exception as e:
            print(f"❌ فشل كامل في تحليل المشروع: {e}")
            import traceback
            traceback.print_exc()
            task.mark_failed(str(e))


    def _execute_create_bundles(self, task: BackgroundTask):
        """تنفيذ إنشاء الحزم"""
        from src.bundler import Bundler
        
        project_path = Path(task.data['project_path'])
        analysis = task.data['analysis']
        
        task.update_progress(10, "جاري تهيئة المولد...")
        bundler = Bundler(analysis, str(project_path))
        
        task.update_progress(30, "جاري إنشاء الحزم...")
        bundles = bundler.create_bundles()
        
        task.update_progress(90, "جاري إنشاء الأرشيف...")
        
        # إنشاء ZIP للحزم
        from src.utils.file_manager import FileManager
        file_manager = FileManager()
        zip_path = file_manager.create_bundle_zip(project_path.name, bundles)
        
        task.update_progress(100, "اكتمل إنشاء الحزم")
        
        result = {
            'bundles': bundles,
            'zip_path': str(zip_path),
            'output_dir': str(bundler.output_dir),
            'total_bundles': len(bundles)
        }
        
        task.mark_completed(result)
    
    def _execute_generate_report(self, task: BackgroundTask):
        """تنفيذ إنشاء التقرير"""
        from src.reporter import ReportGenerator
        
        project_path = Path(task.data['project_path'])
        analysis = task.data['analysis']
        
        task.update_progress(20, "جاري تهيئة مولد التقارير...")
        reporter = ReportGenerator(analysis, str(project_path))
        
        task.update_progress(50, "جاري إنشاء تقرير HTML...")
        html_path = reporter.generate_html_report()
        
        task.update_progress(80, "جاري إنشاء تقرير JSON...")
        json_path = reporter.generate_json_report()
        
        task.update_progress(100, "اكتمل إنشاء التقارير")
        
        result = {
            'html_report': html_path,
            'json_report': json_path,
            'report_url': f'file://{html_path}'
        }
        
        task.mark_completed(result)
    
    def _execute_cleanup_project(self, task: BackgroundTask):
        """تنفيذ تنظيف المشروع"""
        from src.utils.file_manager import FileManager
        
        file_manager = FileManager()
        project_id = task.data['project_id']
        
        task.update_progress(30, "جاري حذف الملفات المؤقتة...")
        
        # حذف المشروع
        if file_manager.delete_project(project_id):
            task.update_progress(100, "اكتمل التنظيف")
            task.mark_completed({'deleted': True})
        else:
            task.mark_failed("فشل في حذف المشروع")
    
    def _extract_imports_simple(self, content: str) -> List[str]:
        """استخراج الواردات بطريقة مبسطة"""
        import re
        
        imports = []
        
        # أنماط الواردات
        patterns = [
            r"import\s+.*from\s+['\"]([^'\"]+)['\"]",
            r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
            r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            imports.extend(matches)
        
        return imports
    
    def submit_task(self, task_type: str, data: Dict[str, Any]) -> str:
        """إرسال مهمة جديدة"""
        task_id = str(uuid.uuid4())
        task = BackgroundTask(task_id, task_type, data)
        
        self.task_queue.put(task)
        self._tasks[task_id] = task
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """الحصول على حالة المهمة"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            return task.to_dict()
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """إلغاء مهمة"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.mark_cancelled()
                return True
        return False
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """الحصول على جميع المهام"""
        return [task.to_dict() for task in self._tasks.values()]
    
    def cleanup_old_tasks(self, older_than_hours: int = 24):
        """تنظيف المهام القديمة"""
        now = datetime.now()
        to_remove = []
        
        for task_id, task in self._tasks.items():
            age = now - task.created_at
            if age.total_seconds() > older_than_hours * 3600:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._tasks[task_id]

# وظائف مساعدة للوصول إلى Singleton
_worker_instance = None

def get_worker() -> BackgroundWorker:
    """الحصول على مثيل عامل الخلفية"""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = BackgroundWorker()
    return _worker_instance

def start_worker():
    """بدء عامل الخلفية"""
    worker = get_worker()
    worker.start()

def stop_worker():
    """إيقاف عامل الخلفية"""
    worker = get_worker()
    worker.stop()

def submit_task(task_type: str, data: Dict[str, Any]) -> str:
    """إرسال مهمة جديدة"""
    worker = get_worker()
    return worker.submit_task(task_type, data)

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """الحصول على حالة المهمة"""
    worker = get_worker()
    return worker.get_task_status(task_id)

def cancel_task(task_id: str) -> bool:
    """إلغاء مهمة"""
    worker = get_worker()
    return worker.cancel_task(task_id)

def get_all_tasks() -> List[Dict[str, Any]]:
    """الحصول على جميع المهام"""
    worker = get_worker()
    return worker.get_all_tasks()

def cleanup_old_tasks(older_than_hours: int = 24):
    """تنظيف المهام القديمة"""
    worker = get_worker()
    worker.cleanup_old_tasks(older_than_hours)