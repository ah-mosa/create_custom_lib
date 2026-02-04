"""
محلل كود JavaScript
"""

import re
from pathlib import Path
from typing import List, Dict, Set, Any, Tuple
import esprima
from collections import defaultdict
import networkx as nx

class DependencyAnalyzer:
    """فئة تحليل التبعيات"""
    
    def __init__(self):
        self.import_patterns = [
            # ES6 Imports
            (r"import\s+(?:\*\s+as\s+\w+|\{[^}]*\}|\w+)\s+from\s+['\"]([^'\"]+)['\"]", 'es6'),
            (r"import\s+['\"]([^'\"]+)['\"]", 'es6_dynamic'),
            # CommonJS Require
            (r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", 'commonjs'),
            # Dynamic Import
            (r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", 'dynamic'),
            # AMD/RequireJS
            (r"define\s*\([^)]*['\"]([^'\"]+)['\"]", 'amd'),
        ]
        
        # أنماط المكتبات الشائعة
        self.library_patterns = {
            'lodash': [r'lodash', r'lodash-es', r'lodash\.'],
            'jquery': [r'jquery', r'\$'],
            'axios': [r'axios'],
            'moment': [r'moment'],
            'react': [r'react', r'react-dom'],
            'vue': [r'vue', r'@vue/'],
            'angular': [r'@angular/', r'angular'],
            'express': [r'express'],
            'underscore': [r'underscore']
        }
        
        self.dependency_graph = nx.DiGraph()
    
    def extract_imports(self, content: str) -> List[Tuple[str, str]]:
        """استخراج عبارات الاستيراد من المحتوى"""
        imports = []
        
        for pattern, import_type in self.import_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if len(match.groups()) >= 1:
                    import_path = match.group(1)
                    imports.append((import_path, import_type))
        
        return imports
    
    def normalize_library_name(self, import_path: str) -> str:
        """تطبيع اسم المكتبة من مسار الاستيراد"""
        # إزالة المسار النسبي والتركيز على اسم المكتبة الرئيسي
        parts = import_path.split('/')
        
        # التعامل مع نماذج scoped packages
        if import_path.startswith('@'):
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
        
        # العودة بالجزء الأول إذا لم يكن مساراً نسبياً
        if parts and not parts[0].startswith('.'):
            return parts[0]
        
        return ''
    
    def identify_library(self, import_path: str) -> Tuple[str, str]:
        """تحديد المكتبة من مسار الاستيراد"""
        normalized = self.normalize_library_name(import_path)
        
        for lib_name, patterns in self.library_patterns.items():
            for pattern in patterns:
                if re.search(pattern, import_path, re.IGNORECASE) or re.search(pattern, normalized, re.IGNORECASE):
                    return lib_name, import_path
        
        # إذا لم تكن مكتبة معروفة، نعود بالاسم المطبيع
        return normalized, import_path
    
    def analyze_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """تحليل ملف واحد"""
        analysis = {
            'file': str(file_path),
            'imports': [],
            'libraries': defaultdict(list),
            'functions_used': set()
        }
        
        try:
            # استخراج الواردات
            imports = self.extract_imports(content)
            analysis['imports'] = imports
            
            # تحديد المكتبات
            for import_path, import_type in imports:
                lib_name, full_path = self.identify_library(import_path)
                if lib_name:
                    analysis['libraries'][lib_name].append({
                        'path': full_path,
                        'type': import_type,
                        'original_import': import_path
                    })
            
            # تحليل استخدام الدوال (مبسط)
            self._analyze_function_usage(content, analysis)
            
        except Exception as e:
            print(f"⚠️  خطأ في تحليل {file_path}: {e}")
        
        return analysis
    
    def _analyze_function_usage(self, content: str, analysis: Dict):
        """تحليل استخدام الدوال (تنفيذ مبسط)"""
        try:
            # استخدام esprima لتحليل AST
            ast = esprima.parseScript(content, loc=True)
            
            # البحث عن استخدام الدوال من المكتبات المعروفة
            for lib_name in analysis['libraries'].keys():
                # نمط: library.function
                pattern = rf'{lib_name}\.(\w+)'
                matches = re.finditer(pattern, content)
                for match in matches:
                    analysis['functions_used'].add(match.group(0))
        except:
            # بديل بسيط في حالة فشل التحليل
            pass
    
    def aggregate_analysis(self, files_analysis: List[Dict]) -> Dict[str, Any]:
        """تجميع نتائج التحليل من جميع الملفات"""
        aggregated = {
            'total_files': len(files_analysis),
            'libraries': defaultdict(lambda: {
                'count': 0,
                'files': set(),
                'imports': set(),
                'functions_used': set()
            }),
            'files_by_library': defaultdict(list),
            'total_functions': 0
        }
        
        for analysis in files_analysis:
            for lib_name, imports in analysis['libraries'].items():
                lib_data = aggregated['libraries'][lib_name]
                lib_data['count'] += 1
                lib_data['files'].add(analysis['file'])
                
                for imp in imports:
                    lib_data['imports'].add(imp['original_import'])
                
                lib_data['functions_used'].update(analysis['functions_used'])
                
                aggregated['files_by_library'][lib_name].append(analysis['file'])
        
        # تحويل المجموعات إلى قوائم للتسلسل
        for lib_name, data in aggregated['libraries'].items():
            data['files'] = list(data['files'])
            data['imports'] = list(data['imports'])
            data['functions_used'] = list(data['functions_used'])
            aggregated['total_functions'] += len(data['functions_used'])
        
        # إنشاء توصيات
        aggregated['recommendations'] = self._generate_recommendations(aggregated)
        
        return aggregated
    
    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """توليد توصيات بناءً على التحليل"""
        recommendations = []
        
        for lib_name, data in analysis['libraries'].items():
            # التحقق من الاستخدام المحدود
            if data['count'] == 1:
                recommendations.append({
                    'type': 'warning',
                    'library': lib_name,
                    'message': f'المكتبة {lib_name} مستخدمة في ملف واحد فقط. فكر في استبدالها بمكتبة أصغر أو دالة مخصصة.',
                    'files': data['files']
                })
            
            # التحقق من المكتبات الكبيرة ذات الاستخدام المحدود
            large_libs = ['lodash', 'moment', 'jquery']
            if lib_name in large_libs and len(data['functions_used']) < 3:
                recommendations.append({
                    'type': 'suggestion',
                    'library': lib_name,
                    'message': f'المكتبة {lib_name} كبيرة ولكنك تستخدم {len(data["functions_used"])} دوال فقط. يمكن إنشاء حزمة مخصصة أصغر.',
                    'functions': data['functions_used']
                })
        
        return recommendations