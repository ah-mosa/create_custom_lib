"""
واجهة سطر أوامر لأداة مسح مشاريع الويب
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# استيراد الوحدات
try:
    from scanner import scan_project
    from bundler import create_custom_bundle
    from utils import setup_logger, validate_path, format_file_size, save_json
    from config import get_config, Config
except ImportError:
    # استيراد بديل للتوافق
    sys.path.append('.')
    from scanner import scan_project
    from bundler import create_custom_bundle
    from utils import setup_logger, validate_path, format_file_size, save_json
    from config import get_config, Config

logger = setup_logger('cli')

class CLI:
    """واجهة سطر أوامر"""
    
    def __init__(self):
        self.config = get_config()
        
    def run(self):
        """تشغيل الواجهة"""
        parser = argparse.ArgumentParser(
            description='أداة مسح مشاريع الويب وإنشاء الحزم المخصصة',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
أمثلة:
  %(prog)s scan /path/to/project
  %(prog)s scan /path/to/project --output scan_result.json
  %(prog)s bundle scan_result.json
  %(prog)s bundle --libraries jquery bootstrap tailwind
  %(prog)s interactive
            """
        )
        
        subparsers = parser.add_subparsers(dest='command', help='الأوامر المتاحة')
        
        # أمر المسح
        scan_parser = subparsers.add_parser('scan', help='مسح مشروع ويب')
        scan_parser.add_argument('path', help='مسار المشروع المراد مسحه')
        scan_parser.add_argument('-o', '--output', help='ملف لحفظ النتائج')
        scan_parser.add_argument('-v', '--verbose', action='store_true', help='عرض تفاصيل أكثر')
        scan_parser.add_argument('--no-html', action='store_true', help='تجاهل ملفات HTML')
        scan_parser.add_argument('--no-css', action='store_true', help='تجاهل ملفات CSS')
        scan_parser.add_argument('--no-js', action='store_true', help='تجاهل ملفات JavaScript')
        scan_parser.add_argument('--no-php', action='store_true', help='تجاهل ملفات PHP')
        
        # أمر إنشاء الحزمة
        bundle_parser = subparsers.add_parser('bundle', help='إنشاء حزمة مخصصة')
        bundle_group = bundle_parser.add_mutually_exclusive_group(required=True)
        bundle_group.add_argument('-s', '--scan-file', help='ملف نتائج المسح')
        bundle_group.add_argument('-l', '--libraries', nargs='+', help='قائمة المكتبات')
        bundle_parser.add_argument('-o', '--output-dir', help='مجلد الإخراج')
        bundle_parser.add_argument('-n', '--name', help='اسم الحزمة')
        bundle_parser.add_argument('--no-zip', action='store_true', help='عدم إنشاء ملف مضغوط')
        
        # أمر الوضع التفاعلي
        subparsers.add_parser('interactive', help='الوضع التفاعلي')
        
        # أمر عرض الإعدادات
        subparsers.add_parser('config', help='عرض الإعدادات الحالية')
        
        # أمر الإصدار
        subparsers.add_parser('version', help='عرض إصدار الأداة')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            sys.exit(1)
        
        # تنفيذ الأمر
        if args.command == 'scan':
            self.handle_scan(args)
        elif args.command == 'bundle':
            self.handle_bundle(args)
        elif args.command == 'interactive':
            self.handle_interactive()
        elif args.command == 'config':
            self.handle_config()
        elif args.command == 'version':
            self.handle_version()
    
    def handle_scan(self, args):
        """معالجة أمر المسح"""
        print(f"🔍 جاري مسح المشروع: {args.path}")
        
        # التحقق من صحة المسار
        is_valid, message = validate_path(args.path)
        if not is_valid:
            print(f"❌ خطأ: {message}")
            sys.exit(1)
        
        try:
            # إجراء المسح
            results = scan_project(args.path)
            
            # حفظ النتائج إذا طُلب
            if args.output:
                output_path = Path(args.output)
                save_json(results, output_path)
                print(f"✅ تم حفظ النتائج في: {output_path}")
            
            # عرض النتائج
            self.display_scan_results(results, args.verbose)
            
        except Exception as e:
            print(f"❌ خطأ في المسح: {e}")
            logger.exception("فشل المسح")
            sys.exit(1)
    
    def display_scan_results(self, results: Dict, verbose: bool = False):
        """عرض نتائج المسح"""
        print("\n" + "="*50)
        print("📊 نتائج المسح")
        print("="*50)
        
        # المعلومات الأساسية
        print(f"📁 المشروع: {results.get('project_path', 'غير معروف')}")
        print(f"🆔 معرف المسح: {results.get('scan_id', 'غير معروف')}")
        print(f"⏱️  مدة المسح: {results.get('scan_duration', 'غير معروف')}")
        print(f"📦 حجم المشروع: {results.get('size', {}).get('formatted', '0 B')}")
        print(f"📄 الملفات الممسوحة: {results.get('files', {}).get('scanned', 0)}")
        
        # المكتبات المكتشفة
        print("\n📚 المكتبات المكتشفة:")
        
        # مكتبات JavaScript
        js_libs = results.get('dependencies', {}).get('javascript', [])
        if js_libs:
            print(f"  JavaScript ({len(js_libs)}):")
            for lib in js_libs[:5]:  # عرض أول 5 فقط
                print(f"    • {lib}")
            if len(js_libs) > 5:
                print(f"    • و {len(js_libs) - 5} أخرى...")
        
        # مكتبات CSS
        css_libs = results.get('dependencies', {}).get('css', [])
        if css_libs:
            print(f"  CSS ({len(css_libs)}):")
            for lib in css_libs:
                print(f"    • {lib}")
        
        # مكتبات خاصة
        detected = results.get('detected_libraries', {})
        if any(detected.values()):
            print("\n🎯 المكتبات الخاصة:")
            for lib_name, lib_data in detected.items():
                if lib_data.get('files'):
                    version = lib_data.get('version', 'غير معروف')
                    files_count = len(lib_data.get('files', []))
                    print(f"  • {lib_name.title()} (v{version}) - في {files_count} ملف")
        
        # روابط CDN
        cdn_links = results.get('cdn_links', [])
        if cdn_links:
            print(f"\n🌐 روابط CDN ({len(cdn_links)}):")
            for link in cdn_links[:3]:  # عرض أول 3 فقط
                print(f"  • {link}")
            if len(cdn_links) > 3:
                print(f"  • و {len(cdn_links) - 3} أخرى...")
        
        # التحذيرات والأخطاء
        warnings = results.get('warnings', [])
        if warnings:
            print(f"\n⚠️  التحذيرات ({len(warnings)}):")
            for warning in warnings[:3]:
                print(f"  • {warning}")
        
        errors = results.get('errors', [])
        if errors:
            print(f"\n❌ الأخطاء ({len(errors)}):")
            for error in errors[:3]:
                print(f"  • {error}")
        
        # تفاصيل إضافية إذا كان الوضع التفصيلي
        if verbose:
            print("\n📈 تفاصيل إضافية:")
            
            # إحصائيات الملفات
            file_types = results.get('file_types', {})
            if file_types:
                print("  أنواع الملفات:")
                for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"    • {ext}: {count}")
            
            # أدوات المشروع
            project_tools = results.get('project_tools', [])
            if project_tools:
                print(f"  أدوات المشروع: {', '.join(project_tools)}")
        
        print("="*50 + "\n")
        
        # اقتراح إنشاء حزمة
        total_deps = sum(len(deps) for deps in results.get('dependencies', {}).values())
        if total_deps > 0:
            print("💡 يمكنك إنشاء حزمة مخصصة باستخدام الأمر:")
            print(f"  python cli.py bundle --scan-file {'نتائج_المسح.json' if args.output else 'ملف_النتائج'}")
    
    def handle_bundle(self, args):
        """معالجة أمر إنشاء الحزمة"""
        print("📦 جاري إنشاء الحزمة المخصصة...")
        
        try:
            if args.scan_file:
                # تحميل نتائج المسح من ملف
                scan_file = Path(args.scan_file)
                if not scan_file.exists():
                    print(f"❌ ملف النتائج غير موجود: {scan_file}")
                    sys.exit(1)
                
                with open(scan_file, 'r', encoding='utf-8') as f:
                    scan_results = json.load(f)
                
                print(f"📄 تم تحميل نتائج مسح من: {scan_file}")
                
            elif args.libraries:
                # إنشاء نتائج مسح افتراضية من قائمة المكتبات
                scan_results = {
                    'scan_id': f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'project_path': 'مشروع يدوي',
                    'scan_end': datetime.now().isoformat(),
                    'dependencies': {
                        'javascript': [lib for lib in args.libraries if not self._is_css_library(lib)],
                        'css': [lib for lib in args.libraries if self._is_css_library(lib)]
                    },
                    'detected_libraries': {},
                    'summary': {
                        'total_dependencies': len(args.libraries),
                        'project_size': '0 B'
                    }
                }
                
                # إضافة المكتبات إلى detected_libraries
                for lib in args.libraries:
                    scan_results['detected_libraries'][lib] = {
                        'version': None,
                        'files': []
                    }
                
                print(f"📚 المكتبات المحددة: {', '.join(args.libraries)}")
            
            # إنشاء الحزمة
            bundle_results = create_custom_bundle(
                scan_results,
                args.output_dir
            )
            
            # عرض النتائج
            self.display_bundle_results(bundle_results)
            
        except Exception as e:
            print(f"❌ خطأ في إنشاء الحزمة: {e}")
            logger.exception("فشل إنشاء الحزمة")
            sys.exit(1)
    
    def display_bundle_results(self, results: Dict):
        """عرض نتائج إنشاء الحزمة"""
        print("\n" + "="*50)
        print("🎁 نتائج الحزمة")
        print("="*50)
        
        # المعلومات الأساسية
        print(f"🆔 معرف الحزمة: {results.get('bundle_id', 'غير معروف')}")
        print(f"📁 موقع الحزمة: {results.get('bundle_path', 'غير معروف')}")
        print(f"📦 حجم الحزمة: {results.get('total_size_formatted', '0 B')}")
        
        # المكتبات المضمنة
        libraries = results.get('libraries', [])
        if libraries:
            print(f"\n📚 المكتبات المضمنة ({len(libraries)}):")
            
            for lib in libraries:
                status_icon = '✅' if lib.get('status') == 'downloaded' else '⚠️'
                version = lib.get('version', 'أحدث')
                print(f"  {status_icon} {lib['name'].title()} (v{version}) - {lib['type']}")
        
        # الملفات المنشأة
        files_created = results.get('files_created', [])
        if files_created:
            print(f"\n📄 الملفات المنشأة ({len(files_created)}):")
            for file in files_created:
                print(f"  • {file}")
        
        # ملف ZIP إذا تم إنشاؤه
        zip_file = results.get('zip_file')
        if zip_file:
            print(f"\n🗜️  الأرشيف المضغوط: {zip_file}")
        
        # التحذيرات والأخطاء
        warnings = results.get('warnings', [])
        if warnings:
            print(f"\n⚠️  التحذيرات ({len(warnings)}):")
            for warning in warnings[:3]:
                print(f"  • {warning}")
        
        errors = results.get('errors', [])
        if errors:
            print(f"\n❌ الأخطاء ({len(errors)}):")
            for error in errors:
                print(f"  • {error}")
        
        print("="*50 + "\n")
        
        # تعليمات الاستخدام
        print("💡 تعليمات الاستخدام:")
        print("1. انسخ مجلد الحزمة إلى مشروعك")
        print("2. أضف الروابط إلى ملفات HTML:")
        print("   <!-- CSS -->")
        print("   <link rel=\"stylesheet\" href=\"css/bootstrap.min.css\">")
        print("   <!-- JavaScript -->")
        print("   <script src=\"js/jquery.min.js\"></script>")
        
        if zip_file and Path(zip_file).exists():
            print(f"\n📥 يمكنك تحميل الحزمة من: {zip_file}")
    
    def handle_interactive(self):
        """الوضع التفاعلي"""
        print("🎮 الوضع التفاعلي - أداة مسح مشاريع الويب")
        print("="*50)
        
        while True:
            print("\nالأوامر المتاحة:")
            print("  1. مسح مشروع")
            print("  2. إنشاء حزمة من نتائج مسح")
            print("  3. إنشاء حزمة يدوياً")
            print("  4. عرض الإعدادات")
            print("  5. الخروج")
            
            choice = input("\nاختر رقم الأمر (1-5): ").strip()
            
            if choice == '1':
                self.interactive_scan()
            elif choice == '2':
                self.interactive_bundle_from_scan()
            elif choice == '3':
                self.interactive_bundle_manual()
            elif choice == '4':
                self.handle_config()
            elif choice == '5':
                print("👋 مع السلامة!")
                break
            else:
                print("❌ اختيار غير صالح، حاول مرة أخرى")
    
    def interactive_scan(self):
        """المسح التفاعلي"""
        print("\n" + "="*50)
        print("🔍 المسح التفاعلي")
        
        path = input("أدخل مسار المشروع: ").strip()
        if not path:
            print("❌ يجب إدخال مسار المشروع")
            return
        
        # التحقق من صحة المسار
        is_valid, message = validate_path(path)
        if not is_valid:
            print(f"❌ {message}")
            return
        
        output_file = input("ملف لحفظ النتائج (اختياري): ").strip()
        
        print("\n⚙️  إعدادات المسح:")
        print("  1. مسح كامل (افتراضي)")
        print("  2. تخصيص الإعدادات")
        
        scan_choice = input("اختر الإعدادات (1-2): ").strip()
        
        # إعدادات المسح
        args = type('Args', (), {
            'path': path,
            'output': output_file if output_file else None,
            'verbose': True,
            'no_html': False,
            'no_css': False,
            'no_js': False,
            'no_php': False
        })()
        
        if scan_choice == '2':
            print("\n📊 تخصيص أنواع الملفات:")
            args.no_html = input("تجاهل HTML؟ (y/N): ").lower() == 'y'
            args.no_css = input("تجاهل CSS؟ (y/N): ").lower() == 'y'
            args.no_js = input("تجاهل JavaScript؟ (y/N): ").lower() == 'y'
            args.no_php = input("تجاهل PHP؟ (y/N): ").lower() == 'y'
        
        self.handle_scan(args)
    
    def interactive_bundle_from_scan(self):
        """إنشاء حزمة من نتائج مسح تفاعلي"""
        print("\n" + "="*50)
        print("📦 إنشاء حزمة من نتائج مسح")
        
        scan_file = input("أدخل مسار ملف نتائج المسح: ").strip()
        if not scan_file:
            print("❌ يجب إدخال مسار الملف")
            return
        
        if not Path(scan_file).exists():
            print(f"❌ الملف غير موجود: {scan_file}")
            return
        
        bundle_name = input("اسم الحزمة (اختياري): ").strip()
        output_dir = input("مجلد الإخراج (اختياري): ").strip()
        
        args = type('Args', (), {
            'scan_file': scan_file,
            'libraries': None,
            'output_dir': output_dir if output_dir else None,
            'name': bundle_name if bundle_name else None,
            'no_zip': False
        })()
        
        self.handle_bundle(args)
    
    def interactive_bundle_manual(self):
        """إنشاء حزمة يدوياً"""
        print("\n" + "="*50)
        print("📦 إنشاء حزمة يدوياً")
        
        print("\n📚 أدخل أسماء المكتبات (افصل بينها بفاصلة):")
        print("مثال: jquery, bootstrap, tailwind, fontawesome")
        
        libs_input = input("المكتبات: ").strip()
        if not libs_input:
            print("❌ يجب إدخال مكتبة واحدة على الأقل")
            return
        
        libraries = [lib.strip() for lib in libs_input.split(',')]
        
        bundle_name = input("اسم الحزمة (اختياري): ").strip()
        output_dir = input("مجلد الإخراج (اختياري): ").strip()
        
        args = type('Args', (), {
            'scan_file': None,
            'libraries': libraries,
            'output_dir': output_dir if output_dir else None,
            'name': bundle_name if bundle_name else None,
            'no_zip': False
        })()
        
        self.handle_bundle(args)
    
    def handle_config(self):
        """عرض الإعدادات الحالية"""
        config = get_config()
        
        print("\n" + "="*50)
        print("⚙️  إعدادات الأداة")
        print("="*50)
        
        print(f"📊 الإصدار: {config.get('version', '1.0.0')}")
        
        print("\n🎯 التقنيات المدعومة:")
        focus_tech = config.get('focus_technologies', {})
        for tech, enabled in focus_tech.items():
            status = '✅' if enabled else '❌'
            print(f"  {status} {tech}")
        
        print("\n📏 الحدود:")
        limits = config.get('limits', {})
        print(f"  • الحد الأقصى لحجم الملف: {format_file_size(limits.get('max_file_size', 0))}")
        print(f"  • الحد الأقصى لحجم المشروع: {format_file_size(limits.get('max_project_size', 0))}")
        print(f"  • مهلة المسح: {limits.get('scan_timeout', 30)} ثانية")
        
        print("\n📁 المسارات:")
        paths = config.get('paths', {})
        for name, path in paths.items():
            print(f"  • {name}: {path}")
        
        print("="*50 + "\n")
    
    def handle_version(self):
        """عرض إصدار الأداة"""
        config = get_config()
        version = config.get('version', '1.0.0')
        
        print(f"""
╔══════════════════════════════════════════╗
║     أداة مسح مشاريع الويب               ║
║     الإصدار: {version:<10}               ║
║                                          ║
║     التركيز على:                        ║
║     • HTML, CSS, JavaScript              ║
║     • jQuery, Bootstrap, Tailwind        ║
║     • PHP                                ║
╚══════════════════════════════════════════╝
        """)
    
    def _is_css_library(self, lib_name: str) -> bool:
        """التحقق مما إذا كانت المكتبة من نوع CSS"""
        css_libs = ['bootstrap', 'tailwind', 'tailwindcss', 'fontawesome', 'animate.css']
        return any(css_lib in lib_name.lower() for css_lib in css_libs)


def main():
    """الدالة الرئيسية"""
    try:
        cli = CLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\n👋 تم إيقاف الأداة بواسطة المستخدم")
        sys.exit(0)
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        logger.exception("فشل في CLI")
        sys.exit(1)


if __name__ == '__main__':
    main()