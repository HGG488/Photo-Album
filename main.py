import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from tkinter import filedialog
import cx_Oracle
from PIL import Image, ImageTk
import hashlib
import os

'''

!!! A se schimba atat datele de logare pentru server-ul Oracle
    cat si locatia pe disc pentru Oracle Client ( daca acesta nu se afla 
    deja in variabila de sistem PATH/ORACLE_PATH )
'''
cx_Oracle.init_oracle_client(
    lib_dir=r"C:\Users\georg\OneDrive\Desktop\Projects\PhotoAlbum\cx_Oracle_libs\instantclient_21_12")
# Connect to Oracle database
con = cx_Oracle.connect("XX1233", "XX1234", "XX-XX.XX.XX.ro:1234/orcl")


class State:
    def __init__(self, window):
        self.window = window

    def switch(self, state):
        self.window.state = state
        self.window.state.display()


class LoginState(State):
    def display(self):
        self.window.clear()
        self.window.title("Login")
        self.window.geometry("300x250")
        tk.Label(self.window, text="Please enter details below to login").pack()
        tk.Label(self.window, text="").pack()

        self.username_verify = tk.StringVar()
        self.password_verify = tk.StringVar()

        tk.Label(self.window, text="Username * ").pack()
        self.username_login_entry = tk.Entry(self.window, textvariable=self.username_verify)
        self.username_login_entry.pack()
        tk.Label(self.window, text="").pack()
        tk.Label(self.window, text="Password * ").pack()
        self.password__login_entry = tk.Entry(self.window, textvariable=self.password_verify, show='*')
        self.password__login_entry.pack()
        tk.Label(self.window, text="").pack()
        tk.Button(self.window, text="Login", width=10, height=1, command=self.login).pack()
        tk.Button(self.window, text="Create Account", width=10, height=1, command=self.create_account).pack()

    def login(self):
        username = self.username_verify.get()
        password = self.password_verify.get()
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        cursor = con.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM Users
            WHERE Username = :username AND Password = :password
        """, {'username': username, 'password': hashed_password})
        count, = cursor.fetchone()
        cursor.close()
        if count > 0:
            self.switch(HomeState(self.window, username))
        else:
            messagebox.showerror("Error", "Invalid username or password")

    def create_account(self):
        self.switch(CreateAccountState(self.window))


class CreateAccountState(State):
    def display(self):
        self.window.clear()
        self.window.title("Create Account")
        self.window.geometry("300x250")

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.email = tk.StringVar()

        tk.Label(self.window, text="Please enter details below", bg="white").pack()
        tk.Label(self.window, text="").pack()
        username_lable = tk.Label(self.window, text="Username * ")
        username_lable.pack()
        self.username_entry = tk.Entry(self.window, textvariable=self.username)
        self.username_entry.pack()
        password_lable = tk.Label(self.window, text="Password * ")
        password_lable.pack()
        self.password_entry = tk.Entry(self.window, textvariable=self.password, show='*')
        self.password_entry.pack()
        email_lable = tk.Label(self.window, text="Email * ")
        email_lable.pack()
        self.email_entry = tk.Entry(self.window, textvariable=self.email)
        self.email_entry.pack()
        tk.Label(self.window, text="").pack()
        tk.Button(self.window, text="Create Account", width=10, height=1, bg="white",
                  command=self.create_account).pack()
        tk.Button(self.window, text="Back", width=10, height=1, command=self.back).pack()

    def create_account(self):
        username = self.username.get()
        password = self.password.get()
        email = self.email.get()
        cursor = con.cursor()
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        cursor.execute("""
            SELECT COUNT(*)
            FROM Users
            WHERE Username = :username
        """, {'username': username})
        count, = cursor.fetchone()
        if count > 0:
            messagebox.showerror("Error", "Username already exists")
            cursor.close()
        else:
            try:
                cursor.execute("""
                    INSERT INTO Users (Username, Password, Email)
                    VALUES (:username, :password, :email)
                """, {'username': username, 'password': hashed_password, 'email': email})
                cursor.execute('commit')
                messagebox.showinfo("Success", "Account created successfully")
                cursor.close()
            except cx_Oracle.DatabaseError as e:
                error, = e.args
                if error.code == 1400:  # This is the error code for a null constraint violation
                    messagebox.showerror("Error", "Fields can't be empty")
                else:
                    messagebox.showerror('Error', 'Invalid email')

            self.switch(LoginState(self.window))

    def back(self):
        self.switch(LoginState(self.window))


class HomeState(State):
    def __init__(self, window, username):
        super().__init__(window)
        self.photo_grid = None
        self.album_list = None
        self.username = username

    def display(self):
        self.window.clear()
        self.window.title("Home")
        self.window.geometry("570x400")

        # Top bar
        top_bar = tk.Frame(self.window)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        tk.Label(top_bar, text=f"{self.username}").pack(side=tk.LEFT)
        tk.Button(top_bar, text="Add Album", command=self.add_album).pack(side=tk.LEFT)
        tk.Button(top_bar, text="Logout", command=self.logout).pack(side=tk.RIGHT)
        tk.Button(top_bar, text="Delete Album", command=self.delete_album).pack(side=tk.RIGHT)
        # Left side with album list
        left_side = tk.Frame(self.window)
        left_side.pack(side=tk.LEFT, fill=tk.Y)
        scrollbar = tk.Scrollbar(left_side)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.album_list = tk.Listbox(left_side, yscrollcommand=scrollbar.set)
        self.album_list.pack(side=tk.LEFT, fill=tk.BOTH)
        scrollbar.config(command=self.album_list.yview)
        self.album_list.bind('<ButtonRelease-1>', self.on_album_select)
        # Load albums from database
        self.load_albums()

        tk.Button(top_bar, text="Add Photo", command=self.add_photo).pack(side=tk.LEFT)

        right_side = tk.Frame(self.window)
        right_side.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # # Photo grid frame inside a canvas

        # self.photo_grid = tk.Canvas(right_side)
        # self.photo_grid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create a canvas for the photo grid and a scrollbar
        self.photo_grid_frame = tk.Frame(right_side)
        self.photo_grid_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.photo_grid_frame, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar_photo_grid = tk.Scrollbar(self.photo_grid_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar_photo_grid.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar_photo_grid.set)

        # Create a frame inside the canvas to hold the images
        self.frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=self.frame, anchor=tk.NW)
        # Load photos from database
        self.load_photos()

    def delete_album(self):
        selected_album = self.album_list.get(tk.ACTIVE)

        # Confirm deletion with a messagebox
        confirmation = messagebox.askyesno("Delete Album",
                                           f"Are you sure you want to delete the album '{selected_album}'?")
        if not confirmation:
            return

        # Delete album, associated photos, and comments
        cursor = con.cursor()
        try:
            con.begin()  # Begin the transaction

            cursor.execute("""
                        SELECT P.CommentID
                        FROM Photos P
                        JOIN Albums A ON P.AlbumID = A.AlbumID
                        WHERE A.AlbumName = :album_name AND A.UserID = (
                            SELECT UserID
                            FROM Users
                            WHERE Username = :username
                        )
                    """, {'username': self.username, 'album_name': selected_album})
            comment_ids = cursor.fetchall()

            # Delete photos associated with the selected album
            cursor.execute("""
                        DELETE FROM Photos
                        WHERE AlbumID = (
                            SELECT AlbumID
                            FROM Albums
                            WHERE AlbumName = :album_name AND UserID = (
                                SELECT UserID
                                FROM Users
                                WHERE Username = :username
                            )
                        )
                    """, {'username': self.username, 'album_name': selected_album})

            # Delete comments associated with the retrieved CommentIDs
            for comment_id in comment_ids:
                cursor.execute("""
                            DELETE FROM Comments
                            WHERE CommentID = :comment_id
                        """, {'comment_id': comment_id[0]})

            # Delete the album
            cursor.execute("""
                        DELETE FROM Albums
                        WHERE AlbumName = :album_name AND UserID = (
                            SELECT UserID
                            FROM Users
                            WHERE Username = :username
                        )
                    """, {'username': self.username, 'album_name': selected_album})

            cursor.execute('commit')  # Commit the transaction
            messagebox.showinfo("Success", f"Album '{selected_album}' deleted successfully")
            self.display()
        except Exception as e:
            con.rollback()  # Rollback changes if an error occurs
            messagebox.showerror("Error", f"Error deleting album: {str(e)}")
        finally:
            cursor.close()

    def on_album_select(self, event):
        self.load_photos()

    def load_photos(self):
        if self.album_list.size() > 0:
            # for widget in self.photo_grid.winfo_children():
            #     widget.destroy()
            self.frame.destroy()
            self.frame = tk.Frame(self.canvas, bg="white")
            self.canvas.create_window((0, 0), window=self.frame, anchor=tk.NW)
            selected_album = self.album_list.get(tk.ACTIVE)
            cursor = con.cursor()
            cursor.execute("""
                        SELECT PhotoPath
                        FROM Photos
                        WHERE AlbumID = (
                            SELECT AlbumID
                            FROM Albums
                            WHERE AlbumName = :album_name AND UserID = (SELECT UserID FROM Users WHERE Username = :username)
                        )
                    """, {'username': self.username, 'album_name': selected_album})
            photos = cursor.fetchall()
            cursor.execute('commit')
            cursor.close()

            for i, photo in enumerate(photos):
                image = Image.open(photo[0])
                image = image.resize((100, 100), Image.LANCZOS)  # resize image to 100x100 pixels
                photo_image = ImageTk.PhotoImage(image)
                photo_label = tk.Label(self.frame, image=photo_image)
                photo_label.image = photo_image  # keep a reference to avoid garbage collection
                photo_label.bind("<Button-1>",
                                 lambda e, path=photo[0], i1=i, photos1=photos: self.view_photo(path, i1, photos1))

                photo_label.grid(row=i // 4, column=i % 4)  # place the photo in a grid
            self.canvas.update_idletasks()
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        # self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def view_photo(self, photo_path, i, photos):

        self.switch(PhotoState(self.window, self.username, photo_path, i, photos))

    def add_photo(self):
        if self.album_list.size() > 0:
            selected_album = self.album_list.get(tk.ACTIVE)
            self.switch(AddPhotoState(self.window, self.username, selected_album))
        else:
            messagebox.showerror("Error", "No album selected")

    def logout(self):
        self.switch(LoginState(self.window))

    def add_album(self):
        self.switch(AddAlbumState(self.window, self.username))

    def load_albums(self):
        cursor = con.cursor()
        cursor.execute("""
            SELECT AlbumName
            FROM Albums
            WHERE UserID = (
                SELECT UserID
                FROM Users
                WHERE Username = :username
            )
        """, {'username': self.username})
        albums = cursor.fetchall()
        for album in albums:
            self.album_list.insert(tk.END, album[0])
        cursor.close()


class PhotoState(State):
    def __init__(self, window, username, photo_path, index, photos):
        super().__init__(window)
        self.username = username
        self.photo_path = photo_path

        self.comment_text = None
        self.last_date = None
        self.insertion_date = None
        self.index = index
        self.photos = photos
        self.comment_id = None

    def display(self):
        self.window.clear()
        self.window.title("Photo")
        cursor = con.cursor()
        cursor.execute("""
                   SELECT CommentID
                   FROM Photos
                   WHERE PhotoPath = :photo_path
               """, {'photo_path': self.photo_path})
        result = cursor.fetchone()
        cursor.close()
        cursor = con.cursor()
        cursor.execute("""
                            SELECT CommentText
                            FROM Comments
                            WHERE CommentID = (
                                SELECT CommentID
                                FROM Photos
                                WHERE PhotoPath = :photo_path
                                FETCH FIRST 1 ROW ONLY
                            )
                        """, {'photo_path': self.photo_path})
        self.comment_text, = cursor.fetchone()
        cursor.execute('commit')
        cursor.close()

        if result:
            self.comment_id, = result

        cursor = con.cursor()

        cursor.execute("""
                    SELECT InsertionDate
                    FROM Comments
                    WHERE CommentID = :comment_id
                """, {'comment_id': self.comment_id})
        self.insertion_date, = cursor.fetchone()
        cursor.execute('commit')

        cursor.execute("""
                           SELECT LastModifiedDate
                           FROM Comments
                           WHERE CommentID = :comment_id
                       """, {'comment_id': self.comment_id})
        self.last_date, = cursor.fetchone()
        cursor.execute('commit')

        cursor.close()

        image = Image.open(self.photo_path)
        img_width, img_height = image.size

        # Set the window size dynamically based on the image size
        window_width = max(img_width, 500)  # Minimum width of 500
        window_height = img_height + 150  # Add some padding for buttons and labels

        self.window.geometry(f"{window_width}x{window_height}")

        # Top bar
        top_bar = tk.Frame(self.window)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(top_bar, text="Back", command=self.back).pack(side=tk.LEFT)
        tk.Button(top_bar, text="Delete Photo", command=self.delete_photo).pack(side=tk.LEFT)
        tk.Button(top_bar, text="Change Description", command=self.edit_message).pack(side=tk.LEFT)

        tk.Button(top_bar, text="Next", command=self.previous).pack(side=tk.RIGHT)
        tk.Button(top_bar, text="Previous", command=self.next).pack(side=tk.RIGHT)

        # Edit Message button

        # Photo and description
        image = Image.open(self.photo_path)
        photo_image = ImageTk.PhotoImage(image)
        photo_label = tk.Label(self.window, image=photo_image)
        photo_label.image = photo_image  # keep a reference to avoid garbage collection
        photo_label.pack()
        date_frame = tk.Frame(self.window)
        date_frame.pack()
        tk.Label(date_frame, text=f"Insertion Date: {self.insertion_date}").pack()
        tk.Label(date_frame, text=f"Last Modified Date: {self.last_date}").pack()
        # tk.Label(self.window, text=self.comment_text).pack()
        self.comment_text_var = tk.StringVar()
        self.comment_text_var.set(self.comment_text)
        comment_label = tk.Label(self.window, textvariable=self.comment_text_var, wraplength=window_width - 20)
        comment_label.pack(pady=10)

    def back(self):
        self.switch(HomeState(self.window, self.username))

    def next(self):
        if self.index > 0:
            self.switch(
                PhotoState(self.window, self.username, (self.photos[self.index - 1])[0], self.index - 1, self.photos))

    def previous(self):
        if self.index < len(self.photos) - 1:
            self.switch(
                PhotoState(self.window, self.username, (self.photos[self.index + 1][0]), self.index + 1, self.photos))

    def delete_photo(self):

        # Delete the photo and its associated comment
        try:
            cursor = con.cursor()
            con.begin()
            cursor.execute("DELETE FROM Photos WHERE PhotoPath = :photo_path AND CommentID = :comment_id",
                           {'photo_path': self.photo_path, 'comment_id': self.comment_id})
            cursor.execute("DELETE FROM Comments WHERE CommentID = :comment_id", {'comment_id': self.comment_id})
            con.commit()
        # Commit the transaction
        except Exception as e:
            con.rollback()  # Rollback changes if an error occurs
            messagebox.showerror("Error", f"Error deleting photo: {str(e)}")
        finally:
            cursor.close()

        # Switch to the HomeState
        self.switch(HomeState(self.window, self.username))

        # Close the cursor

    def edit_message(self):
        # Enable text editing and add a submit button
        self.comment_text_var.set("")  # Clear the current text
        comment_entry = tk.Entry(self.window, textvariable=self.comment_text_var, width=50)
        comment_entry.pack(pady=10)

        # Submit button
        submit_button = tk.Button(self.window, text="Submit", command=self.submit_message)
        submit_button.pack()
        self.window.update_idletasks()
        submit_button_height = submit_button.winfo_reqheight()
        self.window.geometry(f"{self.window.winfo_width()}x{self.window.winfo_height() + submit_button_height}")

    def submit_message(self):
        last_modified_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        new_comment_text = self.comment_text_var.get()
        cursor = con.cursor()
        cursor.execute(
            "UPDATE Comments SET CommentText = :comment_text ,LastModifiedDate=TO_DATE(:last_modified_date, 'YYYY-MM-DD HH24:MI:SS') WHERE CommentID = :comment_id",
            {'comment_text': new_comment_text, 'last_modified_date': last_modified_date, 'comment_id': self.comment_id})
        cursor.execute('commit')
        cursor.close()

        self.display()


class AddPhotoState(State):
    def __init__(self, window, username, album_name):
        super().__init__(window)
        self.username = username
        self.album_name = album_name

    def display(self):
        self.window.clear()
        self.window.title("Add Photo")
        self.window.geometry("300x250")

        self.photo_name = tk.StringVar()
        self.photo_description = tk.StringVar()

        tk.Label(self.window, text="Please enter the photo details below", bg="white").pack()
        tk.Label(self.window, text="").pack()
        photo_name_lable = tk.Label(self.window, text="Photo Name * ")
        photo_name_lable.pack()
        self.photo_name_entry = tk.Entry(self.window, textvariable=self.photo_name)
        self.photo_name_entry.pack()
        photo_description_lable = tk.Label(self.window, text="Photo Description * ")
        photo_description_lable.pack()
        self.photo_description_entry = tk.Entry(self.window, textvariable=self.photo_description)
        self.photo_description_entry.pack()
        tk.Label(self.window, text="").pack()
        tk.Button(self.window, text="Select Photo", width=10, height=1, bg="white", command=self.select_photo).pack()
        tk.Button(self.window, text="Back", width=10, height=1, command=self.back).pack()

    def select_photo(self):
        photo_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg *.png *.jpeg")])
        if photo_paths:
            for photo_path in photo_paths:
                photo_name = os.path.basename(photo_path)  # Get the filename from the path
                photo_description = f"Description for {photo_name}"
                if len(photo_paths) == 1:
                    self.add_photo(photo_path, photo_name, photo_description, 1)
                else:
                    self.add_photo(photo_path, photo_name, photo_description, 0)

    def add_photo(self, photo_path, photo_name, photo_description, is_single_photo):
        if is_single_photo:
            photo_name = self.photo_name.get()
            photo_description = self.photo_description.get()
        cursor = con.cursor()
        return_val = cursor.var(cx_Oracle.NUMBER)
        insertion_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        con.begin()
        try:
            cursor.execute("""
                INSERT INTO Comments (CommentText,insertiondate,lastmodifieddate)
                VALUES (:photo_description,TO_DATE(:insertion_date, 'YYYY-MM-DD HH24:MI:SS'),TO_DATE(:insertion_date, 'YYYY-MM-DD HH24:MI:SS'))
                RETURNING commentID INTO :return_val
             """, {'photo_description': photo_description, 'insertion_date': insertion_date, 'return_val': return_val})
            comment_id = return_val.getvalue()[0]
            cursor.execute("""
                INSERT INTO Photos (AlbumID, PhotoName, PhotoPath, CommentID)
                VALUES (
                    (SELECT AlbumID FROM Albums WHERE AlbumName = :album_name AND UserID = (SELECT UserID FROM Users WHERE Username = :username)),
                    :photo_name,
                    :photo_path,
                    :comment_id
                )
            """, {'username': self.username, 'album_name': self.album_name, 'photo_name': photo_name,
                  'photo_path': photo_path, 'comment_id': comment_id})
            cursor.execute('commit')
            if is_single_photo:
                messagebox.showinfo("Success", "Photo added successfully")
        except cx_Oracle.DatabaseError as e:
            error, = e.args
            if error.code == 1400:  # This is the error code for a null constraint violation
                messagebox.showerror("Error", "Neither of the fields can be empty")
            if error.code == 955:  # This is the error code for a null constraint violation
                messagebox.showerror("Error", "Photo name already in use")
        except Exception as e:
            con.rollback()
            messagebox.showerror("Error", "Error inserting photo")

        cursor.close()

        self.switch(HomeState(self.window, self.username))

    def back(self):
        self.switch(HomeState(self.window, self.username))


class AddAlbumState(State):
    def __init__(self, window, username):
        super().__init__(window)
        self.username = username

    def display(self):
        self.window.clear()
        self.window.title("Add Album")
        self.window.geometry("300x250")

        self.album_name = tk.StringVar()

        tk.Label(self.window, text="Please enter the album name below", bg="white").pack()
        tk.Label(self.window, text="").pack()
        album_name_lable = tk.Label(self.window, text="Album Name * ")
        album_name_lable.pack()
        self.album_name_entry = tk.Entry(self.window, textvariable=self.album_name)
        self.album_name_entry.pack()
        tk.Label(self.window, text="").pack()
        tk.Button(self.window, text="Create Album", width=10, height=1, bg="white", command=self.create_album).pack()
        tk.Button(self.window, text="Back", width=10, height=1, command=self.back).pack()

    def create_album(self):
        album_name = self.album_name.get()
        try:
            cursor = con.cursor()
            cursor.execute("""
                INSERT INTO Albums (UserID, AlbumName)
                VALUES (
                    (SELECT UserID FROM Users WHERE Username = :username),
                    :album_name
                )
            """, {'username': self.username, 'album_name': album_name})
            cursor.execute('commit')
            cursor.close()
            messagebox.showinfo("Success", "Album created successfully")
        except cx_Oracle.DatabaseError as e:
            error, = e.args
            if error.code == 1400:  # This is the error code for a null constraint violation
                messagebox.showerror("Error", "Album name can't be empty")
            if error.code == 955:  # This is the error code for a null constraint violation
                messagebox.showerror("Error", "Album name already in use")

        self.switch(HomeState(self.window, self.username))

    def back(self):
        self.switch(HomeState(self.window, self.username))


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1800x600")
        self.resizable(False, False)
        self.state = LoginState(self)

    def run(self):
        self.state.display()
        self.mainloop()

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()


app = Application()
app.run()
