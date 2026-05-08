# Page Builder System for Journal

A flexible and elegant automatic page builder for the journal application that loads and displays paired pages with smooth fade animations between them.

## Overview

The page builder system treats the journal like a real book - pages always come in pairs (left and right). When you navigate, both pages change together, creating a cohesive book-like experience.

### Key Features

- **Paired Pages**: Left and right pages are always synchronized
- **Smooth Animations**: Fade in/out transitions between page pairs
- **Dynamic Content Loading**: Pages are loaded from HTML files on demand
- **Page Preloading**: All pages are preloaded for smooth transitions
- **Keyboard Navigation**: Arrow keys for page navigation
- **Script Execution**: Inline scripts in pages are properly executed
- **Custom Events**: `pagechange` event dispatches when pages change
- **Easy to Extend**: Simple API to add new pages

## File Structure

```
apps/journal/
├── static/
│   ├── pages/
│   │   ├── entry-form.html
│   │   ├── success-left.html
│   │   └── success-right.html
│   ├── scripts/
│   │   ├── pageManager.js      # Main page manager class
│   │   └── journal.js          # Initialization and alignment
│   └── styles/
│       └── journal.css          # Includes page builder styles
└── templates/
    └── journal/
        ├── journal.html         # Main template (now uses page builder)
        └── pages/               # Django template pages (optional)
```

## Usage

### Basic Setup

The page manager is initialized in `journal.html`:

```javascript
const pageManager = new PageManager();
window.pageManager = pageManager;

const pagePairs = [
    { left: 'entry-form', right: 'entry-form' },
    { left: 'success-left', right: 'success-right' }
];

await pageManager.loadPages(pagePairs, '/static/pages/');
```

### Creating New Pages

1. Create two HTML files in `/static/pages/`:
   - `your-page-left.html`
   - `your-page-right.html`

2. Wrap content in `<div class="page-content">`:
```html
<div class="page-content">
    <div class="your-page-container">
        <h2>Your Content</h2>
        <p>Your page content goes here</p>
    </div>
</div>
```

3. Add to the `pagePairs` array in `journal.html`:
```javascript
const pagePairs = [
    { left: 'entry-form', right: 'entry-form' },
    { left: 'success-left', right: 'success-right' },
    { left: 'your-page-left', right: 'your-page-right' }  // Add this
];
```

### JavaScript in Pages

Pages can include inline scripts that will be executed when loaded:

```html
<div class="page-content">
    <button id="my-button">Click Me</button>
</div>

<script>
(function() {
    const btn = document.getElementById('my-button');
    if (btn) {
        btn.addEventListener('click', () => {
            if (window.pageManager) {
                window.pageManager.nextPage();
            }
        });
    }
})();
</script>
```

## PageManager API

### Constructor
```javascript
new PageManager(leftPageSelector = '#left-page', rightPageSelector = '#right-page')
```

### Methods

#### `loadPages(pagePairs, basePath)`
Load and preload all page pairs.

```javascript
const pagePairs = [
    { left: 'page-name', right: 'page-name' }
];
await pageManager.loadPages(pagePairs, '/static/pages/');
```

#### `goToPage(index)`
Navigate to a specific page pair by index.

```javascript
await pageManager.goToPage(0);  // Go to first page pair
```

#### `nextPage()`
Navigate to the next page pair.

```javascript
await pageManager.nextPage();
```

Returns `true` if successful, `false` if at the last page.

#### `previousPage()`
Navigate to the previous page pair.

```javascript
await pageManager.previousPage();
```

Returns `true` if successful, `false` if at the first page.

#### `getCurrentPageIndex()`
Get the current page pair index.

```javascript
const index = pageManager.getCurrentPageIndex();
```

#### `getTotalPages()`
Get the total number of page pairs.

```javascript
const total = pageManager.getTotalPages();
```

#### `hasNextPage()`
Check if there's a next page.

```javascript
if (pageManager.hasNextPage()) {
    // Show next button
}
```

#### `hasPreviousPage()`
Check if there's a previous page.

```javascript
if (pageManager.hasPreviousPage()) {
    // Show previous button
}
```

#### `setAnimationDurations(fadeOutDuration, fadeInDuration)`
Customize animation timings (in milliseconds).

```javascript
pageManager.setAnimationDurations(300, 400);
```

## Events

### pagechange
Dispatched when the page changes.

```javascript
document.addEventListener('pagechange', (e) => {
    console.log('Current page index:', e.detail.currentIndex);
    console.log('Total pages:', e.detail.totalPages);
    console.log('Current page pair:', e.detail.currentPagePair);
});
```

## Keyboard Navigation

Arrow keys are supported:
- **← (Left Arrow)**: Go to previous page
- **→ (Right Arrow)**: Go to next page

## Example: Success Page Flow

When the form is submitted successfully, it navigates to the success page:

```javascript
// In entry-form.html
const response = await fetch('/journal/create-entry/', {
    method: 'POST',
    body: formData,
});

if (response.status === 200) {
    // Navigate to next page (success-left/success-right)
    if (window.pageManager) {
        await window.pageManager.nextPage();
    }
}
```

The success page then includes a button to return to the form:

```javascript
// In success-right.html
const returnBtn = document.getElementById('return-to-form');
if (returnBtn) {
    returnBtn.addEventListener('click', async () => {
        if (window.pageManager) {
            // Go back to the form page (index 0)
            await window.pageManager.goToPage(0);
        }
    });
}
```

## Styling

Custom CSS classes are provided:

- `.page-content`: Main content wrapper (styles fade animations)
- `.success-container`: For success page left content
- `.success-info`: For success page right content
- `.action-btn`: For action buttons
- `.page-error`: For error states

### Animations

The system includes built-in fade animations:
- **Fade Out**: 300ms (ease-out)
- **Fade In**: 400ms (ease-in)
- **Success Icon**: Scale-in animation on success page

## Best Practices

1. **Always use page pairs**: Left and right pages should be thematically related
2. **Wrap content in `.page-content`**: Ensures proper styling and animations
3. **Use IIFE for scripts**: Wrap page scripts in immediately-invoked function expressions to avoid conflicts
4. **Check for element existence**: Always verify elements exist before adding listeners
5. **Use `window.pageManager`**: Access the global page manager instance from page scripts
6. **Keep pages modular**: Each page pair should be self-contained and independent

## Future Enhancements

- Touch gestures for mobile navigation
- Custom transition effects
- Page history/back button support
- Analytics integration
- Page preloading priority
- Lazy loading for large projects
