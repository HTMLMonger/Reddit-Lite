document.addEventListener('DOMContentLoaded', function() {
    const searchContainer = document.querySelector('.search-container');
    const postsGrid = document.querySelector('.posts-grid');
    
    // Initially hide posts grid and show centered search
    postsGrid.classList.add('loading');
    searchContainer.classList.add('loading');

    // Function to show content after loading
    window.showContent = function() {
        searchContainer.classList.remove('loading');
        postsGrid.classList.remove('loading');
    }

    // Function to hide content during loading
    window.hideContent = function() {
        searchContainer.classList.add('loading');
        postsGrid.classList.add('loading');
    }
});
