function formatRupiah(num) {
    if (num === null || num === undefined) num = 0;
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(num);
}

function formatTanggal(str) {
    try {
        const d = new Date(str);
        if (isNaN(d)) return str;
        return d.toLocaleDateString('id-ID', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return str;
    }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    const icon = toast.querySelector('.toast-icon');
    const msg = document.getElementById('toast-message');
    
    msg.textContent = message;
    toast.className = `toast show ${type}`;
    
    if (type === 'success') {
        icon.innerHTML = '<i class="fa-solid fa-circle-check"></i>';
    } else {
        icon.innerHTML = '<i class="fa-solid fa-circle-xmark"></i>';
    }
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// ---- API Centralized Fetch Requests ----

async function apiGet(url) {
    const res = await fetch(url);
    if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
    }
    return res.json();
}

async function apiPost(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    const data = await res.json();
    return { ok: res.ok, data };
}

async function apiDelete(url) {
    const res = await fetch(url, { method: 'DELETE' });
    const data = await res.json();
    return { ok: res.ok, data };
}

// Beranda: Saldo & Ringkasan

let saldoData = { saldo: 0, totalMasuk: 0, totalKeluar: 0 };
let saldoVisible = true;

function applySaldoVisibility() {
    const saldoEl = document.getElementById('saldo-amount');
    const masukEl = document.getElementById('total-masuk');
    const keluarEl = document.getElementById('total-keluar');
    const toggleBtn = document.getElementById('toggle-saldo');
    const icon = toggleBtn ? toggleBtn.querySelector('i') : null;

    if (saldoVisible) {
        if (saldoEl) saldoEl.textContent = formatRupiah(saldoData.saldo || 0);
        if (masukEl) masukEl.textContent = formatRupiah(saldoData.totalMasuk || 0);
        if (keluarEl) keluarEl.textContent = formatRupiah(saldoData.totalKeluar || 0);
        if (icon) {
            icon.className = 'fa-regular fa-eye';
            toggleBtn.title = 'Sembunyikan saldo';
            toggleBtn.setAttribute('aria-label', 'Sembunyikan saldo');
        }
    } else {
        if (saldoEl) saldoEl.textContent = 'Rp •••••';
        if (masukEl) masukEl.textContent = 'Rp •••••';
        if (keluarEl) keluarEl.textContent = 'Rp •••••';
        if (icon) {
            icon.className = 'fa-regular fa-eye-slash';
            toggleBtn.title = 'Tampilkan saldo';
            toggleBtn.setAttribute('aria-label', 'Tampilkan saldo');
        }
    }
}

async function initBeranda() {
    const toggleBtn = document.getElementById('toggle-saldo');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            saldoVisible = !saldoVisible;
            applySaldoVisibility();
        });
    }

    await loadBerandaSaldoDanRingkasan();
    await loadBerandaAnalitik();
}

async function loadBerandaSaldoDanRingkasan() {
    try {
        const data = await apiGet('/api/ringkasan');
        saldoData = {
            saldo: data.saldo || 0,
            totalMasuk: data.total_masuk || 0,
            totalKeluar: data.total_keluar || 0
        };
        applySaldoVisibility();
    } catch (e) {
        console.error('Gagal memuat ringkasan saldo:', e);
    }
}

async function loadBerandaAnalitik() {
    try {
        const data = await apiGet('/api/analitik');
        const container = document.getElementById('chart-container');
        if (!container) return;

        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="chart-empty">
                    <i class="fa-solid fa-chart-pie"></i>
                    <p>Belum ada data pengeluaran bulan ini</p>
                </div>`;
            return;
        }

        container.innerHTML = '<canvas id="analitikChart"></canvas>';
        const ctx = document.getElementById('analitikChart').getContext('2d');
        const colors = ['#1a73e8', '#ef4444', '#f59e0b', '#22c55e', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.kategori),
                datasets: [{
                    data: data.map(d => d.total),
                    backgroundColor: colors.slice(0, data.length),
                    borderWidth: 1,
                    borderColor: '#ffffff',
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 10,
                            usePointStyle: true,
                            font: { family: 'Poppins', size: 10 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${formatRupiah(context.parsed)}`;
                            }
                        }
                    }
                }
            }
        });
    } catch (e) {
        console.error('Gagal memuat grafik analitik:', e);
    }
}

