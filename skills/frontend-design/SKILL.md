---
name: frontend-design
description: Guides the design and redesign of the RISE UP Streamlit frontend. Use this when adding new pages, redesigning UI components, fixing layout bugs, or making the interface consistent with the platform design system.
---

# Frontend Design Skill

## Mission

Produce clean, professional, light-mode Streamlit pages that are consistent
with the RISE UP design system and ready to run without additional changes.

The platform audience is investigators, security analysts, and operational
staff. The interface must communicate trust, accuracy, and operational clarity.
It must not look like a gaming dashboard or a generic AI chatbot.

---

## When to Use

- Adding a new page or tab to the application
- Redesigning an existing page or panel
- Fixing layout bugs, spacing issues, or style inconsistencies
- Adding a new UI component (card, badge, filter panel, timeline bar)
- Reviewing whether a proposed design follows the platform conventions

## When Not to Use

- Changes that are purely backend (database, R2, NIM API calls)
- Changes confined to `database.py`, `r2.py`, `nim.py`, or `video.py`
- Minor copy edits with no layout or style impact

---

## Inputs

Before starting any design work, read:

1. `src/frontend/app.py` — current page structure and session state keys
2. `src/frontend/database.py` — available fields for each report
3. `.streamlit/config.toml` — active theme overrides

---

## Design System

### Colour Palette

| Token | Hex | Use |
|---|---|---|
| Main background | `#FFFFFF` | Page and card surfaces |
| Page background | `#F7F8FA` | App canvas behind cards |
| Primary text | `#171A1F` | Headings and body copy |
| Secondary text | `#667085` | Labels, captions, metadata |
| Muted text | `#98A2B3` | Timestamps, fine print |
| Border | `#E4E7EC` | Card borders, dividers, inputs |
| Accent green | `#76B900` | Primary buttons, active nav, progress |
| Accent green hover | `#5A8F00` | Hover state for green elements |
| Active background | `#F1F8E8` | Selected nav item, active chip |
| Info blue | `#2563EB` | Informational highlights |
| Warning amber | `#D97706` | Review-required status |
| Critical red | `#DC2626` | Severity 5, incident markers |
| Success green | `#16A34A` | Verified status |

**Rule:** use accent green only for buttons, active nav indicators, and small
visual highlights. Do not use it for large backgrounds or long text.

### Typography

Import Inter from Google Fonts. Apply globally via CSS:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif !important;
}
```

| Role | Size | Weight |
|---|---|---|
| Page title | 28–32 px | 700 |
| Section heading | 18–22 px | 600 |
| Card title | 15–17 px | 600 |
| Body text | 14–16 px | 400 |
| Metadata / label | 12–14 px | 400–500 |

### Status Badges

Use these HTML classes (defined in the CSS block):

```html
<span class="status-badge status-verified">Verified</span>
<span class="status-badge status-review">Under Review</span>
<span class="status-badge status-unreviewed">Unreviewed</span>
```

Severity badges use `sev-1` through `sev-5` classes.

### Cards

Use `st.container(border=True)` for report cards in a grid layout.

Do NOT wrap `st.metric` widgets inside `st.container(border=True)` — this
causes a white circle rendering bug. Instead, style metrics with raw CSS
targeting `[data-testid="stMetric"]`, or use plain HTML `<div>` containers.

### Sidebar Navigation

Navigation uses `st.button` with `type="primary"` for the active page and
`type="secondary"` for inactive pages. Do not use `st.radio` or `st.selectbox`
for top-level navigation.

Active button style (via CSS):
```css
section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
    background-color: #F1F8E8 !important;
    color: #171A1F !important;
    border: 1px solid #76B900 !important;
}
```

### Filter Panels

For filter rows that sit above a content grid, use a plain HTML `<div>` with a
white background and border — not `st.container(border=True)`. Follow
immediately with `st.columns` for the actual filter widgets.

```python
st.markdown("""
<div style="background-color: #FFFFFF; border: 1px solid #E4E7EC;
            border-radius: 10px; padding: 16px 20px; margin-bottom: 24px;">
    <div style="font-size: 14px; font-weight: 600; color: #171A1F;">Section Title</div>
</div>
""", unsafe_allow_html=True)
f1, f2, f3 = st.columns(3)
```

---

## Navigation and Page Structure

The app uses `st.session_state.current_page` to switch between top-level pages.
Within a page, sub-views are controlled by a secondary session key such as
`reports_subview` (`"list"` | `"detail"` | `"analyze"`).

Current top-level pages:

| Key | Label | Purpose |
|---|---|---|
| `"reports"` | Incident Reports | Browse, view, edit reports; upload and analyze videos |
| `"dashboard"` | Analytics Dashboard | Metrics and charts from the database |

The analyze sub-view lives inside `"reports"`, not as a standalone tab.
After a user uploads a video, redirect them to `reports_subview = "analyze"`.

---

## Steps for Adding a New Page

1. Add the new key and label to `nav_items` in the sidebar section.
2. Add an `elif st.session_state.current_page == "new_key":` block at the
   bottom of the file, following the existing pattern.
3. If the page has sub-views, add a new session key (e.g., `new_page_subview`)
   and handle `"list"` / detail flows separately.
4. Clear any page-specific session state when navigating away (in the nav
   button's `if` block).

---

## Steps for Adding a New Component

1. Identify the closest existing component in `app.py` (card, badge, timeline).
2. Re-use the existing HTML class names and CSS variables — do not introduce new
   inline colour values.
3. If the component requires a new CSS class, add it to the `<style>` block at
   the top of `app.py`.
4. Test the component in the list view, detail view, and on a narrow viewport.

---

## Validation Checklist

After making any frontend change:

- [ ] Run `uv run python -m streamlit run src/frontend/app.py`
      and confirm no import or syntax errors appear in the terminal.
- [ ] Navigate to every top-level page and confirm it renders without a white
      screen or Python traceback.
- [ ] Confirm no emojis are present in any label, heading, caption, or button.
- [ ] Confirm background is light (`#F7F8FA` / `#FFFFFF`), not dark.
- [ ] Confirm metric cards do not show a white circle border artifact.
- [ ] Confirm sidebar shows only the two nav items (no Faculty Supervisor text).
- [ ] Confirm filter panels render above content without overlap.

---

## Common Pitfalls

| Pitfall | Fix |
|---|---|
| `st.metric` inside `st.container(border=True)` shows a white circle | Style metrics with CSS on `[data-testid="stMetric"]` instead |
| Emojis in labels break the no-emoji project rule | Replace with plain text descriptions |
| Dark background leaking through | Add `background-color: #F7F8FA !important` to `[data-testid="stAppViewContainer"]` |
| New nav tab breaks back-navigation | Clear `selected_report_id` and subview keys in the nav button handler |
| Upload does not redirect to analyze | Set `reports_subview = "analyze"` and `analyze_video_key` before calling `st.rerun()` |

---

## Key Files

| File | Role |
|---|---|
| `src/frontend/app.py` | All pages, CSS, session state, routing |
| `src/frontend/database.py` | SQLite CRUD for incident reports |
| `src/frontend/assets/nvidia_logo_horizontal.png` | NVIDIA logo shown in header |
| `.streamlit/config.toml` | Streamlit theme and server config |
