"""
واجهة سطر الأوامر
"""

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
import json
import asyncio
import webbrowser
from pathlib import Path

from .scanner import ProjectScanner
from .analyzer import DependencyAnalyzer
from .bundler import Bundler
from .reporter import ReportGenerator
from .webui import start_web_server

console = Console()

@click.group()
def cli():
    """أداة إنشاء إصدارات مخصصة من مكتبات JavaScript"""
    pass

@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--output', '-o', default='analysis.json', help='مسار حفظ النتائج')
def scan(project_path, output):
    """مسح مشروع JavaScript وتحليل التبعيات"""
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]جاري مسح المشروع...", total=None)
            
            # مسح المشروع
            scanner = ProjectScanner(project_path)
            files = scanner.scan()
            
            progress.update(task, description="[cyan]جاري تحليل الملفات...")
            
            # تحليل الملفات
            analyzer = DependencyAnalyzer()
            files_analysis = []
            
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    analysis = analyzer.analyze_file(file_path, content)
                    files_analysis.append(analysis)
                except Exception as e:
                    console.print(f"[yellow]⚠️  تخطي {file_path.name}: {e}[/yellow]")
                    continue
            
            progress.update(task, description="[cyan]جاري تجميع النتائج...")
            
            # تجميع النتائج
            aggregated = analyzer.aggregate_analysis(files_analysis)
            
            # حفظ النتائج
            output_path = Path(output)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(aggregated, f, ensure_ascii=False, indent=2)
            
            progress.update(task, description="[green]✅ اكتمل التحليل!")
        
        # عرض النتائج
        console.print(Panel.fit(
            f"[bold green]✅ تم تحليل المشروع بنجاح![/bold green]\n\n"
            f"📁 الملفات الممسوحة: [cyan]{aggregated['total_files']}[/cyan]\n"
            f"📦 المكتبات المكتشفة: [cyan]{len(aggregated['libraries'])}[/cyan]",
            title="نتائج التحليل",
            border_style="green"
        ))
        
        # عرض جدول بالمكتبات
        if aggregated['libraries']:
            table = Table(title="المكتبات المكتشفة", show_lines=True)
            table.add_column("المكتبة", style="cyan", no_wrap=True)
            table.add_column("عدد الملفات", style="magenta")
            table.add_column("الدوال المستخدمة", style="green")
            table.add_column("مسار الاستيراد", style="yellow")
            
            for lib_name, data in aggregated['libraries'].items():
                functions = data['functions_used'][:3]  # عرض أول 3 دوال فقط
                functions_str = ', '.join(functions) + ('...' if len(data['functions_used']) > 3 else '')
                
                imports = data['imports'][:2]  # عرض أول مسارين فقط
                imports_str = ', '.join(imports) + ('...' if len(data['imports']) > 2 else '')
                
                table.add_row(
                    lib_name,
                    str(data['count']),
                    functions_str or "جميع الدوال",
                    imports_str
                )
            
            console.print(table)
        
        console.print(f"\n📄 تم حفظ النتائج في: [underline blue]{output_path}[/underline blue]")
        
    except Exception as e:
        console.print(f"[red]❌ خطأ: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--analysis', '-a', default='analysis.json', help='ملف تحليل سابق')
@click.option('--output-dir', '-o', default='custom_bundles', help='مجلد الحفظ')
def bundle(project_path, analysis, output_dir):
    """إنشاء إصدارات مخصصة من المكتبات"""
    
    try:
        # تحميل نتائج التحليل
        analysis_path = Path(analysis)
        if not analysis_path.exists():
            console.print(f"[red]❌ ملف التحليل غير موجود: {analysis}[/red]")
            raise click.Abort()
        
        with open(analysis_path, 'r', encoding='utf-8') as f:
            aggregated = json.load(f)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]جاري إنشاء الحزم المخصصة...", total=len(aggregated['libraries']))
            
            # إنشاء الحزم
            bundler = Bundler(aggregated, project_path)
            bundles = bundler.create_bundles()
            
            for lib_name in aggregated['libraries'].keys():
                progress.update(task, advance=1, description=f"[cyan]جاري معالجة {lib_name}...")
            
            progress.update(task, description="[green]✅ اكتمل إنشاء الحزم!")
        
        # عرض النتائج
        console.print(Panel.fit(
            f"[bold green]✅ تم إنشاء الحزم بنجاح![/bold green]\n\n"
            f"📦 عدد الحزم المنشأة: [cyan]{len(bundles)}[/cyan]\n"
            f"📁 مجلد الحفظ: [cyan]{bundler.output_dir}[/cyan]",
            title="نتائج التجميع",
            border_style="green"
        ))
        
        # عرض الحزم المنشأة
        if bundles:
            table = Table(title="الحزم المنشأة", show_lines=True)
            table.add_column("المكتبة", style="cyan")
            table.add_column("مسار الحزمة", style="blue")
            table.add_column("الحجم", style="magenta")
            
            for lib_name, bundle_path in bundles.items():
                bundle_file = Path(bundle_path)
                if bundle_file.exists():
                    size = bundle_file.stat().st_size
                    size_str = f"{size / 1024:.1f} ك.ب" if size < 1024*1024 else f"{size / (1024*1024):.1f} م.ب"
                    table.add_row(lib_name, str(bundle_file), size_str)
            
            console.print(table)
        
        console.print(f"\n💡 يمكنك استخدام هذه الحزم بدلاً من المكتبات الأصلية لتقليل حجم المشروع.")
        
    except Exception as e:
        console.print(f"[red]❌ خطأ: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--analysis', '-a', default='analysis.json', help='ملف تحليل سابق')
@click.option('--open-browser', '-o', is_flag=True, help='فتح التقرير في المتصفح')
def report(project_path, analysis, open_browser):
    """إنشاء تقرير تفاعلي"""
    
    try:
        # تحميل نتائج التحليل
        analysis_path = Path(analysis)
        if not analysis_path.exists():
            console.print(f"[red]❌ ملف التحليل غير موجود: {analysis}[/red]")
            raise click.Abort()
        
        with open(analysis_path, 'r', encoding='utf-8') as f:
            aggregated = json.load(f)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]جاري إنشاء التقرير...", total=None)
            
            # إنشاء التقرير
            reporter = ReportGenerator(aggregated, project_path)
            html_path = reporter.generate_html_report()
            json_path = reporter.generate_json_report()
            
            progress.update(task, description="[green]✅ اكتمل إنشاء التقرير!")
        
        # عرض النتائج
        console.print(Panel.fit(
            f"[bold green]✅ تم إنشاء التقارير بنجاح![/bold green]\n\n"
            f"📊 تقرير HTML: [underline blue]{html_path}[/underline blue]\n"
            f"📄 تقرير JSON: [underline blue]{json_path}[/underline blue]",
            title="التقارير المنشأة",
            border_style="green"
        ))
        
        # فتح التقرير في المتصفح إذا طلب المستخدم
        if open_browser:
            webbrowser.open(f'file://{html_path}')
            console.print("\n🌐 يتم فتح التقرير في المتصفح الافتراضي...")
        
        console.print(f"\n💡 يحتوي التقرير على تحليل مفصل واستخدامات المكتبات وتوصيات للتحسين.")
        
    except Exception as e:
        console.print(f"[red]❌ خطأ: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.option('--host', default='127.0.0.1', help='عنوان الخادم')
@click.option('--port', default=8080, help='منفذ الخادم')
@click.option('--open-browser', '-o', is_flag=True, help='فتح المتصفح تلقائياً')
def web(host, port, open_browser):
    """تشغيل واجهة الويب"""
    
    try:
        if open_browser:
            # فتح المتصفح بعد تأخير بسيط
            import threading
            import time
            
            def open_browser_delayed():
                time.sleep(2)
                webbrowser.open(f'http://{host}:{port}')
            
            threading.Thread(target=open_browser_delayed, daemon=True).start()
        
        # تشغيل خادم الويب
        start_web_server(host, port)
        
    except KeyboardInterrupt:
        console.print("\n🛑 تم إيقاف خادم الويب")
    except Exception as e:
        console.print(f"[red]❌ خطأ: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
def full_analysis(project_path):
    """إجراء تحليل كامل وإنشاء حزم وتقارير"""
    
    try:
        # المسح
        console.print("[bold cyan]🚀 بدء التحليل الكامل للمشروع...[/bold cyan]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task1 = progress.add_task("[cyan]المرحلة 1: مسح المشروع...", total=None)
            scanner = ProjectScanner(project_path)
            files = scanner.scan()
            progress.update(task1, description="[green]✅ اكتمل مسح المشروع")
            
            task2 = progress.add_task("[cyan]المرحلة 2: تحليل الملفات...", total=None)
            analyzer = DependencyAnalyzer()
            files_analysis = []
            
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    analysis = analyzer.analyze_file(file_path, content)
                    files_analysis.append(analysis)
                except:
                    continue
            
            aggregated = analyzer.aggregate_analysis(files_analysis)
            progress.update(task2, description="[green]✅ اكتمل تحليل الملفات")
            
            # حفظ التحليل
            with open('analysis.json', 'w', encoding='utf-8') as f:
                json.dump(aggregated, f, ensure_ascii=False, indent=2)
            
            task3 = progress.add_task("[cyan]المرحلة 3: إنشاء الحزم المخصصة...", total=len(aggregated['libraries']))
            bundler = Bundler(aggregated, project_path)
            bundles = bundler.create_bundles()
            progress.update(task3, description="[green]✅ اكتمل إنشاء الحزم")
            
            task4 = progress.add_task("[cyan]المرحلة 4: إنشاء التقارير...", total=None)
            reporter = ReportGenerator(aggregated, project_path)
            html_path = reporter.generate_html_report()
            json_path = reporter.generate_json_report()
            progress.update(task4, description="[green]✅ اكتمل إنشاء التقارير")
        
        # عرض ملخص النتائج
        console.print(Panel.fit(
            f"[bold green]🎉 اكتمل التحليل الكامل بنجاح![/bold green]\n\n"
            f"📊 ملخص النتائج:\n"
            f"  📁 الملفات الممسوحة: {aggregated['total_files']}\n"
            f"  📦 المكتبات المكتشفة: {len(aggregated['libraries'])}\n"
            f"  🛠️  الحزم المنشأة: {len(bundles)}\n"
            f"  📄 التقارير المنشأة: 2 (HTML وJSON)",
            title="النتائج النهائية",
            border_style="green"
        ))
        
        # عرض خطوات المتابعة
        console.print(Panel.fit(
            f"[bold cyan]📝 خطوات المتابعة:[/bold cyan]\n\n"
            f"1. 📊 عرض التقرير التفاعلي:\n"
            f"   [blue]python main.py report {project_path} --open-browser[/blue]\n\n"
            f"2. 🌐 استخدام واجهة الويب:\n"
            f"   [blue]python main.py web[/blue]\n\n"
            f"3. 📦 استبدال المكتبات الأصلية بالحزم المخصصة",
            title="التوصيات",
            border_style="blue"
        ))
        
    except Exception as e:
        console.print(f"[red]❌ خطأ: {e}[/red]")
        raise click.Abort()

@cli.command()
def info():
    """عرض معلومات عن الأداة"""
    
    console.print(Panel.fit(
        "[bold cyan]🚀 JS Custom Bundler[/bold cyan]\n\n"
        "أداة متكاملة لتحليل مشاريع JavaScript وإنشاء إصدارات مخصصة\n"
        "من المكتبات تحتوي فقط على الأكواد المستخدمة فعلياً.\n\n"
        "[bold yellow]الميزات الرئيسية:[/bold yellow]\n"
        "• 🔍 مسح وتحليل تلقائي للمشاريع\n"
        "• 📦 إنشاء مكتبات مخصصة (Tree Shaking)\n"
        "• 📊 تقارير تفاعلية مع رسوم بيانية\n"
        "• 🌐 واجهة ويب محلية سهلة الاستخدام\n"
        "• 💾 خفيفة الوزن، تعمل من فلاش ميموري\n\n"
        "[bold green]الاستخدام:[/bold green]\n"
        "  python main.py [COMMAND] [OPTIONS]\n\n"
        "[bold blue]الأوامر المتاحة:[/bold blue]\n"
        "  scan        مسح وتحليل المشروع\n"
        "  bundle      إنشاء حزم مخصصة\n"
        "  report      إنشاء تقارير تفاعلية\n"
        "  web         تشغيل واجهة الويب\n"
        "  full-analysis   تحليل كامل شامل\n"
        "  info        عرض هذه المعلومات",
        title="معلومات الأداة",
        border_style="cyan"
    ))

if __name__ == "__main__":
    cli()