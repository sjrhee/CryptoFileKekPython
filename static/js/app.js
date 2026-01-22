/**
 * File Encryption System - Frontend Logic
 * Structure: Module Pattern (State, API, UI, App)
 */

// ==========================================
// 1. STATE MODULE
// ==========================================
const State = {
    currentMode: null, // 'encrypt' | 'decrypt'
    currentStep: 1,
    selectedFiles: {
        encrypt: null,
        decrypt: { file: null, dek: null }
    },

    reset() {
        this.currentMode = null;
        this.currentStep = 1;
        this.selectedFiles = {
            encrypt: null,
            decrypt: { file: null, dek: null }
        };
    },

    setMode(mode) {
        this.currentMode = mode;
        this.currentStep = 1;
    }
};

// ==========================================
// 2. API MODULE
// ==========================================
const API = {
    async get(url) {
        const response = await fetch(url);
        return this.handleResponse(response);
    },

    async post(url, body = {}) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        return this.handleResponse(response);
    },

    async postFormData(url, formData) {
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });
        return this.handleResponse(response);
    },

    async delete(url) {
        const response = await fetch(url, { method: 'DELETE' });
        // DELETE endpoints might not return JSON content, handle gracefully
        if (!response.ok) throw new Error('Delete operation failed');
        return true;
    },

    async handleResponse(response) {
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.message || 'An error occurred');
        }
        return data.data;
    },

    // Specific API Calls
    listFiles: () => API.get('/api/files/list'),
    uploadFile: (formData) => API.postFormData('/api/files/upload', formData),
    cleanupTemp: () => API.post('/api/files/cleanup-temp'),

    encrypt: {
        select: (filename) => API.post('/api/encrypt/select', { filename }),
        process: (fileId) => API.post(`/api/encrypt/process/${fileId}`)
    },

    decrypt: {
        select: (encryptedFilename, dekFilename) => API.post('/api/decrypt/select', { encryptedFilename, dekFilename }),
        process: (fileId) => API.post(`/api/decrypt/process/${fileId}`)
    }
};

// ==========================================
// 3. UI MODULE
// ==========================================
const UI = {
    elements: {
        modeSelection: 'modeSelection',
        wizardSteps: 'wizardSteps',
        encryptWizard: 'encryptWizard',
        decryptWizard: 'decryptWizard',
        errorAlert: 'errorAlert',
        errorMessage: 'errorMessage',
        encryptFileSelect: 'encryptFileSelect',
        decryptFileSelect: 'decryptFileSelect',
        decryptDekSelect: 'decryptDekSelect'
    },

    getElement(id) {
        return document.getElementById(id);
    },

    show(id) {
        const el = this.getElement(id);
        if (el) el.classList.remove('hidden');
    },

    hide(id) {
        const el = this.getElement(id);
        if (el) el.classList.add('hidden');
    },

    updateStep(step) {
        const steps = document.querySelectorAll('.wizard-step');
        steps.forEach((stepEl, index) => {
            const stepNum = index + 1;
            stepEl.classList.remove('active', 'completed');
            if (stepNum < step) stepEl.classList.add('completed');
            else if (stepNum === step) stepEl.classList.add('active');
        });
    },

    updateProgress(mode, percent, text) {
        const bar = this.getElement(`${mode}Progress`);
        const label = this.getElement(`${mode}ProgressText`);
        if (bar) bar.style.width = `${percent}%`;
        if (label) label.textContent = text;
    },

    populateSelect(id, files, filterFn, currentValue) {
        const select = this.getElement(id);
        if (!select) return;

        select.innerHTML = '<option value="">Select a file...</option>';
        files.filter(filterFn).forEach(file => {
            const option = document.createElement('option');
            option.value = file;
            option.textContent = file;
            select.appendChild(option);
        });

        if (files.includes(currentValue)) {
            select.value = currentValue;
        }
    },

    showError(message) {
        const elMsg = this.getElement(this.elements.errorMessage);
        if (elMsg) elMsg.textContent = message;
        this.show(this.elements.errorAlert);
        setTimeout(() => this.hide(this.elements.errorAlert), 5000);
    },

    resetAll() {
        // Hide wizards
        this.hide(this.elements.encryptWizard);
        this.hide(this.elements.decryptWizard);
        this.hide(this.elements.wizardSteps);
        this.hide(this.elements.errorAlert);

        // Show mode selection
        this.show(this.elements.modeSelection);

        // Reset inputs
        document.querySelectorAll('select').forEach(s => s.value = '');
        this.hide('encryptFileInfo');
    },

    // Helpers
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
};

