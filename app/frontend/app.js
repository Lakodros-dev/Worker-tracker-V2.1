// Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Debug - ekranda ko'rsatish
const debugDiv = document.createElement('div');
debugDiv.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#000;color:#0f0;padding:10px;font-size:12px;z-index:9999;max-height:200px;overflow:auto;';
debugDiv.innerHTML = `
<b>DEBUG:</b><br>
initData: ${tg.initData ? tg.initData.substring(0, 100) + '...' : 'BO\'SH!'}<br>
user: ${JSON.stringify(tg.initDataUnsafe?.user || 'YO\'Q')}
`;
document.body.appendChild(debugDiv);

// State
let currentUser = null;
let isAdmin = false;
let statsChart = null;

// API Helper
async function api(endpoint, options = {}) {
    const url = `${API_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': tg.initData
    };

    try {
        const response = await fetch(url, { ...options, headers });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Xatolik yuz berdi');
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Screen Management
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    showScreen('error-screen');
}

// Tab Management
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
    });
});

// Initialize App
async function init() {
    try {
        // Get current user
        currentUser = await api('/users/me');

        // Check admin status
        const adminCheck = await api('/users/is-admin');
        isAdmin = adminCheck.is_admin;

        // Update UI
        document.getElementById('user-name').textContent =
            `${currentUser.first_name} ${currentUser.last_name || ''}`.trim();
        document.getElementById('user-status').textContent =
            currentUser.status === 'active' ? '✅ Faol' : '⏳ Kutilmoqda';

        if (isAdmin) {
            document.getElementById('admin-badge').classList.remove('hidden');
            document.getElementById('admin-tab').style.display = 'block';
            loadAdminData();
        }

        // Load initial data
        await loadDashboard();
        await loadReportHistory();
        initDateInputs();

        showScreen('main-app');
    } catch (error) {
        showError(error.message);
    }
}

// Dashboard
async function loadDashboard() {
    try {
        // Load session
        const sessionData = await api('/sessions/today');
        updateSessionUI(sessionData.session);

        // Load report status
        const reportStatus = await api('/reports/status');
        document.getElementById('report-status').innerHTML = reportStatus.submitted
            ? '<p>✅ Hisobot topshirilgan</p>'
            : '<p>⏳ Hisobot topshirilmagan</p>';
    } catch (error) {
        console.error('Dashboard error:', error);
    }
}

function updateSessionUI(session) {
    const sessionInfo = document.getElementById('session-info');
    const startBtn = document.getElementById('start-session-btn');
    const endBtn = document.getElementById('end-session-btn');

    if (session) {
        sessionInfo.innerHTML = `
            <p>🕐 Boshlangan: ${session.start_time || '—'}</p>
            <p>⏱ Onlayn: ${session.total_online_minutes} daqiqa</p>
            <p>🏢 Ofisda: ${session.total_office_minutes} daqiqa</p>
            <p>⚠️ Kechikish: ${session.late_arrival_minutes} daqiqa</p>
            <p>📊 Status: ${session.status}</p>
        `;

        if (session.status === 'online') {
            startBtn.classList.add('hidden');
            endBtn.classList.remove('hidden');
        } else {
            startBtn.classList.remove('hidden');
            endBtn.classList.add('hidden');
        }
    } else {
        sessionInfo.innerHTML = '<p>Sessiya boshlanmagan</p>';
        startBtn.classList.remove('hidden');
        endBtn.classList.add('hidden');
    }
}

// Session Actions
document.getElementById('start-session-btn').addEventListener('click', async () => {
    try {
        const session = await api('/sessions/start', { method: 'POST' });
        updateSessionUI(session);
        tg.showAlert('✅ Sessiya boshlandi!');
    } catch (error) {
        tg.showAlert(error.message);
    }
});

document.getElementById('end-session-btn').addEventListener('click', async () => {
    try {
        const session = await api('/sessions/end', { method: 'POST' });
        updateSessionUI(session);
        tg.showAlert('✅ Sessiya tugatildi!');
    } catch (error) {
        tg.showAlert(error.message);
    }
});

// Location
document.getElementById('send-location-btn').addEventListener('click', () => {
    if (!navigator.geolocation) {
        tg.showAlert('Geolokatsiya qo\'llab-quvvatlanmaydi');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            try {
                const result = await api('/locations/record', {
                    method: 'POST',
                    body: JSON.stringify({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    })
                });

                if (result.recorded === false) {
                    tg.showAlert(result.message);
                } else {
                    document.getElementById('location-status').innerHTML = `
                        <p>📍 ${result.is_inside_office ? '🏢 Ofisda' : '🚶 Ofis tashqarisida'}</p>
                        <p>Vaqt: ${new Date(result.timestamp).toLocaleTimeString()}</p>
                    `;
                    tg.showAlert('✅ Joylashuv saqlandi!');
                }
            } catch (error) {
                tg.showAlert(error.message);
            }
        },
        (error) => {
            tg.showAlert('Joylashuvni aniqlab bo\'lmadi');
        }
    );
});

// Reports
document.getElementById('submit-report-btn').addEventListener('click', async () => {
    const content = document.getElementById('report-content').value.trim();
    if (!content) {
        tg.showAlert('Hisobot bo\'sh bo\'lishi mumkin emas');
        return;
    }

    try {
        await api('/reports/submit', {
            method: 'POST',
            body: JSON.stringify({ content })
        });
        tg.showAlert('✅ Hisobot topshirildi!');
        document.getElementById('report-content').value = '';
        loadReportHistory();
        loadDashboard();
    } catch (error) {
        tg.showAlert(error.message);
    }
});

async function loadReportHistory() {
    try {
        const reports = await api('/reports/history');
        const container = document.getElementById('report-history');

        if (reports.length === 0) {
            container.innerHTML = '<p>Hisobotlar yo\'q</p>';
            return;
        }

        container.innerHTML = reports.slice(0, 10).map(r => `
            <div class="report-item">
                <div class="date">${r.date}</div>
                <div>${r.content.substring(0, 100)}${r.content.length > 100 ? '...' : ''}</div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Report history error:', error);
    }
}