// Transaksi pemasukan pengeluaran
function initTransaksiForm(tipe) {
    const form = document.getElementById('transaksi-form');
    if (!form) return;

    // Set default tanggal ke hari ini
    const tglInput = document.getElementById('tanggal');
    if (tglInput) {
        tglInput.value = new Date().toISOString().split('T')[0];
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const jumlahInput = document.getElementById('jumlah');
        const keteranganInput = document.getElementById('keterangan');
        const jumlah = parseFloat(jumlahInput.value);
        const keterangan = keteranganInput.value.trim();

        if (!jumlah || jumlah <= 0) {
            showToast('Nominal harus lebih besar dari 0', 'error');
            return;
        }
        if (!keterangan) {
            showToast('Kategori keterangan harus diisi', 'error');
            return;
        }

        try {
            const { ok, data } = await apiPost('/api/transaksi', {
                tipe: tipe,
                jumlah: jumlah,
                keterangan: keterangan
            });

            if (ok) {
                showToast(data.message || 'Transaksi berhasil disimpan!');
                form.reset();
                if (tglInput) {
                    tglInput.value = new Date().toISOString().split('T')[0];
                }
            } else {
                showToast(data.message || 'Gagal menyimpan transaksi', 'error');
            }
        } catch (err) {
            console.error('Error saat menyimpan transaksi:', err);
            showToast('Koneksi terputus', 'error');
        }
    });
}

// Catatan

async function initCatatan() {
    const textarea = document.getElementById('catatan-textarea');
    const btnSave = document.getElementById('btn-save-catatan');
    const saveStatus = document.getElementById('save-status');
    
    if (!textarea) return;

    // Load initial note
    try {
        const data = await apiGet('/api/catatan');
        textarea.value = data.konten || '';
    } catch (e) {
        console.error('Gagal memuat catatan:', e);
    }

    // Helper to display save status
    function setSaveStatus(state) {
        if (!saveStatus) return;
        saveStatus.classList.add('visible');
        if (state === 'saving') {
            saveStatus.className = 'save-status visible saving';
            saveStatus.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Menyimpan...';
        } else if (state === 'saved') {
            saveStatus.className = 'save-status visible saved';
            saveStatus.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Tersimpan';
            setTimeout(() => {
                saveStatus.classList.remove('visible');
            }, 2000);
        } else if (state === 'error') {
            saveStatus.className = 'save-status visible error';
            saveStatus.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Gagal menyimpan';
        }
    }

    // Save logic
    async function saveNoteAction(showNotification = false) {
        setSaveStatus('saving');
        try {
            const { ok, data } = await apiPost('/api/catatan', {
                konten: textarea.value
            });
            if (ok) {
                setSaveStatus('saved');
                if (showNotification) {
                    showToast('Catatan berhasil disimpan!');
                }
            } else {
                setSaveStatus('error');
                if (showNotification) {
                    showToast(data.message || 'Gagal menyimpan catatan', 'error');
                }
            }
        } catch (err) {
            console.error(err);
            setSaveStatus('error');
            if (showNotification) {
                showToast('Koneksi terputus', 'error');
            }
        }
    }

    // Autosave with debounce (1.5 seconds)
    let autosaveTimeout;
    textarea.addEventListener('input', () => {
        setSaveStatus('saving');
        clearTimeout(autosaveTimeout);
        autosaveTimeout = setTimeout(() => {
            saveNoteAction(false);
        }, 1500);
    });

    // Manual save
    if (btnSave) {
        btnSave.addEventListener('click', () => {
            saveNoteAction(true);
        });
    }
}

// Target tabungan

async function initTarget() {
    await loadTargetList();

    const form = document.getElementById('target-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const namaInput = document.getElementById('target-nama');
            const nominalInput = document.getElementById('target-nominal');
            const nama = namaInput.value.trim();
            const nominal = parseFloat(nominalInput.value);

            if (!nama) {
                showToast('Nama target tabungan harus diisi', 'error');
                return;
            }
            if (!nominal || nominal <= 0) {
                showToast('Nominal target harus lebih dari 0', 'error');
                return;
            }

            try {
                const { ok, data } = await apiPost('/api/target', {
                    nama: nama,
                    nominal_target: nominal
                });
                if (ok) {
                    showToast(data.message || 'Target berhasil dibuat!');
                    form.reset();
                    await loadTargetList();
                } else {
                    showToast(data.message || 'Gagal menyimpan target', 'error');
                }
            } catch (err) {
                console.error(err);
                showToast('Koneksi terputus', 'error');
            }
        });
    }

    // Setup modal event listener
    const closeModalBtn = document.getElementById('btn-close-modal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }

    const modalSubmitBtn = document.getElementById('btn-submit-tambah-dana');
    if (modalSubmitBtn) {
        modalSubmitBtn.addEventListener('click', submitTambahDana);
    }
}

