// State management
const state = {
    currentPage: 1,
    loading: false,
    hasMore: true
};

// Utility functions
const utils = {
    truncateText(text, type = 'preview') {
        if (!text) return '';
        const limits = {
            title: 100,
            grid: 300,
            list: 2000 // Increased to 2000 characters for list view
        };
        const limit = limits[type] || limits.preview;
        return text.length <= limit ? text : 
            text.substr(0, limit).split(' ').slice(0, -1).join(' ') + '...';
    },

    formatNumber(num) {
        if (!num) return '0';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    },

    formatTime(timestamp) {
        if (!timestamp) return 'unknown';
        const diff = (Date.now() - timestamp * 1000) / 1000;
        if (diff < 60) return 'just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        if (diff < 2592000) return `${Math.floor(diff / 86400)}d ago`;
        return new Date(timestamp * 1000).toLocaleDateString();
    }
};

// DOM Elements
const elements = {
    postsContainer: document.getElementById('posts-container'),
    errorMessage: document.getElementById('error-message'),
    loadingIndicator: document.getElementById('loading-indicator'),
    searchForm: document.getElementById('searchForm'),
    viewToggleButtons: document.querySelectorAll('.view-toggle button')
};

// Post rendering
function createPostElement(post, viewMode = 'grid') {
    const truncatedSelftext = utils.truncateText(post.selftext || 'No content available', viewMode); // Now properly passing 'grid' or 'list'
    const truncatedTitle = utils.truncateText(post.title, 'title');
    
    return `
        <div class="post-card">
            <div class="post-content">
                <h3 class="post-title">${truncatedTitle}</h3>
                <div class="post-meta">
                    <span class="subreddit">r/${post.subreddit}</span>
                    <span class="author">u/${post.author}</span>
                </div>
                <div class="post-preview ${viewMode === 'list' ? 'list-view' : ''}">${truncatedSelftext}</div>
                <div class="post-stats">
                    <span class="score">${utils.formatNumber(post.score)} points</span>
                    <span class="comments">${utils.formatNumber(post.num_comments)} comments</span>
                </div>
            </div>
            <div class="post-actions">
                <a href="${post.url}" target="_blank" class="btn btn-primary">View Post</a>
            </div>
        </div>
    `;
}

// API calls
const api = {
    async fetchPosts(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const response = await fetch(`/search?${queryString}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
    },

    async loadMorePosts() {
        if (state.loading || !state.hasMore) return;
        state.loading = true;
        
        try {
            const data = await api.fetchPosts({ page: state.currentPage, per_page: 20 });
            if (data.posts?.length) {
                const viewMode = elements.postsContainer.classList.contains('posts-grid') ? 'grid' : 'list';
                const newPosts = data.posts.map(post => createPostElement(post, viewMode)).join('');
                elements.postsContainer.insertAdjacentHTML('beforeend', newPosts);
                
                state.currentPage++;
                state.hasMore = state.currentPage <= data.pages;
            } else {
                state.hasMore = false;
            }
        } catch (error) {
            console.error('Error loading posts:', error);
        } finally {
            state.loading = false;
        }
    }
};

// Event handlers
async function handleSearch(e) {
    e.preventDefault();
    state.currentPage = 1;
    state.hasMore = true;
    
    try {
        elements.errorMessage.style.display = 'none';
        elements.loadingIndicator.style.display = 'flex';
        elements.postsContainer.innerHTML = '';
        
        // Get form values directly from elements
        const query = document.getElementById('searchQuery').value.trim();
        const subreddit = document.getElementById('subreddit').value.trim();
        const pages = document.getElementById('numPages').value || '1';
        
        // Build search parameters
        const params = new URLSearchParams();
        if (query) params.append('query', query);
        if (subreddit) params.append('subreddit', subreddit.replace(/^r\//, ''));
        params.append('pages', pages);
        
        const response = await fetch(`/search?${params.toString()}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        const posts = data.posts || [];
        if (posts.length === 0) {
            elements.postsContainer.innerHTML = '<div class="no-posts-message">No posts found. Try different search terms!</div>';
            return;
        }
        
        const viewMode = elements.postsContainer.classList.contains('posts-grid') ? 'grid' : 'list';
        elements.postsContainer.innerHTML = posts.map(post => createPostElement(post, viewMode)).join('');
        
    } catch (error) {
        elements.errorMessage.textContent = 'Error performing search: ' + error.message;
        elements.errorMessage.style.display = 'block';
    } finally {
        elements.loadingIndicator.style.display = 'none';
    }
}

function handleViewToggle(e) {
    const view = e.target.dataset.view;
    if (!view) return;
    
    elements.viewToggleButtons.forEach(btn => btn.classList.remove('active'));
    e.target.classList.add('active');
    
    // Clear existing classes and add the new view class
    elements.postsContainer.className = '';
    elements.postsContainer.classList.add(view === 'grid' ? 'posts-grid' : 'posts-list');
    
    // Refresh current posts with new layout
    const posts = Array.from(elements.postsContainer.querySelectorAll('.post-card'))
        .map(card => ({
            title: card.querySelector('.post-title').textContent,
            subreddit: card.querySelector('.subreddit').textContent.replace('r/', ''),
            author: card.querySelector('.author').textContent.replace('u/', ''),
            selftext: card.querySelector('.post-preview').textContent,
            score: parseInt(card.querySelector('.score').textContent),
            num_comments: parseInt(card.querySelector('.comments').textContent),
            url: card.querySelector('.post-actions a').href
        }));
    
    // Re-render with the correct view mode
    elements.postsContainer.innerHTML = posts.map(post => createPostElement(post, view)).join('');
}

// Initialize
function init() {
    // Set up infinite scroll
    const observer = new IntersectionObserver(
        entries => entries.forEach(entry => {
            if (entry.isIntersecting) api.loadMorePosts();
        }), 
        { threshold: 0.5 }
    );

    // Default to list view on mobile
    if (window.innerWidth <= 1064) {
        elements.postsContainer.classList.remove('posts-grid');
        elements.postsContainer.classList.add('posts-list');
    }

    // Event listeners
    elements.searchForm.addEventListener('submit', handleSearch);
    elements.viewToggleButtons.forEach(button => 
        button.addEventListener('click', handleViewToggle));

    // Initial load
    api.loadMorePosts();
}

// Start the application
document.addEventListener('DOMContentLoaded', init);
