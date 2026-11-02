
let sb;
let adminSession;
let reports = [];
let workers = [];

const $ = id => document.getElementById(id);

function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;',
        '"': '&quot;', "'": '&#39;'
    })[char]);
}

async function api(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            Authorization: `Bearer ${adminSession.access_token}`,
            ...(options.body ? { 'Content-Type': 'application/json' } : {}),
            ...options.headers
        }
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || `Request failed: ${response.status}`);
    }

    return data;
}

function message(text, error = false) {
    $('message').textContent = text;
    $('message').className = error ? 'error' : 'muted';
}

async function loadDashboard() {
    const [reportData, stats] = await Promise.all([
        api('/api/staff/reports'),
        api('/api/public/statistics')
    ]);

    reports = reportData.reports || [];

    $('total').textContent = stats.total;
    $('pending').textContent = stats.status_counts.pending || 0;
    $('progress').textContent = stats.status_counts.in_progress || 0;
    $('resolved').textContent = stats.status_counts.resolved || 0;

    renderReports();
    message(`Loaded ${reports.length} complaints.`);
}

async function loadWorkers() {
    const data = await api('/api/admin/users');
    const users = data.users || [];

    workers = users.filter(
        user => user.role === 'worker' && user.is_active
    );

    $('staffList').innerHTML = users.map(user => `
        <div class="card">
            <strong>${esc(user.display_name)}</strong>
            <span class="pill">${esc(user.role)}</span>
            <span class="pill">${user.is_active ? 'Active' : 'Inactive'}</span>
            ${
                user.role === 'citizen'
                    ? `<button data-promote="${esc(user.id)}">Approve as worker</button>`
                    : ''
            }
        </div>
    `).join('') || 'No registered accounts found.';

    document.querySelectorAll('[data-promote]').forEach(button => {
        button.addEventListener('click', async () => {
            if (!confirm('Approve this citizen as a worker?')) return;

            try {
                await api(
                    `/api/admin/users/${encodeURIComponent(button.dataset.promote)}/role`,
                    {
                        method: 'PATCH',
                        body: JSON.stringify({ role: 'worker' })
                    }
                );

                message('Worker account approved.');
                await loadWorkers();
            } catch (error) {
                message(error.message, true);
            }
        });
    });
}

