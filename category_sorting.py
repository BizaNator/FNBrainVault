        if progress_callback:
            self.manager.progress_callback = progress_callback
        if status_callback:
            self.manager.status_callback = status_callback
            # Category extraction script
        self.category_script = """
        () => {
            const tocElement = document.querySelector('[slot="documentation-toc"]');
            if (tocElement) {
                const parentLinks = tocElement.querySelectorAll('a.contents-table-link.is-parent');
                const currentPath = window.location.pathname;
                
                for (const link of parentLinks) {
                    const href = link.getAttribute('href');
                    if (currentPath.startsWith(href)) {
                        return {
                            category: link.textContent.trim(),
                            href: href
                        };
                    }
                }
            }
            
            const breadcrumbs = document.querySelectorAll('.breadcrumb-item');
            if (breadcrumbs.length) {
                const lastBreadcrumb = Array.from(breadcrumbs).pop();
                if (lastBreadcrumb) {
                    return {
                        category: lastBreadcrumb.getAttribute('title'),
                        href: lastBreadcrumb.getAttribute('href')
                    };
                }
            }
            return null;
        }
        """