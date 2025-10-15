import pyodbc
from dataclasses import dataclass
from typing import Iterable, Optional, List


@dataclass
class dbo:
    id: Optional[int]
    page: str
    content: str

    @staticmethod
    def from_row(row) -> "dbo":
        return dbo(
            id=int(row[0]) if row[0] is not None else None,
            page=str(row[1]).rstrip(),
            content=str(row[2]).rstrip(),
        )


class Repo:
    connection_string: str
    data: List[dbo]

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.data = []

    def connect(self) -> pyodbc.Connection:
        return pyodbc.connect(self.connection_string)

    def updateDownload(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM dbo.Technika_jadrowa ORDER BY Id")
            self.data = [dbo.from_row(r) for r in cur.fetchall()]

    def updateUpload(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            for d in self.data:
                cur.execute(
                    f"""
                    IF NOT EXISTS (
                        SELECT 1 FROM dbo.Technika_jadrowa WHERE Page = {d.page} AND Content = {d.content}
                    )
                    BEGIN
                        INSERT INTO dbo.Technika_jadrowa (Page, Content)
                        VALUES ({d.page}, {d.content});
                    END
                    """
                )
            conn.commit()
        self.updateDownload()

    def getAll(self) -> List[dbo]:
        return list(self.data)

    def getById(self, id: int) -> Optional[dbo]:
        return next((x for x in self.data if x.id == id), None)

    def add(self, d: dbo) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                IF NOT EXISTS (
                    SELECT 1 FROM dbo.Technika_jadrowa WHERE Page = {d.page} AND Copntent = {d.content}
                )
                BEGIN
                    INSERT INTO dbo.Technika_jadrowa (Page, Tresc)
                    VALUES ({d.page}, {d.content});
                    SELECT CAST(SCOPE_IDENTITY() AS INT);
                END
                ELSE
                BEGIN
                    SELECT Id FROM dbo.Technika_jadrowa WHERE Page = {d.page} AND Copntent = {d.content};
                END
                """
            )
            new_id = cur.fetchval() 
            conn.commit()

        d.id = int(new_id) if new_id is not None else None

        self._upsert_cache(d)
        return d.id if d.id is not None else -1

    def _upsert_cache(self, d: dbo) -> None:
        for i, existing in enumerate(self.data):
            if existing.id == d.id:
                self.data[i] = d
                break
        else:
            if not any(x.page == d.page and x.content == d.content for x in self.data):
                self.data.append(d)


if __name__ == "__main__":
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        r"Server=(localdb)\MSSQLLocalDB;"
        "Database=Wikipedia;"
        "Trusted_Connection=yes;"
    )

    repo = Repo(connection_string)

    repo.updateDownload()
    print("Stan bazy:", repo.getAll())

    nowy = dbo(id=None, page="Elektrownia Jaworzno II", content="Opis testowy")
    new_id = repo.add(nowy)
    print("ID nowego rekordu:", new_id)

    repo.updateUpload()

    repo.updateDownload()

    for r in repo.getAll():
        print(r)
