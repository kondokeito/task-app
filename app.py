import os
import requests
from dotenv import load_dotenv
from src.model import Task, Group, Tag, Status
from src.config import db
from src import config
from sqlalchemy.orm import joinedload
from flask import Flask, request, render_template, redirect, url_for
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from croniter import croniter
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, template_folder='src/templates')

config.init_sql_alchemy(app)

with app.app_context():
    # db.drop_all()
    db.create_all()

load_dotenv()
WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')


def remind_job():
    with app.app_context():
        db.session.remove()
        if not WEBHOOK_URL:
            print("WEBHOOK_URLが適切に設定されていないため送信できません。「.env」ファイルをご参照ください。")
            return

        jst = ZoneInfo("Asia/Tokyo")
        now = datetime.now(jst).replace(tzinfo=None)

        filter_tasks = Task.query.filter(
            Task.is_notified == False,
            Task.completed_at == None,
            Task.datetime != None,
            Task.remind_offset_minutes != None
        ).all()

        if not filter_tasks:
            print(f"{now}通知するタスクがありませんでした。(not exist filter_tasks)")
            return

        target_tasks = []
        for task in filter_tasks:
            offset = int(
                task.remind_offset_minutes) if task.remind_offset_minutes is not None else 0
            remind_at = task.datetime - timedelta(minutes=offset)
            if remind_at <= now:
                target_tasks.append(task)
            print(
                f"DEBUG: task={task.task_name}, remind_at={remind_at}, now={now}")

        if not target_tasks:
            print(f"{now}通知するタスクがありませんでした。(not exist target_tasks)")
            return

        message = ""
        for task in target_tasks:
            if task.note:
                message += f"{task.task_name}が{task.remind_offset_minutes}分後にあります！\n備考: {task.note}\n"
            else:
                message += f"{task.task_name}が{task.remind_offset_minutes}分後にあります！\n"

        payload = {"content": message}
        try:
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code == 204:
                print(f"{now}Discordへ送信成功しました。")
                for task in target_tasks:
                    task.is_notified = True
                db.session.commit()
            else:
                print(f"{now}送信失敗:ステータスコード{response.status_code}")
        except Exception as e:
            print(f"{now}送信中にエラーが発生しました:{e}")


if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler = BackgroundScheduler()
    scheduler.add_job(remind_job, 'cron', second=0)
    scheduler.start()


@app.route('/')
def main():
    tasks = Task.query.options(
        joinedload(Task.group),
        joinedload(Task.tag),
        joinedload(Task.status)
    ).all()

    return render_template('main.html', tasks=tasks)


@app.route('/edit/task/<int:id>')
def edit_task(id):
    task = Task.query.get(id)
    if not task:
        return redirect(url_for('main'))

    groups = Group.query.all()
    tags = Tag.query.all()
    statuses = Status.query.all()
    return render_template('edit_task.html', task=task, groups=groups, tags=tags, statuses=statuses)


@app.route('/new/task')
def new_task():
    groups = Group.query.all()
    tags = Tag.query.all()
    statuses = Status.query.all()
    return render_template('new_task.html', groups=groups, tags=tags, statuses=statuses)


@app.route('/create/task', methods=['post'])
def create_task():
    new_task = Task()
    new_task.task_name = request.form.get('task_name', '')

    group_id_str = request.form.get('group_id', '')
    new_task.group_id = int(group_id_str) if group_id_str.isdigit() else None

    tag_id_str = request.form.get('tag_id', '')
    new_task.tag_id = int(tag_id_str) if tag_id_str.isdigit() else None

    status_id_str = request.form.get('status_id', '')
    new_task.status_id = int(
        status_id_str) if status_id_str.isdigit() else None

    datetime_str = request.form.get('datetime', '')
    new_task.datetime = datetime.fromisoformat(
        datetime_str) if datetime_str else None

    new_task.repetition = request.form.get('repetition', '') or None

    offset_str = request.form.get('remind_offset_minutes', '')
    new_task.remind_offset_minutes = int(
        offset_str) if offset_str.isdigit() else None

    note_str = request.form.get('note', '')
    new_task.note = note_str if note_str else None

    db.session.add(new_task)
    db.session.commit()

    return redirect(url_for('main'))


@app.route('/delete/task/<int:id>')
def delete_task(id):
    delete_task = Task.query.get(id)
    if not delete_task:
        return redirect(url_for('main'))

    db.session.delete(delete_task)
    db.session.commit()

    return redirect(url_for('main'))


@app.route('/complete/task/<int:id>')
def complete_task(id):
    complete_task = Task.query.get(id)
    if not complete_task:
        return redirect(url_for('main'))

    if complete_task.datetime and complete_task.repetition and croniter.is_valid(complete_task.repetition):
        new_task = Task()
        new_task.task_name = complete_task.task_name
        new_task.group_id = complete_task.group_id
        new_task.tag_id = complete_task.tag_id
        new_task.status_id = complete_task.status_id
        new_task.datetime = croniter(
            complete_task.repetition, complete_task.datetime).get_next(datetime)
        new_task.repetition = complete_task.repetition
        new_task.remind_offset_minutes = complete_task.remind_offset_minutes
        new_task.note = complete_task.note
        db.session.add(new_task)

    complete_task.completed_at = datetime.now()
    db.session.commit()

    return redirect(url_for('main'))


