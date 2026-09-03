# ConservaTrack (COMP639 Project 2)

## About The Application
ConservaTrack is a comprehensive web application designed for conservation groups to manage their ecological efforts. It provides a centralised platform for:
- **Conservation Group Management**: Super Admins and Group Coordinators can manage groups, members, roles, and group visibility.
- **Trap and Bait Station Management**: Track trap lines, bait lines, individual traps, and bait stations with geographical coordinates.
- **Field Data Recording**: Operators can log trap catches, bait station usage, and general field observations.
- **Knowledge Sharing**: A Knowledge Hub allows users to share articles, guides, and group updates.
- **Donation Management**: Groups can receive donations, and administrators can manage donation settings, receipts, and view contribution records.
- **Interactive Maps**: Visualize trap lines, bait stations, and conservation activity on interactive geographic maps.
- **Gamification & Badges**: Users can earn points and unlock badges for their contributions and field data recording.
- **Customizable Themes**: Groups can personalise their dashboard appearance with custom themes.

## Test Users
The database is seeded with test accounts for various roles. All test accounts share the same password: **@hashed_password123**

| Role | Username | Email |
| :--- | :--- | :--- |
| **Super Admin** | `admin_main` | `admin@pf.org.nz` |
| **Group Coordinator** | `alice_coord` | `alice@waitakere.org` |
| **Operator** | `op_dave` | `dave@work.com` |
| **Observer** | `observer1` | `sarah.jones@example.org` |

## AI Acknowledgements 

This project utilised various Large Language Models (LLMs) to assist with implementation planning, UI/UX design, routing logic, and debugging.

