document.addEventListener('DOMContentLoaded', () => {
    // Register Service Worker
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js').then((registration) => {
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
            }, (error) => {
                console.log('ServiceWorker registration failed: ', error);
            });
        });
    }

    const loginForm = document.getElementById('login-form');
    const loginSection = document.getElementById('login-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const loginError = document.getElementById('login-error');
    const loginBtn = loginForm.querySelector('button');
    const loader = loginBtn.querySelector('.loader');
    const btnText = loginBtn.querySelector('.btn-text');
    const logoutBtn = document.getElementById('logout-btn');

    let currentData = null;
    let attendanceChart = null;
    let analysisData = null;
    let currentUsername = '';
    let currentPassword = '';

    // Auto-login if credentials exist in localStorage
    checkAutoLogin();

    // Check for saved credentials and auto-login
    async function checkAutoLogin() {
        const saved = localStorage.getItem('lnctu_credentials');
        if (saved) {
            try {
                const creds = JSON.parse(saved);
                // Check if not expired (1 month = 30 days)
                const oneMonth = 30 * 24 * 60 * 60 * 1000;
                if (Date.now() - creds.savedAt < oneMonth) {
                    // Auto login
                    document.getElementById('username').value = creds.username;
                    document.getElementById('password').value = creds.password;
                    await performLogin(creds.username, creds.password);
                } else {
                    // Expired, remove it
                    localStorage.removeItem('lnctu_credentials');
                }
            } catch (e) {
                localStorage.removeItem('lnctu_credentials');
            }
        }
    }

    // Save credentials to localStorage
    function saveCredentials(username, password) {
        const creds = {
            username: username,
            password: password,
            savedAt: Date.now()
        };
        localStorage.setItem('lnctu_credentials', JSON.stringify(creds));
    }

    // Clear saved credentials
    function clearCredentials() {
        localStorage.removeItem('lnctu_credentials');
    }

    // Perform login
    async function performLogin(username, password) {
        currentUsername = username;
        currentPassword = password;

        setLoading(true);
        loginError.classList.add('hidden');

        try {
            const response = await fetch(`/attendance?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`);
            const result = await response.json();

            if (result.success) {
                currentData = result.data;
                showDashboardUI(currentData);
                await fetchAnalysis(username, password);
                // Save credentials for auto-login next time
                saveCredentials(username, password);
            } else {
                showError(result.detail || result.error || 'Login failed');
                clearCredentials();
            }
        } catch (err) {
            showError('Network error. Please try again.');
            clearCredentials();
        } finally {
            setLoading(false);
        }
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        await performLogin(username, password);
    });

    logoutBtn.addEventListener('click', () => {
        dashboardSection.classList.add('hidden-section');
        loginSection.classList.remove('hidden-section');
        loginSection.classList.add('active-section');
        loginForm.reset();
        currentData = null;
        // Clear saved credentials on logout
        clearCredentials();
    });

    document.getElementById('calc-btn').addEventListener('click', calculatePrediction);

    function setLoading(isLoading) {
        if (isLoading) {
            loader.classList.remove('hidden');
            btnText.classList.add('hidden');
            loginBtn.disabled = true;
        } else {
            loader.classList.add('hidden');
            btnText.classList.remove('hidden');
            loginBtn.disabled = false;
        }
    }

    function showError(msg) {
        loginError.textContent = msg;
        loginError.classList.remove('hidden');
    }

    function showDashboardUI(data) {
        loginSection.classList.add('hidden-section');
        loginSection.classList.remove('active-section');
        dashboardSection.classList.remove('hidden-section');
        dashboardSection.classList.add('active-section');

        renderDashboard(data);
    }

    function renderDashboard(data) {
        // Update Welcome Message
        const welcomeMsg = document.getElementById('welcome-message');
        const nameDisplay = document.getElementById('student-name-display');
        if (data.student_name && data.student_name !== '') {
            nameDisplay.textContent = data.student_name;
            welcomeMsg.classList.remove('hidden');
            welcomeMsg.style.display = 'inline-block';
        } else {
            welcomeMsg.classList.add('hidden');
            welcomeMsg.style.display = 'none';
        }

        // Update Stats
        document.getElementById('total-classes').textContent = data.total_classes;
        document.getElementById('present-classes').textContent = data.present;
        document.getElementById('absent-classes').textContent = data.absent;
        document.getElementById('overall-percentage').textContent = data.percentage + '%';

        // Render Chart
        renderChart(data.present, data.absent);

        // Render Date Wise Table
        renderDateWiseTable(data.datewise);
    }

    // Expose function to global scope for onclick
    window.showSubjectDetails = function (subjectName) {
        if (!currentData) return;

        const subject = currentData.subjects.find(s => s.name === subjectName);
        if (!subject) return;

        // Update Header
        document.getElementById('detail-subject-name').textContent = subjectName;

        // Update Stats
        document.getElementById('detail-total').textContent = subject.total;
        document.getElementById('detail-present').textContent = subject.present;
        document.getElementById('detail-absent').textContent = subject.absent;
        document.getElementById('detail-percentage').textContent = subject.percentage + '%';

        // Filter and Render History
        const history = currentData.datewise.filter(d => d.subject === subjectName);
        renderDetailTable(history);

        // Switch View
        dashboardSection.classList.add('hidden-section');
        document.getElementById('subject-details-section').classList.remove('hidden-section');
        document.getElementById('subject-details-section').classList.add('active-section');
    };

    function renderDetailTable(history) {
        const tbody = document.querySelector('#detail-table tbody');
        tbody.innerHTML = '';

        if (!history || history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;">No records found</td></tr>';
            return;
        }

        // Sort by date descending
        const sortedHistory = [...history].sort((a, b) => {
            const dateA = new Date(a.date);
            const dateB = new Date(b.date);
            return dateB - dateA;
        });

        sortedHistory.forEach(record => {
            const tr = document.createElement('tr');
            const statusClass = record.status.toLowerCase() === 'p' ? 'text-success' : 'text-danger';

            tr.innerHTML = `
                <td>${record.date}</td>
                <td>${record.lecture}</td>
                <td class="${statusClass}" style="font-weight:bold;">${record.status}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    document.getElementById('back-to-dashboard').addEventListener('click', () => {
        document.getElementById('subject-details-section').classList.add('hidden-section');
        document.getElementById('subject-details-section').classList.remove('active-section');
        dashboardSection.classList.remove('hidden-section');
    });

    function renderDateWiseTable(datewise) {
        const tbody = document.querySelector('#datewise-table tbody');
        tbody.innerHTML = '';

        if (!datewise || datewise.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No records found</td></tr>';
            return;
        }

        // Sort by date descending (most recent first)
        const sortedData = [...datewise].sort((a, b) => {
            const dateA = new Date(a.date);
            const dateB = new Date(b.date);
            return dateB - dateA; // Descending order
        });

        sortedData.forEach(record => {
            const tr = document.createElement('tr');
            const statusClass = record.status.toLowerCase() === 'p' ? 'text-success' : 'text-danger';

            tr.innerHTML = `
                <td>${record.date}</td>
                <td>${record.lecture}</td>
                <td>${record.subject}</td>
                <td class="${statusClass}" style="font-weight:bold;">${record.status}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    function getBadgeClass(percentage) {
        if (percentage >= 75) return 'badge-success';
        if (percentage >= 60) return 'badge-warning';
        return 'badge-danger';
    }

    function renderChart(present, absent) {
        const ctx = document.getElementById('attendanceDonut').getContext('2d');

        if (attendanceChart) {
            attendanceChart.destroy();
        }

        attendanceChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Present', 'Absent'],
                datasets: [{
                    data: [present, absent],
                    backgroundColor: ['#4ade80', '#f87171'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#fff' }
                    }
                }
            }
        });
    }

    function calculatePrediction() {
        if (!currentData) return;

        const CLASSES_PER_DAY = 7;
        const target = parseFloat(document.getElementById('target-percentage').value);
        const present = currentData.present;
        const total = currentData.total_classes;
        const currentPct = (present / total) * 100;
        const resultDiv = document.getElementById('prediction-result');

        if (currentPct >= target) {
            const bunkable = Math.floor(((100 * present) / target) - total);
            if (bunkable > 0) {
                const days = Math.floor(bunkable / CLASSES_PER_DAY);
                const extraClasses = bunkable % CLASSES_PER_DAY;
                let message = `<p style="color: #10b981">You can bunk <strong>${bunkable} classes</strong>`;
                if (days > 0) {
                    message += ` (<strong>${days} day${days > 1 ? 's' : ''}</strong>`;
                    if (extraClasses > 0) {
                        message += ` + <strong>${extraClasses} class${extraClasses > 1 ? 'es' : ''}</strong>`;
                    }
                    message += `)`;
                }
                message += ` and still maintain ${target}%.</p>`;
                resultDiv.innerHTML = message;
            } else {
                resultDiv.innerHTML = `<p style="color: #f59e0b">You are right on track! Don't miss any more if you want to keep it.</p>`;
            }
        } else {
            if (target >= 100) {
                resultDiv.innerHTML = `<p style="color: #ef4444">Target impossible if you have missed any class.</p>`;
                return;
            }

            const needed = Math.ceil(((target * total) - (100 * present)) / (100 - target));
            if (needed > 0) {
                const days = Math.floor(needed / CLASSES_PER_DAY);
                const extraClasses = needed % CLASSES_PER_DAY;
                let message = `<p style="color: #ef4444">You need to attend <strong>${needed} classes</strong>`;
                if (days > 0) {
                    message += ` (<strong>${days} day${days > 1 ? 's' : ''}</strong>`;
                    if (extraClasses > 0) {
                        message += ` + <strong>${extraClasses} class${extraClasses > 1 ? 'es' : ''}</strong>`;
                    }
                    message += `)`;
                }
                message += ` consecutively to reach ${target}%.</p>`;
                resultDiv.innerHTML = message;
            } else {
                resultDiv.innerHTML = `<p style="color: #f59e0b">Calculation error or already achieved.</p>`;
            }
        }
    }

    // ==============================
    // ANALYSIS & TIMETABLE FUNCTIONS
    // ==============================

    async function fetchAnalysis(username, password) {
        try {
            const response = await fetch(`/analysis?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`);
            const result = await response.json();
            if (result.success && result.data) {
                analysisData = result.data;
                renderAnalysis();
            }
        } catch (err) {
            console.error('Failed to fetch analysis:', err);
        }
    }

    async function fetchTimetable() {
        try {
            const response = await fetch('/timetable');
            const result = await response.json();
            if (result.success) {
                timetableData = result.data;
                renderTimetable();
            }
        } catch (err) {
            console.error('Failed to fetch timetable:', err);
        }
    }

    function renderAnalysis() {
        if (!analysisData) return;

        // Render summary cards
        const summaryDiv = document.getElementById('analysis-summary');
        const { summary } = analysisData;

        // Determine overall status class
        const overallStatusClass = summary.overall_status === 'GOOD' ? 'success' :
            summary.overall_status === 'WARNING' ? 'warning' : 'danger';

        summaryDiv.innerHTML = `
            <div class="analysis-card danger">
                <div class="analysis-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <div class="analysis-info">
                    <h4>At Risk</h4>
                    <p>${summary.at_risk_count} subjects</p>
                    <span class="analysis-sub">Below 75%</span>
                </div>
            </div>
            <div class="analysis-card success">
                <div class="analysis-icon"><i class="fa-solid fa-check-circle"></i></div>
                <div class="analysis-info">
                    <h4>Safe</h4>
                    <p>${summary.safe_count} subjects</p>
                    <span class="analysis-sub">Above 75%</span>
                </div>
            </div>
            ${summary.overall_percentage ? `
            <div class="analysis-card ${overallStatusClass}">
                <div class="analysis-icon"><i class="fa-solid ${summary.overall_status === 'GOOD' ? 'fa-thumbs-up' : summary.overall_status === 'WARNING' ? 'fa-hand' : 'fa-circle-exclamation'}"></i></div>
                <div class="analysis-info">
                    <h4>${summary.overall_percentage}% Overall</h4>
                    <p>${summary.overall_message}</p>
                    <span class="analysis-sub">${summary.overall_status}</span>
                </div>
            </div>
            ` : ''}
        `;

        // Render prediction table with full details
        const tbody = document.querySelector('#prediction-table tbody');
        tbody.innerHTML = '';

        // Get subject data from currentData
        const subjectData = currentData?.subjects || [];

        if (analysisData.predictions && analysisData.predictions.length > 0) {
            analysisData.predictions.forEach(pred => {
                const tr = document.createElement('tr');
                const statusClass = pred.status === 'CRITICAL' ? 'status-critical' :
                    pred.status === 'WARNING' ? 'status-warning' : 'status-safe';

                // Find full subject details
                const fullSubj = subjectData.find(s => s.name === pred.subject) || {};
                const total = fullSubj.total || 0;
                const present = fullSubj.present || 0;
                const absent = fullSubj.absent || 0;

                tr.innerHTML = `
                    <td><strong>${pred.subject}</strong></td>
                    <td>${total}</td>
                    <td>${present}</td>
                    <td>${absent}</td>
                    <td>
                        <div class="percentage-bar">
                            <div class="percentage-fill ${statusClass}" style="width: ${pred.current_percentage}%"></div>
                            <span>${pred.current_percentage}%</span>
                        </div>
                    </td>
                    <td><span class="status-badge ${statusClass}">${pred.status}</span></td>
                    <td>${pred.message}</td>
                    <td>
                        <button class="btn-sm btn-info" onclick="window.showSubjectDetails('${pred.subject.replace(/'/g, "\\'")}')">
                            Details
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 1rem;">No predictions available</td></tr>';
        }
    }

    function renderTimetable() {
        if (!timetableData) return;

        const grid = document.getElementById('timetable-grid');
        if (!grid) return;
        grid.innerHTML = '';

        const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
        const dayColors = {
            'Monday': '#3b82f6',
            'Tuesday': '#8b5cf6',
            'Wednesday': '#10b981',
            'Thursday': '#f59e0b',
            'Friday': '#ef4444'
        };

        days.forEach(day => {
            const dayCard = document.createElement('div');
            dayCard.className = 'day-card';
            dayCard.style.borderTop = `4px solid ${dayColors[day]}`;

            const periods = timetableData[day] || [];
            const academicPeriods = periods.filter(p =>
                p.subject !== 'LUNCH' &&
                p.subject !== 'Lunch Break' &&
                p.subject !== 'Mentor/Library' &&
                p.subject !== 'Innovative Practices'
            );

            // Group consecutive periods with same subject
            const groupedPeriods = [];
            let currentGroup = null;

            periods.forEach((p, idx) => {
                if (p.subject === 'LUNCH' || p.subject === 'Lunch Break') {
                    if (currentGroup) {
                        groupedPeriods.push(currentGroup);
                        currentGroup = null;
                    }
                    groupedPeriods.push({ type: 'lunch', period: p });
                } else if (p.subject === 'Mentor/Library' || p.subject === 'Innovative Practices') {
                    if (currentGroup) {
                        groupedPeriods.push(currentGroup);
                        currentGroup = null;
                    }
                    groupedPeriods.push({ type: 'break', period: p });
                } else {
                    if (!currentGroup || currentGroup.subject !== p.subject) {
                        if (currentGroup) groupedPeriods.push(currentGroup);
                        currentGroup = {
                            type: 'class',
                            subject: p.subject,
                            startTime: p.time.split('-')[0],
                            endTime: p.time.split('-')[1],
                            periods: [p]
                        };
                    } else {
                        currentGroup.endTime = p.time.split('-')[1];
                        currentGroup.periods.push(p);
                    }
                }
            });
            if (currentGroup) groupedPeriods.push(currentGroup);

            // Generate subject tags with colors
            const subjectColors = {};
            let colorIndex = 0;
            const colors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#f97316'];

            const subjectsList = academicPeriods
                .map(p => {
                    if (!subjectColors[p.subject]) {
                        subjectColors[p.subject] = colors[colorIndex % colors.length];
                        colorIndex++;
                    }
                    return `<span class="subject-tag" style="background: ${subjectColors[p.subject]}20; color: ${subjectColors[p.subject]}; border: 1px solid ${subjectColors[p.subject]}40;">${p.subject}</span>`;
                })
                .join('');

            dayCard.innerHTML = `
                <div class="day-header" style="background: linear-gradient(135deg, ${dayColors[day]}15, transparent);">
                    <h4 style="color: ${dayColors[day]};">${day}</h4>
                    <span class="class-count" style="background: ${dayColors[day]}20; color: ${dayColors[day]};">${academicPeriods.length} classes</span>
                </div>
                <div class="day-subjects">
                    ${subjectsList}
                </div>
                <div class="day-schedule">
                    ${groupedPeriods.map(group => {
                if (group.type === 'lunch') {
                    return `
                                <div class="schedule-item lunch-break">
                                    <span class="time">${group.period.time}</span>
                                    <span class="subject"><i class="fa-solid fa-utensils"></i> ${group.period.subject}</span>
                                </div>
                            `;
                } else if (group.type === 'break') {
                    return `
                                <div class="schedule-item break-period">
                                    <span class="time">${group.period.time}</span>
                                    <span class="subject">${group.period.subject}</span>
                                </div>
                            `;
                } else {
                    const duration = group.periods.length > 1 ? ` (${group.periods.length} periods)` : '';
                    return `
                                <div class="schedule-item class-period" style="border-left: 3px solid ${subjectColors[group.subject] || '#3b82f6'};">
                                    <div class="class-time">
                                        <span class="time">${group.startTime}-${group.endTime}</span>
                                        ${duration ? `<span class="duration">${duration}</span>` : ''}
                                    </div>
                                    <span class="subject">${group.subject}</span>
                                </div>
                            `;
                }
            }).join('')}
                </div>
            `;

            grid.appendChild(dayCard);
        });
    }

    // Refresh analysis button
    document.getElementById('refresh-analysis').addEventListener('click', async () => {
        if (currentUsername && currentPassword) {
            await fetchAnalysis(currentUsername, currentPassword);
        }
    });

    // ==============================
    // RISK ENGINE & SIMULATOR
    // ==============================

    // Risk Engine
    document.getElementById('analyze-risk-btn').addEventListener('click', async (e) => {
        if (!currentUsername || !currentPassword) return;

        const btn = e.currentTarget;
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
        btn.disabled = true;

        document.getElementById('risk-summary').innerHTML = '<div style="text-align: center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--accent-primary);"></i><p style="margin-top: 1rem; color: var(--text-secondary);">Analyzing risk...</p></div>';
        document.getElementById('risk-details').innerHTML = '';

        const threshold = parseFloat(document.getElementById('risk-threshold').value) || 75;

        try {
            const response = await fetch(`/risk-engine?username=${encodeURIComponent(currentUsername)}&password=${encodeURIComponent(currentPassword)}&threshold=${threshold}`);
            const result = await response.json();
            if (result.success) {
                renderRiskEngine(result.data);
            }
        } catch (err) {
            console.error('Failed to fetch risk analysis:', err);
            document.getElementById('risk-summary').innerHTML = '<p style="color: var(--danger-color); text-align: center;">Failed to load risk analysis.</p>';
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // Leave Simulator
    document.getElementById('run-simulation-btn').addEventListener('click', async (e) => {
        if (!currentUsername || !currentPassword) return;

        const day = document.getElementById('sim-day-select').value;
        if (!day) {
            alert('Please select a day to simulate');
            return;
        }

        const btn = e.currentTarget;
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Simulating...';
        btn.disabled = true;

        const resultsDiv = document.getElementById('simulation-results');
        resultsDiv.classList.remove('hidden');
        const emptyState = document.getElementById('sim-empty-state');
        if (emptyState) emptyState.classList.add('hidden');
        document.getElementById('simulation-summary').innerHTML = '<div style="text-align: center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--accent-primary);"></i><p style="margin-top: 1rem; color: var(--text-secondary);">Running simulation...</p></div>';
        document.getElementById('simulation-details').innerHTML = '';

        try {
            const response = await fetch(`/leave-simulator?username=${encodeURIComponent(currentUsername)}&password=${encodeURIComponent(currentPassword)}&day=${encodeURIComponent(day)}`);
            const result = await response.json();
            if (result.success) {
                renderSimulation(result.data);
            }
        } catch (err) {
            console.error('Failed to run simulation:', err);
            document.getElementById('simulation-summary').innerHTML = '<p style="color: var(--danger-color); text-align: center;">Failed to load simulation results.</p>';
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // Weekly Leave Simulator
    document.getElementById('run-week-simulation-btn').addEventListener('click', async (e) => {
        if (!currentUsername || !currentPassword) return;

        const btn = e.currentTarget;
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Simulating Week...';
        btn.disabled = true;

        const reqDiv = document.getElementById('week-simulation-results');
        if (reqDiv) {
            reqDiv.classList.remove('hidden');
            const emptyState = document.getElementById('sim-empty-state');
            if (emptyState) emptyState.classList.add('hidden');
            document.getElementById('week-summary').innerHTML = '<div style="text-align: center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--accent-primary);"></i><p style="margin-top: 1rem; color: var(--text-secondary);">Running weekly simulation...</p></div>';
            document.getElementById('week-details').innerHTML = '';
        }

        try {
            const response = await fetch(`/leave-simulator-week?username=${encodeURIComponent(currentUsername)}&password=${encodeURIComponent(currentPassword)}`);
            const result = await response.json();
            if (result.success) {
                // If the render method exists, call it. Otherwise do nothing.
                if (typeof renderWeekSimulation === 'function') {
                    renderWeekSimulation(result.data);
                }
            }
        } catch (err) {
            console.error('Failed to run week simulation:', err);
            if (reqDiv) {
                document.getElementById('week-summary').innerHTML = '<p style="color: var(--danger-color); text-align: center;">Failed to load weekly simulation results.</p>';
            }
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    function renderRiskEngine(data) {
        const summaryDiv = document.getElementById('risk-summary');
        const detailsDiv = document.getElementById('risk-details');

        // Summary
        const lowest = data.lowest_attendance_subject;
        const statusClass = data.overall_risk_status.toLowerCase();

        summaryDiv.innerHTML = `
            <div class="risk-alert ${statusClass}">
                <div class="risk-alert-icon">
                    <i class="fa-solid ${data.critical_alert ? 'fa-circle-exclamation' : 'fa-shield-halved'}"></i>
                </div>
                <div class="risk-alert-content">
                    <h3>Overall Status: ${data.overall_risk_status}</h3>
                    <p>${data.at_risk_subjects_count} subject(s) below ${data.threshold}% threshold</p>
                </div>
            </div>
            ${lowest ? `
            <div class="lowest-subject-card">
                <h4><i class="fa-solid fa-arrow-down"></i> Lowest Attendance</h4>
                <div class="lowest-subject-info">
                    <span class="subject-name">${lowest.name}</span>
                    <span class="subject-percentage ${getRiskClass(lowest.percentage)}">${lowest.percentage}%</span>
                </div>
                <div class="lowest-subject-stats">
                    <span>Present: ${lowest.present}/${lowest.total}</span>
                    <span>Absent: ${lowest.absent}</span>
                </div>
            </div>
            ` : ''}
        `;

        // Details
        detailsDiv.innerHTML = `
            <h3><i class="fa-solid fa-list-check"></i> Subject Risk Analysis</h3>
            <div class="risk-table-container">
                <table class="risk-table">
                    <thead>
                        <tr>
                            <th>Subject</th>
                            <th>Current %</th>
                            <th>Risk Level</th>
                            <th>Absents Allowed</th>
                            <th>Recovery Needed</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.subject_risks.map(risk => `
                            <tr class="risk-row ${risk.risk_level.toLowerCase()}">
                                <td><strong>${risk.subject}</strong></td>
                                <td>
                                    <div class="mini-percentage-bar">
                                        <div class="fill ${getRiskClass(risk.percentage)}" style="width: ${risk.percentage}%"></div>
                                        <span>${risk.percentage}%</span>
                                    </div>
                                </td>
                                <td><span class="risk-badge ${risk.risk_level.toLowerCase()}">${risk.risk_level}</span></td>
                                <td>
                                    ${risk.already_below_threshold
                ? '<span class="text-danger">Below threshold!</span>'
                : `<span class="text-success">${risk.absents_allowed_before_threshold} classes</span>`
            }
                                </td>
                                <td>
                                    ${risk.consecutive_presents_needed > 0
                ? `<span class="text-warning">${risk.consecutive_presents_needed} classes (${risk.estimated_days_to_recover} days)</span>`
                : '<span class="text-success">✓ Safe</span>'
            }
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    function renderSimulation(data) {
        const resultsDiv = document.getElementById('simulation-results');
        const summaryDiv = document.getElementById('simulation-summary');
        const detailsDiv = document.getElementById('simulation-details');

        resultsDiv.classList.remove('hidden');

        const recClass = data.recommendation.toLowerCase().replace('_', '-');

        // Summary
        summaryDiv.innerHTML = `
            <div class="simulation-alert ${recClass}">
                <div class="sim-alert-icon">
                    <i class="fa-solid ${getSimIcon(data.recommendation)}"></i>
                </div>
                <div class="sim-alert-content">
                    <h3>${data.recommendation.replace('_', ' ')}</h3>
                    <p>${data.advice}</p>
                    <div class="sim-stats">
                        <span><i class="fa-solid fa-calendar"></i> ${data.simulated_day}</span>
                        <span><i class="fa-solid fa-book"></i> ${data.total_classes_on_day} classes</span>
                    </div>
                    ${data.overall_attendance ? `
                    <div class="overall-attendance-impact">
                        <div class="overall-metric">
                            <span class="label">Current Overall:</span>
                            <span class="value">${data.overall_attendance.current}%</span>
                        </div>
                        <div class="overall-metric">
                            <span class="label">After Leave:</span>
                            <span class="value ${data.overall_attendance.projected < 75 ? 'text-danger' : ''}">${data.overall_attendance.projected}%</span>
                        </div>
                        <div class="overall-metric">
                            <span class="label">Drop:</span>
                            <span class="value text-danger">-${data.overall_attendance.drop}%</span>
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;

        // Details
        detailsDiv.innerHTML = `
            <h3><i class="fa-solid fa-chart-bar"></i> Projected Impact</h3>
            <div class="simulation-grid">
                ${data.subject_simulations.map(sim => `
                    <div class="sim-card ${sim.impact_level.toLowerCase()}">
                        <div class="sim-card-header">
                            <span class="sim-subject">${sim.subject}</span>
                            <span class="sim-impact-badge ${sim.impact_level.toLowerCase()}">${sim.impact_level}</span>
                        </div>
                        <div class="sim-card-body">
                            <div class="sim-metric">
                                <span class="label">Current:</span>
                                <span class="value">${sim.current_percentage}%</span>
                            </div>
                            <div class="sim-metric">
                                <span class="label">After Absence:</span>
                                <span class="value ${sim.projected_percentage < 75 ? 'text-danger' : ''}">${sim.projected_percentage}%</span>
                            </div>
                            <div class="sim-metric">
                                <span class="label">Drop:</span>
                                <span class="value text-danger">-${sim.percentage_drop}%</span>
                            </div>
                            <div class="sim-metric">
                                <span class="label">Classes on ${data.simulated_day}:</span>
                                <span class="value">${sim.classes_on_this_day}</span>
                            </div>
                        </div>
                        ${sim.will_fall_below_75 ? `
                            <div class="sim-warning">
                                <i class="fa-solid fa-triangle-exclamation"></i>
                                Will fall below 75%!
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        `;

        // Scroll to results
        resultsDiv.scrollIntoView({ behavior: 'smooth' });
    }

    function renderWeekSimulation(data) {
        const weekResultsDiv = document.getElementById('week-simulation-results');
        const weekSummaryDiv = document.getElementById('week-summary');
        const weekDetailsDiv = document.getElementById('week-details');

        weekResultsDiv.classList.remove('hidden');

        // Summary with current overall and whole week leave
        const wholeWeek = data.whole_week_leave;
        const weekStatusClass = wholeWeek.projected_overall_percentage < 60 ? 'critical' :
            wholeWeek.projected_overall_percentage < 75 ? 'warning' : 'safe';

        weekSummaryDiv.innerHTML = `
            <div class="week-summary-header">
                <h3><i class="fa-solid fa-calendar-week"></i> Weekly Leave Analysis</h3>
                <div class="current-overall">
                    <span>Current Overall: <strong>${data.current_overall_percentage}%</strong></span>
                </div>
            </div>
            <div class="whole-week-leave-box ${weekStatusClass}">
                <div class="whole-week-header">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <span>If You Take Whole Week Leave</span>
                </div>
                <div class="whole-week-stats">
                    <div class="stat">
                        <span class="label">Total Absences:</span>
                        <span class="value">${wholeWeek.total_absences} classes</span>
                    </div>
                    <div class="stat">
                        <span class="label">Overall After:</span>
                        <span class="value ${wholeWeek.projected_overall_percentage < 75 ? 'text-danger' : ''}">${wholeWeek.projected_overall_percentage}%</span>
                    </div>
                    <div class="stat">
                        <span class="label">Total Drop:</span>
                        <span class="value text-danger">-${wholeWeek.overall_drop}%</span>
                    </div>
                </div>
                <div class="whole-week-message">
                    ${wholeWeek.projected_overall_percentage < 60 ? '⚠️ Critical! Your attendance will be very low!' :
                wholeWeek.projected_overall_percentage < 75 ? '⚠️ Warning! You will fall below 75%!' :
                    '✓ Safe! You will maintain above 75%.'}
                </div>
            </div>
        `;

        // Day cards sorted by recommendation (best to worst)
        weekDetailsDiv.innerHTML = `
            <div class="week-days-grid">
                ${data.week_simulation.map(day => {
            const recClass = day.recommendation.toLowerCase();
            const recIcon = day.recommendation === 'SAFE' ? 'fa-check-circle' :
                day.recommendation === 'CAUTION' ? 'fa-triangle-exclamation' :
                    day.recommendation === 'RISKY' ? 'fa-circle-xmark' : 'fa-ban';
            return `
                        <div class="week-day-card ${recClass}">
                            <div class="week-day-header">
                                <h4>${day.day}</h4>
                                <span class="week-rec-badge ${recClass}">
                                    <i class="fa-solid ${recIcon}"></i> ${day.recommendation}
                                </span>
                            </div>
                            <div class="week-day-stats">
                                <div class="stat">
                                    <span class="label">Classes:</span>
                                    <span class="value">${day.total_class_units}</span>
                                </div>
                                <div class="stat">
                                    <span class="label">Affected:</span>
                                    <span class="value">${day.affected_subjects_count}</span>
                                </div>
                                <div class="stat">
                                    <span class="label">Overall After:</span>
                                    <span class="value ${day.projected_overall_percentage < 75 ? 'text-danger' : ''}">${day.projected_overall_percentage}%</span>
                                </div>
                                <div class="stat">
                                    <span class="label">Drop:</span>
                                    <span class="value text-danger">-${day.overall_drop}%</span>
                                </div>
                            </div>
                            ${day.subject_simulations.length > 0 ? `
                            <div class="week-top-subjects">
                                <span class="label">Most Impacted:</span>
                                <div class="subject-tags">
                                    ${day.subject_simulations.slice(0, 2).map(s => `
                                        <span class="subject-tag ${s.impact_level.toLowerCase()}">${s.subject.split(' ').slice(0, 3).join(' ')}</span>
                                    `).join('')}
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    `;
        }).join('')}
            </div>
        `;

        // Scroll to results
        weekResultsDiv.scrollIntoView({ behavior: 'smooth' });
    }

    function getRiskClass(percentage) {
        if (percentage < 65) return 'critical';
        if (percentage < 75) return 'high';
        return 'low';
    }

    function getSimIcon(recommendation) {
        switch (recommendation) {
            case 'STRONGLY_DISCOURAGED': return 'fa-ban';
            case 'NOT_RECOMMENDED': return 'fa-circle-xmark';
            case 'YOU MAY CONSIDER': return 'fa-triangle-exclamation';
            case 'CAUTION': return 'fa-triangle-exclamation';
            case 'SAFE': return 'fa-check-circle';
            default: return 'fa-question-circle';
        }
    }
});
