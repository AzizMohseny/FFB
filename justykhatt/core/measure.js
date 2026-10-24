/**
 * Core Module: measure.js
 * Responsibility: Parse text, measure rendered width of words + spaces, and calculate remaining space.
 * Contains no justification logic or DOM manipulation.
 */

const MeasureEngine = {
    /**
     * Measures the line and calculates remaining space.
     * @param {string} text - The raw text to measure.
     * @param {number} targetWidth - The target width of the line in pixels.
     * @param {Object} context - DOM context for measurement (e.g., fontFamily, fontSize).
     * @returns {Object} { wordCount, totalWidth, remainingSpace, words }
     */
    measureLine: function(text, targetWidth, context) {
        // 1. Parse words
        const words = text.split(/[ \t\n]+/).filter(w => w.length > 0);
        
        if (words.length === 0) {
            return { wordCount: 0, totalWidth: 0, remainingSpace: targetWidth, words: [] };
        }

        // 2. Create a hidden DOM element for accurate measurement
        const measureSpan = document.createElement('span');
        measureSpan.style.fontFamily = context.fontFamily;
        measureSpan.style.fontSize = context.fontSize;
        measureSpan.style.position = 'absolute';
        measureSpan.style.visibility = 'hidden';
        measureSpan.style.whiteSpace = 'nowrap';
        // Ensure the element doesn't affect the page layout
        measureSpan.style.left = '-9999px';
        document.body.appendChild(measureSpan);

        let totalWidth = 0;

        // 3. Measure each word
        words.forEach(word => {
            measureSpan.textContent = word;
            totalWidth += measureSpan.getBoundingClientRect().width;
        });

        // Measure the space character
        measureSpan.textContent = ' ';
        const spaceWidth = measureSpan.getBoundingClientRect().width;
        
        // Add spaces (one space per word, as per architectural design)
        totalWidth += (words.length * spaceWidth);

        // 4. Cleanup (remove the hidden element)
        document.body.removeChild(measureSpan);

        // 5. Calculate remaining space
        const remainingSpace = targetWidth - totalWidth;

        return {
            wordCount: words.length,
            totalWidth: totalWidth,
            remainingSpace: remainingSpace,
            words: words // Return the parsed words for the tagger
        };
    }
};