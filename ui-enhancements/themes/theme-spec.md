# TUNIX Theme System

## Design Principles
- **Visual Hierarchy**: Clear distinction between interactive and static elements
- **Color Theory**: Scientifically-backed color palette for readability and reduced eye strain
- **Accessibility First**: High contrast options and screen reader compatibility
- **Consistency**: Uniform design language across all applications

## Theme Components

### Color Scheme
- **Primary Colors**: A carefully selected palette that balances aesthetics and usability
- **Accent Colors**: User-configurable accent colors that apply system-wide
- **Dark/Light Modes**: Fully implemented dark and light themes with automatic switching
- **High Contrast**: Accessibility themes for vision-impaired users

### Typography
- **Font Selection**: Optimized fonts for screen readability
- **Font Rendering**: Enhanced subpixel rendering and hinting
- **Consistent Sizing**: Standardized font sizes across the system
- **Variable DPI Support**: Proper scaling for different display resolutions

### Interface Elements
- **Buttons & Controls**: Redesigned interactive elements with clear states
- **Window Decorations**: Modern, clean window frames and controls
- **Dialog Boxes**: Simplified, intuitive dialog layouts
- **Menus**: Enhanced dropdown and context menus

### Icons
- **Icon Set**: Comprehensive icon set with consistent style
- **Scalable Graphics**: SVG-based icons for crisp rendering at any size
- **Visual Metaphors**: Intuitive, universally understood icon designs
- **Contextual Variants**: Icons that adapt to light/dark themes

## Technical Implementation
- GTK4 theme engine with custom CSS
- SVG icon toolkit
- Runtime theme switching without restart
- Theme extension API for third-party applications