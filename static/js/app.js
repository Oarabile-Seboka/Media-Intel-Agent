document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Update active nav
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            // Update active view
            const viewId = item.getAttribute('data-view');
            views.forEach(view => {
                view.classList.remove('active');
                if (view.id === viewId) {
                    view.classList.add('active');
                }
            });

            // Load view specific data
            if (viewId === 'feed-view') loadArticles();
            if (viewId === 'settings-view') loadConfig();
        });
    });

    // Chat
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatContainer = document.getElementById('chat-container');

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Add user message
        appendMessage(text, 'user');
        chatInput.value = '';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();
            appendMessage(data.response, 'agent');
        } catch (error) {
            appendMessage('Error: Could not reach the agent.', 'agent');
            console.error(error);
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    function appendMessage(text, sender) {
        const div = document.createElement('div');
        div.classList.add('message', sender);
        // Simple markdown-like parsing for links could be added here
        div.innerText = text;
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Feed
    const feedContainer = document.getElementById('feed-container');
    const refreshBtn = document.getElementById('refresh-btn');
    const deleteAllBtn = document.getElementById('delete-all-btn');
    const filterCategory = document.getElementById('filter-category');
    const filterStartDate = document.getElementById('filter-start-date');
    const filterEndDate = document.getElementById('filter-end-date');
    const clearFiltersBtn = document.getElementById('clear-filters-btn');

    function getSavedFilters() {
        const saved = localStorage.getItem('feedFilters');
        if (!saved) return {};
        try {
            const parsed = JSON.parse(saved);
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (error) {
            console.warn('Invalid saved filters in localStorage, resetting.', error);
            localStorage.removeItem('feedFilters');
            return {};
        }
    }

    // Persistence: Load filters from localStorage
    function loadSavedFilters() {
        const filters = getSavedFilters();
        filterCategory.value = filters.category || '';
        filterStartDate.value = filters.start_date || '';
        filterEndDate.value = filters.end_date || '';
    }

    function saveCurrentFilters() {
        const filters = {
            category: filterCategory.value,
            start_date: filterStartDate.value,
            end_date: filterEndDate.value
        };
        localStorage.setItem('feedFilters', JSON.stringify(filters));
    }

    async function loadArticles() {
        saveCurrentFilters();
        feedContainer.innerHTML = '<p>Loading articles...</p>';
        try {
            const params = new URLSearchParams();
            if (filterCategory.value) params.append('category', filterCategory.value);
            if (filterStartDate.value) params.append('start_date', filterStartDate.value);
            if (filterEndDate.value) params.append('end_date', filterEndDate.value);

            const url = `/api/articles?${params.toString()}`;
            const response = await fetch(url);
            const articles = await response.json();
            renderArticles(articles);
        } catch (error) {
            feedContainer.innerHTML = '<p>Error loading articles.</p>';
            console.error(error);
        }
    }

    async function loadCategories() {
        try {
            const response = await fetch('/api/categories');
            const categories = await response.json();

            const currentVal = filterCategory.value || getSavedFilters().category;
            filterCategory.innerHTML = '<option value="">All Categories</option>';
            categories.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat;
                opt.innerText = cat;
                filterCategory.appendChild(opt);
            });
            if (currentVal) filterCategory.value = currentVal;
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    }

    function renderArticles(articles) {
        feedContainer.innerHTML = '';
        if (articles.length === 0) {
            feedContainer.innerHTML = '<p>No articles found. Try refreshing feeds.</p>';
            return;
        }

        articles.forEach(article => {
            const score = article.relevance_score ? article.relevance_score.toLowerCase() : 'low';
            // REMOVED: Automatic low filter to give user control

            const card = document.createElement('div');
            card.classList.add('article-card');

            const tagsHtml = article.tags.map(tag => `<span class="tag">${tag}</span>`).join('');

            // Determine relevance class
            let relevanceClass = 'relevance-low';
            if (score.includes('high')) relevanceClass = 'relevance-high';
            else if (score.includes('medium')) relevanceClass = 'relevance-medium';

            // Image HTML
            let imageHtml = '';
            if (article.image_url) {
                imageHtml = `<div class="article-image"><img src="${article.image_url}" alt="${article.title}" loading="lazy"></div>`;
            }

            card.innerHTML = `
                ${imageHtml}
                <div class="article-header">
                    <a href="${article.url}" target="_blank" class="article-title">${article.title}</a>
                    <span class="relevance-badge ${relevanceClass}">${article.relevance_score || 'Low'}</span>
                </div>
                <div class="article-meta">
                    <span>${article.published_date}</span>
                    <span>•</span>
                    <span>${article.category}</span>
                </div>
                <p class="article-summary">${article.summary}</p>
                <div class="tags-container">
                    ${tagsHtml}
                </div>
                <div class="article-actions">
                    <button class="delete-article-btn" data-id="${article.id}">
                        Delete
                    </button>
                </div>
            `;
            feedContainer.appendChild(card);
        });

        // Add delete listeners
        document.querySelectorAll('.delete-article-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                if (confirm('Delete this article?')) {
                    try {
                        const res = await fetch(`/api/articles/${id}`, { method: 'DELETE' });
                        if (res.ok) loadArticles();
                    } catch (err) {
                        console.error(err);
                    }
                }
            });
        });
    }

    refreshBtn.addEventListener('click', async () => {
        refreshBtn.disabled = true;
        refreshBtn.innerText = 'Ingesting...';
        try {
            const response = await fetch('/api/ingest', { method: 'POST' });
            const data = await response.json();
            alert(`Ingestion complete. ${data.new_articles} new articles.`);
            loadArticles();
            loadCategories();
        } catch (error) {
            alert('Error during ingestion.');
            console.error(error);
        } finally {
            refreshBtn.disabled = false;
            refreshBtn.innerText = 'Refresh Feeds';
        }
    });

    deleteAllBtn.addEventListener('click', async () => {
        if (confirm('Are you sure you want to clear ALL articles? This cannot be undone.')) {
            try {
                const res = await fetch('/api/articles', { method: 'DELETE' });
                if (res.ok) {
                    const data = await res.json();
                    alert(`Deleted ${data.deleted_count} articles.`);
                    loadArticles();
                    loadCategories();
                }
            } catch (err) {
                console.error(err);
            }
        }
    });

    // Filter event listeners
    filterCategory.addEventListener('change', loadArticles);
    filterStartDate.addEventListener('change', loadArticles);
    filterEndDate.addEventListener('change', loadArticles);

    clearFiltersBtn.addEventListener('click', () => {
        filterCategory.value = '';
        filterStartDate.value = '';
        filterEndDate.value = '';
        loadArticles();
    });

    // Initial load
    loadSavedFilters();
    loadCategories();
    loadArticles();

    // Settings
    const configEditor = document.getElementById('config-editor');
    const saveConfigBtn = document.getElementById('save-config-btn');
    const scheduleEnabled = document.getElementById('schedule-enabled');
    const scheduleInterval = document.getElementById('schedule-interval');
    const scheduleLimit = document.getElementById('schedule-limit');
    const statusBar = document.getElementById('status-bar');

    async function loadConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            configEditor.value = data.config;

            // Simple parsing for scheduling UI (regex for safety)
            const enabledMatch = data.config.match(/scheduling:\s*\n\s*enabled:\s*(true|false)/);
            const intervalMatch = data.config.match(/interval_hours:\s*(\d+)/);
            const limitMatch = data.config.match(/pull_limit:\s*(\d+)/);

            if (enabledMatch) scheduleEnabled.checked = enabledMatch[1] === 'true';
            if (intervalMatch) scheduleInterval.value = intervalMatch[1];
            if (limitMatch) scheduleLimit.value = limitMatch[1];

        } catch (error) {
            console.error(error);
        }
    }

    saveConfigBtn.addEventListener('click', async () => {
        let currentYaml = configEditor.value;

        // Update YAML with UI values before saving
        const enabled = scheduleEnabled.checked;
        const interval = scheduleInterval.value;
        const limit = scheduleLimit.value;

        // Update or insert scheduling block
        if (currentYaml.includes('scheduling:')) {
            currentYaml = currentYaml.replace(/enabled:\s*(true|false)/, `enabled: ${enabled}`);
            currentYaml = currentYaml.replace(/interval_hours:\s*(\d+)/, `interval_hours: ${interval}`);
            if (currentYaml.includes('pull_limit:')) {
                currentYaml = currentYaml.replace(/pull_limit:\s*(\d+)/, `pull_limit: ${limit}`);
            } else {
                currentYaml = currentYaml.replace(/(interval_hours:.*)/, `$1\n    pull_limit: ${limit}`);
            }
        } else {
            // Append if missing
            currentYaml += `\nscheduling:\n  enabled: ${enabled}\n  interval_hours: ${interval}\n  pull_limit: ${limit}\n`;
        }

        configEditor.value = currentYaml;

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: currentYaml })
            });

            if (response.ok) {
                showStatus('Configuration saved successfully.', 'success');
            } else {
                const data = await response.json();
                showStatus(`Error: ${data.detail}`, 'error');
            }
        } catch (error) {
            showStatus('Network error.', 'error');
        }
    });

    // Export Logic
    const exportCsvBtn = document.getElementById('export-csv-btn');
    const exportLimitInput = document.getElementById('export-limit');

    if (exportCsvBtn && exportLimitInput) {
        exportCsvBtn.addEventListener('click', () => {
            const limit = exportLimitInput.value.trim();
            let url = '/api/export/csv';
            if (limit) {
                url += `?limit=${encodeURIComponent(limit)}`;
            }
            // Safari can block async blob downloads; direct navigation is reliable.
            window.location.href = url;
        });
    }

    function showStatus(msg, type) {

        statusBar.innerText = msg;
        statusBar.className = `status-bar ${type}`;
        setTimeout(() => {
            statusBar.style.display = 'none';
        }, 3000);
    }
});
