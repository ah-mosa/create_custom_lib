"""
مولد التقارير
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import jinja2
import webbrowser

class ReportGenerator:
    """فئة توليد التقارير"""
    
    def __init__(self, analysis: Dict[str, Any], project_path: str):
        self.analysis = analysis
        self.project_path = Path(project_path)
        self.output_dir = self.project_path / 'reports'
        self.output_dir.mkdir(exist_ok=True)
        
        # إعداد قوالب Jinja2
        template_dir = Path(__file__).parent.parent / 'templates'
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
    
    def generate_json_report(self) -> str:
        """إنشاء تقرير بصيغة JSON"""
        report_data = {
            'metadata': {
                'project_path': str(self.project_path),
                'generated_at': datetime.now().isoformat(),
                'total_files': self.analysis['total_files'],
                'total_libraries': len(self.analysis['libraries'])
            },
            'analysis': self.analysis,
            'recommendations': self.analysis.get('recommendations', [])
        }
        
        report_path = self.output_dir / 'analysis_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return str(report_path)
    
    def generate_html_report(self) -> str:
        """إنشاء تقرير HTML تفاعلي"""
        # تحضير البيانات للقالب
        template_data = {
            'project_name': self.project_path.name,
            'project_path': str(self.project_path),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_files': self.analysis['total_files'],
            'total_libraries': len(self.analysis['libraries']),
            'libraries': self.analysis['libraries'],
            'files_by_library': self.analysis['files_by_library'],
            'total_functions': self.analysis.get('total_functions', 0),
            'recommendations': self.analysis.get('recommendations', [])
        }
        
        # تحميل القالب وتوليد HTML
        try:
            template = self.env.get_template('report_template.html')
            html_content = template.render(**template_data)
        except:
            # إذا لم يوجد قالب، أنشئ واحداً بسيطاً
            html_content = self._create_simple_report(template_data)
        
        report_path = self.output_dir / 'analysis_report.html'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(report_path)
    
    def _create_simple_report(self, data: Dict) -> str:
        """إنشاء تقرير HTML بسيط"""
        html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تقرير تحليل - {data['project_name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        .library {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .function {{ display: inline-block; background: #e3f2fd; padding: 5px 10px; margin: 2px; border-radius: 3px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>📊 تقرير تحليل المشروع: {data['project_name']}</h1>
    <p><strong>تاريخ الإنشاء:</strong> {data['generated_at']}</p>
    <p><strong>إجمالي الملفات:</strong> {data['total_files']}</p>
    <p><strong>المكتبات المكتشفة:</strong> {data['total_libraries']}</p>
    <p><strong>الدوال المستخدمة:</strong> {data['total_functions']}</p>
    
    <h2>📦 المكتبات المكتشفة</h2>
    {self._generate_libraries_html(data['libraries'])}
    
    <h2>💡 التوصيات</h2>
    {self._generate_recommendations_html(data['recommendations'])}
</body>
</html>"""
        
        return html
    
    def _generate_libraries_html(self, libraries: Dict) -> str:
        """توليد HTML للمكتبات"""
        if not libraries:
            return "<p>لم يتم اكتشاف أي مكتبات</p>"
        
        html = ""
        for lib_name, data in libraries.items():
            functions_html = "".join([f'<span class="function">{func}</span>' for func in data.get('functions_used', [])])
            html += f"""
            <div class="library">
                <h3>{lib_name}</h3>
                <p><strong>عدد الملفات:</strong> {data['count']}</p>
                <p><strong>الدوال المستخدمة:</strong> {len(data.get('functions_used', []))}</p>
                <div>{functions_html}</div>
            </div>
            """
        
        return html
    
    def _generate_recommendations_html(self, recommendations: List[Dict]) -> str:
        """توليد HTML للتوصيات"""
        if not recommendations:
            return "<p>لا توجد توصيات حالياً</p>"
        
        html = "<ul>"
        for rec in recommendations:
            html += f"<li><strong>{rec['library']}:</strong> {rec['message']}</li>"
        html += "</ul>"
        
        return html
    
    def open_report(self):
        """فتح التقرير في المتصفح الافتراضي"""
        html_path = self.generate_html_report()
        webbrowser.open(f'file://{html_path}')