// ==========================================
// 3.5 SETTINGS MODULE
// ==========================================
const Settings = {
    init() {
        console.log("Settings: Initializing...");
        const btn = document.getElementById("settingsBtn");
        const modal = document.getElementById("settingsModal");
        const closeBtn = document.getElementById("settingsCloseBtn");
        const cancelBtn = document.getElementById("settingsCancelBtn");
        const saveBtn = document.getElementById("settingsSaveBtn");
        const checkbox = document.getElementById("useHsmCheckbox");

        if (btn && modal) {
            btn.addEventListener('click', (e) => {
                console.log("Settings: Opening modal");
                modal.classList.add('flex');
                modal.classList.remove('hidden');
                this.loadStatus();
            });

            // Close handles
            if (closeBtn) closeBtn.addEventListener('click', () => this.close());
            if (cancelBtn) cancelBtn.addEventListener('click', () => this.close());
            if (saveBtn) saveBtn.addEventListener('click', () => this.save());
            if (checkbox) checkbox.addEventListener('change', () => this.togglePinInput());

            // Close on outside click
            window.addEventListener('click', (event) => {
                if (event.target === modal) {
                    console.log("Settings: Closing via outside click");
                    this.close();
                }
            });
        } else {
            console.error("Settings: Required elements not found!", { btn, modal });
        }
    },

    close() {
        console.log("Settings: Closing modal");
        const modal = document.getElementById("settingsModal");
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
        const errorDiv = document.getElementById("settingsError");
        if (errorDiv) errorDiv.classList.add('hidden');
    },

    togglePinInput() {
        console.log("Settings: Toggling PIN input");
        const checkbox = document.getElementById("useHsmCheckbox");
        const slotInput = document.getElementById("hsmSlotId");
        const labelInput = document.getElementById("hsmLabel");
        const pinInput = document.getElementById("hsmPin");
        if (checkbox && pinInput) {
            const useHsm = checkbox.checked;
            pinInput.disabled = !useHsm;
            if (labelInput) labelInput.disabled = !useHsm;
            if (slotInput) slotInput.disabled = !useHsm;

            console.log("Settings: Use HSM =", useHsm);
            if (!useHsm) {
                // pinInput.value = ''; // Keep default value for demo convenience
                const errorDiv = document.getElementById("settingsError");
                if (errorDiv) errorDiv.classList.add('hidden');
            }
        }
    },

    async loadStatus() {
        console.log("Settings: Loading status...");
        try {
            const response = await fetch('/api/hsm/status');
            if (response.ok) {
                const status = await response.json();
                console.log("Settings: Received status", status);
                const checkbox = document.getElementById("useHsmCheckbox");
                if (checkbox) {
                    checkbox.checked = status.useHsm;
                    this.togglePinInput();
                }
            } else {
                console.error("Settings: Failed to load status", response.status);
            }
        } catch (error) {
            console.error("Settings: Failed to load HSM status", error);
        }
    },

    async save() {
        console.log("Settings: Saving configuration...");
        const checkbox = document.getElementById("useHsmCheckbox");
        const slotInput = document.getElementById("hsmSlotId");
        const labelInput = document.getElementById("hsmLabel");
        const pinInput = document.getElementById("hsmPin");
        const errorDiv = document.getElementById("settingsError");

        if (!checkbox || !pinInput || !errorDiv) {
            console.error("Settings: Save failed due to missing elements", { checkbox, pinInput, errorDiv });
            return;
        }

        const useHsm = checkbox.checked;
        const pin = pinInput.value;
        const label = labelInput ? labelInput.value : 'master_key';
        const slotId = (slotInput && slotInput.value) ? parseInt(slotInput.value) : 1;

        console.log("Settings: Saving", { useHsm, pinHasValue: !!pin, label, slotId });

        // Validation
        if (useHsm && (!pin || pin.trim() === '')) {
            errorDiv.textContent = "PIN is required when using HSM.";
            errorDiv.classList.remove('hidden');
            console.warn("Settings: Save aborted - PIN required");
            return;
        }

        try {
            errorDiv.classList.add('hidden');
            const response = await fetch('/api/hsm/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ useHsm: useHsm, pin: pin, label: label, slotId: slotId })
            });

            if (response.ok) {
                console.log("Settings: Save successful");
                this.close();
                alert("Settings saved successfully!");
            } else {
                const errorText = await response.text();
                console.error("Settings: Save failed", errorText);
                errorDiv.textContent = "Error: " + errorText;
                errorDiv.classList.remove('hidden');
            }
        } catch (error) {
            console.error("Settings: Save network error", error);
            errorDiv.textContent = "Network Error: " + error.message;
            errorDiv.classList.remove('hidden');
        }
    }
};

