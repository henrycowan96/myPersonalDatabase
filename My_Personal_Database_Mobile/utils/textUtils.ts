/**
 * Utility functions for text processing
 */

/**
 * Removes markdown formatting symbols from text
 * @param text - The text to clean
 * @returns Cleaned text without markdown symbols
 */
export const stripMarkdown = (text: string): string => {
  if (!text) return '';
  
  return text
    // Remove bold/italic markers
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    // Remove headers
    .replace(/^#{1,6}\s+/gm, '')
    // Remove strikethrough
    .replace(/~~([^~]+)~~/g, '$1')
    // Remove inline code
    .replace(/`([^`]+)`/g, '$1')
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, '')
    // Remove links but keep text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove reference-style links
    .replace(/\[([^\]]+)\]\s*\[[^\]]*\]/g, '$1')
    // Remove blockquote markers
    .replace(/^>\s+/gm, '')
    // Remove horizontal rules
    .replace(/^---+$/gm, '')
    .replace(/^\*\*\*+$/gm, '')
    // Remove list markers
    .replace(/^[\s]*[-*+]\s+/gm, '')
    .replace(/^[\s]*\d+\.\s+/gm, '')
    // Clean up extra whitespace
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

/**
 * Removes HTML tags from text
 * @param text - The text to clean
 * @returns Cleaned text without HTML tags
 */
export const stripHtml = (text: string): string => {
  if (!text) return '';
  
  return text
    // Remove HTML tags
    .replace(/<[^>]*>/g, '')
    // Remove HTML entities
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    // Clean up extra whitespace
    .replace(/\s+/g, ' ')
    .trim();
};

/**
 * Formats category names by replacing underscores with spaces and capitalizing words
 * @param category - The category name to format (e.g., "Financial_Milestone")
 * @returns Formatted category name (e.g., "Financial Milestone")
 */
export const formatCategoryName = (category: string): string => {
  if (!category) return '';
  
  return category
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase());
};
