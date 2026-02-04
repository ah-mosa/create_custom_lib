// JavaScript for JS Custom Bundler Web UI

let analysisData = null;

// إدارة سحب وإفلات الملفات
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('projectUpload');

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.background = '#e3f2fd';
});

uploadArea.addEventListener('dragleave', (e) => {
    e.preventDefault();
    uploadArea.style.background = '';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.background = '';
    
    const items = e.dataTransfer.items;
    if (items && items[0].webkitGetAsEntry) {
        const entry = items[0].webkitGetAsEntry();
        if (entry && entry.isDirectory) {
            document.getElementById('projectPath').value = entry.fullPath || entry.name;
            analyzeProject();
        }
    }
});

fileInput.addEventListener('change', (e) => {
    const files = e.target.files;
    if (files.length > 0) {
        // في المتصفحات الحديثة، يمكن الحصول على مسار المجلد
        const path = files[0].webkitRelativePath.split('/')[0];
        document.getElementById('projectPath').value = path;
    }
});

// وظيفة تحليل المشروع
async function analyzeProject() {
    const projectPath = document.getElementById('projectPath').value.trim();
    if (!projectPath) {
        alert('يرجى اختيار مجلد المشروع أولاً');
        return;
    }
    
    showLoading('جاري مسح وتحليل المشروع...');
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ project_path: projectPath })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            analysisData = data;
            displayResults(data);
            document.getElementById('resultsSection').classList.remove('hidden');
        } else {
            alert('خطأ: ' + data.detail || 'حدث خطأ غير معروف');
        }
    } catch (error) {
        alert('خطأ في الاتصال: ' + error.message);
    } finally {
        hideLoading();
    }
}

// عرض النتائج
function displayResults(data) {
    // تحديث الإحصائيات
    document.getElementById('fileCount').textContent = data.total_files;
    document.getElementById('libCount').textContent = data.total_libraries;
    
    // تحديث الجدول
    const tableBody = document.getElementById('libTableBody');
    tableBody.innerHTML = '';
    
    for (const [libName, libData] of Object.entries(data.libraries)) {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td><strong>${libName}</strong></td>
            <td>${libData.count}</td>
            <td>${libData.functions_used.length > 0 ? 
                libData.functions_used.join(', ') : 
                'جميع الدوال'}</td>
            <td>
                <button onclick="createBundle('${libName}')" class="btn-secondary" style="padding: 5px 10px; font-size: 0.9rem;">
                    إنشاء حزمة
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    }
    
    // إنشاء الرسم البياني
    createChart(data);
}

// إنشاء رسم بياني
function createChart(data) {
    const ctx = document.getElementById('libChart').getContext('2d');
    
    // إعداد البيانات
    const labels = Object.keys(data.libraries);
    const counts = labels.map(lib => data.libraries[lib].count);
    
    // تدمير المخطط القديم إذا كان موجوداً
    if (window.libChart) {
        window.libChart.destroy();
    }
    
    // إنشاء مخطط جديد
    window.libChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'عدد الملفات المستخدمة',
                data: counts,
                backgroundColor: [
                    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                    '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
                ],
                borderColor: '#fff',
                borderWidth: 2,
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            size: 14
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// إنشاء الحزم المخصصة
async function generateBundles() {
    if (!analysisData) {
        alert('يرجى تحليل المشروع أولاً');
        return;
    }
    
    showLoading('جاري إنشاء الحزم المخصصة...');
    
    try {
        const response = await fetch('/api/bundle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ analysis: analysisData })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('✅ تم إنشاء الحزم بنجاح!\nيمكنك العثور عليها في: ' + data.output_dir);
            
            // عرض روابط التحميل
            if (data.bundles && Object.keys(data.bundles).length > 0) {
                let bundleList = '\nالحزم المنشأة:\n';
                for (const [lib, path] of Object.entries(data.bundles)) {
                    bundleList += `\n• ${lib}: ${path}`;
                }
                alert(bundleList);
            }
        } else {
            alert('خطأ: ' + data.detail || 'حدث خطأ أثناء إنشاء الحزم');
        }
    } catch (error) {
        alert('خطأ في الاتصال: ' + error.message);
    } finally {
        hideLoading();
    }
}

// إنشاء تقرير
async function generateReport() {
    if (!analysisData) {
        alert('يرجى تحليل المشروع أولاً');
        return;
    }
    
    showLoading('جاري إنشاء التقرير...');
    
    try {
        const response = await fetch('/api/report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ analysis: analysisData })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // فتح التقرير في نافذة جديدة
            window.open(data.report_url, '_blank');
        } else {
            alert('خطأ: ' + data.detail || 'حدث خطأ أثناء إنشاء التقرير');
        }
    } catch (error) {
        alert('خطأ في الاتصال: ' + error.message);
    } finally {
        hideLoading();
    }
}

// إنشاء حزمة لمكتبة محددة
async function createBundle(libName) {
    if (!analysisData) return;
    
    showLoading(`جاري إنشاء حزمة مخصصة لـ ${libName}...`);
    
    try {
        const response = await fetch('/api/bundle-library', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                library: libName,
                data: analysisData.libraries[libName] 
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`✅ تم إنشاء حزمة ${libName} بنجاح!\nالمسار: ${data.bundle_path}`);
        } else {
            alert('خطأ: ' + data.detail);
        }
    } catch (error) {
        alert('خطأ في الاتصال: ' + error.message);
    } finally {
        hideLoading();
    }
}

// وظائف التحكم في شاشة التحميل
function showLoading(message = 'جاري المعالجة...') {
    document.getElementById('loadingText').textContent = message;
    document.getElementById('loading').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

// تهيئة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // يمكن إضافة أي تهيئة إضافية هنا
});