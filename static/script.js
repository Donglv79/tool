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
});
