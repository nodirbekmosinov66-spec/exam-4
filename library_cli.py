import sys
import sqlite3
import re  # Telefon raqamini tekshirish uchun muntazam ifodalar moduli

class Book:
    def __init__(self, book_id, title, author, year, status="bor"):
        self.id = book_id
        self.title = title
        self.author = author
        self.year = year
        self.status = status

class Member:
    def __init__(self, member_id, name, phone):
        self.id = member_id
        self.name = name
        self.phone = phone

class Library:
    def __init__(self, db_name="library.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            year TEXT,
            status TEXT DEFAULT 'bor'
        )
        """)
        # phone ustuniga UNIQUE qo'shildi, ya'ni bir xil raqamli a'zo qayta qo'shilmaydi
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT UNIQUE
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            book_id INTEGER,
            FOREIGN KEY(member_id) REFERENCES members(id),
            FOREIGN KEY(book_id) REFERENCES books(id)
        )
        """)
        self.conn.commit()

    def add_book(self, title, author, year):
        try:
            self.cursor.execute("INSERT INTO books (title, author, year) VALUES (?, ?, ?)", (title, author, year))
            self.conn.commit()
            print("Kitob muvaffaqiyatli qo'shildi!")
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

    def get_all_books(self):
        try:
            self.cursor.execute("SELECT id, title, author, year, status FROM books")
            rows = self.cursor.fetchall()
            if not rows:
                print("Kutubxonada kitoblar yo'q.")
                return
            for row in rows:
                print(f"ID: {row[0]} | Nomi: {row[1]} | Muallifi: {row[2]} | Yili: {row[3]} | Holati: {row[4]}")
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

    def search_books(self, query):
        try:
            self.cursor.execute("SELECT id, title, author, year, status FROM books WHERE title LIKE ? OR author LIKE ?", (f"%{query}%", f"%{query}%"))
            rows = self.cursor.fetchall()
            if not rows:
                print("Mos kitob topilmadi.")
                return
            for row in rows:
                print(f"ID: {row[0]} | Nomi: {row[1]} | Muallifi: {row[2]} | Yili: {row[3]} | Holati: {row[4]}")
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

    def add_member(self, name, phone):
        try:
            self.cursor.execute("INSERT INTO members (name, phone) VALUES (?, ?)", (name, phone))
            self.conn.commit()
            print("A'zo muvaffaqiyatli qo'shildi!")
        except sqlite3.IntegrityError:
            print("Xato: Bu telefon raqami allaqachon ro'yxatdan o'tgan!")
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

    def give_book(self, member_id, book_id):
        try:
            self.cursor.execute("SELECT status FROM books WHERE id = ?", (book_id,))
            res = self.cursor.fetchone()
            if not res:
                print("Bunday ID dagi kitob mavjud emas!")
                return
            if res[0] == "berilgan":
                print("Kitob allaqachon berilgan!")
                return

            self.cursor.execute("SELECT id FROM members WHERE id = ?", (member_id,))
            if not self.cursor.fetchone():
                print("Bunday ID dagi a'zo mavjud emas!")
                return

            self.cursor.execute("INSERT INTO orders (member_id, book_id) VALUES (?, ?)", (member_id, book_id))
            self.cursor.execute("UPDATE books SET status = 'berilgan' WHERE id = ?", (book_id,))
            self.conn.commit()
            print("Kitob muvaffaqiyatli berildi!")
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

    def return_book(self, book_id):
        try:
            self.cursor.execute("SELECT status FROM books WHERE id = ?", (book_id,))
            res = self.cursor.fetchone()
            if not res:
                print("Bunday ID dagi kitob mavjud emas!")
                return
            if res[0] == "bor":
                print("Kitob kutubxonada turibdi, u berilmagan!")
                return

            self.cursor.execute("DELETE FROM orders WHERE book_id = ?", (book_id,))
            self.cursor.execute("UPDATE books SET status = 'bor' WHERE id = ?", (book_id,))
            self.conn.commit()
            print("Kitob muvaffaqiyatli qaytarildi!")
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

    def who_has_what(self):
        try:
            query = """
            SELECT books.id, books.title, members.name 
            FROM orders
            JOIN books ON orders.book_id = books.id
            JOIN members ON orders.member_id = members.id
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            if not rows:
                print("Hech kimda kitob yo'q.")
                return
            for row in rows:
                print(f"Kitob ID: {row[0]} | Nomi: {row[1]} | Kimda: {row[2]}")
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

def main():
    lib = Library()
    
    while True:
        print("\n1. Kitob qo'shish")
        print("2. Barcha kitoblar")
        print("3. Kitob qidirish")
        print("4. A'zo qo'shish")
        print("5. Kitob berish")
        print("6. Kitobni qaytarish")
        print("7. Kimda qaysi kitob bor")
        print("0. Chiqish")
        
        choice = input("Tanlovni kiriting: ").strip()
        
        if choice == "1":
            title = input("Kitob nomi: ").strip()
            author = input("Muallifi: ").strip()
            year = input("Yili: ").strip()
            if title and author and year:
                lib.add_book(title, author, year)
            else:
                print("Xato: Kitob ma'lumotlarini bo'sh qoldirmang!")
                
        elif choice == "2":
            lib.get_all_books()
            
        elif choice == "3":
            query = input("Qidiruv kalit so'zi: ")
            lib.search_books(query)
            
        elif choice == "4":
            # Ismni tekshirish (bo'sh qolmasligi kerak)
            while True:
                name = input("Ismi: ").strip()
                if name:
                    break
                print("Xato: Ism bo'sh bo'lishi mumkin emas!")
            
            # Telefon raqamini aniq formatda tekshirish
            while True:
                phone = input("Telefon raqami : ").strip()
                
                # O'zbekiston raqamlari formati uchun shablon:
                # +998 bilan yoki usiz faqat 9 ta raqam bo'lishi shart
                pattern = r"^(\+?998)?\d{9}$"
                
                if re.match(pattern, phone):
                    break
                print("Xato: Noto'g'ri telefon raqami! Faqat haqiqiy raqam kiriting (masalan: 991234567).")
                
            lib.add_member(name, phone)
            
        elif choice == "5":
            try:
                m_id = int(input("A'zo ID: "))
                b_id = int(input("Kitob ID: "))
                lib.give_book(m_id, b_id)
            except ValueError:
                print("Xato: ID raqam bo'lishi kerak!")
                
        elif choice == "6":
            try:
                b_id = int(input("Kitob ID: "))
                lib.return_book(b_id)
            except ValueError:
                print("Xato: ID raqam bo'lishi kerak!")
                
        elif choice == "7":
            lib.who_has_what()
            
        elif choice == "0":
            sys.exit()
        else:
            print("Noto'g'ri tanlov. Qaytadan urunib ko'ring.")

if __name__ == "__main__":
    main()
