// مدير المهام - التعامل مع المهام الخلفية

class TaskManager {
    constructor() {
        this.tasks = new Map();
        this.updateInterval = null;
    }
    
    // بدء مراقبة المهام
    startMonitoring() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        this.updateInterval = setInterval(() => {
            this.updateTasks();
        }, 3000);
    }
    
    // إيقاف المراقبة
    stopMonitoring() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    // تحديث المهام
    async updateTasks() {
        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            
            if (response.ok) {
                this.processTasks(tasks);
            }
        } catch (error) {
            console.error('❌ خطأ في تحديث المهام:', error);
        }
    }
    
    // معالجة المهام
    processTasks(tasks) {
        this.tasks.clear();
        
        tasks.forEach(task => {
            this.tasks.set(task.task_id, task);
            
            // تحديث واجهة المهمة إذا كانت قيد التنفيذ
            if (task.status === 'running' || task.status === 'pending') {
                this.updateTaskUI(task);
            }
            
            // إذا اكتملت المهمة، معالجة النتيجة
            if (task.status === 'completed' && task.result) {
                this.handleTaskCompletion(task);
            }
        });
        
        // تحديث العدادات
        this.updateTaskCounters(tasks);
    }
    
    // تحديث واجهة المهمة
    updateTaskUI(task) {
        // البحث عن عناصر المهمة في الصفحة
        const taskElements = document.querySelectorAll(`[data-task-id="${task.task_id}"]`);
        
        taskElements.forEach(element => {
            // تحديث شريط التقدم
            const progressBar = element.querySelector('.task-progress');
            if (progressBar) {
                progressBar.style.width = `${task.progress}%`;
            }
            
            // تحديث النص
            const statusText = element.querySelector('.task-status');
            if (statusText) {
                statusText.textContent = this.getStatusText(task.status);
            }
            
            const messageText = element.querySelector('.task-message');
            if (messageText && task.message) {
                messageText.textContent = task.message;
            }
        });
    }
    
    // معالجة اكتمال المهمة
    handleTaskCompletion(task) {
        // إزالة المهمة من القوائم النشطة
        const taskElements = document.querySelectorAll(`[data-task-id="${task.task_id}"]`);
        taskElements.forEach(element => {
            element.remove();
        });
        
        // عرض الإشعار المناسب
        let message = '';
        let type = 'success';
        
        switch (task.task_type) {
            case 'scan_project':
                message = '✅ اكتمل مسح المشروع بنجاح';
                this.handleScanCompletion(task.result);
                break;
            case 'analyze_project':
                message = '✅ اكتمل تحليل المشروع بنجاح';
                this.handleAnalysisCompletion(task.result);
                break;
            case 'create_bundles':
                message = '✅ اكتمل إنشاء الحزم بنجاح';
                this.handleBundleCompletion(task.result);
                break;
            case 'generate_report':
                message = '✅ اكتمل إنشاء التقرير بنجاح';
                this.handleReportCompletion(task.result);
                break;
            default:
                message = '✅ اكتملت المهمة بنجاح';
        }
        
        if (task.status === 'failed') {
            message = `❌ فشلت المهمة: ${task.error}`;
            type = 'error';
        }
        
        // إظهار الإشعار
        if (window.showNotification) {
            window.showNotification(message, type);
        }
    }
    
    // معالجة اكتمال المسح
    handleScanCompletion(result) {
        console.log('نتيجة المسح:', result);
        // يمكن تحديث واجهة المشروع هنا
    }
    
    // معالجة اكتمال التحليل
    handleAnalysisCompletion(result) {
        console.log('نتيجة التحليل:', result);
        
        // تحديث حالة التطبيق
        if (window.appState) {
            window.appState.currentAnalysis = result.analysis_id;
        }
        
        // عرض النتائج إذا كنا في قسم التحليل
        if (window.displayAnalysisResults) {
            window.displayAnalysisResults(result.analysis || result);
        }
    }
    
    // معالجة اكتمال الحزم
    handleBundleCompletion(result) {
        console.log('نتيجة الحزم:', result);
        
        // عرض روابط التنزيل
        if (result.zip_path && window.showNotification) {
            window.showNotification(
                `✅ تم إنشاء ${result.total_bundles} حزمة. <a href="/api/download/bundles/${result.zip_path}" target="_blank">انقر للتنزيل</a>`,
                'success'
            );
        }
    }
    
    // معالجة اكتمال التقرير
    handleReportCompletion(result) {
        console.log('نتيجة التقرير:', result);
        
        // فتح التقرير في نافذة جديدة
        if (result.report_url) {
            window.open(result.report_url, '_blank');
        }
    }
    
    // تحديث العدادات
    updateTaskCounters(tasks) {
        const pendingCount = tasks.filter(t => t.status === 'pending').length;
        const runningCount = tasks.filter(t => t.status === 'running').length;
        const completedCount = tasks.filter(t => t.status === 'completed').length;
        
        // تحديث العدادات في الواجهة
        const counters = {
            'pendingCount': pendingCount,
            'runningCount': runningCount,
            'completedCount': completedCount
        };
        
        Object.entries(counters).forEach(([id, count]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = count;
            }
        });
    }
    
    // الحصول على نص الحالة
    getStatusText(status) {
        const statusMap = {
            'pending': '⏳ في الانتظار',
            'running': '🔄 قيد التنفيذ',
            'completed': '✅ مكتمل',
            'failed': '❌ فشل',
            'cancelled': '⛔ ملغي'
        };
        return statusMap[status] || status;
    }
    
    // إلغاء مهمة
    async cancelTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/cancel`, {
                method: 'POST'
            });
            
            if (response.ok) {
                if (window.showNotification) {
                    window.showNotification('✅ تم إلغاء المهمة', 'success');
                }
                return true;
            }
        } catch (error) {
            console.error('❌ خطأ في إلغاء المهمة:', error);
        }
        return false;
    }
    
    // إرسال مهمة جديدة
    async submitTask(taskType, data) {
        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_type: taskType,
                    data: data
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                if (window.showNotification) {
                    window.showNotification('✅ تم إرسال المهمة بنجاح', 'success');
                }
                return result.task_id;
            } else {
                throw new Error(result.detail || 'حدث خطأ');
            }
        } catch (error) {
            console.error('❌ خطأ في إرسال المهمة:', error);
            if (window.showNotification) {
                window.showNotification(`❌ ${error.message}`, 'error');
            }
            return null;
        }
    }
    
    // إنشاء عنصر مهمة في الواجهة
    createTaskElement(task) {
        const element = document.createElement('div');
        element.className = 'task-item';
        element.setAttribute('data-task-id', task.task_id);
        
        element.innerHTML = `
            <div class="task-header">
                <span class="task-title">${this.getTaskTypeName(task.task_type)}</span>
                <span class="task-status ${task.status}">${this.getStatusText(task.status)}</span>
            </div>
            <div class="task-body">
                <p class="task-message">${task.message || 'جاري المعالجة...'}</p>
                <div class="task-progress-container">
                    <div class="task-progress" style="width: ${task.progress || 0}%"></div>
                </div>
                <div class="task-actions">
                    <button class="btn btn-sm btn-danger" onclick="taskManager.cancelTask('${task.task_id}')">
                        <i class="fas fa-times"></i> إلغاء
                    </button>
                </div>
            </div>
            <div class="task-footer">
                <small>${new Date(task.created_at).toLocaleString('ar')}</small>
            </div>
        `;
        
        return element;
    }
    
    // الحصول على اسم نوع المهمة
    getTaskTypeName(type) {
        const typeMap = {
            'scan_project': 'مسح المشروع',
            'analyze_project': 'تحليل المشروع',
            'create_bundles': 'إنشاء الحزم',
            'generate_report': 'إنشاء التقرير',
            'cleanup_project': 'تنظيف المشروع'
        };
        return typeMap[type] || type;
    }
    
    // إضافة مهمة إلى القائمة
    addTaskToList(task, listId) {
        const list = document.getElementById(listId);
        if (!list) return;
        
        const taskElement = this.createTaskElement(task);
        list.prepend(taskElement);
    }
}

// إنشاء مثيل مدير المهام
const taskManager = new TaskManager();

// بدء المراقبة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    taskManager.startMonitoring();
});

// جعل المدير متاحاً عالمياً
window.taskManager = taskManager;
