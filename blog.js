fetch("static/blog_posts.json")
    .then(response => response.json())
    .then(blogPosts => {
        const blogContainer = document.getElementById("blog-container");

        blogPosts.forEach(post => {
            // Validate post fields
            if (!post.title || !post.link || !post.image || !post.synopsis) {
                console.error("Invalid blog post data:", post);
                return;
            }

            const postElement = document.createElement("div");
            postElement.classList.add("blog-preview");
            postElement.innerHTML = `
                <img src="${post.image}" alt="${post.title}">
                <div class="blog-details">
                    <h3 onclick="window.location.href='${post.link}'">${post.title}</h3>
                    <div class="meta">${post.date} | ${post.author}</div>
                    <p class="synopsis">${post.synopsis}</p>
                </div>
            `;
            blogContainer.appendChild(postElement);

            // Add a separator
            const separator = document.createElement("hr");
            separator.classList.add("gray-line");
            blogContainer.appendChild(separator);
        });
    })
    .catch(error => console.error("Error loading blog posts:", error));
