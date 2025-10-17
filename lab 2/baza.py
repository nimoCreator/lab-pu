import pyodbc
from dataclasses import dataclass
from typing import Optional, List
import json

@dataclass
class Haslo:
    id: Optional[int]
    haslo: str
    tresc: str

    @staticmethod
    def from_row(row) -> "Haslo":
        return Haslo(
            id=int(row[0]) if row[0] is not None else None,
            haslo=str(row[1]).rstrip(),
            tresc=str(row[2]).rstrip(),
        )
    
    def __str__(self) -> str:
        return f"[{self.id}] {self.haslo}: {self.tresc[:60]}..."

class Tabela_Technika_jadrowa:
    connection_string: str
    data: List[Haslo]
    connection: Optional[pyodbc.Connection] = None
    cursor: Optional[pyodbc.Cursor] = None

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.data = []

    def connect(self) -> pyodbc.Connection:
        return pyodbc.connect(self.connection_string)
    
    def __enter__(self) -> "Tabela_Technika_jadrowa":
        self.connection = pyodbc.connect(self.connection_string)
        self.cursor = self.connection.cursor()
        return self
    
    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None and self.connection is not None:
                self.connection.commit()
        finally:
            if self.cursor is not None:
                self.cursor.close()
            if self.connection is not None:
                self.connection.close()
        self.connection = None
        self.cursor = None

    def updateDownload(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT Id, Haslo, Tresc FROM dbo.Technika_jadrowa ORDER BY Id")
            self.data = [Haslo.from_row(r) for r in cur.fetchall()]

    def updateUpload(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            for d in self.data:
                cur.execute(
                    """
                    IF NOT EXISTS (
                        SELECT 1 FROM dbo.Technika_jadrowa WHERE Haslo = ? AND Tresc = ?
                    )
                    BEGIN
                        INSERT INTO dbo.Technika_jadrowa (Haslo, Tresc)
                        VALUES (?, ?);
                    END
                    """,
                    d.haslo, d.tresc, d.haslo, d.tresc
                )
            conn.commit()
        self.updateDownload()

    def pobierz_hasla(self) -> List[Haslo]:
        return list(self.data)

    def getById(self, id: int) -> Optional[Haslo]:
        return next((x for x in self.data if x.id == id), None)

    def dodaj_haslo(self, d: Haslo):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT Id FROM dbo.Technika_jadrowa WHERE Haslo = ?", d.haslo)
            row = cur.fetchone()
            if row:
                rec_id = int(row[0])
                cur.execute("UPDATE dbo.Technika_jadrowa SET Tresc = ? WHERE Id = ?", d.tresc, rec_id)
            else:
                cur.execute(
                    "INSERT INTO dbo.Technika_jadrowa (Haslo, Tresc) OUTPUT INSERTED.Id VALUES (?, ?)",
                    d.haslo, d.tresc
                )
                rec_id = int(cur.fetchone()[0])
            conn.commit()
        d.id = rec_id
        self.updateLocal(d)

    def usun_wszystko(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM dbo.Technika_jadrowa")
            conn.commit()
        self.data.clear()

    def policz_hasla(self) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM dbo.Technika_jadrowa")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def updateLocal(self, d: Haslo) -> None:
        for i, existing in enumerate(self.data):
            if existing.id == d.id and d.id is not None:
                self.data[i] = d
                break
        else:
            if not any(x.haslo == d.haslo and x.tresc == d.tresc for x in self.data):
                self.data.append(d)

# CONNECTION STRING:
# Data Source=(localdb)\MSSQLLocalDB;
# Initial Catalog=Wikipedia;
# Integrated Security=True;

if __name__ == "__main__":
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=(localdb)\\MSSQLLocalDB;"
        "Database=Wikipedia;"
        "Trusted_Connection=yes;"
    )

    with Tabela_Technika_jadrowa(connection_string) as repo:
        repo.updateDownload()
        print("=====[ STAN BAZY PRZED DODANIEM ]=====\n", repo.pobierz_hasla())

        nowy = Haslo(id=None, haslo="Litwo Ojczyzno Moja", tresc="Opis testowy 2")
        repo.dodaj_haslo(nowy)

        repo.updateUpload()
        repo.updateDownload()

        print("=====[ STAN BAZY PO DODANIU ]=====")
        for r in repo.pobierz_hasla():
            print(r)

        with open("hasla.json", "w", encoding="utf-8") as f:
            json.dump([h.__dict__ for h in repo.pobierz_hasla()], f, ensure_ascii=False, indent=2)
        print("Zapisano hasla.json")