// Statistics
function initDateInputs() {
    const today = new Date();
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);

    const formatDate = d => d.toISOString().split('T')[0];

    document.getElementById('stat-start-date').value = formatDate(weekAgo);
    document.getElementById('stat-end-date').value = formatDate(today);
    document.getElementById('admin-stat-start').value = formatDate(weekAgo);
    document.getElementById('admin-stat-end').value = formatDate(today);
}

document.getElementById('load-stats-btn').addEventListener('click', loadStatistics);

async function loadStatistics() {
    const startDate = document.getElementById('stat-start-date').value;
    const endDate = document.getElementById('stat-end-date').value;

    if (!startDate || !endDate) {
        tg.showAlert('Sanalarni tanlang');
        return;
    }

    try {
        // Load summary
        const stats = await api('/statistics/me', {
            method: 'POST',
            body: JSON.stringify({ start_date: startDate, end_date: endDate })
        });

        document.getElementById('stats-summary').innerHTML = `
            <div class="stat-item">
                <div class="value">${stats.total_days}</div>
                <div class="label">Kunlar</div>
            </div>
            <div class="stat-item">
                <div class="value">${Math.round(stats.total_online_minutes / 60)}</div>
                <div class="label">Onlayn (soat)</div>
            </div>
            <div class="stat-item">
                <div class="value">${Math.round(stats.total_office_minutes / 60)}</div>
                <div class="label">Ofisda (soat)</div>
            </div>
            <div class="stat-item">
                <div class="value">${stats.total_late_minutes}</div>
                <div class="label">Kechikish (daq)</div>
            </div>
            <div class="stat-item">
                <div class="value">${Math.round(stats.attendance_rate)}%</div>
                <div class="label">Davomat</div>
            </div>
            <div class="stat-item">
                <div class="value">${stats.total_early_leave_minutes}</div>
                <div class="label">Erta ketish (daq)</div>
            </div>
        `;

        // Load chart
        const chartData = await api('/statistics/chart/me', {
            method: 'POST',
            body: JSON.stringify({ start_date: startDate, end_date: endDate })
        });

        renderChart(chartData);
    } catch (error) {
        tg.showAlert(error.message);
    }
}

function renderChart(data) {
    const ctx = document.getElementById('stats-chart').getContext('2d');

    if (statsChart) {
        statsChart.destroy();
    }

    statsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: data.datasets.map(ds => ({
                ...ds,
                fill: false,
                tension: 0.1
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { size: 10 } }
                }
            },
            scales: {
                x: { ticks: { font: { size: 10 } } },
                y: { beginAtZero: true, ticks: { font: { size: 10 } } }
            }
        }
    });
}