@app.route('/update/task/<int:id>', methods=['post'])
def update_task(id):
    update_task = Task.query.get(id)
    if not update_task:
        return redirect(url_for('main'))

    update_task.task_name = request.form.get('task_name', '')

    group_id_str = request.form.get('group_id', '')
    update_task.group_id = int(
        group_id_str) if group_id_str.isdigit() else None

    tag_id_str = request.form.get('tag_id', '')
    update_task.tag_id = int(tag_id_str) if tag_id_str.isdigit() else None

    status_id_str = request.form.get('status_id', '')
    update_task.status_id = int(
        status_id_str) if status_id_str.isdigit() else None

    datetime_str = request.form.get('datetime', '')
    update_task.datetime = datetime.fromisoformat(
        datetime_str) if datetime_str else None

    update_task.repetition = request.form.get('repetition', '') or None

    offset_str = request.form.get('remind_offset_minutes', '')
    update_task.remind_offset_minutes = int(
        offset_str) if offset_str.isdigit() else None

    note_str = request.form.get('note', '')
    update_task.note = note_str if note_str else None

    db.session.commit()

    return redirect(url_for('main'))


@app.route('/option')
def option():
    groups = Group.query.all()

    tags = Tag.query.options(
        joinedload(Tag.group),
    ).all()

    statuses = Status.query.options(
        joinedload(Status.tag)
    ).all()

    return render_template('option.html', groups=groups, tags=tags, statuses=statuses)


@app.route('/create/group', methods=['post'])
def create_group():
    new_group = Group()
    new_group.group_name = request.form.get('group_name', '')

    db.session.add(new_group)
    db.session.commit()

    return redirect(url_for('option'))


@app.route('/edit/group/<int:id>')
def edit_group(id):
    group = Group.query.get(id)
    if not group:
        return redirect(url_for('option'))
    return render_template('edit_group.html', group=group)


@app.route('/update/group/<int:id>', methods=['post'])
def update_group(id):
    update_group = Group.query.get(id)
    if not update_group:
        return redirect(url_for('option'))

    update_group.group_name = request.form.get('group_name', '')
    db.session.commit()

    return redirect(url_for('option'))


@app.route('/delete/group/<int:id>')
def delete_group(id):
    delete_group = Group.query.get(id)
    if not delete_group:
        return redirect(url_for('option'))

    Task.query.filter_by(group_id=id).update({"group_id": None})
    Tag.query.filter_by(group_id=id).update({"group_id": None})

    db.session.delete(delete_group)
    db.session.commit()

    return redirect(url_for('option'))


@app.route('/create/tag', methods=['post'])
def create_tag():
    new_tag = Tag()
    new_tag.tag_name = request.form.get('tag_name', '')

    group_id_str = request.form.get('group_id', '')
    new_tag.group_id = int(group_id_str) if group_id_str.isdigit() else None

    db.session.add(new_tag)
    db.session.commit()

    return redirect(url_for('option'))


@app.route('/edit/tag/<int:id>')
def edit_tag(id):
    tag = Tag.query.get(id)
    if not tag:
        return redirect(url_for('option'))

    groups = Group.query.all()
    return render_template('edit_tag.html', tag=tag, groups=groups)


@app.route('/update/tag/<int:id>', methods=['post'])
def update_tag(id):
    update_tag = Tag.query.get(id)
    if not update_tag:
        return redirect(url_for('option'))

    update_tag.tag_name = request.form.get('tag_name', '')

    group_id_str = request.form.get('group_id', '')
    update_tag.group_id = int(group_id_str) if group_id_str.isdigit() else None

    db.session.commit()

    return redirect(url_for('option'))


@app.route('/delete/tag/<int:id>')
def delete_tag(id):
    delete_tag = Tag.query.get(id)
    if not delete_tag:
        return redirect(url_for('option'))

    Task.query.filter_by(tag_id=id).update({"tag_id": None})
    Status.query.filter_by(tag_id=id).update({"tag_id": None})

    db.session.delete(delete_tag)
    db.session.commit()

    return redirect(url_for('option'))


@app.route('/create/status', methods=['post'])
def create_status():
    new_status = Status()
    new_status.status_name = request.form.get('status_name', '')

    tag_id_str = request.form.get('tag_id', '')
    new_status.tag_id = int(tag_id_str) if tag_id_str.isdigit() else None

    db.session.add(new_status)
    db.session.commit()

    return redirect(url_for('option'))


@app.route('/edit/status/<int:id>')
def edit_status(id):
    status = Status.query.get(id)
    if not status:
        return redirect(url_for('option'))

    tags = Tag.query.all()
    return render_template('edit_status.html', status=status, tags=tags)


@app.route('/update/status/<int:id>', methods=['post'])
def update_status(id):
    update_status = Status.query.get(id)
    if not update_status:
        return redirect(url_for('option'))

    update_status.status_name = request.form.get('status_name', '')

    tag_id_str = request.form.get('tag_id', '')
    update_status.tag_id = int(tag_id_str) if tag_id_str.isdigit() else None

    db.session.commit()

    return redirect(url_for('option'))


@app.route('/delete/status/<int:id>')
def delete_status(id):
    delete_status = Status.query.get(id)
    if not delete_status:
        return redirect(url_for('option'))

    Task.query.filter_by(status_id=id).update({"status_id": None})

    db.session.delete(delete_status)
    db.session.commit()

    return redirect(url_for('option'))


app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