| # | AI Asset | Description of Contribution |
| :--- | :--- | :--- |
| 01 | Antigravity (Gemini 3 Flash) | Implementation of Bait Station Line CRUD functionality, including repository, routes, and management UI. |
| 02 | Antigravity (Gemini 3 Flash) | Implementation of AC2 & AC3: Adding Individual Bait Stations to Lines with custom "Other" type handling, including new repository, modularized routes, and station management UI with dynamic validation. |
| 03 | GitHub CoPilot | Added public Donate page and navigation link; small UI/template updates. |
| 04 | GitHub CoPilot | Added group-specific Donate buttons on home and group pages (public-only) and updated donate route to accept `group_id`. |
| 05 | GitHub CoPilot | Implemented donation form and client-side JS (anonymous flag), server-side validation, `Donations` DB persistence via a new repository, and a public group selector so donations can be associated with specific groups. |
| 06 | GitHub CoPilot | Added donation summary to public group page and removed "View group details" label from group cards. |
| 07 | Antigravity (Claude Sonnet) | Implemented dynamic Donation Impact Statement: Group Coordinators can enter a custom impact description on the Donation Settings page that replaces the default text on the public Donate page. Falls back to the default statement if no custom text is set. Client-side JavaScript updates the description dynamically when the user changes the selected group or donation type. |
| 08 | Antigravity (Claude Sonnet) | Implemented conditional Donate button visibility: When a Group Coordinator toggles off donations in the Donation Settings page, the Donate button is hidden from the home page group cards, the group detail page, and the group is removed from the public Donate page's group selector dropdown. |
| 09 | Antigravity (Claude Sonnet) | Added "Donation Setting" link to the left-side sidebar navigation footer for Coordinator users, consistent with its placement in the top-navbar Account dropdown for the standard layout. |
| 10 | Antigravity (Gemini 3.5 Flash) | Updated the public Donate page's group dropdown to display active private groups when donations are enabled. |
| 11 | Antigravity (Gemini 3.5 Flash) | Refactored donation-related routes (public donation and donation settings) from common_routes.py to a new modular donate_routes.py module. |
| 12 | Antigravity (Gemini 3.5 Flash) | Fixed type mismatch (string vs integer) in coordinator donation receipt route causing 403 Forbidden errors when viewing group receipts. |
| 13 | Antigravity (Gemini 3.5 Flash) | Implemented site-wide donation records viewing page for the Super Admin, showing records across all groups, styled consistently with coordinator donations history view. |
| 14 | Antigravity (Gemini 3.5 Flash) | Implemented global donation receipt settings for Super Admin to upload receipt logo and configure footer text (up to 200 chars), automatically applying them to receipts across all groups. |
| 15 | Antigravity (Gemini 3.5 Flash) | Secured donation records and management routes using roles-required decorator to deny access to Observers and Operators, flashing unauthorized access alert. |
| 16 | Antigravity (Gemini 3.5 Flash) | Updated donation receipt back button to link dynamically based on role, resolving issues when receipts open in new tabs. |
| 17 | Antigravity (Gemini 3.5 Flash) | Added a total donation amount summary badge on both the Super Admin and Group Coordinator donation records history pages. |
| 18 | Antigravity (Gemini 3.5 Flash) | Fixed psycopg2 CardinalityViolation error on operator login/dashboard by using SUM() aggregate for cumulative points. |
| 19 | Antigravity (Gemini 3.5 Flash) | Fixed time displayed on the donation receipt PDF and footer to use New Zealand Time (NZT) in 24-hour format. |
| 20 | GitHub CoPilot | Group selection function: Based on the common_routes.py and the core_repository.py, move the select group function to a new group_selection_routes.py and ensure all group selection functions of users are consolidated in this file. |
| 21 | GitHub CoPilot | Bait activity record function: Modify bait station record entry columns to add bait_removed and drop down list for bait active ingredience. |
| 22 | GitHub CoPilot | Filter function: Find operators not currently assigned to the specified line in the database. |
| 23 | GitHub CoPilot | Notification function: Pop up window notification for users whose roles are changed by admin or coordinator. Utilise the existing notification repository and database setting. |
| 24 | GitHub CoPilot | Parameter management: Extract the param of trap status, trap type, bait type, species and Bait station type from the look up table to enable param editing and management like the other parameters in the admin Control Parameters page. |
| 25 | GitHub CoPilot | Knowledge hub: Create a knowledge hub page with two sections (global knowledge sharing and group-specific sharing). Implemented moderation controls for Group Coordinators and Super Admins. Put the code in a separate knowhub_repository.py and knowhub_route.py. |
| 26 | GitHub CoPilot | Knowledge hub: Sticky buttons. |
| 27 | GitHub CoPilot | Knowledge hub: Put publish notice and create knowledge post into a new page. |
| 28 | GitHub CoPilot | Knowledge hub: Tab structure of the knowledge hub page. |
| 29 | GitHub CoPilot | Knowledge hub: Create a knowledge compose page to separate the knowledge hub draft page. |
| 30 | GitHub CoPilot | Knowledge hub: Draw a star for the featured article. |
| 31 | GitHub CoPilot | Knowledge hub: Filter function for knowledge hub posts. |
| 32 | GitHub CoPilot | Knowledge hub: Store uploaded documents directly into the database. |
| 33 | GitHub CoPilot | Knowledge hub: Debugged issue where uploaded documents were lost when clicking edit on a drafted post. |
| 34 | GitHub CoPilot | Knowledge hub: Filter function of the page in the UI Level. |
| 35 | GitHub CoPilot | Knowledge hub: Debugged issue where changing group and clicking a navigation link lost the chosen group context. |
| 36 | Claude (Anthropic) | Implementation of US 1.1 and 1.2: Application rebranding to ConservaTrack and home page group discovery tiles with Bootstrap card layout, public/private badges, and member count display. |
| 37 | Claude (Anthropic) | Implementation of US 1.01: Super Admin group management including create group, edit group tile/image/description, approve or reject group applications, appoint and remove Group Coordinators, and manage global data records (species, trap types, bait types). |
| 38 | Claude (Anthropic) | Implementation of US 1.02 and US 1.12: Group Coordinator user management including group-scoped member view, role assignment with in-app notifications, group visibility toggle, and join request approval/rejection. Access control enforced so Coordinators can only manage members within their own group. |
| 39 | GitHub CoPilot | Group selection function. |
| 40 | Claude (Anthropic) | Removed redundant total row from Donation History popup table, as the total amount is already displayed in the header badge. |
| 41 | Claude (Anthropic) | Implemented site-wide theme-aware button styling: replaced hardcoded Bootstrap colour classes (btn-primary, btn-success, btn-outline-secondary, etc.) with a unified btn-outline-theme class and CSS variable overrides in theme.css, so all buttons follow the active group theme colour across all pages. |
| 42 | Claude (Anthropic) | Redesigned Your Group and Coordinator Dashboard hero bar buttons to use semi-transparent white style, consistent with the dark gradient background across all themes. Removed Manage Join Requests button from the dashboard hero bar. |
| 43 | Claude (Anthropic) | Fixed donation receipt and generated timestamp to display in New Zealand Daylight Time (NZDT, UTC+13) with 12-hour am/pm format instead of UTC. |
| 44 | Claude (Anthropic) | Fixed psycopg2.errors.CardinalityViolation on operator dashboard by replacing scalar subquery with SUM() aggregate for cumulative points lookup in dashboard_repository.py. |
| 45 | Claude (Anthropic) | Redesigned Knowledge Hub Edit and Delete update buttons to be equal width and symmetrical, added ✏️ and 🗑️ emoji icons, and increased margin between Previous versions and Like sections. |
| 46 | Claude (Anthropic) | Refactored group_lines.html to remove Add trap and Add bait station buttons, replaced all hardcoded colour button classes with btn-outline-theme, and made Edit Line button full-width. |
| 47 | Claude (Anthropic) | Fixed default green theme hero bar gradient: darkened the right-side fade colour to improve text legibility against the lighter yellow-green end stop. |
| 48 | GitHub CoPilot | Lines route: Create a GET route /lines in Flask that only shows lines belonging to the current user’s group. Split them into trap lines and bait station lines. Each entry should show name, type, status, number of traps/bait stations, and assigned operator. Let users edit only if they are Operator or Group Coordinator; block people not in the group. Show a message if there are no lines. Include the route code, template, and any missing database functions. Use raw psycopg2 and lowercase table names. |
| 49 | GitHub CoPilot | Cancel join request: Add "Cancel Join Request" button for canceling pending private group join requests. |
| 50 | GitHub CoPilot | Points accumulation implementation: Build a points system in Flask with minimal new files. Make one function to log points and update the total. Award points for actions like submitting catches, adding traps/bait stations, creating lines/groups, posting/liking in Knowledge Hub, and daily logins — follow the point values and rules I list. Add an API route to get points, and show the user’s total in the navigation bar. Use Python, HTML, CSS, JS, and only create/modify what’s necessary. |
| 51 | Gemini 3.5 Flash | Badge Images Creation: create badges with these designs: Matariki Kiwi Special. Deep indigo + nine specific arranged stars; Whetū Kiwi (Star) Dark blue kiwi with scattered star speckles; Pounamu Kiwi (Jade) Translucent nephrite jade green; Mānuka Kiwi Translucent Sparkling yellow mānuka honeycomb texture; Kōwhai Kiwi Golden-yellow kiwi with hanging kōwhai flowers; Pōhutukawa Kiwi Crimson red kiwi with flowering branches; Rimu Kiwi Deep green kiwi with rimu leaf patterns; Kauri Kiwi Warm woody browns – rich caramel, mahogany, and aged timber tones |
| 52 | Gemini 3.5 Flash | Badge Images Crop: Separate badges into individual images, do not change badge design at all, only make background transparent |