async function loadTargetList() {
    const list = document.getElementById('target-list');
    if (!list) return;

    try {
        const data = await apiGet('/api/target');
        if (data.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-bullseye"></i>
                    <p>Belum ada target tabungan yang ditambahkan.</p>
                </div>`;
            return;
        }

        list.innerHTML = data.map(t => {
            const persen = t.nominal_target > 0 ? Math.min((t.terkumpul / t.nominal_target) * 100, 100) : 0;
            const isComplete = persen >= 100;
            return `
                <div class="target-card">
                    <div class="target-card-header">
                        <span class="target-name">${t.nama}</span>
                        <span class="target-badge ${isComplete ? 'completed' : 'in-progress'}">
                            ${isComplete ? '✓ Tercapai' : Math.round(persen) + '%'}
                        </span>
                    </div>
                    <div class="target-amounts">
                        <span>Terkumpul: <span class="collected">${formatRupiah(t.terkumpul)}</span></span>
                        <span>Target: ${formatRupiah(t.nominal_target)}</span>
                    </div>
                    <div class="progress-bar-track">
                        <div class="progress-bar-fill ${isComplete ? 'completed' : ''}" style="width: ${persen}%"></div>
                    </div>
                    <div class="target-actions">
                        ${!isComplete ? `
                        <button class="btn btn-primary btn-sm" onclick="openTambahDana(${t.id})">
                            <i class="fa-solid fa-plus"></i> Tambah Dana
                        </button>
                        ` : ''}
                        <button class="btn btn-outline btn-sm" onclick="hapusTarget(${t.id})" title="Hapus target">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>`;
        }).join('');
    } catch (e) {
        console.error('Gagal memuat target list:', e);
    }
}

function openTambahDana(id) {
    const modal = document.getElementById('modal-tambah-dana');
    if (!modal) return;
    modal.dataset.targetId = id;
    modal.classList.add('active');

    const input = document.getElementById('tambah-dana-jumlah');
    if (input) {
        input.value = '';
        input.focus();
    }
}

function closeModal() {
    const modal = document.getElementById('modal-tambah-dana');
    if (modal) {
        modal.classList.remove('active');
    }
}

async function submitTambahDana() {
    const modal = document.getElementById('modal-tambah-dana');
    const targetId = modal ? modal.dataset.targetId : null;
    const input = document.getElementById('tambah-dana-jumlah');
    const jumlah = parseFloat(input ? input.value : 0);

    if (!targetId) return;
    if (!jumlah || jumlah <= 0) {
        showToast('Masukkan nominal dana yang valid', 'error');
        return;
    }

    try {
        const { ok, data } = await apiPost(`/api/target/${targetId}/tambah`, { jumlah });
        if (ok) {
            showToast('Dana tabungan berhasil ditambahkan!');
            closeModal();
            await loadTargetList();
        } else {
            showToast(data.message || 'Gagal menambahkan dana', 'error');
        }
    } catch (err) {
        console.error(err);
        showToast('Koneksi terputus', 'error');
    }
}

async function hapusTarget(id) {
    openConfirmModal({
        title: 'Hapus Target Tabungan?',
        message: 'Target tabungan ini akan dihapus permanen. Lanjutkan?',
        confirmText: 'Hapus',
        cancelText: 'Batal',
        onConfirm: async () => {
            try {
                const { ok, data } = await apiDelete(`/api/target/${id}`);
                if (ok) {
                    showToast('Target tabungan telah dihapus');
                    await loadTargetList();
                } else {
                    showToast(data.message || 'Gagal menghapus target', 'error');
                }
            } catch (err) {
                console.error(err);
                showToast('Koneksi terputus', 'error');
            }
        }
    });
}

// riwayat transaksi

function openConfirmModal(options) {
    const modal = document.getElementById('confirm-modal');
    const titleEl = modal ? modal.querySelector('.modal-title') : null;
    const messageEl = modal ? modal.querySelector('.modal-message') : null;
    const btnCancel = document.getElementById('confirm-cancel');
    const btnAccept = document.getElementById('confirm-accept');

    if (!modal || !btnCancel || !btnAccept) {
        const confirmed = window.confirm(options.message || 'Apakah Anda yakin?');
        if (confirmed) {
            if (typeof options.onConfirm === 'function') options.onConfirm();
        } else if (typeof options.onCancel === 'function') {
            options.onCancel();
        }
        return;
    }

    if (titleEl) titleEl.textContent = options.title || 'Konfirmasi';
    if (messageEl) messageEl.textContent = options.message || 'Apakah Anda yakin?';
    btnAccept.textContent = options.confirmText || 'Ya';
    btnCancel.textContent = options.cancelText || 'Batal';

    function cleanup() {
        modal.classList.remove('active');
        btnCancel.removeEventListener('click', handleCancel);
        btnAccept.removeEventListener('click', handleAccept);
        modal.removeEventListener('click', handleOverlayClick);
    }

    function handleCancel() {
        cleanup();
        if (typeof options.onCancel === 'function') options.onCancel();
    }

    async function handleAccept() {
        cleanup();
        if (typeof options.onConfirm === 'function') await options.onConfirm();
    }

    function handleOverlayClick(event) {
        if (event.target === modal) {
            cleanup();
        }
    }

    btnCancel.addEventListener('click', handleCancel);
    btnAccept.addEventListener('click', handleAccept);
    modal.addEventListener('click', handleOverlayClick);
    modal.classList.add('active');
}

async function initRiwayat() {
    await loadRiwayatAktivitas();

    const btnReset = document.getElementById('btn-reset');
    if (btnReset) {
        btnReset.addEventListener('click', () => {
            openConfirmModal({
                title: 'Hapus Semua Riwayat?',
                message: 'Semua transaksi dalam riwayat akan dihapus permanen. Lanjutkan?',
                confirmText: 'Hapus',
                cancelText: 'Batal',
                onConfirm: async () => {
                    try {
                        const { ok, data } = await apiDelete('/api/delete');
                        if (ok) {
                            showToast('Seluruh riwayat berhasil direset');
                            await loadRiwayatAktivitas();
                        } else {
                            showToast(data.message || 'Gagal mereset data', 'error');
                        }
                    } catch (e) {
                        showToast('Koneksi terputus', 'error');
                    }
                }
            });
        });
    }
}

async function loadRiwayatAktivitas() {
    const list = document.getElementById('riwayat-list');
    if (!list) return;

    try {
        const data = await apiGet('/api/riwayat');
        if (data.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-receipt"></i>
                    <p>Belum ada riwayat transaksi.</p>
                </div>`;
            return;
        }

        list.innerHTML = data.map(item => {
            const isIncome = item.tipe === 'pemasukan';
            const prefix = isIncome ? '+' : '-';
            const typeClass = isIncome ? 'income' : 'expense';
            const icon = isIncome ? 'fa-arrow-down' : 'fa-arrow-up';
            return `
                <div class="riwayat-item">
                    <div class="riwayat-icon ${typeClass}">
                        <i class="fa-solid ${icon}"></i>
                    </div>
                    <div class="riwayat-details">
                        <div class="riwayat-desc">${item.keterangan}</div>
                        <div class="riwayat-date">${formatTanggal(item.tanggal)}</div>
                    </div>
                    <div class="riwayat-amount ${typeClass}">
                        ${prefix} ${formatRupiah(item.jumlah)}
                    </div>
                </div>`;
        }).join('');
    } catch (e) {
        console.error('Gagal memuat riwayat:', e);
    }
}

// copyright

function initFooterYear() {
    document.querySelectorAll('[data-copyright-year]').forEach((el) => {
        el.textContent = new Date().getFullYear();
    });
}

// page initialization based on data-page attribute

document.addEventListener('DOMContentLoaded', () => {
    initFooterYear();
    const page = document.body.dataset.page;

    switch (page) {
        case 'beranda':
            initBeranda();
            break;
        case 'pemasukan':
            initTransaksiForm('pemasukan');
            break;
        case 'pengeluaran':
            initTransaksiForm('pengeluaran');
            break;
        case 'catatan':
            initCatatan();
            break;
        case 'target':
            initTarget();
            break;
        case 'riwayat':
            initRiwayat();
            break;
    }
});
