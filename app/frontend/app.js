// Telegram WebApp
const tg = window.Telegram?.WebApp;

// Localhost/development rejimini aniqlash
const isLocalhost = window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname.includes('192.168.');

// Telegram WebApp tekshiruvi - localhost'da yumshoqroq
const isTelegramWebApp = !!(tg && tg.initData && tg.initData.length > 0);
const isDevMode = isLocalhost && !isTelegramWebApp;

console.log('Environment check:', {
    tg: !!tg,
    initData: tg?.initData,
    initDataLength: tg?.initData?.length,
    isTelegramWebApp,
    isLocalhost,
    isDevMode
});

if (isTelegramWebApp) {
    tg.ready();
    tg.expand();
}

// State
let currentUser = null;
let isAdmin = false;
let statsChart = null;
let authToken = localStorage.getItem('authToken');
let authType = isTelegramWebApp ? 'telegram' : 'browser';

// API Helper
async function api(endpoint, options = {}) {
    const url = `${API_URL}${endpoint}`;
    console.log('API call:', url);

    const headers = {
        'Content-Type': 'application/json'
    };

    // Auth header
    if (isTelegramWebApp) {
        headers['X-Telegram-Init-Data'] = tg.initData;
        console.log('Using Telegram auth');
    } else if (authToken) {
        headers['X-Browser-Token'] = authToken;
        console.log('Using browser token');
    } else if (isDevMode) {
        // Localhost dev rejimida test uchun
        headers['X-Dev-Mode'] = 'true';
        console.log('Using dev mode (no auth header)');
    }

    try {
        console.log('Fetching...', { url, options, headers });
        const response = await fetch(url, { ...options, headers });
        console.log('Response status:', response.status);

        if (!response.ok) {
            const error = await response.json();
            console.error('API error response:', error);
            throw new Error(error.detail || 'Xatolik yuz berdi');
        }
        const data = await response.json();
        console.log('API response:', data);
        return data;
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

function showAuthMessage(message, isError = false) {
    const msgEl = document.getElementById('auth-message');
    msgEl.textContent = message;
    msgEl.className = `auth-message ${isError ? 'error' : 'success'}`;
    msgEl.classList.remove('hidden');
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

// Browser Auth
document.getElementById('show-register')?.addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
    document.getElementById('auth-message').classList.add('hidden');
});

document.getElementById('show-login')?.addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('auth-message').classList.add('hidden');
});

document.getElementById('register-btn')?.addEventListener('click', async () => {
    const username = document.getElementById('register-username').value.trim();
    if (!username) {
        showAuthMessage('Username kiriting', true);
        return;
    }

    try {
        const result = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const data = await result.json();

        if (!result.ok) {
            showAuthMessage(data.detail || 'Xatolik', true);
            return;
        }

        showAuthMessage('✅ ' + data.message);
        document.getElementById('register-username').value = '';
    } catch (error) {
        showAuthMessage(error.message, true);
    }
});

document.getElementById('login-btn')?.addEventListener('click', async () => {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value.trim();

    if (!username || !password) {
        showAuthMessage('Username va parol kiriting', true);
        return;
    }

    try {
        const result = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await result.json();

        if (!result.ok) {
            showAuthMessage(data.detail || 'Xatolik', true);
            return;
        }

        // Token saqlash
        authToken = data.token;
        localStorage.setItem('authToken', authToken);
        currentUser = data.user;

        // App ga o'tish
        await initMainApp();
    } catch (error) {
        showAuthMessage(error.message, true);
    }
});

// Logout
function logout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    showScreen('login-screen');
}

// Initialize App
async function init() {
    console.log('Init started, isTelegramWebApp:', isTelegramWebApp);

    if (isTelegramWebApp) {
        // Telegram WebApp - to'g'ridan-to'g'ri init
        console.log('Telegram WebApp detected, calling initMainApp...');
        await initMainApp();
    } else {
        // Browser - auth tekshirish
        console.log('Browser mode, authToken:', authToken ? 'exists' : 'null');
        if (authToken && authToken !== 'null' && authToken !== 'undefined') {
            try {
                console.log('Auth token found, checking with API...');
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000);

                const check = await api('/auth/check', { signal: controller.signal });
                clearTimeout(timeoutId);

                console.log('Auth check result:', check);
                if (check.authenticated) {
                    currentUser = check.user;
                    await initMainApp();
                    return;
                }
            } catch (e) {
                console.error('Auth check error:', e);
                localStorage.removeItem('authToken');
                authToken = null;
            }
        }
        console.log('Showing login screen...');
        showScreen('login-screen');
    }
}

