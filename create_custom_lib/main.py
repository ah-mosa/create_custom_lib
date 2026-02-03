#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JS Custom Bundler - الإدارة الكاملة من واجهة الويب
"""

import sys
import os
import webbrowser
import threading
import time
from pathlib import Path
import uvicorn

# إضافة مسار src إلى النظام
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.webui import app, initialize_web_app
from src.utils.background_worker import start_worker, stop_worker

def main():
    """تشغيل واجهة الويب كواجهة رئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description='JS Custom Bundler - واجهة ويب متكاملة')
    parser.add_argument('--host', default='127.0.0.1', help='عنوان الخادم')
    parser.add_argument('--port', default=8080, type=int, help='منفذ الخادم')
    parser.add_argument('--no-browser', action='store_true', help='عدم فتح المتصفح تلقائياً')
    parser.add_argument('--debug', action='store_true', help='وضع التصحيح')
    
    args = parser.parse_args()
    
    try:
        # تهيئة التطبيق
        initialize_web_app()
        
        # تشغيل عامل الخلفية للمهام الطويلة
        start_worker()
        
        # فتح المتصفح تلقائياً
        if not args.no_browser:
            threading.Thread(
                target=lambda: (
                    time.sleep(2),
                    webbrowser.open(f'http://{args.host}:{args.port}')
                ),
                daemon=True
            ).start()
        
        print("\n" + "="*60)
        print("🚀 JS Custom Bundler - الإدارة الكاملة من الويب")
        print("="*60)
        print(f"🌐 الواجهة متاحة على: http://{args.host}:{args.port}")
        print("📁 يمكنك تحميل المشاريع وفحصها وإنشاء حزم مخصصة من المتصفح")
        print("🛑 اضغط Ctrl+C لإيقاف الخادم")
        print("="*60 + "\n")
        
        # تشغيل الخادم
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info" if not args.debug else "debug"
        )
        
    except KeyboardInterrupt:
        print("\n\n🛑 تم إيقاف الخادم")
        stop_worker()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        stop_worker()
        sys.exit(1)

if __name__ == "__main__":
    main()