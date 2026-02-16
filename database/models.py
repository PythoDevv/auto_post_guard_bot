from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Time, Text
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String)
    username = Column(String)
    is_admin = Column(Integer, default=0) # 0: User, 1: Admin, etc.

    groups = relationship("Group", back_populates="owner")

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String)
    is_channel = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey('users.id'))
    next_post_index = Column(Integer, default=0)

    owner = relationship("User", back_populates="groups")
    posts = relationship("Post", back_populates="group")
    schedule_times = relationship("ScheduleTimes", back_populates="group")
    keywords = relationship("Keyword", back_populates="group")

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    name = Column(String, nullable=True)  # Custom post name (e.g. "Tandirchi")
    content_type = Column(String) # text, photo, video, etc.
    file_id = Column(String, nullable=True)
    caption = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    entities = Column(Text, nullable=True) # JSON stored as text

    group = relationship("Group", back_populates="posts")

class ScheduleTimes(Base):
    __tablename__ = 'schedule_times'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=True) # Link to specific post
    time = Column(String) # Format: "HH:MM"
    is_recurring = Column(Integer, default=1) # 1: Daily, 0: One-time

    group = relationship("Group", back_populates="schedule_times")

class Keyword(Base):
    __tablename__ = 'keywords'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    word = Column(String)

    group = relationship("Group", back_populates="keywords")