async function initMainApp() {
    console.log('initMainApp started...');
    try {
        // Get current user
        if (!currentUser) {
            console.log('Fetching current user...');
            currentUser = await api('/users/me');
            console.log('Current user:', currentUser);
        }

        // Check admin status
        console.log('Checking admin status...');
        const adminCheck = await api('/users/is-admin');
        console.log('Admin check:', adminCheck);
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

        // Browser uchun logout tugmasi
        if (!isTelegramWebApp) {
            addLogoutButton();
        }

        // Avval asosiy ekranga o'tish - loader'ni to'xtatish
        showScreen('main-app');

        // Keyin ma'lumotlarni yuklash (xato bo'lsa ham ekran ko'rinadi)
        loadDashboard().catch(err => console.error('Dashboard error:', err));
        loadReportHistory().catch(err => console.error('Report history error:', err));
        initDateInputs();
    } catch (error) {
        console.error('Init error:', error);
        if (!isTelegramWebApp) {
            localStorage.removeItem('authToken');
            showScreen('login-screen');
            showAuthMessage(error.message, true);
        } else {
            showError(error.message);
        }
    }
}

function addLogoutButton() {
    const header = document.querySelector('header');
    if (!document.getElementById('logout-btn')) {
        const btn = document.createElement('button');
        btn.id = 'logout-btn';
        btn.className = 'btn small danger';
        btn.textContent = '🚪 Chiqish';
        btn.onclick = logout;
        header.appendChild(btn);
    }
}

// Dashboard
async function loadDashboard() {
    try {
        const sessionData = await api('/sessions/today');
        updateSessionUI(sessionData.session);

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
        showAlert('✅ Sessiya boshlandi!');
    } catch (error) {
        showAlert(error.message);
    }
});

document.getElementById('end-session-btn').addEventListener('click', async () => {
    try {
        const session = await api('/sessions/end', { method: 'POST' });
        updateSessionUI(session);
        showAlert('✅ Sessiya tugatildi!');
    } catch (error) {
        showAlert(error.message);
    }
});

// Alert helper
function showAlert(message) {
    if (isTelegramWebApp && tg.showAlert) {
        tg.showAlert(message);
    } else {
        alert(message);
    }
}

// Location
document.getElementById('send-location-btn').addEventListener('click', () => {
    if (!navigator.geolocation) {
        showAlert('Geolokatsiya qo\'llab-quvvatlanmaydi');
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
                    showAlert(result.message);
                } else {
                    document.getElementById('location-status').innerHTML = `
                        <p>📍 ${result.is_inside_office ? '🏢 Ofisda' : '🚶 Ofis tashqarisida'}</p>
                        <p>Vaqt: ${new Date(result.timestamp).toLocaleTimeString()}</p>
                    `;
                    showAlert('✅ Joylashuv saqlandi!');
                }
            } catch (error) {
                showAlert(error.message);
            }
        },
        () => showAlert('Joylashuvni aniqlab bo\'lmadi')
    );
});

