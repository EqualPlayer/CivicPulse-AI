
let sb;
let session;

const $ = id => document.getElementById(id);

function esc(v) {
    return String(v ?? '').replace(/[&<>"']/g, c => ({
        '&':'&amp;','<':'&lt;','>':'&gt;',
        '"':'&quot;',"'":'&#39;'
    })[c]);
}

async function api(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            Authorization: `Bearer ${session.access_token}`,
            ...(options.body ? {'Content-Type':'application/json'} : {}),
            ...options.headers
        }
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Request failed.');
    return data;
}

async function loadAssignedReports() {
    const data = await api('/api/staff/reports');
    const reports = data.reports || [];

    if (!reports.length) {
        $('reportList').innerHTML =
            '<div class="card">No complaints have been assigned to you yet.</div>';
        $('message').textContent = 'You are up to date.';
        return;
    }

    $('message').textContent = `${reports.length} assigned complaint(s).`;

    $('reportList').innerHTML = reports.map(r => `
        <article class="card">
            <h2>${esc(r.complaint_title)}</h2>
            <p class="muted">${esc(r.id)} · ${esc(r.location)}</p>
            <span class="pill">${esc(r.status)}</span>

            <div class="grid" style="margin-top:20px">
                <div>
                    ${
                        r.evidence_url
                        ? `<img src="${esc(r.evidence_url)}" alt="Complaint evidence">`
                        : '<p class="muted">No stored photograph available.</p>'
                    }
                    <p><b>Category:</b> ${esc(r.category)}</p>
                    <p><b>AI severity:</b> ${esc(r.severity)}</p>
                    <p><b>Department:</b> ${esc(r.recommended_department)}</p>
                    <p><b>Citizen description:</b><br>${esc(r.user_description)}</p>
                    <p><b>Complaint:</b><br>${esc(r.complaint_body)}</p>
                </div>

                <div>
                    <label>Status</label>
                    <select data-status="${esc(r.id)}">
                        ${['pending','under_review','in_progress','resolved','rejected'].map(s =>
                            `<option value="${s}" ${r.status===s?'selected':''}>${s.replace(/_/g,' ')}</option>`
                        ).join('')}
                    </select>

                    <label>Official remark (required)</label>
                    <textarea data-remark="${esc(r.id)}"
                        placeholder="Describe inspection, action taken or reason for rejection..."></textarea>

                    <button data-update="${esc(r.id)}">Update complaint</button>

                    <h3>Status history</h3>
                    <div data-history="${esc(r.id)}">Loading history…</div>
                </div>
            </div>
        </article>
    `).join('');

    for (const r of reports) {
        loadHistory(r.id);
    }

    document.querySelectorAll('[data-update]').forEach(button => {
        button.addEventListener('click', async () => {
            const id = button.dataset.update;
            const status = document.querySelector(`[data-status="${CSS.escape(id)}"]`).value;
            const remark = document.querySelector(`[data-remark="${CSS.escape(id)}"]`).value.trim();

            if (remark.length < 5) {
                $('message').textContent = 'Please enter an official remark of at least 5 characters.';
                $('message').className = 'error';
                return;
            }

            button.disabled = true;

            try {
                await api(`/api/staff/reports/${encodeURIComponent(id)}/status`, {
                    method:'PATCH',
                    body:JSON.stringify({status,remark})
                });

                $('message').textContent = 'Complaint updated successfully.';
                $('message').className = 'muted';
                await loadAssignedReports();

            } catch (error) {
                $('message').textContent = error.message;
                $('message').className = 'error';
            } finally {
                button.disabled = false;
            }
        });
    });
}

async function loadHistory(id) {
    try {
        const data = await api(
            `/api/staff/reports/${encodeURIComponent(id)}/history`
        );

        const target = document.querySelector(
            `[data-history="${CSS.escape(id)}"]`
        );

        if (!target) return;

        target.innerHTML = (data.history || []).map(h => `
            <div class="history">
                <b>${esc(h.new_status.replace(/_/g,' '))}</b>
                <p>${esc(h.remark)}</p>
                <small class="muted">${esc(h.created_at)}</small>
            </div>
        `).join('') || '<p class="muted">No history available.</p>';

    } catch (error) {
        const target = document.querySelector(
            `[data-history="${CSS.escape(id)}"]`
        );
        if (target) target.textContent = error.message;
    }
}

async function initialize() {
    const response = await fetch('/api/config');
    if (!response.ok) throw new Error('Supabase configuration unavailable.');

    const config = await response.json();
    const {createClient} = await import(
        'https://esm.sh/@supabase/supabase-js@2'
    );

    sb = createClient(config.supabase_url, config.supabase_publishable_key);

    const result = await sb.auth.getSession();
    session = result.data.session;

    if (!session) {
        location.replace('/');
        return;
    }

    const identity = await api('/api/auth/me');

    if (identity.user.role !== 'worker') {
        document.body.innerHTML =
            '<h2 style="padding:35px">Access denied. Worker account required.</h2>';
        return;
    }

    await loadAssignedReports();
}

$('logoutBtn').addEventListener('click', async () => {
    if (sb) await sb.auth.signOut();
    location.replace('/');
});

initialize().catch(error => {
    console.error('[CivicPulse Worker]', error);
    $('message').textContent = error.message;
    $('message').className = 'error';
});

// Refresh assigned complaints automatically.
setInterval(() => {
    if (!document.hidden && session) {
        loadAssignedReports();
    }
}, 15000);