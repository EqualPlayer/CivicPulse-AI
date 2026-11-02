
const $ = (id) => document.getElementById(id);
let latestAnalysis = null;
let selectedImage = null;

function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  window.setTimeout(() => el.classList.remove('show'), 3200);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

$('issueImage').addEventListener('change', (event) => {
  const file = event.target.files?.[0];
  selectedImage = file || null;
  const preview = $('imagePreview');
  if (!file) {
    preview.hidden = true;
    preview.removeAttribute('src');
    $('dropzone').classList.remove('has-image');
    return;
  }
  if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 8 * 1024 * 1024) {
    toast('Choose a JPG, PNG or WEBP image under 8 MB.');
    event.target.value = '';
    selectedImage = null;
    return;
  }
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  $('dropzone').classList.add('has-image');
});


$('analyzeBtn').addEventListener('click', async () => {
    if (!selectedImage) {
        return toast('Please add a photo first.');
    }

    if ($('location').value.trim().length < 3) {
        return toast('Please enter the issue location.');
    }

    const button = $('analyzeBtn');

    button.disabled = true;
    button.innerHTML =
        '<span class="spinner">◌</span> Analysing image with AI…';

    const form = new FormData();
    form.append('image', selectedImage);
    form.append('location', $('location').value.trim());
    form.append('description', $('description').value.trim());
    form.append('language', $('language').value);

    try {
        console.log('[CivicPulse] Sending image to Gemini...');

        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: form,
            signal: AbortSignal.timeout(95000)
        });

        const responseText = await response.text();

        let payload;

        try {
            payload = JSON.parse(responseText);
        } catch {
            throw new Error(
                `Invalid server response (HTTP ${response.status}).`
            );
        }

        if (!response.ok) {
            throw new Error(
                payload.detail || 'AI analysis failed.'
            );
        }

        if (!payload.analysis) {
            throw new Error(
                'The server response does not contain AI analysis.'
            );
        }

        latestAnalysis = payload.analysis;

        console.log('[CivicPulse] AI analysis received:', latestAnalysis);

        renderAnalysis(latestAnalysis);

        toast('AI analysis complete! Review your complaint.');

    } catch (error) {
        console.error('[CivicPulse] Analysis error:', error);

        if (
            error.name === 'TimeoutError' ||
            error.name === 'AbortError'
        ) {
            toast('Analysis timed out. Please try again.');
        } else {
            toast(error.message || 'AI analysis failed.');
        }

    } finally {
        button.disabled = false;
        button.innerHTML =
            '<span>✦</span> Analyse with AI <span class="btn-arrow">→</span>';
    }
});


function renderAnalysis(data) {
  $('emptyState').hidden = true;
  $('analysisContent').hidden = false;
  $('categoryValue').textContent = data.category;
  $('severityValue').textContent = data.severity;
  $('severityValue').className = `severity-${String(data.severity).toLowerCase()}`;
  $('confidenceValue').textContent = `${Math.round(Number(data.confidence) * 100)}%`;
  $('observationValue').textContent = data.image_observation;
  $('severityReasonValue').textContent = data.severity_reason;
  $('departmentValue').textContent = data.recommended_department;
  $('departmentCaveat').textContent = data.department_caveat;
  $('complaintTitle').value = data.complaint_title;
  $('complaintBody').value = data.complaint_body;
  $('missingInfo').textContent = data.missing_information?.length ? `Consider adding: ${data.missing_information.join('; ')}` : '';
  $('resultPanel').scrollIntoView({behavior:'smooth',block:'nearest'});
}


