document.addEventListener('DOMContentLoaded', () => {
    const btnExcel = document.getElementById('btn-excel');
    const btnJson = document.getElementById('btn-json');
    const excelSection = document.getElementById('excel-section');
    const jsonSection = document.getElementById('json-section');
    const container = document.querySelector('.container');
    
    // Excel Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const selectedFileUI = document.getElementById('selected-file');
    const fileNameSpan = document.getElementById('file-name');
    const removeFileBtn = document.getElementById('remove-file');
    const processBtn = document.getElementById('process-btn');
    const uploadTitle = document.getElementById('upload-title');
    const uploadSubtitle = document.getElementById('upload-subtitle');
    const jsonColumnInput = document.getElementById('json-column-input');
    
    // JSON Elements
    const jsonInputText = document.getElementById('json-input-text');
    const jsonOutputText = document.getElementById('json-output-text');
    const processJsonBtn = document.getElementById('process-json-btn');
    const copyJsonBtn = document.getElementById('copy-json-btn');
    const detailsBtn = document.getElementById('details-btn');
    const detailsModal = document.getElementById('details-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const detailsContent = document.getElementById('details-content');

    // Status Elements
    const statusBox = document.getElementById('status-box');
    const statusText = document.getElementById('status-text');
    const loader = document.getElementById('loader');

    let currentMode = 'excel';
    let currentFile = null;

    // Toggle Modes
    btnExcel.addEventListener('click', () => {
        currentMode = 'excel';
        btnExcel.classList.add('active');
        btnJson.classList.remove('active');
        excelSection.style.display = 'block';
        jsonSection.style.display = 'none';
        container.classList.remove('wide');
        resetFile();
    });

    btnJson.addEventListener('click', () => {
        currentMode = 'json';
        btnJson.classList.add('active');
        btnExcel.classList.remove('active');
        excelSection.style.display = 'none';
        jsonSection.style.display = 'flex';
        container.classList.add('wide');
        statusBox.style.display = 'none';
    });

    // Excel Drag and Drop
    dropZone.addEventListener('click', (e) => {
        if (e.target !== removeFileBtn && !removeFileBtn.contains(e.target)) {
            fileInput.click();
        }
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFile(e.target.files[0]);
        }
    });

    function handleFile(file) {
        if (!file.name.match(/\.(xlsx|xls)$/i)) {
            showStatus('Vui lòng chọn file Excel!', true);
            return;
        }

        currentFile = file;
        fileNameSpan.textContent = file.name;
        
        dropZone.querySelector('.upload-icon').style.display = 'none';
        uploadTitle.style.display = 'none';
        uploadSubtitle.style.display = 'none';
        selectedFileUI.style.display = 'flex';
        processBtn.disabled = false;
        statusBox.style.display = 'none';
    }

    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resetFile();
    });

    function resetFile() {
        currentFile = null;
        fileInput.value = '';
        dropZone.querySelector('.upload-icon').style.display = 'block';
        uploadTitle.style.display = 'block';
        uploadSubtitle.style.display = 'block';
        selectedFileUI.style.display = 'none';
        processBtn.disabled = true;
        statusBox.style.display = 'none';
    }

    function showStatus(msg, isError = false) {
        statusBox.style.display = 'flex';
        statusText.textContent = msg;
        if (isError) {
            loader.style.display = 'none';
            statusText.classList.add('error-text');
        } else {
            loader.style.display = 'block';
            statusText.classList.remove('error-text');
        }
    }

    // Process Excel File
    processBtn.addEventListener('click', async () => {
        if (!currentFile) return;

        showStatus('Đang xử lý dữ liệu, vui lòng chờ...');
        processBtn.disabled = true;
        
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('json_column', jsonColumnInput.value || 'Input JSON');

        try {
            const response = await fetch('/api/process-excel', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Lỗi server khi xử lý file');
            }

            const contentDisposition = response.headers.get('Content-Disposition');
            let downloadFilename = `mapped_${currentFile.name}`;
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="?([^"]+)"?/);
                if (match && match[1]) downloadFilename = match[1];
            }

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            a.download = downloadFilename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            a.remove();

            showStatus('Xử lý thành công! File đã được tải xuống.');
            loader.style.display = 'none';
            processBtn.disabled = false;
        } catch (error) {
            showStatus(error.message, true);
            processBtn.disabled = false;
        }
    });

    // Auto-format JSON on input
    jsonInputText.addEventListener('input', () => {
        const text = jsonInputText.value.trim();
        if (!text) return;
        try {
            const parsed = JSON.parse(text);
            const formatted = JSON.stringify(parsed, null, 2);
            if (jsonInputText.value !== formatted) {
                jsonInputText.value = formatted;
            }
        } catch (e) {
            // Do nothing if it's not valid JSON yet
        }
    });

    // Process JSON Text
    processJsonBtn.addEventListener('click', async () => {
        const jsonText = jsonInputText.value.trim();
        if (!jsonText) {
            showStatus('Vui lòng nhập hoặc dán JSON vào ô Input!', true);
            return;
        }

        let parsedJson;
        try {
            parsedJson = JSON.parse(jsonText);
        } catch (e) {
            showStatus('Dữ liệu không phải là JSON hợp lệ!', true);
            return;
        }

        showStatus('Đang xử lý JSON...');
        processJsonBtn.disabled = true;
        jsonOutputText.value = '';
        copyJsonBtn.style.display = 'none';
        if (detailsBtn) detailsBtn.style.display = 'none';

        try {
            const response = await fetch('/api/process-raw-json', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(parsedJson)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Lỗi server khi xử lý JSON');
            }

            const data = await response.json();
            jsonOutputText.value = JSON.stringify(data, null, 2);
            
            showStatus('Xử lý JSON thành công!');
            loader.style.display = 'none';
            copyJsonBtn.style.display = 'flex';
            if (detailsBtn) detailsBtn.style.display = 'flex';
        } catch (error) {
            showStatus(error.message, true);
        } finally {
            processJsonBtn.disabled = false;
        }
    });

    // Copy Output JSON
    copyJsonBtn.addEventListener('click', () => {
        if (jsonOutputText.value) {
            navigator.clipboard.writeText(jsonOutputText.value)
                .then(() => {
                    const originalText = copyJsonBtn.innerHTML;
                    copyJsonBtn.innerHTML = '<i class="fa-solid fa-check"></i> Đã Copy!';
                    setTimeout(() => {
                        copyJsonBtn.innerHTML = originalText;
                    }, 2000);
                })
                .catch(err => {
                    console.error('Lỗi khi copy: ', err);
                });
        }
    });

    // Helper function to flatten JSON
    function flattenJSON(data) {
        let result = {};
        function recurse(cur, prop) {
            if (Object(cur) !== cur) {
                result[prop] = cur;
            } else if (Array.isArray(cur)) {
                for (let i = 0; i < cur.length; i++) {
                    recurse(cur[i], prop + "[" + i + "]");
                }
                if (cur.length === 0) result[prop] = [];
            } else {
                let isEmpty = true;
                for (let p in cur) {
                    isEmpty = false;
                    recurse(cur[p], prop ? prop + "." + p : p);
                }
                if (isEmpty && prop) result[prop] = {};
            }
        }
        recurse(data, "");
        return result;
    }

    // Show Details Modal
    if (detailsBtn) {
        detailsBtn.addEventListener('click', () => {
            if (!jsonOutputText.value) return;
            try {
                const outData = JSON.parse(jsonOutputText.value);
                const flatOut = flattenJSON(outData);
                
                let inData = {};
                try {
                    inData = JSON.parse(jsonInputText.value);
                } catch (e) {
                    console.warn("Input JSON không hợp lệ");
                }
                const flatIn = flattenJSON(inData);
                
                // Xây dựng map giá trị Input để dò ngược
                let inValueMap = {};
                for (let k in flatIn) {
                    let v = flatIn[k];
                    if (v !== "" && v !== null && v !== undefined) {
                        if (!inValueMap[v]) inValueMap[v] = [];
                        inValueMap[v].push(k);
                    }
                }
                
                let html = '<table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.95rem;">';
                html += '<tr style="border-bottom: 2px solid var(--primary);"><th style="padding: 12px; width: 30%;">Trường Output (Kết quả)</th><th style="padding: 12px; width: 35%;">Trường Input Tương Ứng (Nguồn gốc)</th><th style="padding: 12px; width: 35%;">Giá trị</th></tr>';
                
                let hasData = false;
                for (let key in flatOut) {
                    let val = flatOut[key];
                    if (val !== "" && val !== null && val !== undefined && 
                        !(Array.isArray(val) && val.length === 0) && 
                        !(typeof val === 'object' && Object.keys(val).length === 0)) {
                        
                        hasData = true;
                        let sourceHtml = '<span style="color: #64748B; font-style: italic;">[Được tổng hợp / tự động sinh]</span>';
                        
                        // Kiểm tra nếu là các trường cấu trúc cứng của file Output
                        if (key.endsWith('.order') || key.endsWith('.title') || key === 'order' || key === 'title') {
                            sourceHtml = '<span style="color: #8B5CF6; font-style: italic;">[Trường cấu trúc cố định]</span>';
                        }
                        // Tìm kiếm xem giá trị output này có khớp hoàn toàn với một trường input nào không
                        else if (inValueMap[val]) {
                            sourceHtml = inValueMap[val].map(k => `<span style="color: var(--secondary); font-weight: 600;">${k}</span>`).join('<br>');
                        } else if (typeof val === 'string') {
                            // Nếu không khớp hoàn toàn, thử xem nó có phải là một phần được cắt ra từ chuỗi input không (tìm chuỗi dài > 3 ký tự)
                            let partials = [];
                            if (val.length > 3) {
                                for (let k in flatIn) {
                                    if (typeof flatIn[k] === 'string' && flatIn[k].includes(val)) {
                                        partials.push(k);
                                    }
                                }
                            }
                            if (partials.length > 0) {
                                sourceHtml = partials.map(k => `<span style="color: #F59E0B; font-weight: 500;">${k} <br><small>(Cắt một phần)</small></span>`).join('<br><br>');
                            }
                        }
                        
                        html += `<tr style="border-bottom: 1px dashed var(--border-color);">
                            <td style="padding: 12px; font-weight: 600; color: var(--primary); word-break: break-word;">${key}</td>
                            <td style="padding: 12px; font-size: 0.9em; word-break: break-word;">${sourceHtml}</td>
                            <td style="padding: 12px; word-break: break-word; color: var(--text-main);">${val}</td>
                        </tr>`;
                    }
                }
                html += '</table>';
                
                if (!hasData) html = '<p style="text-align: center; padding: 20px;">Không có dữ liệu.</p>';
                
                const detailsContent = document.getElementById('details-content');
                if (detailsContent) detailsContent.innerHTML = html;
                
                detailsModal.style.display = 'flex';
            } catch (e) {
                console.error("Lỗi khi đọc JSON:", e);
                showStatus("Lỗi khi xem chi tiết", true);
            }
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            detailsModal.style.display = 'none';
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === detailsModal) {
            detailsModal.style.display = 'none';
        }
    });
});
