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
            list: 1500 // Increased to 2000 characters for list view
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

// Client-side cache
const postCache = new Map();

// API calls
const api = {
    async fetchPosts(params = {}) {
        const defaultParams = {
            query: '',
            subreddit: '',
            page: 1,
            per_page: 20
        };
        const mergedParams = { ...defaultParams, ...params };
        
        const queryString = new URLSearchParams(mergedParams).toString();
        const response = await fetch(`/search?${queryString}`);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || data.details || `HTTP error! status: ${response.status}`);
        }
        return data;
    },

    async loadMorePosts() {
        if (state.loading || !state.hasMore) return;
        state.loading = true;
        
        try {
            const data = await api.fetchPosts({ page: state.currentPage });
            
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
            elements.errorMessage.textContent = 'Error loading posts: ' + error.message;
            elements.errorMessage.style.display = 'block';
            state.hasMore = false;
        } finally {
            state.loading = false;
        }
    }
};

// Post rendering with lazy loading
function createPostElement(post, viewMode = 'grid') {
    console.log('Creating post element:', post);
    const truncatedSelftext = utils.truncateText(post.selftext || 'No content available', viewMode); // Now properly passing 'grid' or 'list'
    const truncatedTitle = utils.truncateText(post.title, 'title');
    
    // Construct the full Reddit post URL
    const postUrl = `https://www.reddit.com/r/${post.subreddit}/comments/${post.id}`;
    
    return `
        <div class="post-card">
            <div class="post-content">
                <h3 class="post-title">${truncatedTitle}</h3>
                <div class="post-meta">
                    <span class="subreddit">r/${post.subreddit}</span>
                    <span class="author">u/${post.author}</span>
                </div>
                <div class="post-preview ${viewMode === 'list' ? 'list-view' : ''}" data-full-text="${post.selftext}">${truncatedSelftext}</div>
                <div class="post-stats">
                    <span class="score">${utils.formatNumber(post.score)} points</span>
                    <span class="comments">${utils.formatNumber(post.num_comments)} comments</span>
                </div>
            </div>
            <div class="post-actions">
                <a href="${postUrl}" target="_blank" class="btn btn-primary">View Post</a>
            </div>
        </div>
    `;
}

// Lazy load post content
function lazyLoadContent() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const preview = entry.target;
                preview.textContent = preview.dataset.fullText;
                observer.unobserve(preview);
            }
        });
    }, { rootMargin: '100px' });

    document.querySelectorAll('.post-preview').forEach(preview => observer.observe(preview));
}

// Event handlers
async function handleSearch(e) {
    e.preventDefault();
    console.log('Search initiated');
    state.currentPage = 1;
    state.hasMore = true;
    
    try {
        elements.errorMessage.style.display = 'none';
        elements.loadingIndicator.style.display = 'flex';
        elements.postsContainer.innerHTML = '';
        
        const query = document.getElementById('searchQuery').value.trim();
        const subreddit = document.getElementById('subreddit').value.trim();
        const pages = document.getElementById('numPages').value || '1';
        
        const params = new URLSearchParams({ query, subreddit, pages });
        
        console.log('Sending search request with params:', params.toString());
        
        const response = await fetch(`/search?${params.toString()}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        
        console.log('Received search response:', data);
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        const posts = data.posts || [];
        if (posts.length === 0) {
            elements.postsContainer.innerHTML = '<div class="no-posts-message">No posts found. Try different search terms!</div>';
            return;
        }
        
        const viewMode = elements.postsContainer.classList.contains('posts-grid') ? 'grid' : 'list';
        const postsHTML = posts.map(post => createPostElement(post, viewMode)).join('');
        elements.postsContainer.innerHTML = postsHTML;
        
        console.log(`Rendered ${posts.length} posts`);
        
        // Update pagination info
        state.currentPage = data.current_page;
        state.hasMore = state.currentPage < data.pages;
        
        // Trigger lazy loading for the new content
        lazyLoadContent();
        
    } catch (error) {
        console.error('Search error:', error);
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

// Add this function to check database connectivity
async function checkDatabaseConnection() {
    try {
        const response = await fetch('/debug_db');
        const data = await response.json();
        console.log('Database connection status:', data);
    } catch (error) {
        console.error('Error checking database connection:', error);
    }
}

// Add this function to check debug info
async function checkDebugInfo() {
    try {
        const response = await fetch('/debug');
        const data = await response.json();
        console.log('Debug info:', data);
    } catch (error) {
        console.error('Error fetching debug info:', error);
    }
}

// Initialize
function init() {
    console.log('Initializing app');
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

    // Lazy load content
    lazyLoadContent();

    // Check database connection
    checkDatabaseConnection();

    // Check debug info
    checkDebugInfo();
}

// Start the application
document.addEventListener('DOMContentLoaded', init);