function renderReports() {
    const filter = $('filter').value;

    const visible = reports.filter(report =>
        filter === 'all' || report.status === filter
    );

    if (!visible.length) {
        $('complaints').innerHTML =
            '<div class="card">No complaints in this category.</div>';
        return;
    }

    $('complaints').innerHTML = visible.map(report => {
        const workerOptions = workers.map(worker => `
            <option value="${esc(worker.id)}"
                ${report.assigned_to === worker.id ? 'selected' : ''}>
                ${esc(worker.display_name)}
            </option>
        `).join('');

        return `
            <article class="card">
                <div class="toolbar">
                    <h2>${esc(report.complaint_title)}</h2>
                    <span class="pill">${esc(report.status)}</span>
                </div>

                <p class="muted">
                    ${esc(report.id)} · ${esc(report.location)}
                </p>

                <div class="complaint">
                    <div>
                        ${
                            report.evidence_url
                                ? `<img src="${esc(report.evidence_url)}" alt="Complaint evidence">`
                                : '<p class="muted">No stored photograph available.</p>'
                        }

                        <p><strong>Category:</strong> ${esc(report.category)}</p>
                        <p><strong>Severity:</strong> ${esc(report.severity)}</p>
                        <p><strong>Department:</strong> ${esc(report.recommended_department)}</p>
                        <p><strong>Citizen description:</strong><br>${esc(report.user_description)}</p>
                        <p><strong>Complaint:</strong><br>${esc(report.complaint_body)}</p>
                    </div>

                    <div>
                        <label>Assign worker</label>
                        <select data-worker="${esc(report.id)}">
                            <option value="">Unassigned</option>
                            ${workerOptions}
                        </select>
                        <button data-assign="${esc(report.id)}">Save assignment</button>

                        <label>Update complaint status</label>
                        <select data-status="${esc(report.id)}">
                            ${[
                                'pending', 'under_review', 'in_progress',
                                'resolved', 'rejected'
                            ].map(status => `
                                <option value="${status}"
                                    ${report.status === status ? 'selected' : ''}>
                                    ${status.replace(/_/g, ' ')}
                                </option>
                            `).join('')}
                        </select>

                        <label>Official remark (required)</label>
                        <textarea data-remark="${esc(report.id)}"
                            placeholder="Enter inspection findings or official action taken..."></textarea>

                        <button data-update="${esc(report.id)}">
                            Save status and remark
                        </button>

                        <p class="muted">
                            Previous remark: ${esc(report.current_remark || 'None')}
                        </p>
                    </div>
                </div>
            </article>
        `;
    }).join('');

    document.querySelectorAll('[data-update]').forEach(button => {
        button.addEventListener('click', async () => {
            const id = button.dataset.update;
            const status = document.querySelector(`[data-status="${CSS.escape(id)}"]`).value;
            const remark = document.querySelector(`[data-remark="${CSS.escape(id)}"]`).value.trim();

            if (remark.length < 5) {
                return message('Enter an official remark of at least 5 characters.', true);
            }

            button.disabled = true;

            try {
                await api(
                    `/api/staff/reports/${encodeURIComponent(id)}/status`,
                    {
                        method: 'PATCH',
                        body: JSON.stringify({ status, remark })
                    }
                );

                message('Complaint status updated.');
                await loadDashboard();
            } catch (error) {
                message(error.message, true);
            } finally {
                button.disabled = false;
            }
        });
    });

    document.querySelectorAll('[data-assign]').forEach(button => {
        button.addEventListener('click', async () => {
            const id = button.dataset.assign;
            const workerId = document.querySelector(
                `[data-worker="${CSS.escape(id)}"]`
            ).value;

            if (!workerId) {
                return message('Select a worker before assigning.', true);
            }

            try {
                await api(
                    `/api/admin/reports/${encodeURIComponent(id)}/assign`,
                    {
                        method: 'PATCH',
                        body: JSON.stringify({ worker_id: workerId })
                    }
                );

                message('Complaint assigned successfully.');
                await loadDashboard();
            } catch (error) {
                message(error.message, true);
            }
        });
    });
}

async function initializeAdmin() {
    const configResponse = await fetch('/api/config');
    if (!configResponse.ok) throw new Error('Authentication configuration unavailable.');

    const config = await configResponse.json();

    const { createClient } = await import(
        'https://esm.sh/@supabase/supabase-js@2'
    );

    sb = createClient(
        config.supabase_url,
        config.supabase_publishable_key
    );

    const { data, error } = await sb.auth.getSession();
    if (error) throw error;

    adminSession = data.session;

    if (!adminSession) {
        location.replace('/');
        return;
    }

    const identity = await api('/api/auth/me');

    if (identity.user.role !== 'admin') {
        document.body.innerHTML =
            '<h2 style="padding:40px">Access denied. Administrator account required.</h2>';
        return;
    }

    $('adminIdentity').textContent =
        identity.user.email || 'Administrator';

    await loadWorkers();
    await loadDashboard();

    $('filter').addEventListener('change', renderReports);
    $('refreshBtn').addEventListener('click', async () => {
        await loadWorkers();
        await loadDashboard();
    });

    $('logoutBtn').addEventListener('click', async () => {
        await sb.auth.signOut();
        location.replace('/');
    });
}

initializeAdmin().catch(error => {
    console.error('[CivicPulse Admin]', error);
    message(error.message || 'Could not load administration dashboard.', true);
});

// Refresh the administration dashboard automatically.
setInterval(() => {
    if (!document.hidden && adminSession) {
        loadDashboard();
    }
}, 15000);