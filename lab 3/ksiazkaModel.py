from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text

Base = declarative_base()

class Ksiazka(Base):
    __tablename__ = "ksiazki"
    id = Column(Integer, primary_key=True, autoincrement=True)
    angielski_tytul = Column(String(500), nullable=False)
    angielskie_streszczenie = Column(Text, nullable=False)
    polski_tytul = Column(String(500), nullable=True)
    polskie_streszczenie = Column(Text, nullable=True)
