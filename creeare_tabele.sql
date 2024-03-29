CREATE TABLE Users (
    UserID NUMBER GENERATED ALWAYS AS IDENTITY,
    Username VARCHAR2(50) NOT NULL,
    Password VARCHAR2(64) NOT NULL,
    Email VARCHAR2(100) NOT NULL,
    CONSTRAINT Users_PK PRIMARY KEY(UserID),
    CONSTRAINT Users_Username_UQ UNIQUE(Username),
    CONSTRAINT Users_Email_UQ UNIQUE(Email),
    CONSTRAINT Users_Email_CHK CHECK(Email LIKE '_%@_%._%'))
);


CREATE TABLE Albums (
    AlbumID NUMBER GENERATED ALWAYS AS IDENTITY,
    UserID NUMBER NOT NULL,
    AlbumName VARCHAR2(100) NOT NULL,
    CONSTRAINT Albums_PK PRIMARY KEY(AlbumID),
    CONSTRAINT Album_Name_UQ UNIQUE(AlbumName)),
    CONSTRAINT Albums_User_FK FOREIGN KEY(UserID) REFERENCES Users(UserID)
);

CREATE TABLE Comments (
    CommentID NUMBER GENERATED ALWAYS AS IDENTITY,
    CommentText VARCHAR2(500) NOT NULL,
    InsertionDate DATE NOT NULL,
    LastModifiedDate DATE NOT NULL,
    CONSTRAINT Comments_PK PRIMARY KEY(CommentID)
);

CREATE TABLE Photos (
    PhotoID NUMBER GENERATED ALWAYS AS IDENTITY,
    AlbumID NUMBER NOT NULL,
    PhotoName VARCHAR2(100) NOT NULL,
    PhotoPath VARCHAR2(500) NOT NULL,
    CommentID NUMBER,
    CONSTRAINT Photos_PK PRIMARY KEY(PhotoID),
    CONSTRAINT Photos_Album_FK FOREIGN KEY(AlbumID) REFERENCES Albums(AlbumID),
    CONSTRAINT Photos_Comment_FK FOREIGN KEY(CommentID) REFERENCES Comments(CommentID),
    CONSTRAINT Photos_Name_UQ UNIQUE(PhotoName)
);