// Reports
document.getElementById('submit-report-btn').addEventListener('click', async () => {
    const content = document.getElementById('report-content').value.trim();
    if (!content) {
        showAlert('Hisobot bo\'sh bo\'lishi mumkin emas');
        return;
    }

    try {
        await api('/reports/submit', {
            method: 'POST',
            body: JSON.stringify({ content })
        });
        showAlert('✅ Hisobot topshirildi!');
        document.getElementById('report-content').value = '';
        loadReportHistory();
        loadDashboard();
    } catch (error) {
        showAlert(error.message);
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
        showAlert('Sanalarni tanlang');
        return;
    }

    try {
        const stats = await api('/statistics/me', {
            method: 'POST',
            body: JSON.stringify({ start_date: startDate, end_date: endDate })
        });

        document.getElementById('stats-summary').innerHTML = `
            <div class="stat-item"><div class="value">${stats.total_days}</div><div class="label">Kunlar</div></div>
            <div class="stat-item"><div class="value">${Math.round(stats.total_online_minutes / 60)}</div><div class="label">Onlayn (soat)</div></div>
            <div class="stat-item"><div class="value">${Math.round(stats.total_office_minutes / 60)}</div><div class="label">Ofisda (soat)</div></div>
            <div class="stat-item"><div class="value">${stats.total_late_minutes}</div><div class="label">Kechikish (daq)</div></div>
            <div class="stat-item"><div class="value">${Math.round(stats.attendance_rate)}%</div><div class="label">Davomat</div></div>
            <div class="stat-item"><div class="value">${stats.total_early_leave_minutes}</div><div class="label">Erta ketish (daq)</div></div>
        `;

        const chartData = await api('/statistics/chart/me', {
            method: 'POST',
            body: JSON.stringify({ start_date: startDate, end_date: endDate })
        });
        renderChart(chartData);
    } catch (error) {
        showAlert(error.message);
    }
}

function renderChart(data) {
    const ctx = document.getElementById('stats-chart').getContext('2d');
    if (statsChart) statsChart.destroy();

    statsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: data.datasets.map(ds => ({ ...ds, fill: false, tension: 0.1 }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } } },
            scales: { x: { ticks: { font: { size: 10 } } }, y: { beginAtZero: true, ticks: { font: { size: 10 } } } }
        }
    });
}

// Admin Functions
async function loadAdminData() {
    try {
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
                <div class="name">${u.first_name} ${u.last_name || ''} ${u.username ? `(@${u.username})` : ''}</div>
                <div class="type">${u.auth_type === 'browser' ? '🌐 Browser' : '📱 Telegram'}</div>
                <div class="actions">
                    <button class="approve" onclick="approveUser('${u.telegram_id || u.username}', ${u.telegram_id ? 'true' : 'false'})">✅</button>
                    <button class="block" onclick="blockUser('${u.telegram_id || u.username}', ${u.telegram_id ? 'true' : 'false'})">⛔</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Pending users error:', error);
    }
}

async function approveUser(id, isTelegramId) {
    try {
        const endpoint = isTelegramId ? `/users/${id}/status` : `/users/username/${id}/status`;
        const result = await api(endpoint, {
            method: 'PUT',
            body: JSON.stringify({ status: 'active' })
        });

        if (result.password) {
            showAlert(`✅ Tasdiqlandi!\n\nParol: ${result.password}\n\nBu parolni foydalanuvchiga yuboring.`);
        } else {
            showAlert('✅ Tasdiqlandi');
        }
        loadPendingUsers();
    } catch (error) {
        showAlert(error.message);
    }
}

async function blockUser(id, isTelegramId) {
    try {
        const endpoint = isTelegramId ? `/users/${id}/status` : `/users/username/${id}/status`;
        await api(endpoint, {
            method: 'PUT',
            body: JSON.stringify({ status: 'blocked' })
        });
        showAlert('⛔ Bloklandi');
        loadPendingUsers();
    } catch (error) {
        showAlert(error.message);
    }
}

// Settings
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
        showAlert('✅ Saqlandi');
    } catch (error) {
        showAlert(error.message);
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
        showAlert('✅ Saqlandi');
    } catch (error) {
        showAlert(error.message);
    }
});

document.getElementById('load-all-stats-btn').addEventListener('click', async () => {
    const startDate = document.getElementById('admin-stat-start').value;
    const endDate = document.getElementById('admin-stat-end').value;

    if (!startDate || !endDate) {
        showAlert('Sanalarni tanlang');
        return;
    }

    try {
        const data = await api('/statistics/all', {
            method: 'POST',
            body: JSON.stringify({ start_date: startDate, end_date: endDate })
        });

        document.getElementById('all-users-stats').innerHTML = data.map(item => `
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
        showAlert(error.message);
    }
});

// Start App
console.log('App.js loaded, API_URL:', API_URL);
init().catch(err => {
    console.error('Init failed:', err);
    showError(err.message);
});
