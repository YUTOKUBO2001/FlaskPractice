from datetime import datetime

from flask import (
    Blueprint, abort, request, render_template,
    redirect, url_for, flash, session, jsonify
)
from flask_login import (
    login_user, login_required, logout_user, current_user
)
from flaskr.models import User, PasswordResetToken, Voice
from flaskr import db

from flaskr.forms import (
    LoginForm, RegisterForm, ResetPasswordForm,
    ForgotPasswordForm, UserForm, ChangePassword, CreateVoiceForm,
    UpdateVoiceForm
)

bp = Blueprint('app', __name__, url_prefix='')

# ホーム
@bp.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        # Voiceテーブルの全てのデータを取得
        voices = Voice.query.all()
    return render_template('home.html', voices=voices)

# ログアウト時
@bp.route('/logout')
def logout():
    logout_user() # ログアウト
    return redirect(url_for('app.home'))

# ログイン時
@bp.route('/login', methods=['GET', 'POST'])
def login():
    # インスタンス生成
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        # メールアドレスが存在するか確認
        user = User.select_user_by_email(form.email.data)
        # ユーザが存在し、アクティブであり、パスワードが正しい場合
        if user and user.is_active and user.validate_password(form.password.data):
            login_user(user, remember=True)
            # ログイン後の移動先
            next = request.args.get('next')
            if not next:
                next = url_for('app.home')
            return redirect(next)
        elif not user:
            flash('存在しないユーザーです')
        elif not user.is_active:
            flash('無効なユーザです。パスワードを再設定してください')
        elif not user.validate_password(form.password.data):
            flash('メールアドレスとパスワードの組み合わせが間違っています')
    return render_template('login.html', form=form)

# 新規登録時
@bp.route('/register', methods=['GET', 'POST'])
def register():
    # インスタンス生成
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        # Userクラスのインスタンス生成
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        # dbに追加
        user.create_new_user()
        db.session.commit()
        token = ''
        token = PasswordResetToken.publish_token(user)
        db.session.commit()
        # メールに飛ばすほうがいい
        print(
            f'パスワード設定用URL: http://127.0.0.1:5000/reset_password/{token}'
        )
        flash('パスワード設定用のURLをお送りしました。ご確認ください')
        return redirect(url_for('app.login'))
    return render_template('register.html', form=form)

# パスワード設定時
@bp.route('/reset_password/<uuid:token>', methods=['GET', 'POST'])
def reset_password(token):
    form = ResetPasswordForm(request.form)
    reset_user_id = PasswordResetToken.get_user_id_by_token(token)
    if not reset_user_id:
        abort(500)
    if request.method == 'POST' and form.validate():
        password = form.password.data
        user = User.select_user_by_id(reset_user_id)
        user.save_new_password(password)
        PasswordResetToken.delete_token(token)
        db.session.commit()
        flash('パスワードを更新しました')
        return redirect(url_for('app.login'))
    return render_template('reset_password.html', form=form)

# パスワード忘れた時
@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        user = User.select_user_by_email(email)
        if user:
            token = PasswordResetToken.publish_token(user)
            db.session.commit()
            reset_url = f'http://127.0.0.1:5000/reset_password/{token}'
            print(reset_url)
            flash('パスワード再登録用のURLを発行しました')
        else:
            flash('存在しないユーザです')
    return render_template('forgot_password.html', form=form)


# マイページ時
@bp.route('/mypage/<int:id>')
@login_required
def mypage(id):
    voices = Voice.select_by_from_user_id_all(id)
    return render_template('mypage.html', voices=voices)


# ユーザ詳細閲覧時
@bp.route('/show_profile/<int:id>')
@login_required
def show_profile(id):
    user = User.select_user_by_id(id)
    voices = Voice.select_by_from_user_id_all(id)
    return render_template('show_profile.html', user=user, voices=voices)


# ユーザリスト閲覧時
@bp.route('/list_user', methods=['GET', 'POST'])
def list_user():
    if request.method == 'POST':
        search_word = request.form['search']
        if search_word is None:
            users = User.query.all()
            print(search_word)
        else:
            # 検索した文字が含まれているユーザを取得
            users = User.query.filter(User.username.contains(search_word)).all()
    else:
        users = User.query.all()
    return render_template('list_user.html', users=users)


# ユーザ登録情報変更時
@bp.route('/mypage/change_user_info/<int:id>', methods=['GET', 'POST'])
@login_required
def change_user_info(id):
    form = UserForm(request.form)
    if request.method == 'POST' and form.validate():
        # ユーザ情報をidから取得する
        user = User.select_user_by_id(id)
        user.username = form.username.data
        user.email = form.email.data
        file = request.files[form.picture_path.name].read()
        if len(file) != 0:
            file_name = str(id) + '_' + str(int(datetime.now().timestamp())) + 'jpg'
            picture_path = 'flaskr/static/user_image/' + file_name
            open(picture_path, 'wb').write(file)
            user.picture_path = 'user_image/' + file_name
        db.session.commit()
        flash('ユーザ情報の更新に成功しました')
    return render_template('user.html', form=form)


# パスワード再設定時
@bp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    form = ChangePassword(request.form)
    if request.method == 'POST' and form.validate():
        user_id = current_user.get_id()
        user = User.select_user_by_id(user_id)
        password = form.password.data
        user.save_new_password(password)
        db.session.commit()
        flash('パスワードの更新に成功しました')
        redirect(url_for('app.user'))
    return render_template('change_password.html', form=form)


# ボイス作成時
@bp.route('/voice', methods=['GET', 'POST'])
@login_required
def voice():
    form = CreateVoiceForm(request.form)
    if request.method == 'POST' and form.validate():
        file = request.files[form.picture_path.name].read()
        # picture_pathに何も入っていない場合
        if len(file) == 0:
            new_voice = Voice(current_user.get_id(), form.title.data, None, form.voice.data)
        else:
            file = request.files[form.picture_path.name].read()
            file_name = str(current_user.get_id()) + '_' + str(int(datetime.now().timestamp())) + '.jpg'
            picture_path = 'flaskr/static/voice_image/' + file_name
            open(picture_path, 'wb').write(file)
            voice_picture_path = 'voice_image/' + file_name
            new_voice = Voice(current_user.get_id(), form.title.data, voice_picture_path, form.voice.data)
        new_voice.create_voice()
        db.session.commit()
        flash('新規ボイス投稿に成功しました')
        return redirect(url_for('app.home'))
    return render_template(
        'voice.html', form=form
    )


@bp.route('/update_voice/<int:id>', methods=['GET', 'POST'])
@login_required
def update_voice(id):
    form = UpdateVoiceForm(request.form)
    voice = Voice.select_voice_by_id(id)
    if request.method == 'POST' and form.validate():
        voice.title = form.title.data
        voice.voice = form.voice.data
        file = request.files[form.picture_path.name].read()
        if len(file) != 0:
            file_name = str(current_user.get_id()) + '_' + str(int(datetime.now().timestamp())) + '.jpg'
            picture_path = 'flaskr/static/voice_image/' + file_name
            open(picture_path, 'wb').write(file)
            voice.picture_path = 'voice_image/' + file_name
        db.session.commit()
        flash('ボイスの投稿に成功しました')
        return redirect(url_for('app.home'))
    return render_template('update_voice.html', form=form, voice=voice)


@bp.route('/delete_voice/<int:id>')
@login_required
def delete_voice(id):
    voice = Voice.select_voice_by_id(id)
    voice.delete_voice()
    db.session.commit()
    return redirect(url_for('app.home'))

