# app.py
import os, uuid
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Pattern, favorites as favorites_table, PatternRating, PatternView
from werkzeug.utils import secure_filename
from sqlalchemy import or_, func, desc

login_manager = LoginManager()
login_manager.login_view = "login"

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Ensure instance/ exists and use absolute SQLite path
    os.makedirs(app.instance_path, exist_ok=True)
    db_path = os.path.join(app.instance_path, "app.db")

    app.config.update(
        SECRET_KEY="dev-change-me",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TEMPLATES_AUTO_RELOAD=True,
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
    )

    upload_folder = os.path.join(app.instance_path, "uploads")
    os.makedirs(upload_folder, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_folder

    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}

    def allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():

        days = 14
        cutoff = db.func.datetime(db.func.current_timestamp(), f"-{days} days")
        trending_rows = (
            db.session.query(Pattern, func.count(PatternView.id).label("v"))
            .join(PatternView, PatternView.pattern_id == Pattern.id)
            .filter(PatternView.created_at >= cutoff)
            .group_by(Pattern.id)
            .order_by(desc("v"))
            .limit(8)
            .all()
        )
        trending = [p for (p, v) in trending_rows]

        if not trending:
            fav_rows = (
                db.session.query(Pattern, func.count(favorites_table.c.user_id).label("f"))
                .outerjoin(favorites_table, favorites_table.c.pattern_id == Pattern.id)
                .group_by(Pattern.id)
                .order_by(desc("f"), desc(Pattern.id))
                .limit(8)
                .all()
            )
            trending = [p for (p, f) in fav_rows]

        new_items = Pattern.query.order_by(Pattern.id.desc()).limit(8).all()

        for_you = []
        if current_user.is_authenticated:
            my_fav_ids = [p.id for p in current_user.favorites]
            if my_fav_ids:
                co_rows = (
                    db.session.query(Pattern, func.count().label("cnt"))
                    .join(favorites_table, favorites_table.c.pattern_id == Pattern.id)
                    .filter(
                        favorites_table.c.user_id.in_(
                            db.session.query(favorites_table.c.user_id)
                            .filter(favorites_table.c.pattern_id.in_(my_fav_ids))
                        ),
                        ~Pattern.id.in_(my_fav_ids)  # don’t recommend what I already favorited
                    )
                    .group_by(Pattern.id)
                    .order_by(desc("cnt"))
                    .limit(8)
                    .all()
                )
                for_you = [p for (p, cnt) in co_rows]

        knit_teaser = Pattern.query.filter_by(craft="knit").order_by(Pattern.id.desc()).limit(6).all()
        crochet_teaser = Pattern.query.filter_by(craft="crochet").order_by(Pattern.id.desc()).limit(6).all()

        return render_template(
            "index.html",
            trending=trending,
            new_items=new_items,
            for_you=for_you,
            knit_teaser=knit_teaser,
            crochet_teaser=crochet_teaser,
        )


    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirmation = request.form.get("confirmation", "")

            if not username or not email or not password:
                flash("All fields are required.")
                return redirect(url_for("register"))
            if password != confirmation:
                flash("Passwords do not match.")
                return redirect(url_for("register"))
            if User.query.filter((User.username == username) | (User.email == email)).first():
                flash("Username or email already taken.")
                return redirect(url_for("register"))

            u = User(username=username, email=email)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            flash("Registered! You can now log in.")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            u = User.query.filter_by(username=username).first()
            if not u or not u.check_password(password):
                flash("Invalid username or password.")
                return redirect(url_for("login"))
            login_user(u)
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/patterns/new", methods=["GET", "POST"])
    @login_required
    def new_pattern():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            craft = request.form.get("craft", "").strip()
            difficulty = request.form.get("difficulty", "").strip()
            instructions = request.form.get("instructions_md", "").strip()

            if not title or not craft or not instructions:
                flash("Title, craft, and instructions are required.")
                return redirect(url_for("new_pattern"))

            file = request.files.get("image")
            filename = None
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit(".", 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(filename)))

            p = Pattern(
                title=title,
                craft=craft,
                difficulty=difficulty or None,
                instructions_md=instructions,
                author_id=current_user.id,
                image_path=filename,
            )

            db.session.add(p)
            db.session.commit()
            flash("Pattern created.")
            return redirect(url_for("pattern_detail", pattern_id=p.id))

        return render_template("new.html")

    @app.route("/patterns/<int:pattern_id>")
    def pattern_detail(pattern_id):
        p = Pattern.query.get_or_404(pattern_id)

        db.session.add(PatternView(pattern_id=pattern_id, user_id=current_user.id if current_user.is_authenticated else None))
        db.session.commit()

        user_ids_subq = db.session.query(favorites_table.c.user_id).filter(
            favorites_table.c.pattern_id == pattern_id
        )
        if current_user.is_authenticated:
            user_ids_subq = user_ids_subq.filter(favorites_table.c.user_id != current_user.id)

        co_q = (
            db.session.query(Pattern, func.count().label("cnt"))
            .join(favorites_table, favorites_table.c.pattern_id == Pattern.id)
            .filter(
                favorites_table.c.user_id.in_(user_ids_subq),
                Pattern.id != pattern_id,
            )
            .group_by(Pattern.id)
            .order_by(desc("cnt"))
        )

        if current_user.is_authenticated:
            my_fav_ids = [pp.id for pp in current_user.favorites]
            if my_fav_ids:
                co_q = co_q.filter(~Pattern.id.in_(my_fav_ids))

        people_also_liked = [pp for (pp, cnt) in co_q.limit(8).all()]

        avg_, cnt_ = db.session.query(
            func.avg(PatternRating.rating), func.count(PatternRating.rating)
        ).filter_by(pattern_id=pattern_id).first()
        rating_avg = float(avg_ or 0.0)
        rating_count = int(cnt_ or 0)

        my_rating = 0
        if current_user.is_authenticated:
            pr = PatternRating.query.get((current_user.id, pattern_id))
            my_rating = pr.rating if pr else 0

        return render_template(
            "detail.html",
            p=p,
            people_also_liked=people_also_liked,
            rating_avg=rating_avg,
            rating_count=rating_count,
            my_rating=my_rating,
        )

    @app.route("/patterns/<int:pattern_id>/rate", methods=["POST"])
    @login_required
    def rate_pattern(pattern_id):
        Pattern.query.get_or_404(pattern_id)  # ensure exists
        try:
            rating = int(request.form.get("rating", "0"))
        except ValueError:
            rating = 0
        rating = max(1, min(5, rating))  # clamp 1..5

        pr = PatternRating.query.get((current_user.id, pattern_id))
        if pr:
            pr.rating = rating
        else:
            pr = PatternRating(user_id=current_user.id, pattern_id=pattern_id, rating=rating)
            db.session.add(pr)
        db.session.commit()
        flash("Thanks for rating!")
        return redirect(request.referrer or url_for("pattern_detail", pattern_id=pattern_id))



    @app.route("/u/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/favorites")
    @login_required
    def favorites_page():
        patterns = current_user.favorites
        return render_template("patterns.html", patterns=patterns, craft="")

    @app.route("/patterns/<int:pattern_id>/favorite", methods=["POST"])
    @login_required
    def favorite_pattern(pattern_id):
        p = Pattern.query.get_or_404(pattern_id)
        if p in current_user.favorites:
            current_user.favorites.remove(p)
            db.session.commit()
            flash("Removed from favorites.")
        else:
            current_user.favorites.append(p)
            db.session.commit()
            flash("Added to favorites.")

        return redirect(request.referrer or url_for("pattern_detail", pattern_id=pattern_id))

    @app.route("/patterns")
    def patterns_browse():
        craft = (request.args.get("craft") or "").lower()
        q = (request.args.get("q") or "").strip()
        difficulty = (request.args.get("difficulty") or "").strip().lower()
        only_fav = request.args.get("only_fav") == "1"
        sort = (request.args.get("sort") or "new").lower()  # new | old | az | za

        query = Pattern.query

        if craft in ("knit", "crochet"):
            query = query.filter_by(craft=craft)

        allowed_difficulties = {"beginner", "easy", "intermediate", "advanced"}
        if difficulty in allowed_difficulties:
            query = query.filter(Pattern.difficulty == difficulty)

        if q:
            like = f"%{q}%"
            query = query.filter(or_(Pattern.title.ilike(like),
                                 Pattern.instructions_md.ilike(like)))

        if only_fav and current_user.is_authenticated:
            fav_ids = [p.id for p in current_user.favorites]
            if fav_ids:
                query = query.filter(Pattern.id.in_(fav_ids))
            else:
                query = query.filter(False)

        if sort == "old":
            query = query.order_by(Pattern.id.asc())
        elif sort == "az":
            query = query.order_by(Pattern.title.asc())
        elif sort == "za":
            query = query.order_by(Pattern.title.desc())
        else:
            query = query.order_by(Pattern.id.desc())

        patterns = query.all()

        ids = [p.id for p in patterns]
        rating_stats = {}
        if ids:
            rows = (
                db.session.query(PatternRating.pattern_id,
                         func.avg(PatternRating.rating),
                         func.count(PatternRating.rating))
                .filter(PatternRating.pattern_id.in_(ids))
                .group_by(PatternRating.pattern_id)
                .all()
            )
            for pid, avg, cnt in rows:
                rating_stats[pid] = (float(avg or 0.0), int(cnt or 0))

        return render_template(
            "patterns.html",
            patterns=patterns,
            rating_stats=rating_stats,
            craft=craft,
            q=q,
            difficulty=difficulty,
            only_fav=only_fav,
            sort=sort,
        )


    @app.after_request
    def no_cache(resp):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Expires"] = 0
        resp.headers["Pragma"] = "no-cache"
        return resp

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
