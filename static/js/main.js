let currentPage = 1;
let loading = false;
let hasMore = true;

async function loadMorePosts() {
    if (loading || !hasMore) return;
    
    loading = true;
    const postsContainer = document.getElementById('posts-container');
    
    try {
        const response = await fetch(`/get_posts?page=${currentPage}&per_page=20`);
        const data = await response.json();
        
        if (data.posts && data.posts.length > 0) {
            const viewMode = postsContainer.classList.contains('posts-grid') ? 'grid' : 'list';
            const newPosts = data.posts.map(post => createPostElement(post, viewMode)).join('');
            postsContainer.insertAdjacentHTML('beforeend', newPosts);
            
            currentPage++;
            hasMore = currentPage <= data.pages;
        } else {
            hasMore = false;
        }
    } catch (error) {
        console.error('Error loading more posts:', error);
    } finally {
        loading = false;
    }
}

// Infinite scroll implementation
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            loadMorePosts();
        }
    });
}, { threshold: 0.5 });

// Observe the last post
function observeLastPost() {
    const posts = document.querySelectorAll('.post-card');
    if (posts.length > 0) {
        observer.observe(posts[posts.length - 1]);
    }
}

// Modified displayPosts function
async function displayPosts() {
    currentPage = 1;
    hasMore = true;
    const postsContainer = document.getElementById('posts-container');
    const viewMode = postsContainer.classList.contains('posts-grid') ? 'grid' : 'list';
    
    try {
        const response = await fetch('/get_posts');
        const data = await response.json();
        
        if (data.posts && Array.isArray(data.posts)) {
            postsContainer.innerHTML = data.posts.map(post => createPostElement(post, viewMode)).join('');
            hasMore = currentPage < data.pages;
            observeLastPost();
        } else {
            postsContainer.innerHTML = '<p class="error">No posts available</p>';
        }
        
    } catch (error) {
        console.error('Error fetching posts:', error);
        postsContainer.innerHTML = '<p class="error">Error loading posts</p>';
    }
}

// Call displayPosts when page loads
document.addEventListener('DOMContentLoaded', displayPosts);

async function fetchAndDisplayPosts(subreddit = '', pages = 1) {
    const postsContainer = document.getElementById('posts-container');
    const lastUpdated = document.getElementById('last-updated');
    const fetchButton = document.querySelector('.fetch-button');
    
    fetchButton.disabled = true;
    postsContainer.classList.add('loading');
    
    try {
        const response = await fetch('/scrape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ subreddit, max_pages: pages })
        });
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        // Display posts immediately after scraping
        await displayPosts();
        
    } catch (error) {
        console.error('Error:', error);
        alert(`Failed to fetch posts: ${error.message}`);
    } finally {
        fetchButton.disabled = false;
        postsContainer.classList.remove('loading');
    }
}

document.getElementById('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const subreddit = document.getElementById('subreddit').value;
    const pages = document.getElementById('numPages').value || 1;
    
    await fetchAndDisplayPosts(subreddit, pages);
});

function truncateText(text, type = 'preview') {
    if (!text) return '';
    
    const limits = {
        title: 100,
        preview: {
            list: 1000,    // Increased from 500
            grid: 150    
        }
    };
    
    const limit = type === 'title' ? limits.title : 
                 (type === 'list' ? limits.preview.list : limits.preview.grid);
    
    if (text.length <= limit) return text;
    
    // Find the last complete word within the limit
    const truncated = text.substr(0, limit).split(' ');
    truncated.pop(); // Remove last (potentially partial) word
    return truncated.join(' ') + '...';
}

function createPostElement(post, viewMode) {
    return `
        <div class="post-card">
            <h3 class="post-title">${truncateText(post.title, 'title')}</h3>
            <div class="post-meta">
                <span class="subreddit">r/${post.subreddit}</span>
                <span class="author">u/${post.author}</span>
            </div>
            <div class="post-preview">
                ${truncateText(post.selftext || 'No content available', viewMode)}
            </div>
            <div class="post-stats">
                <span class="score">${post.score} points</span>
                <span class="comments">${post.num_comments} comments</span>
            </div>
            <div class="post-actions">
                <a href="${post.url}" target="_blank" class="btn btn-primary btn-sm">View Post</a>
            </div>
        </div>
    `;
}
