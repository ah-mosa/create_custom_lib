// مدير المشاريع - التعامل مع المشاريع

class ProjectManager {
    constructor() {
        this.projects = [];
        this.currentProject = null;
    }
    
    // تحميل جميع المشاريع
    async loadProjects() {
        try {
            const response = await fetch('/api/projects');
            const projects = await response.json();
            
            if (response.ok) {
                this.projects = projects;
                return projects;
            }
        } catch (error) {
            console.error('❌ خطأ في تحميل المشاريع:', error);
        }
        return [];
    }
    
    // تحميل مشروع محدد
    async loadProject(projectId) {
        try {
            const response = await fetch(`/api/projects/${projectId}`);
            const project = await response.json();
            
            if (response.ok) {
                this.currentProject = project;
                return project;
            }
        } catch (error) {
            console.error('❌ خطأ في تحميل المشروع:', error);
        }
        return null;
    }
    
    // إنشاء مشروع جديد
    async createProject(projectName, zipFile = null) {
        const formData = new FormData();
        formData.append('project_name', projectName);
        
        if (zipFile) {
            formData.append('file', zipFile);
        }
        
        try {
            const response = await fetch('/api/projects', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                if (window.showNotification) {
                    window.showNotification('✅ تم إنشاء المشروع بنجاح', 'success');
                }
                return result;
            } else {
                throw new Error(result.detail || 'حدث خطأ');
            }
        } catch (error) {
            console.error('❌ خطأ في إنشاء المشروع:', error);
            if (window.showNotification) {
                window.showNotification(`❌ ${error.message}`, 'error');
            }
            return null;
        }
    }
    
