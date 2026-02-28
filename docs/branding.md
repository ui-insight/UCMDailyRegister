# UI Branding

The frontend follows the University of Idaho Brand Book 2023 guidelines. All colors, typography, and logo usage are configured through Tailwind CSS v4 theme tokens so changes propagate across every component automatically.

## Brand Colors

### Pride Gold (Primary)

The university's signature gold replaces generic amber tones throughout the interface.

| Token              | Hex       | Usage                                      |
|--------------------|-----------|--------------------------------------------|
| `ui-gold-50`       | `#FFF9EB` | Light backgrounds, hover states             |
| `ui-gold-100`      | `#FEF0CD` | Badges, subtle highlights                   |
| `ui-gold-200`      | `#FDE08B` | Borders, dividers                           |
| `ui-gold-300`      | `#FBCD48` | Decorative accents                          |
| `ui-gold-400`      | `#F6BD17` | Hover states on dark backgrounds            |
| `ui-gold-500`      | `#F1B300` | Official Pride Gold -- sidebar active state |
| `ui-gold-600`      | `#D49B00` | Button backgrounds (better contrast)        |
| `ui-gold-700`      | `#A87700` | Button text on light backgrounds            |
| `ui-gold-800`      | `#7C5800` | Dark text accents                           |
| `ui-gold-900`      | `#4D3600` | Darkest gold for high contrast              |

!!! note "WCAG Contrast"
    Pride Gold (#F1B300) does not meet WCAG AA contrast requirements for white text. Use `ui-gold-600` or darker shades for button backgrounds with white text. The sidebar active state uses `text-ui-black` on a gold background for maximum readability.

### Clearwater (Secondary)

The official secondary teal replaces generic indigo tones for interactive and accent elements.

| Token                  | Hex       | Usage                                  |
|------------------------|-----------|-----------------------------------------|
| `ui-clearwater-50`     | `#EEFBFB` | Active provider highlight background    |
| `ui-clearwater-100`    | `#D0F4F4` | Light accents                           |
| `ui-clearwater-200`    | `#A3E8E8` | Borders on active states                |
| `ui-clearwater-300`    | `#5FD4D4` | Ring highlights                         |
| `ui-clearwater-400`    | `#29B8B8` | Active card borders                     |
| `ui-clearwater-500`    | `#008080` | Official Clearwater -- badges, links    |
| `ui-clearwater-600`    | `#006B6B` | Button backgrounds                      |
| `ui-clearwater-700`    | `#005555` | Hover states                            |
| `ui-clearwater-800`    | `#004040` | Dark text accents                       |
| `ui-clearwater-900`    | `#002B2B` | Darkest teal                            |

### Neutrals

| Token          | Hex       | Usage                    |
|----------------|-----------|--------------------------|
| `ui-black`     | `#323232` | Primary text color       |
| `ui-silver`    | `#808080` | Secondary text, borders  |

## Typography

The application uses **Public Sans** as its primary typeface, loaded via Google Fonts. It is configured as the default `font-sans` in the Tailwind theme, so it applies automatically to all text.

```html
<!-- Loaded in index.html -->
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,500&display=swap" rel="stylesheet" />
```

Weights used:

| Weight | Usage                                |
|--------|--------------------------------------|
| 300    | Light captions and metadata          |
| 400    | Body text                            |
| 500    | Medium emphasis, nav items           |
| 600    | Semibold headings, labels            |
| 700    | Bold headings, buttons               |

## Logo

The official University of Idaho horizontal logo (gold on transparent/white text) is displayed in the sidebar header.

- **File:** `frontend/public/ui-logo-gold-white-horizontal.png`
- **Source:** UIBranding asset directory
- **Placement:** Top of the sidebar, above "UCM Newsletter Builder" subtitle
- **Size:** `h-10 w-auto` (40px height, natural aspect ratio)

## Tailwind Theme Configuration

All brand tokens are defined in `frontend/src/index.css` using Tailwind CSS v4's `@theme` directive:

```css
@import "tailwindcss";

@theme {
  --color-ui-gold-500: #F1B300;
  --color-ui-clearwater-500: #008080;
  --color-ui-black: #323232;
  --font-sans: 'Public Sans', ui-sans-serif, system-ui, sans-serif;
  /* ... full scale for all shades */
}
```

!!! tip "Adding New Brand Colors"
    To add a new brand color, define its full shade scale (50--900) in the `@theme` block. Reference it in components as `bg-ui-newcolor-500`, `text-ui-newcolor-700`, etc.

## Sidebar

The sidebar uses a dark gray background (`#111827` / `gray-900`) with:

- Gold-on-transparent logo at top
- Light gray nav text (`gray-300`)
- **Active nav item:** `bg-ui-gold-500 text-ui-black font-medium` (gold background with dark text)
- **Hover state:** `hover:bg-gray-700`

## Component Migration Reference

When the branding was applied, all Tailwind utility classes were updated:

| Old Class Pattern   | New Class Pattern         |
|---------------------|---------------------------|
| `amber-*`           | `ui-gold-*`               |
| `indigo-*`          | `ui-clearwater-*`         |
| System font stack   | Public Sans (`font-sans`) |
