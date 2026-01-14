# Patternzon
#### Description:

## Patternzon - a marketplace for knitting & crochet patterns

Users can discover, upload and review knitting and crochet patterns with options to filter by craft or difficulty, search by keyword, view trending patterns and see ratings. It's built with Flask, SQLAlchemy, and Bootstrap 5.


### Features

- **Account system:** register, login, logout (Flask-Login).

- **Upload patterns:** title, craft (knit/crochet), optional difficulty, instructions (Markdown text allowed) and an optional image upload.

- **Browse & search:** filter by craft and difficulty, search by title or instructions, sort (newest/oldest/A–Z/Z–A), optional “favorites only” filter when logged in.

- **Favorites:** heart/undo-heart patterns, a Favorites page.

- **Ratings & reviews:** 1–5 star rating per user per pattern, average rating displayed with a “filled stars” bar, submit form at the bottom of the detail page.

- **“People also liked”:** simple collaborative filtering based on overlapping favorites with other users who favorited the current pattern.

- **Responsive UI:** Bootstrap layout, “glass card” styling on image backgrounds, accessible keyboard/enter-to-search behavior.

- **File storage:** images saved under `instance/uploads/`.




### Project structure & what each file does

#### `app.py`

`create_app()` configures Flask, SQLAlchemy and Flask-Login, ensures `instance/` and `instance/uploads/` exist, creates the SQLite DB

**Routes:**

- `/` : Homepage with search bar and sections: Trending , New & noteworthy, For you and knit/crochet examples.

- `/register`, `/login`, `/logout` : authentication

- `/patterns` : browse with GET filters (`q`, `craft`, `difficulty`, `sort`, `only_fav`), returns rating aggregates for star display.

- `/patterns/new` : create a new pattern (requires login). Supports optional image upload.

- `/patterns/<int:pattern_id>` : detail page with average rating, image, instructions, people also liked and rating form (requires login).

- `/patterns/<int:pattern_id>/favorite` : toggle favorite.

- `/patterns/<int:pattern_id>/rate` : Create/update a 1–5 rating (clamped server-side).

- `/favorites` : the current user’s favorites list.

- `/u/<path:filename>` : serves uploaded images from `instance/uploads/`.


#### `models.py`

- **User** (`id`, `username`, `email`, `password_hash`).
  Helpers: `set_password()` and `check_password()`.
  Relations: `patterns` (author), `favorites` (many–many to Pattern), `pattern_ratings`, `pattern_views`.

- **Pattern** (`id`, `title`, `craft`, `difficulty`, `instructions_md`, `image_path`, `author_id`) : a single knitting/crochet pattern.
  `author_id`: FK to `User.id`.
  Relations: `author` (User), `liked_by` (Users who favorited), `ratings`, `views`.

- **favorites**  association table for a many–many link between users and patterns.
  Columns: `user_id`, `pattern_id` (both PK & FK). Powers favorites and recommendations.

- **PatternRating** (`user_id`, `pattern_id`, `rating`, `created_at`, `updated_at`) : one rating per user per pattern.
  `rating` is 1–5. Relations: `user`, `pattern`.

- **PatternView** (`id`, `pattern_id`, `user_id?`, `created_at`) : per-view tracking (anonymous allowed) used for Trending.
  Relations: `pattern`, `user`.



### Templates (`templates/`)

**layout.html:** Sticky, dark custom navbar with the “Patternzon” brand, an “All patterns” link, “+ Add Pattern,” and a user dropdown. Shows flash messages; supports background themes. Emoji favicon (🧶).

**index.html:** Landing page with search form and sections for Trending, New & noteworthy, For you (if logged in), plus teasers.

**patterns.html:** Results grid with filters (search, craft, difficulty, sort, favorites-only). Auto-submit on changes. Cards show image, title, badges, author, favorite toggle, and average rating.

**detail.html:** Single pattern page: title, rating, image, badges, author, instructions, “People also liked,” rating form.

**new.html:** Pattern creation form.

**login.html**, **register.html:** Simple Bootstrap forms with “glass card” styling.



### Static assets (`static/`)

**styles.css:**
Brand variables, scenic backgrounds, responsive login background, navbar styling (solid/translucent with blur).
Glass cards with frosted blur + shadows.
Buttons and links with brand colors.
Rating stars using layered “★★★★★” and clipped gold fill.
Dropdown menu styling.



### How the recommendation (“People also liked”) works

On a pattern’s detail page:

1. Find other users who also favorited the current pattern.
2. Find other patterns those users favorited (excluding the current one).
3. Count occurrences and sort by overlap frequency.
4. Show the top few.



### Design choices & tradeoffs

- SQLite is ideal for CS50, can later swap to Postgres.
- Server-rendered Jinja2 templates for simplicity.
- Images stored in `instance/uploads/` with strict allowed extensions (max 4MB), can later swap for cloud storage such as Amazon S3 without changing the frontend.
- Ratings are numeric only, text reviews could be added later.
- Instructions stored raw, for production it would first be converted to HTML so users can’t inject malicious code.