// ==========================================
// 4. APP CONTROLLER
// ==========================================
const App = {
    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.setupHandlers();
            this.refreshFileList();
            Settings.init(); // Initialize settings
        });
    },

    setupHandlers() {
        // Encrypt File Selection
        UI.getElement('encryptFileSelect').addEventListener('change', (e) => {
            const filename = e.target.value;
            State.selectedFiles.encrypt = filename || null;

            if (filename) {
                UI.getElement('encryptFileName').textContent = filename;
                UI.show('encryptFileInfo');
                UI.getElement('encryptNextBtn').disabled = false;
            } else {
                UI.hide('encryptFileInfo');
                UI.getElement('encryptNextBtn').disabled = true;
            }
        });

        // Decrypt File Selections
        const checkDecrypt = () => {
            const encFile = UI.getElement('decryptFileSelect').value;
            const dekFile = UI.getElement('decryptDekSelect').value;
            State.selectedFiles.decrypt = { file: encFile, dek: dekFile };
            UI.getElement('decryptNextBtn').disabled = !(encFile && dekFile);
        };

        UI.getElement('decryptFileSelect').addEventListener('change', checkDecrypt);
        UI.getElement('decryptDekSelect').addEventListener('change', checkDecrypt);
    },

    async refreshFileList() {
        try {
            const files = await API.listFiles();

            const encryptVal = State.selectedFiles.encrypt;
            const decryptFileVal = State.selectedFiles.decrypt.file;
            const decryptDekVal = State.selectedFiles.decrypt.dek;

            UI.populateSelect('encryptFileSelect', files, f => !f.endsWith('.dek') && !f.endsWith('.encrypted'), encryptVal);
            UI.populateSelect('decryptFileSelect', files, f => f.endsWith('.encrypted'), decryptFileVal);
            UI.populateSelect('decryptDekSelect', files, f => f.endsWith('.dek'), decryptDekVal);

        } catch (error) {
            console.error('List error:', error);
            UI.showError('Failed to load file list.');
        }
    },

    async uploadFiles() {
        const input = UI.getElement('uploadInput');
        const files = input.files;
        if (!files || files.length === 0) {
            alert('Please select files to upload.');
            return;
        }

        try {
            let count = 0;
            for (let i = 0; i < files.length; i++) {
                const formData = new FormData();
                formData.append('file', files[i]);
                await API.uploadFile(formData);
                count++;
            }
            alert(`Successfully uploaded ${count} file(s).`);
            input.value = '';
            await this.refreshFileList();
        } catch (error) {
            console.error('Upload error:', error);
            UI.showError('Failed to upload files: ' + error.message);
        }
    },

    selectMode(mode) {
        State.setMode(mode);
        UI.hide('modeSelection');
        UI.show('wizardSteps');

        if (mode === 'encrypt') {
            UI.show('encryptWizard');
            // Ensure step 1 is visible
            UI.show('encryptStep1');
            UI.hide('encryptStep2');
            UI.hide('encryptStep3');
        } else {
            UI.show('decryptWizard');
            // Ensure step 1 is visible
            UI.show('decryptStep1');
            UI.hide('decryptStep2');
            UI.hide('decryptStep3');
        }

        UI.updateStep(1);
        this.refreshFileList();
    },

    async resetWizard() {
        try {
            await API.cleanupTemp();
            console.log('Temp Cleanup Requested via Start Operation');
        } catch (e) {
            console.warn('Cleanup failed', e);
        }
        State.reset();
        UI.resetAll();
    },

    async restartCurrentMode() {
        const mode = State.currentMode;
        if (!mode) return;

        // Cleanup temp files
        try {
            await API.cleanupTemp();
            console.log('Temp Cleanup Requested');
        } catch (e) {
            console.warn('Cleanup failed', e);
        }

        // Reset UI for current mode
        if (mode === 'encrypt') {
            State.selectedFiles.encrypt = null;
            UI.getElement('encryptFileSelect').value = '';
            UI.hide('encryptFileInfo');
            UI.getElement('encryptNextBtn').disabled = true;

            UI.hide('encryptStep3');
            UI.show('encryptStep1');
        } else {
            State.selectedFiles.decrypt = { file: null, dek: null };
            UI.getElement('decryptFileSelect').value = '';
            UI.getElement('decryptDekSelect').value = '';
            UI.getElement('decryptNextBtn').disabled = true;

            UI.hide('decryptStep3');
            UI.show('decryptStep1');
        }

        this.refreshFileList();
        UI.updateProgress(mode, 0, 'Preparing...');
        UI.updateStep(1);
    },

    // -------------------------------------------------------------------------
    // ENCRYPTION FLOW
    // -------------------------------------------------------------------------
    async processEncryption() {
        if (!State.selectedFiles.encrypt) return;
        const mode = 'encrypt';

        try {
            // UI Transition to Step 2
            UI.hide('encryptStep1');
            UI.show('encryptStep2');
            UI.updateStep(2);

            UI.updateProgress(mode, 20, 'Checking file...');
            const selResult = await API.encrypt.select(State.selectedFiles.encrypt);

            UI.updateProgress(mode, 50, 'Encrypting and saving...');
            const finalResult = await API.encrypt.process(selResult.fileId);

            UI.updateProgress(mode, 100, 'Complete!');

            // UI Transition to Step 3 (Delayed for UX)
            setTimeout(() => {
                UI.hide('encryptStep2');
                UI.show('encryptStep3');
                UI.updateStep(3);
                this.renderEncryptionResults(finalResult);
                this.refreshFileList();
            }, 500);

        } catch (error) {
            UI.showError(error.message);
            this.resetToStep1(mode);
        }
    },

    renderEncryptionResults(result) {
        const setText = (id, txt) => {
            const el = UI.getElement(id);
            if (el) el.textContent = txt;
        };

        setText('resultOriginalName', result.originalFilename || '-');
        setText('resultOriginalSize', UI.formatFileSize(result.originalSize));
        setText('resultEncryptedSize', UI.formatFileSize(result.encryptedSize));
        setText('resultEncryptedName', result.encryptedFilename || '-');

        const dekEl = UI.getElement('resultEncryptedDek');
        if (dekEl) {
            dekEl.textContent = result.encryptedDek || 'Error';
            dekEl.style.color = result.encryptedDek ? 'white' : '#ff6b6b';
        }

        // Setup Downloads
        const btnFile = UI.getElement('downloadEncryptedFileBtn');
        if (btnFile) {
            btnFile.href = `/api/files/download/${encodeURIComponent(result.encryptedFilename)}`;
            btnFile.setAttribute('download', result.encryptedFilename);
        }

        const btnDek = UI.getElement('downloadDekBtn');
        if (btnDek) {
            const dekName = result.originalFilename + '.dek';
            btnDek.href = `/api/files/download/${encodeURIComponent(dekName)}`;
            btnDek.setAttribute('download', dekName);
        }
    },

    // -------------------------------------------------------------------------
    // DECRYPTION FLOW
    // -------------------------------------------------------------------------
    async processDecryption() {
        const { file, dek } = State.selectedFiles.decrypt;
        if (!file || !dek) return;
        const mode = 'decrypt';

        try {
            UI.hide('decryptStep1');
            UI.show('decryptStep2');
            UI.updateStep(2);

            UI.updateProgress(mode, 20, 'Checking files...');
            const selResult = await API.decrypt.select(file, dek);

            UI.updateProgress(mode, 50, 'Decrypting and saving...');
            const finalResult = await API.decrypt.process(selResult.fileId);

            UI.updateProgress(mode, 100, 'Complete!');

            setTimeout(() => {
                UI.hide('decryptStep2');
                UI.show('decryptStep3');
                UI.updateStep(3);
                this.renderDecryptionResults(finalResult);
                this.refreshFileList();
            }, 500);

        } catch (error) {
            UI.showError(error.message);
            this.resetToStep1(mode);
        }
    },

    renderDecryptionResults(result) {
        const setText = (id, txt) => {
            const el = UI.getElement(id);
            if (el) el.textContent = txt;
        };
        setText('resultDecryptedName', result.originalFilename);
        // Note: Decryption result might not return sizes in same structure, adjusting if needed
        // Assuming it does based on previous code
    },

    // Helper to fallback
    resetToStep1(mode) {
        if (mode === 'encrypt') {
            UI.hide('encryptStep2');
            UI.show('encryptStep1');
        } else {
            UI.hide('decryptStep2');
            UI.show('decryptStep1');
        }
        UI.updateStep(1);
    }
};

// ==========================================
// 5. BOOTSTRAP
// ==========================================
// Expose functions to global scope for HTML onclick handlers
window.selectMode = (m) => App.selectMode(m);
window.refreshFileList = () => App.refreshFileList();
window.uploadFiles = () => App.uploadFiles();
window.resetWizard = () => App.resetWizard();
window.restartCurrentMode = () => App.restartCurrentMode();
window.processEncryption = () => App.processEncryption();
window.processDecryption = () => App.processDecryption();

// Expose Settings via App for HTML onclick handlers
window.App = {
    selectMode: (m) => App.selectMode(m),
    resetWizard: () => App.resetWizard(),
    Settings: Settings
};

// Initialize App
App.init();