$('saveBtn').addEventListener('click', async () => {
    if (!latestAnalysis || !selectedImage) {
        return toast('Analyse an image first.');
    }

    if (!window.supabaseAuth) {
        return toast('Authentication is not initialized.');
    }

    const { data: { session } } =
        await window.supabaseAuth.auth.getSession();

    if (!session) {
        return toast('Please sign in before submitting a complaint.');
    }

    const button = $('saveBtn');
    button.disabled = true;
    button.textContent = 'Saving complaint securely…';

    const editedAnalysis = {
        ...latestAnalysis,
        complaint_title: $('complaintTitle').value.trim(),
        complaint_body: $('complaintBody').value.trim(),
    };

    const form = new FormData();
    form.append('analysis', JSON.stringify(editedAnalysis));
    form.append('location', $('location').value.trim());
    form.append('description', $('description').value.trim());
    form.append('image', selectedImage, selectedImage.name);

    try {
        const response = await fetch('/api/reports', {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${session.access_token}`
            },
            body: form
        });

        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.detail || 'Complaint submission failed.');
        }

        toast(`Complaint submitted: ${payload.report.id}`);

        latestAnalysis = null;
        selectedImage = null;

        $('issueImage').value = '';
        $('imagePreview').hidden = true;
        $('imagePreview').removeAttribute('src');
        $('dropzone').classList.remove('has-image');
        $('description').value = '';
        $('analysisContent').hidden = true;
        $('emptyState').hidden = false;

        await loadReports();

    } catch (error) {
        console.error('[CivicPulse] Report submission:', error);
        toast(error.message || 'Could not submit complaint.');
    } finally {
        button.disabled = false;
        button.innerHTML = 'Approve & save report <span>→</span>';
    }
});




async function loadReports() {
    try {
        const statsResponse = await fetch('/api/public/statistics');
        const stats = await statsResponse.json();

        if (!statsResponse.ok) {
            throw new Error(stats.detail || 'Statistics unavailable.');
        }

        $('totalCount').textContent = stats.total;
        $('priorityCount').textContent = stats.high_priority;

        if (!window.supabaseAuth) return;

        const { data: { session } } =
            await window.supabaseAuth.auth.getSession();

        if (!session) {
            $('reportsList').innerHTML =
                '<div class="reports-empty">Sign in to track your complaints.</div>';
            return;
        }
        const meResponse = await fetch('/api/auth/me', {
    headers: {
        Authorization: `Bearer ${session.access_token}`
    }
});

const meData = await meResponse.json();

if (!meResponse.ok) {
    throw new Error(meData.detail || 'Authentication failed.');
}

const role = meData.user.role;

        // Always show only this account's own complaints.
        const endpoint = role === 'citizen'
    ? '/api/my-reports'
    : '/api/staff/reports';

const response = await fetch(endpoint, {
            headers: {
                Authorization: `Bearer ${session.access_token}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Could not load complaints.');
        }

        if (!data.reports.length) {
            $('reportsList').innerHTML =
                '<div class="reports-empty">No complaints submitted by this account yet.</div>';
            return;
        }

        $('reportsList').innerHTML = data.reports.map(report => {
            const status = String(report.status || 'pending')
                .replace(/_/g, ' ');

            const date = report.created_at
                ? new Date(report.created_at).toLocaleString()
                : 'Date unavailable';

            const completionDate = report.resolved_at
                ? new Date(report.resolved_at).toLocaleString()
                : '';

            return `
                <div class="report-row">
                    <div class="report-main">
                        <strong>${escapeHtml(report.complaint_title)}</strong>
                        <small>${escapeHtml(report.id)} · ${escapeHtml(date)}</small>
                    </div>

                    <div class="report-cell">
                        ${escapeHtml(report.category)}
                        <small>${escapeHtml(report.location)}</small>
                    </div>

                    <div>
                        <span class="pill ${escapeHtml(status.replace(/ /g, '-'))}">
                            ${escapeHtml(status)}
                        </span>
                    </div>

                    <div class="report-cell">
                        <strong>Official update</strong>
                        <small>${escapeHtml(report.current_remark || 'Awaiting review.')}</small>
                        ${completionDate
                            ? `<small>Resolved: ${escapeHtml(completionDate)}</small>`
                            : ''}
                    </div>

                    <div class="report-history">
                        <button type="button"
                            data-history="${escapeHtml(report.id)}">
                            View status history
                        </button>
                        <div data-history-content="${escapeHtml(report.id)}" hidden></div>
                    </div>
                </div>
            `;
        }).join('');

        document.querySelectorAll('[data-history]').forEach(button => {
            button.addEventListener('click', async () => {
                const id = button.dataset.history;
                const box = document.querySelector(
                    `[data-history-content="${CSS.escape(id)}"]`
                );

                if (!box.hidden) {
                    box.hidden = true;
                    return;
                }

                box.hidden = false;

                if (box.dataset.loaded === 'true') return;

                button.disabled = true;
                box.textContent = 'Loading complaint history…';

                try {
                    const historyResponse = await fetch(
                        role === 'citizen'
    ? `/api/my-reports/${encodeURIComponent(id)}/history`
    : `/api/staff/reports/${encodeURIComponent(id)}/history`,
                        {
                            headers: {
                                Authorization: `Bearer ${session.access_token}`
                            }
                        }
                    );

                    const historyData = await historyResponse.json();

                    if (!historyResponse.ok) {
                        throw new Error(
                            historyData.detail || 'History unavailable.'
                        );
                    }

                    box.innerHTML = historyData.history.length
                        ? historyData.history.map(item => `
                            <div class="history-entry">
                                <strong>${escapeHtml(
                                    item.new_status.replace(/_/g, ' ')
                                )}</strong>
                                <p>${escapeHtml(item.remark)}</p>
                                <small>${escapeHtml(
                                    new Date(item.created_at).toLocaleString()
                                )}</small>
                            </div>
                        `).join('')
                        : '<p>No status history available.</p>';

                    box.dataset.loaded = 'true';

                } catch (error) {
                    box.textContent = error.message;
                } finally {
                    button.disabled = false;
                }
            });
        });

    } catch (error) {
        console.error('[CivicPulse Dashboard]', error);
        $('reportsList').innerHTML =
            `<div class="reports-empty">${escapeHtml(error.message)}</div>`;
    }
}


async function loadHealth() {
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    $('systemStatus').textContent = data.ai_key_configured ? `Backend ready · ${data.provider}` : `Backend ready · ${data.provider} key missing`;
    $('databaseMode').textContent = data.database === 'supabase' ? 'Supabase' : 'Local SQLite';
  } catch {
    $('systemStatus').textContent = 'Backend unavailable';
  }
}

$('refreshBtn').addEventListener('click', loadReports);
loadHealth();
loadReports();

let supabaseAuth = null;
let authMode = 'signin';

const authBackdrop = $('authBackdrop');

function authMessage(message, isError = false) {
    $('authMessage').textContent = message;
    $('authMessage').style.color = isError ? '#b3433d' : '#176b53';
}

function setAuthMode(mode) {
    authMode = mode;

    const signup = mode === 'signup';

    $('authNameWrap').hidden = !signup;

    $('authSignInTab').classList.toggle('active', !signup);
    $('authSignUpTab').classList.toggle('active', signup);

    $('authTitle').textContent = signup
        ? 'Create your account'
        : 'Welcome to CivicPulse';

    $('authSubmitBtn').textContent = signup
        ? 'Create citizen account'
        : 'Sign in';

    authMessage('');
}

function updateAuthUI(user) {
    $('authOpenBtn').hidden = !!user;
    $('signedInEmail').hidden = !user;
    $('authSignOutBtn').hidden = !user;

    $('signedInEmail').textContent =
        user ? user.email || 'Signed in' : '';

    if (user) {
        authBackdrop.hidden = true;
    }
    if (window.supabaseAuth) {
    loadReports();
}
}

$('authOpenBtn').addEventListener('click', () => {
    setAuthMode('signin');
    authBackdrop.hidden = false;
});

$('authCloseBtn').addEventListener('click', () => {
    authBackdrop.hidden = true;
});

authBackdrop.addEventListener('click', (event) => {
    if (event.target === authBackdrop) {
        authBackdrop.hidden = true;
    }
});

$('authSignInTab').addEventListener('click', () => {
    setAuthMode('signin');
});

$('authSignUpTab').addEventListener('click', () => {
    setAuthMode('signup');
});

async function initializeAuthentication() {
  const { createClient } = await import(
    'https://esm.sh/@supabase/supabase-js@2'
);
    const configResponse = await fetch('/api/config');

    if (!configResponse.ok) {
        throw new Error('Supabase configuration unavailable.');
    }

    const config = await configResponse.json();

    if (
        !config.supabase_url ||
        !config.supabase_publishable_key
    ) {
        throw new Error('Supabase configuration is incomplete.');
    }

    supabaseAuth = createClient(
        config.supabase_url,
        config.supabase_publishable_key
    );
    window.supabaseAuth = supabaseAuth;

    const { data, error } = await supabaseAuth.auth.getSession();

    if (error) throw error;

    updateAuthUI(data.session?.user || null);

    supabaseAuth.auth.onAuthStateChange((_event, session) => {
        updateAuthUI(session?.user || null);
    });

    console.log('[CivicPulse] Authentication initialized.');
}

$('authForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    if (!supabaseAuth) {
        return authMessage('Authentication is not configured.', true);
    }

    const button = $('authSubmitBtn');

    const email = $('authEmail').value.trim();
    const password = $('authPassword').value;
    const name = $('authName').value.trim();

    if (authMode === 'signup' && !name) {
        return authMessage('Please enter your full name.', true);
    }

    button.disabled = true;
    authMessage('Please wait...');

    try {
        if (authMode === 'signup') {
            const { data, error } = await supabaseAuth.auth.signUp({
                email,
                password,
                options: {
                    data: {
                        full_name: name
                    },
                    emailRedirectTo: window.location.origin
                }
            });

            if (error) throw error;

            if (data.session) {
                authMessage('Account created and signed in.');
                toast('Welcome to CivicPulse!');
                authBackdrop.hidden = true;
            } else {
                authMessage(
                    'Registration successful. Please check your email to confirm your account.'
                );
            }
        } else {
            const { error } =
                await supabaseAuth.auth.signInWithPassword({
                    email,
                    password
                });

            if (error) throw error;

            authBackdrop.hidden = true;
            toast('Signed in successfully.');
        }
    } catch (error) {
        authMessage(error.message || 'Authentication failed.', true);
        console.error('[CivicPulse Auth]', error);
    } finally {
        button.disabled = false;
    }
});

$('googleSignInBtn').addEventListener('click', async () => {
    if (!supabaseAuth) {
        return authMessage('Supabase is not initialized.', true);
    }

    try {
        const { error } =
            await supabaseAuth.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: window.location.origin
                }
            });

        if (error) throw error;

    } catch (error) {
        authMessage(error.message, true);
        console.error('[Google OAuth]', error);
    }
});

$('authSignOutBtn').addEventListener('click', async () => {
    if (!supabaseAuth) return;

    const { error } = await supabaseAuth.auth.signOut();

    if (error) {
        toast(error.message);
    } else {
        toast('Signed out successfully.');
    }
});

initializeAuthentication().catch((error) => {
    console.error('[CivicPulse Auth Initialization]', error);

    $('authOpenBtn').disabled = true;

    toast('Could not connect to authentication service.');
});

// Automatically refresh complaint status every 15 seconds.
setInterval(() => {
    if (!document.hidden) {
        loadReports();
    }
}, 15000);