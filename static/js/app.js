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

    async function loadArticles() {
        feedContainer.innerHTML = '<p>Loading articles...</p>';
        try {
            const response = await fetch('/api/articles');
            const articles = await response.json();
            renderArticles(articles);
        } catch (error) {
            feedContainer.innerHTML = '<p>Error loading articles.</p>';
            console.error(error);
        }
    }

    function renderArticles(articles) {
        feedContainer.innerHTML = '';
        if (articles.length === 0) {
            feedContainer.innerHTML = '<p>No articles found. Try refreshing feeds.</p>';
            return;
        }

        articles.forEach(article => {
            // FILTER: Skip low relevance articles
            const score = article.relevance_score ? article.relevance_score.toLowerCase() : 'low';
            if (score.includes('low')) return;

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
            `;
            feedContainer.appendChild(card);
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
        } catch (error) {
            alert('Error during ingestion.');
            console.error(error);
        } finally {
            refreshBtn.disabled = false;
            refreshBtn.innerText = 'Refresh Feeds';
        }
    });

    // Settings
    const configEditor = document.getElementById('config-editor');
    const saveConfigBtn = document.getElementById('save-config-btn');
    const statusBar = document.getElementById('status-bar');

    async function loadConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            configEditor.value = data.config;
        } catch (error) {
            console.error(error);
        }
    }

    saveConfigBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: configEditor.value })
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

    function showStatus(msg, type) {
        statusBar.innerText = msg;
        statusBar.className = `status-bar ${type}`;
        setTimeout(() => {
            statusBar.style.display = 'none';
        }, 3000);
    }
});
