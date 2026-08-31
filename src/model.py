from src.config import db


class Group(db.Model):
    __tablename__ = "groups"

    group_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_name = db.Column(db.Text, nullable=False)

    tasks = db.relationship("Task", back_populates="group")
    tags = db.relationship("Tag", back_populates="group")
    statuses = db.relationship("Status", back_populates="group")


class Tag(db.Model):
    __tablename__ = "tags"

    tag_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tag_name = db.Column(db.Text, nullable=False)

    group_id = db.Column(db.Integer, db.ForeignKey(
        "groups.group_id"), nullable=True)

    group = db.relationship("Group", back_populates="tags")
    tasks = db.relationship("Task", back_populates="tag")
    statuses = db.relationship("Status", back_populates="tag")


class Status(db.Model):
    __tablename__ = "statuses"

    status_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    status_name = db.Column(db.Text, nullable=False)

    tag_id = db.Column(db.Integer, db.ForeignKey("tags.tag_id"), nullable=True)

    group = db.relationship("Group", back_populates="statuses")
    tag = db.relationship("Tag", back_populates="statuses")
    tasks = db.relationship("Task", back_populates="status")


class Task(db.Model):
    __tablename__ = "tasks"

    task_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    group_id = db.Column(db.Integer, db.ForeignKey(
        "groups.group_id"), nullable=True)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.tag_id"), nullable=True)
    status_id = db.Column(db.Integer, db.ForeignKey(
        "statuses.status_id"), nullable=True)

    task_name = db.Column(db.Text, nullable=False)
    datetime = db.Column(db.DateTime)
    repetition = db.Column(db.Text)
    remind_offset_minutes = db.Column(db.Integer)
    note = db.Column(db.Text)
    completed_at = db.Column(db.DateTime)
    is_notified = db.Column(db.Boolean, default=False, nullable=False)

    group = db.relationship("Group", back_populates="tasks")
    tag = db.relationship("Tag", back_populates="tasks")
    status = db.relationship("Status", back_populates="tasks")
