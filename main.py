from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def user_loader(user_id):
    return Users.query.get(user_id)


##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # CHILD WITH USERS
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("Users", back_populates="posts")

    # author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # PARENT WITH COMMENT
    comments = relationship("Comment", back_populates="parent_post")  # RELATIONSHIP MUST ALWAYS BE WITH CLASS NAME


class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)

    # PARENT WITH BLOGPOST
    posts = relationship("BlogPost", back_populates="author")   # USER WILL POST SO WE USE 'posts' AS A VARIABLE HERE

    # PARENT WITH COMMENT
    comments = relationship("Comment", back_populates="user_comment") # USER WILL COMMENT SO WE USE 'comments' AS A VARIABLE HERE


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    commentator_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    text = db.Column(db.Text, nullable=False)

    # CHILD WITH BLOGPOST
    parent_post = relationship("BlogPost", back_populates="comments")

    # CHILD WITH USERS
    user_comment = relationship("Users", back_populates="comments")     # comment_author


# db.create_all()


# def decorator(function):
#     def wrapper():
#         function
#         if not current_user:
#             print("403 Forbidden")
#     wrapper()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, user=current_user, logged_in=current_user.is_authenticated)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()

    email = request.form.get("email")
    password = generate_password_hash(password=str(request.form.get("password")), method="pbkdf2:sha256", salt_length=8)

    user = Users.query.filter_by(email=email).first()

    # TO MAKE THE LINE BELOW WORK YOU NEED TO USE 'POST' METHOD
    if form.validate_on_submit():
        if not user:
            new_user = Users(
                email=email,
                password=password,
                name=request.form.get("name")
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts", logged_in=current_user.is_authenticated))
        else:
            flash("Email already registered, login instead.")

    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    email = form.email.data
    password = form.password.data

    user = Users.query.filter_by(email=email).first()

    if form.validate_on_submit():
        if user:
            if check_password_hash(pwhash=user.password, password=password):
                login_user(user)
                return redirect(url_for("get_all_posts", logged_in=current_user.is_authenticated))
            else:
                flash("Wrong password, try again.")
        else:
            flash("That email does not exist, try registering.")

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()

    gravatar = Gravatar(
        app,
        size=100,
        rating='g',
        default='retro',
        force_default=False,
        force_lower=False,
        use_ssl=False,
        base_url=None
    )

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment")
            return redirect(url_for("login"))

        new_cmt = Comment(
            post_id=post_id,
            commentator_id=current_user.id,
            text=form.comment.data
        )
        db.session.add(new_cmt)
        db.session.commit()

    return render_template("post.html", form=form, post=requested_post, gravatar=gravatar, user=current_user, logged_in=current_user.is_authenticated)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # Posting information form the form
        name = request.form.get("name")
        mail = request.form.get("email")
        phone = request.form.get("phone_number")
        message = request.form.get("message")

        # Create mailto link
        subject = f"Message from Blog site"
        body = f"Name: {name}\nEmail: {mail}\nPhone:{phone}\nMessage:\n{message}"
        mailto_link = f"mailto:oliulislam382@gmail.com?subject={subject}&body={body}"

        return redirect(mailto_link)

    return render_template("contact.html", logged_in=current_user.is_authenticated)



@app.route("/new-post", methods=["POST", "GET"])
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@login_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id, logged_in=current_user.is_authenticated))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