// Admin Functions
async function loadAdminData() {
    try {
        // Load settings
        const settings = await api('/settings');
        document.getElementById('work-start').value = settings.work_start;
        document.getElementById('work-end').value = settings.work_end;
        document.getElementById('lunch-start').value = settings.lunch_start;
        document.getElementById('lunch-end').value = settings.lunch_end;

        if (settings.geofence) {
            document.getElementById('geo-lat').value = settings.geofence.center_lat;
            document.getElementById('geo-lng').value = settings.geofence.center_lng;
            document.getElementById('geo-radius').value = settings.geofence.radius_meters;
        }

        // Load pending users
        loadPendingUsers();
    } catch (error) {
        console.error('Admin data error:', error);
    }
}

async function loadPendingUsers() {
    try {
        const users = await api('/users/pending');
        const container = document.getElementById('pending-users');

        if (users.length === 0) {
            container.innerHTML = '<p>Kutilayotgan foydalanuvchilar yo\'q</p>';
            return;
        }

        container.innerHTML = users.map(u => `
            <div class="user-item">
                <div class="name">${u.first_name} ${u.last_name || ''}</div>
                <div class="actions">
                    <button class="approve" onclick="approveUser(${u.telegram_id})">✅</button>
                    <button class="block" onclick="blockUser(${u.telegram_id})">⛔</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Pending users error:', error);
    }
}

async function approveUser(userId) {
    try {
        await api(`/users/${userId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status: 'active' })
        });
        tg.showAlert('✅ Tasdiqlandi');
        loadPendingUsers();
    } catch (error) {
        tg.showAlert(error.message);
    }
}

async function blockUser(userId) {
    try {
        await api(`/users/${userId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status: 'blocked' })
        });
        tg.showAlert('⛔ Bloklandi');
        loadPendingUsers();
    } catch (error) {
        tg.showAlert(error.message);
    }
}

// Save Settings
document.getElementById('save-settings-btn').addEventListener('click', async () => {
    try {
        await api('/settings', {
            method: 'PUT',
            body: JSON.stringify({
                work_start: document.getElementById('work-start').value,
                work_end: document.getElementById('work-end').value,
                lunch_start: document.getElementById('lunch-start').value,
                lunch_end: document.getElementById('lunch-end').value
            })
        });
        tg.showAlert('✅ Saqlandi');
    } catch (error) {
        tg.showAlert(error.message);
    }
});

document.getElementById('save-geofence-btn').addEventListener('click', async () => {
    try {
        await api('/settings', {
            method: 'PUT',
            body: JSON.stringify({
                geofence: {
                    center_lat: parseFloat(document.getElementById('geo-lat').value),
                    center_lng: parseFloat(document.getElementById('geo-lng').value),
                    radius_meters: parseFloat(document.getElementById('geo-radius').value)
                }
            })
        });
        tg.showAlert('✅ Saqlandi');
    } catch (error) {
        tg.showAlert(error.message);
    }
});

// Load All Users Stats
document.getElementById('load-all-stats-btn').addEventListener('click', async () => {
    const startDate = document.getElementById('admin-stat-start').value;
    const endDate = document.getElementById('admin-stat-end').value;

    if (!startDate || !endDate) {
        tg.showAlert('Sanalarni tanlang');
        return;
    }

    try {
        const data = await api('/statistics/all', {
            method: 'POST',
            body: JSON.stringify({ start_date: startDate, end_date: endDate })
        });

        const container = document.getElementById('all-users-stats');
        container.innerHTML = data.map(item => `
            <div class="user-stat-item">
                <div class="name">${item.user.first_name} ${item.user.last_name || ''}</div>
                <div class="stats">
                    <span>Kunlar: ${item.statistics.total_days}</span>
                    <span>Onlayn: ${Math.round(item.statistics.total_online_minutes / 60)}s</span>
                    <span>Ofisda: ${Math.round(item.statistics.total_office_minutes / 60)}s</span>
                    <span>Kechikish: ${item.statistics.total_late_minutes}d</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        tg.showAlert(error.message);
    }
});

// Start App
init();
