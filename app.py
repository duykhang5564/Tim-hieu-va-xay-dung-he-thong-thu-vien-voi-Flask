import os
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# 1. CẤU HÌNH (Giữ nguyên)
# ==============================================================================
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'khoa-bi-mat-sieu-cap-vipro-123456'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'library.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER_AVATARS'] = os.path.join(basedir, 'static', 'avatars')
app.config['UPLOAD_FOLDER_BOOKS'] = os.path.join(basedir, 'static', 'book_covers')
if not os.path.exists(app.config['UPLOAD_FOLDER_AVATARS']): os.makedirs(app.config['UPLOAD_FOLDER_AVATARS'])
if not os.path.exists(app.config['UPLOAD_FOLDER_BOOKS']): os.makedirs(app.config['UPLOAD_FOLDER_BOOKS'])

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Vui lòng đăng nhập để sử dụng tính năng này.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==============================================================================
# 2. MODELS (Giữ nguyên)
# ==============================================================================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    fullname = db.Column(db.String(100), nullable=True)
    user_code = db.Column(db.String(20), unique=True, nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    position = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    avatar = db.Column(db.String(100), nullable=False, default='default.jpg')
    borrow_logs = db.relationship('BorrowLog', backref='borrower', lazy=True)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    books = db.relationship('Book', backref='author', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    books = db.relationship('Book', backref='category', lazy=True)

class Language(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    books = db.relationship('Book', backref='language', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Integer, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'), nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default_book.jpg')
    total_quantity = db.Column(db.Integer, nullable=False, default=1)
    available_quantity = db.Column(db.Integer, nullable=False, default=1)
    borrow_logs = db.relationship('BorrowLog', backref='book', lazy=True)
    @property
    def is_available(self):
        return self.available_quantity > 0

class BorrowLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)

# ==============================================================================
# 3. FORMS (Giữ nguyên)
# ==============================================================================
class RegistrationForm(FlaskForm):
    user_code = StringField('Mã số', validators=[DataRequired(), Length(min=3, max=20)])
    fullname = StringField('Họ tên', validators=[DataRequired(), Length(min=2, max=100)])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    birth_date = DateField('Ngày sinh', format='%Y-%m-%d', validators=[DataRequired()])
    position = StringField('Chức vụ', validators=[DataRequired()])
    password = PasswordField('Mật khẩu', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Nhập lại MK', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Đăng ký')
    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first(): raise ValidationError('Tên đăng nhập đã tồn tại.')
    def validate_user_code(self, user_code):
        if User.query.filter_by(user_code=user_code.data).first(): raise ValidationError('Mã số này đã được sử dụng.')
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Đăng nhập')
class UpdateProfileForm(FlaskForm):
    fullname = StringField('Họ tên', validators=[DataRequired(), Length(min=2)])
    username = StringField('Username', validators=[DataRequired(), Length(min=4)])
    birth_date = DateField('Ngày sinh', format='%Y-%m-%d', validators=[DataRequired()])
    position = StringField('Chức vụ', validators=[DataRequired()])
    avatar = FileField('Avatar', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Chỉ nhận file ảnh!')])
    submit_profile = SubmitField('Cập nhật')
    def validate_username(self, username):
        if username.data != current_user.username:
            if User.query.filter_by(username=username.data).first(): raise ValidationError('Tên đăng nhập này đã có người sử dụng.')
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('MK cũ', validators=[DataRequired()])
    new_password = PasswordField('MK mới', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Xác nhận MK', validators=[DataRequired(), EqualTo('new_password')])
    submit_password = SubmitField('Đổi mật khẩu')

# ==============================================================================
# 4. UTILS (Giữ nguyên)
# ==============================================================================
def save_picture(form_picture, folder_path):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(folder_path, picture_fn)
    form_picture.save(picture_path)
    return picture_fn

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bạn không có quyền truy cập trang quản lý!', 'danger') # <-- Lỗi của bạn là đây
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ==============================================================================
# 5. ROUTES
# ==============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Tất cả user mới đều là user bình thường
            user = User(
                username=form.username.data,
                fullname=form.fullname.data,
                user_code=form.user_code.data,
                birth_date=form.birth_date.data,
                position=form.position.data,
                is_admin=False  # Không phải admin
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            flash('Đăng ký thành công! Mời bạn đăng nhập.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            db.session.rollback()
            print(f"Lỗi đăng ký: {e}")
            flash(f'Có lỗi xảy ra khi đăng ký. Mã lỗi: {e}', 'danger')
    
    if request.method == 'POST' and not form.validate():
        print("Lỗi Validate Form:", form.errors)
        
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user); return redirect(request.args.get('next') or url_for('index'))
        else: flash('Sai tên đăng nhập hoặc mật khẩu.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user(); return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile_form = UpdateProfileForm()
    password_form = ChangePasswordForm()
    if profile_form.submit_profile.data and profile_form.validate():
        if profile_form.avatar.data:
            current_user.avatar = save_picture(profile_form.avatar.data, app.config['UPLOAD_FOLDER_AVATARS'])
        current_user.fullname = profile_form.fullname.data
        current_user.username = profile_form.username.data
        current_user.birth_date = profile_form.birth_date.data
        current_user.position = profile_form.position.data
        db.session.commit()
        flash('Cập nhật hồ sơ thành công!', 'success')
        return redirect(url_for('profile'))
    if password_form.submit_password.data and password_form.validate():
        if not current_user.check_password(password_form.old_password.data):
            flash('Mật khẩu cũ không đúng.', 'danger')
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash('Đổi mật khẩu thành công!', 'success')
            return redirect(url_for('profile'))
    if request.method == 'GET':
        profile_form.fullname.data = current_user.fullname
        profile_form.username.data = current_user.username
        profile_form.birth_date.data = current_user.birth_date
        profile_form.position.data = current_user.position
    image_file = url_for('static', filename='avatars/' + current_user.avatar)
    my_logs = BorrowLog.query.filter_by(user_id=current_user.id).order_by(BorrowLog.borrow_date.desc()).all()
    return render_template('profile.html', profile_form=profile_form, password_form=password_form, image_file=image_file, my_logs=my_logs)

@app.route('/')
@login_required
def index():
    q_title = request.args.get('q_title'); q_author = request.args.get('q_author')
    q_category = request.args.get('q_category'); q_language = request.args.get('q_language')
    query = Book.query.join(Author).join(Category).join(Language)
    if q_title: query = query.filter(Book.title.like(f'%{q_title}%'))
    if q_author: query = query.filter(Author.name.like(f'%{q_author}%'))
    if q_category: query = query.filter(Category.id == q_category)
    if q_language: query = query.filter(Language.id == q_language)
    books = query.order_by(Book.title).all()
    categories = Category.query.all(); languages = Language.query.all()
    return render_template('index.html', books=books, categories=categories, languages=languages,
                           q_title=q_title, q_author=q_author, q_category=q_category, q_language=q_language)

@app.route('/book/<int:id>')
@login_required
def view_book(id):
    book = Book.query.get_or_404(id)
    return render_template('view_book.html', book=book)

@app.route('/borrow_book/<int:book_id>')
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.available_quantity <= 0:
        flash('Sách này đã hết, vui lòng quay lại sau.', 'danger')
        return redirect(url_for('view_book', id=book_id))
    existing_log = BorrowLog.query.filter_by(user_id=current_user.id, book_id=book.id, return_date=None).first()
    if existing_log:
        flash('Bạn đang mượn cuốn sách này rồi. Vui lòng trả trước khi mượn thêm.', 'warning')
        return redirect(url_for('view_book', id=book_id))
    try:
        new_log = BorrowLog(user_id=current_user.id, book_id=book.id)
        db.session.add(new_log)
        book.available_quantity = book.available_quantity - 1
        db.session.commit()
        flash('Bạn đã đăng ký mượn sách thành công!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi mượn sách: {e}', 'danger')
    return redirect(url_for('view_book', id=book_id))


# --- NHÓM: QUẢN TRỊ & MƯỢN/TRẢ ---

@app.route('/borrow_history')
@login_required
@admin_required
def borrow_history():
    all_logs = BorrowLog.query.order_by(BorrowLog.borrow_date.desc()).all()
    return render_template('borrow_history.html', logs=all_logs)

#! <<< ĐÂY LÀ HÀM CẦN SỬA >>>
@app.route('/return_book/<int:log_id>')
@login_required
#@admin_required #! <<< 1. BỎ DÒNG NÀY ĐI >>>
def return_book(log_id):
    log = BorrowLog.query.get_or_404(log_id)
    
    #! <<< 2. THÊM ĐOẠN KIỂM TRA QUYỀN NÀY VÀO >>>
    if not current_user.is_admin and current_user.id != log.user_id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('index'))
    
    if log and log.return_date is None:
        try:
            log.return_date = datetime.utcnow()
            book = Book.query.get(log.book_id)
            if book:
                book.available_quantity = book.available_quantity + 1
            db.session.commit()
            flash('Đã trả sách thành công.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi trả sách: {e}', 'danger')
    else:
        flash('Lịch sử mượn này đã được xử lý hoặc không hợp lệ.', 'warning')
    
    #! <<< 3. THÊM LOGIC CHUYỂN HƯỚNG NÀY >>>
    if current_user.is_admin:
        return redirect(url_for('borrow_history')) # Admin về trang quản lý
    else:
        return redirect(url_for('profile')) # User về trang cá nhân

@app.route('/add_book')
@login_required
@admin_required
def add_book_page():
    return render_template('add_book_page.html', authors=Author.query.all(), categories=Category.query.all(), languages=Language.query.all())

@app.route('/add', methods=['POST'])
@login_required
@admin_required
def add_book():
    try:
        year = request.form['year']; price = request.form['price']
        quantity = int(request.form.get('quantity', 1))
        if quantity < 0: quantity = 1
        new_book = Book(
            title=request.form['title'], author_id=request.form['author_id'],
            category_id=request.form['category_id'], language_id=request.form['language_id'],
            year=int(year) if year else None, price=int(price) if price else None,
            summary=request.form['summary'],
            total_quantity=quantity, available_quantity=quantity
        )
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file.filename != '':
                new_book.image_file = save_picture(file, app.config['UPLOAD_FOLDER_BOOKS'])
        db.session.add(new_book); db.session.commit()
        flash('Thêm sách thành công!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {e}', 'danger')
        return redirect(url_for('add_book_page'))

@app.route('/edit/<int:id>')
@login_required
@admin_required
def edit_page(id):
    return render_template('edit.html', book=Book.query.get_or_404(id), authors=Author.query.all(), categories=Category.query.all(), languages=Language.query.all())

@app.route('/update/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_book(id):
    book = Book.query.get_or_404(id)
    try:
        book.title = request.form['title']
        book.author_id = request.form['author_id']
        book.category_id = request.form['category_id']
        book.language_id = request.form['language_id']
        year = request.form['year']; price = request.form['price']
        book.year = int(year) if year else None
        book.price = int(price) if price else None
        book.summary = request.form['summary']
        new_total_quantity = int(request.form.get('quantity', book.total_quantity))
        borrowed_count = BorrowLog.query.filter_by(book_id=book.id, return_date=None).count()
        if new_total_quantity < borrowed_count:
            flash(f'Không thể giảm tổng số lượng xuống {new_total_quantity}, vì đang có {borrowed_count} cuốn được mượn.', 'danger')
        else:
            book.total_quantity = new_total_quantity
            book.available_quantity = new_total_quantity - borrowed_count
            flash('Cập nhật sách thành công!', 'success')
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file.filename != '':
                book.image_file = save_picture(file, app.config['UPLOAD_FOLDER_BOOKS'])
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {e}', 'danger')
    return redirect(url_for('edit_page', id=id))

@app.route('/delete/<int:id>')
@login_required
@admin_required
def delete_book(id):
    book = Book.query.get_or_404(id)
    if BorrowLog.query.filter_by(book_id=id, return_date=None).first():
        flash(f'Không thể xóa sách "{book.title}" vì đang có người mượn.', 'danger')
        return redirect(url_for('index'))
    try: db.session.delete(book); db.session.commit(); flash('Đã xóa sách.', 'success')
    except Exception as e: db.session.rollback(); flash(f'Lỗi: {e}', 'danger')
    return redirect(url_for('index'))

@app.route('/manage_metadata')
@login_required
@admin_required
def manage_page(): return render_template('manage.html', authors=Author.query.all(), categories=Category.query.all(), languages=Language.query.all())
@app.route('/add_author', methods=['POST'])
@login_required
@admin_required
def add_author():
    if not Author.query.filter_by(name=request.form['author_name']).first(): db.session.add(Author(name=request.form['author_name'])); db.session.commit()
    return redirect(url_for('manage_page'))
@app.route('/add_category', methods=['POST'])
@login_required
@admin_required
def add_category():
    if not Category.query.filter_by(name=request.form['category_name']).first(): db.session.add(Category(name=request.form['category_name'])); db.session.commit()
    return redirect(url_for('manage_page'))
@app.route('/add_language', methods=['POST'])
@login_required
@admin_required
def add_language():
    if not Language.query.filter_by(name=request.form['language_name']).first(): db.session.add(Language(name=request.form['language_name'])); db.session.commit()
    return redirect(url_for('manage_page'))
@app.route('/delete_author/<int:id>')
@login_required
@admin_required
def delete_author(id):
    try: db.session.delete(Author.query.get_or_404(id)); db.session.commit()
    except: db.session.rollback(); flash('Không thể xóa vì có sách liên quan.', 'danger')
    return redirect(url_for('manage_page'))
@app.route('/delete_category/<int:id>')
@login_required
@admin_required
def delete_category(id):
    try: db.session.delete(Category.query.get_or_404(id)); db.session.commit()
    except: db.session.rollback(); flash('Không thể xóa vì có sách liên quan.', 'danger')
    return redirect(url_for('manage_page'))
@app.route('/delete_language/<int:id>')
@login_required
@admin_required
def delete_language(id):
    try: db.session.delete(Language.query.get_or_404(id)); db.session.commit()
    except: db.session.rollback(); flash('Không thể xóa vì có sách liên quan.', 'danger')
    return redirect(url_for('manage_page'))
@app.route('/edit_author/<int:id>')
@login_required
@admin_required
def edit_author_page(id): return render_template('edit_author.html', author=Author.query.get_or_404(id))
@app.route('/update_author/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_author(id):
    Author.query.get_or_404(id).name = request.form['name']; db.session.commit()
    return redirect(url_for('manage_page'))
@app.route('/edit_category/<int:id>')
@login_required
@admin_required
def edit_category_page(id): return render_template('edit_category.html', category=Category.query.get_or_404(id))
@app.route('/update_category/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_category(id):
    Category.query.get_or_404(id).name = request.form['name']; db.session.commit()
    return redirect(url_for('manage_page'))
@app.route('/edit_language/<int:id>')
@login_required
@admin_required
def edit_language_page(id): return render_template('edit_language.html', language=Language.query.get_or_404(id))
@app.route('/update_language/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_language(id):
    Language.query.get_or_404(id).name = request.form['name']; db.session.commit()
    return redirect(url_for('manage_page'))

# ==============================================================================
# 6. TẠO DỮ LIỆU MẪU & CHẠY APP
# ==============================================================================
def create_sample_data():
    """Tạo dữ liệu mẫu nếu DB còn trống, gồm 3 admin và một số metadata"""
    # --- Tạo 3 tài khoản Admin ---
    admin_users = [
        {'username': 'Admin1', 'fullname': 'Admin One', 'user_code': 'A001', 'birth_date': datetime(2005, 1, 1), 'position': 'Quản trị'},
        {'username': 'Admin2', 'fullname': 'Admin Two', 'user_code': 'A002', 'birth_date': datetime(2005, 2, 2), 'position': 'Quản trị'},
        {'username': 'Admin3', 'fullname': 'Admin Three', 'user_code':'A003', 'birth_date': datetime(2005, 3, 3), 'position': 'Quản trị'}
    ]
    for admin in admin_users:
        if not User.query.filter_by(username=admin['username']).first():
            user = User(
                username=admin['username'],
                fullname=admin['fullname'],
                user_code=admin['user_code'],
                birth_date=admin['birth_date'],
                position=admin['position'],
                is_admin=True
            )
            user.set_password('Admin777')  # Mật khẩu mặc định cho tất cả admin
            db.session.add(user)
            
    authors = ["Nguyễn Nhật Ánh", "J.K. Rowling", "Stephen King"]
    categories = ["Tiểu thuyết", "Trinh thám", "Kinh dị"]
    languages = ["Tiếng Việt", "Tiếng Anh"]
    for n in authors: 
        if not Author.query.filter_by(name=n).first(): db.session.add(Author(name=n))
    for n in categories: 
        if not Category.query.filter_by(name=n).first(): db.session.add(Category(name=n))
    for n in languages: 
        if not Language.query.filter_by(name=n).first(): db.session.add(Language(name=n))
    db.session.commit()
    print(">>> Đã thêm dữ liệu mẫu.")

if __name__ == '__main__':
    if not os.path.exists(os.path.join(basedir, 'library.db')):
        with app.app_context():
            db.create_all()
            create_sample_data()
            print(">>> Đã khởi tạo cơ sở dữ liệu mới.")
    
    app.run(debug=True, host="0.0.0.0")
