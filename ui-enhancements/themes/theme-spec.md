# TUNIX Theming System

## Design Philosophy
The TUNIX theming system aims to create a visually consistent, modern, and accessible interface across all applications. It draws inspiration from contemporary design principles while maintaining a unique identity.

## Color Palette
### Primary Colors
- **Accent Blue**: #3584e4 - Used for primary buttons, selected items, and interactive elements
- **Background**: #ffffff (Light) / #242424 (Dark) - Main application backgrounds
- **Surface**: #fafafa (Light) / #303030 (Dark) - Cards, dialogs, and elevated surfaces
- **On Primary**: #ffffff - Text on primary colored elements
- **On Background**: #202020 (Light) / #eeeeee (Dark) - Main text color

### Secondary Colors
- **Success Green**: #26a269 - Success indicators and actions
- **Warning Yellow**: #e5a50a - Warnings and alerts
- **Error Red**: #e01b24 - Error messages and destructive actions
- **Purple**: #9141ac - Alternative accent for variety
- **Teal**: #1a7e76 - Alternative accent for variety

## Typography
- **Primary Font**: Noto Sans - Used for all UI elements
- **Monospace Font**: Fira Code - Used for terminal and code
- **Font Sizes**:
  - Header 1: 24px
  - Header 2: 20px
  - Header 3: 16px
  - Body: 14px
  - Caption: 12px
- **Font Rendering**: Enhanced rendering settings with proper hinting and anti-aliasing

## Interface Elements
### Buttons
- Slightly rounded corners (8px radius)
- Subtle hover and press animations
- Clear visual hierarchy between primary, secondary, and text buttons

### Input Fields
- Consistent styling across applications
- Clear focus states with accent color
- Subtle animations for feedback

### Windows and Dialogs
- Consistent padding (16px)
- Subtle drop shadows for elevation
- Smooth opening and closing animations

### Icons
- Unified icon set based on Papirus with TUNIX modifications
- Consistent sizing and padding
- SVG format for sharp rendering at all sizes

## Dark Mode
- Full dark mode support across all applications
- Automatic switching based on time or manual toggle
- Careful attention to contrast and readability

## Accessibility
- Meets WCAG 2.1 AA standards for contrast
- Support for high-contrast mode
- Scalable interface elements for different DPIs

## Implementation
- GTK4 theme with custom CSS
- Integration with Qt applications via Qt style bridge
- Custom icon theme based on Papirus
- dconf settings for consistent application appearance

## Application Compatibility
- Native GTK applications receive full theming
- Electron apps with themed title bars
- Firefox custom theme integration
- LibreOffice theme compatibility