    // تحديث مشروع
    async updateProject(projectId, updates) {
        try {
            const response = await fetch(`/api/projects/${projectId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updates)
            });
            
            if (response.ok) {
                if (window.showNotification) {
                    window.showNotification('✅ تم تحديث المشروع بنجاح', 'success');
                }
                return true;
            }
        } catch (error) {
            console.error('❌ خطأ في تحديث المشروع:', error);
        }
        return false;
    }
    
    // حذف مشروع
    async deleteProject(projectId) {
        try {
            const response = await fetch(`/api/projects/${projectId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                if (window.showNotification) {
                    window.showNotification('✅ تم حذف المشروع بنجاح', 'success');
                }
                return true;
            }
        } catch (error) {
            console.error('❌ خطأ في حذف المشروع:', error);
        }
        return false;
    }
    
    // مسح مشروع
    async scanProject(projectId) {
        try {
            const response = await fetch(`/api/projects/${projectId}/scan`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                if (window.showNotification) {
                    window.showNotification('✅ تم بدء مسح المشروع', 'success');
                }
                return result.task_id;
            } else {
                throw new Error(result.detail || 'حدث خطأ');
            }
        } catch (error) {
            console.error('❌ خطأ في مسح المشروع:', error);
            if (window.showNotification) {
                window.showNotification(`❌ ${error.message}`, 'error');
            }
            return null;
        }
    }
    
    // تحليل مشروع
    async analyzeProject(projectId) {
        try {
            const response = await fetch(`/api/projects/${projectId}/analyze`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                if (window.showNotification) {
                    window.showNotification('✅ تم بدء تحليل المشروع', 'success');
                }
                return result.task_id;
            } else {
                throw new Error(result.detail || 'حدث خطأ');
            }
        } catch (error) {
            console.error('❌ خطأ في تحليل المشروع:', error);
            if (window.showNotification) {
                window.showNotification(`❌ ${error.message}`, 'error');
            }
            return null;
        }
    }
    
    // إنشاء حزم للمشروع
    async createBundles(projectId, options = {}) {
        try {
            const response = await fetch(`/api/projects/${projectId}/bundles`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(options)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                if (window.showNotification) {
                    window.showNotification('✅ تم بدء إنشاء الحزم', 'success');
                }
                return result.task_id;
            } else {
                throw new Error(result.detail || 'حدث خطأ');
            }
        } catch (error) {
            console.error('❌ خطأ في إنشاء الحزم:', error);
            if (window.showNotification) {
                window.showNotification(`❌ ${error.message}`, 'error');
            }
            return null;
        }
    }
    
    // إنشاء تقرير للمشروع
    async createReport(projectId, reportType = 'html') {
        try {
            const response = await fetch(`/api/projects/${projectId}/reports`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ type: reportType })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                if (window.showNotification) {
                    window.showNotification('✅ تم بدء إنشاء التقرير', 'success');
                }
                return result.task_id;
            } else {
                throw new Error(result.detail || 'حدث خطأ');
            }
        } catch (error) {
            console.error('❌ خطأ في إنشاء التقرير:', error);
            if (window.showNotification) {
                window.showNotification(`❌ ${error.message}`, 'error');
            }
            return null;
        }
    }
    
    // تنزيل الحزم
    async downloadBundles(projectId) {
        try {
            const response = await fetch(`/api/projects/${projectId}/bundles/download`);
            
            if (response.ok) {
                // إنشاء رابط تنزيل
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `bundles_${projectId}.zip`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                return true;
            }
        } catch (error) {
            console.error('❌ خطأ في تنزيل الحزم:', error);
        }
        return false;
    }
    
    // عرض تفاصيل المشروع
    async showProjectDetails(projectId) {
        const project = await this.loadProject(projectId);
        if (!project) return;
        
        const detailsHtml = `
            <div class="project-details">
                <h3>${project.name}</h3>
                <div class="details-grid">
                    <div class="detail-item">
                        <strong>المعرف:</strong>
                        <span>${project.id}</span>
                    </div>
                    <div class="detail-item">
                        <strong>الحجم:</strong>
                        <span>${this.formatFileSize(project.size)}</span>
                    </div>
                    <div class="detail-item">
                        <strong>عدد الملفات:</strong>
                        <span>${project.file_count}</span>
                    </div>
                    <div class="detail-item">
                        <strong>تاريخ الإنشاء:</strong>
                        <span>${new Date(project.created_at).toLocaleString('ar')}</span>
                    </div>
                    <div class="detail-item">
                        <strong>الحالة:</strong>
                        <span class="status-badge ${project.status}">
                            ${project.status === 'active' ? 'نشط' : 'غير نشط'}
                        </span>
                    </div>
                </div>
                
                ${project.analysis ? `
                <div class="analysis-summary">
                    <h4>ملخص التحليل</h4>
                    <div class="stats">
                        <div class="stat">
                            <span class="stat-label">المكتبات:</span>
                            <span class="stat-value">${project.analysis.library_count || 0}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">الدوال:</span>
                            <span class="stat-value">${project.analysis.function_count || 0}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">آخر تحليل:</span>
                            <span class="stat-value">${new Date(project.analysis.last_analyzed).toLocaleDateString('ar')}</span>
                        </div>
                    </div>
                </div>
                ` : ''}
                
                <div class="project-actions">
                    <button class="btn btn-primary" onclick="projectManager.scanProject('${projectId}')">
                        <i class="fas fa-search"></i> مسح
                    </button>
                    <button class="btn btn-success" onclick="projectManager.analyzeProject('${projectId}')">
                        <i class="fas fa-chart-bar"></i> تحليل
                    </button>
                    <button class="btn btn-warning" onclick="projectManager.createBundles('${projectId}')">
                        <i class="fas fa-box"></i> إنشاء حزم
                    </button>
                    <button class="btn btn-info" onclick="projectManager.createReport('${projectId}')">
                        <i class="fas fa-file-alt"></i> إنشاء تقرير
                    </button>
                </div>
            </div>
        `;
        
        // عرض في نافذة منبثقة
        Swal.fire({
            title: 'تفاصيل المشروع',
            html: detailsHtml,
            width: '600px',
            showCloseButton: true,
            showConfirmButton: false
        });
    }
    
    // عرض قائمة المشاريع في جدول
    renderProjectsTable(projects) {
        return `
            <table class="projects-table">
                <thead>
                    <tr>
                        <th>اسم المشروع</th>
                        <th>الحالة</th>
                        <th>الحجم</th>
                        <th>الملفات</th>
                        <th>تاريخ الإنشاء</th>
                        <th>الإجراءات</th>
                    </tr>
                </thead>
                <tbody>
                    ${projects.map(project => `
                        <tr>
                            <td>
                                <strong>${project.name}</strong>
                                <br>
                                <small class="text-muted">${project.id}</small>
                            </td>
                            <td>
                                <span class="badge ${project.status === 'active' ? 'badge-success' : 'badge-secondary'}">
                                    ${project.status === 'active' ? 'نشط' : 'غير نشط'}
                                </span>
                            </td>
                            <td>${this.formatFileSize(project.size)}</td>
                            <td>${project.file_count}</td>
                            <td>${new Date(project.created_at).toLocaleDateString('ar')}</td>
                            <td>
                                <div class="btn-group">
                                    <button class="btn btn-sm btn-outline-primary" 
                                            onclick="projectManager.showProjectDetails('${project.id}')">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-success" 
                                            onclick="projectManager.analyzeProject('${project.id}')">
                                        <i class="fas fa-chart-bar"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" 
                                            onclick="projectManager.deleteProject('${project.id}')">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
    
    // تنسيق حجم الملف
    formatFileSize(bytes) {
        if (bytes === 0) return '0 بايت';
        
        const k = 1024;
        const sizes = ['بايت', 'كيلوبايت', 'ميجابايت', 'جيجابايت'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // عرض نموذج مشروع جديد
    showNewProjectModal() {
        const modalHtml = `
            <div class="new-project-modal">
                <h3>مشروع جديد</h3>
                <div class="form-group">
                    <label for="modalProjectName">اسم المشروع:</label>
                    <input type="text" id="modalProjectName" class="form-control" placeholder="أدخل اسم المشروع...">
                </div>
                <div class="form-group">
                    <label>رفع ملف ZIP (اختياري):</label>
                    <div class="upload-area-small" id="modalUploadArea">
                        <i class="fas fa-cloud-upload-alt"></i>
                        <p>اسحب وأفلت ملف ZIP أو انقر للتصفح</p>
                        <input type="file" id="modalProjectUpload" accept=".zip" style="display: none;">
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="btn btn-secondary" onclick="Swal.close()">إلغاء</button>
                    <button class="btn btn-primary" onclick="projectManager.submitNewProject()">إنشاء</button>
                </div>
            </div>
        `;
        
        Swal.fire({
            title: 'إنشاء مشروع جديد',
            html: modalHtml,
            showConfirmButton: false,
            showCloseButton: true,
            width: '500px'
        });
        
        // إعداد سحب وإفلات
        const uploadArea = document.getElementById('modalUploadArea');
        const fileInput = document.getElementById('modalProjectUpload');
        
        if (uploadArea && fileInput) {
            uploadArea.addEventListener('click', () => fileInput.click());
            
            ['dragover', 'dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                });
            });
            
            uploadArea.addEventListener('dragover', () => {
                uploadArea.style.background = 'rgba(67, 97, 238, 0.1)';
            });
            
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.style.background = '';
            });
            
            uploadArea.addEventListener('drop', (e) => {
                uploadArea.style.background = '';
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    fileInput.files = files;
                    uploadArea.innerHTML = `
                        <i class="fas fa-check-circle" style="color: #28a745;"></i>
                        <p>تم اختيار: ${files[0].name}</p>
                    `;
                }
            });
            
            fileInput.addEventListener('change', (e) => {
                if (fileInput.files.length > 0) {
                    uploadArea.innerHTML = `
                        <i class="fas fa-check-circle" style="color: #28a745;"></i>
                        <p>تم اختيار: ${fileInput.files[0].name}</p>
                    `;
                }
            });
        }
    }
    
    // إرسال مشروع جديد
    async submitNewProject() {
        const projectName = document.getElementById('modalProjectName').value;
        const fileInput = document.getElementById('modalProjectUpload');
        
        if (!projectName.trim()) {
            if (window.showNotification) {
                window.showNotification('⚠️ الرجاء إدخال اسم المشروع', 'warning');
            }
            return;
        }
        
        const result = await this.createProject(projectName, 
            fileInput.files.length > 0 ? fileInput.files[0] : null);
        
        if (result) {
            Swal.close();
            if (window.loadProjects) {
                window.loadProjects();
            }
            if (window.refreshDashboard) {
                window.refreshDashboard();
            }
        }
    }
}

// إنشاء مثيل مدير المشاريع
const projectManager = new ProjectManager();

// جعل المدير متاحاً عالمياً
window.projectManager = projectManager;
window.showNewProjectModal = projectManager.showNewProjectModal.bind(projectManager);

// تهيئة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // تحميل المشاريع إذا كنا في قسم المشاريع
    if (window.location.hash === '#projects' || 
        document.getElementById('projects').classList.contains('active')) {
        projectManager.loadProjects().then(projects => {
            const tableBody = document.getElementById('projectsTableBody');
            if (tableBody && projects.length > 0) {
                tableBody.innerHTML = projectManager.renderProjectsTable(projects);
            }
        });
    }
});
