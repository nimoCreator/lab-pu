CREATE TABLE [dbo].[Technika_jadrowa]
(
	[Id] INT NOT NULL PRIMARY KEY IDENTITY, 
    [haslo] NCHAR(128) NOT NULL, 
    [tresc] NVARCHAR(MAX) NOT NULL
)
