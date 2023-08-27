from flask import Flask,render_template,request,redirect,flash,url_for,jsonify
from flask_migrate import Migrate
from models import db,Book,Member,Transaction,Stock,Charges
import datetime
import requests 
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError


app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///library.db'
app.config['SECRET_KEY']='af9d4e10d142994285d0c1f861a70925'
db.init_app(app)
migrate=Migrate(app,db)

@app.route('/')
def index():
    borrowed_books = db.session.query(Transaction).filter(Transaction.return_date == None).count()
    total_books = Book.query.count()
    total_members = Member.query.count()
    total_rent_current_month = calculate_total_rent_current_month()
    recent_transactions  =  db.session.query(Transaction,Book).join(Book).order_by(Transaction.issue_date.desc()).limit(5).all()

    return render_template('index.html', borrowed_books=borrowed_books, total_books=total_books,total_members=total_members,recent_transactions=recent_transactions,total_rent_current_month=total_rent_current_month)

def calculate_total_rent_current_month():
    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year
    start_date = datetime.datetime(current_year, current_month, 1)
    end_date = datetime.datetime(current_year, current_month + 1, 1) - datetime.timedelta(days=1)

    total_rent = db.session.query(db.func.sum(Transaction.rent_fee)).filter(Transaction.issue_date >= start_date,Transaction.issue_date <= end_date).scalar()

    return total_rent if total_rent else 0

@app.route('/add_book',methods=['GET','POST'])
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        publisher = request.form.get('publisher')
        page = request.form.get('page')
        new_book = Book(title=title, author=author, isbn=isbn, publisher=publisher, page=page)
        stock = request.form.get('stock')
        db.session.add(new_book)
        db.session.flush()
        new_stock=Stock(book_id=new_book.id,total_quantity=stock,available_quantity=stock)
        db.session.add(new_stock)
        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_book.html')


@app.route('/add_member',methods=['GET','POST'])
def add_member():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')


        new_member=Member(name=name,email=email,phone=phone,address=address)

        db.session.add(new_member)
        db.session.commit()

        flash('Member added successfully!', 'success')
        return redirect(url_for('add_member'))
    return render_template('add_member.html')


@app.route('/view_books', methods=['GET', 'POST'])
def book_list():
    if request.method == 'POST':
        if 'searcht'and 'searcha' in request.form:
            title = request.form.get('searcht')
            author=request.form.get('searcha')
            books = db.session.query(Book, Stock).join(Stock).filter((Book.title.like(f'%{title}%')),(Book.author.like(f'%{author}%'))).all()
        elif 'searcht' in request.form:
             title=request.form.get('searcht')
             books = db.session.query(Book, Stock).join(Stock).filter(Book.title.like(f'%{title}%')).all()
        elif 'searcha' in request.form:
             author=request.form.get('searcha')
             books = db.session.query(Book, Stock).join(Stock).filter(Book.author.like(f'%{author}%')).all()
    else:
        books= db.session.query(Book, Stock).join(Stock).all()

    return render_template('view_books.html', books=books)

@app.route('/view_members', methods=['GET','POST'])
def member_list():
    if request.method == 'POST':
        search = request.form.get('search')
        member = db.session.query(Member).filter(Member.name.like(f'%{search}%')).all()
    else:
        member=db.session.query(Member).all()

    return render_template('view_members.html', member=member)

@app.route('/edit_book/<int:id>',methods=['GET','POST'])
def edit_book(id):
    book=Book.query.get(id)
    #print(book.title)
    stock=Stock.query.get(book.id)
    try:
        if request.method == 'POST':
            book.title = request.form.get('title')
            book.author = request.form.get('author')
            book.isbn = request.form.get('isbn')
            book.publisher = request.form.get('publisher')
            book.page = request.form.get('page')
            stock.total_quantity=request.form.get('stock')
            db.session.commit()
            flash("Updated Sucessfully",'success')
    except Exception as e:
        db.session.rollback()
        flash(f"An error ocuured \n{e}",'error')
    return render_template('edit_book.html',book=book,stock=stock)

@app.route('/edit_member/<int:id>',methods=['GET','POST'])
def edit_member(id):
    member=Member.query.get(id)
    try:
        if request.method=="POST":
            member.name=request.form['name']
            member.phone=request.form['phone']
            member.email=request.form['email']
            member.address=request.form['address']
            db.session.commit()
            flash("Updated Sucessfully","success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error ocuured \n{e}",'error') 
    return render_template('edit_member.html',member=member)

@app.route('/delete_member/<int:id>',methods=['GET','POST'])
def delete_member(id):
    try:
        member=Member.query.get(id)
        db.session.delete(member)
        db.session.commit()
        flash("Member removed successfully","success")
    except Exception as e:
        flash(f"An error ocuured \n{e}",'error')
    return redirect('/view_members')

@app.route('/delete_book/<int:id>',methods=['GET','POST'])
def delete_book(id):
    try:
        book=Book.query.get(id)
        stock=Stock.query.get(book.id)
        db.session.delete(book)
        db.session.delete(stock)
        db.session.commit()
        flash("Book removed successfully","success")
    except Exception as e:
        flash(f"An error ocuured \n{e}",'error')
    return redirect('/view_members')

@app.route('/view_book/<int:id>')
def view_book(id):
    book=Book.query.get(id)
    stock=Stock.query.filter_by(book_id=id).first()
    transaction=Transaction.query.filter_by(book_id=id).all()
    return render_template('view_book.html',book=book,trans=transaction,stock=stock)


@app.route('/view_member/<int:id>')
def view_member(id):
    member=Member.query.get(id)
    transaction=Transaction.query.filter_by(member_id=member.id).all()
    dbt=calculate_dbt(member)
    return render_template('view_member.html',member=member,trans=transaction,debt=dbt)


def calculate_dbt(member):
    dbt = 0
    charge = db.session.query(Charges).first()
    transactions = db.session.query(Transaction).filter_by(member_id=member.id, return_date=None).all()

    for transaction in transactions:
        days_difference = (datetime.date.today() - transaction.issue_date.date()).days
        if days_difference > 0: 
            dbt += days_difference * charge.rentfee
    return dbt

@app.route('/issuebook',methods=['GET','POST'])
def issue_book():
    if request.method=="POST":
        memberid=request.form['mk']
        title=request.form['bk']
    
        book = db.session.query(Book, Stock).join(Stock).filter(Book.title.like(f'%{title}%')).first() or db.session.query(Book, Stock).join(Stock).filter(Book.id.like(title)).first()
        print(book)
        mem=db.session.query(Member).get(memberid)
        dbt=calculate_dbt(mem)
        return render_template('issuebook.html',book=book,member=mem,debt=dbt)
    
    return render_template('issuebook.html')

@app.route('/issuebookconfirm', methods=['GET', 'POST'])
def issue_book_confirm():
    if request.method == "POST":
        memberid = request.form['memberid']
        bookid = request.form['bookid']

        stock = db.session.query(Stock).filter_by(book_id=bookid).first()
        if stock.available_quantity <= 0:
            flash("Book is not available for issuance.", "error")
            return redirect('/issuebook')

        new_transaction = Transaction(book_id=bookid, member_id=memberid, issue_date=datetime.date.today())
        print(new_transaction)

        stock.available_quantity -= 1
        stock.borrowed_quantity += 1
        stock.total_borrowed += 1

        db.session.add(new_transaction)
        db.session.commit()

        flash("Transaction added successfully", "success")
        return redirect('/issuebook')

    return render_template('issuebook.html')


@app.route('/transactions', methods=['GET', 'POST'])
def view_borrowings():
    transactions = db.session.query(Transaction, Member, Book).join(Book).join(Member).order_by(desc(Transaction.return_date.is_(None))).all()

    if request.method == "POST":
        search = request.form['search']
        
        transactions_by_name = db.session.query(Transaction, Member, Book).join(Book).join(Member).filter(Member.name.like(f'%{search}%')).order_by(desc(Transaction.return_date.is_(None))).all()
        
        transaction_by_id = db.session.query(Transaction, Member, Book).join(Book).join(Member).filter(Transaction.id == search).order_by(desc(Transaction.return_date.is_(None))).all()
        
        if transactions_by_name:
            transactions = transactions_by_name
        elif transaction_by_id:
            transactions = transaction_by_id
        else:
            transactions = []

    return render_template('transactions.html', trans=transactions)

@app.route('/returnbook/<int:id>', methods=['GET', 'POST'])
def return_book(id):
    transaction = db.session.query(Transaction, Member, Book).join(Book).join(Member).filter(Transaction.id == id).first()
    rent=calculate_rent(transaction)
    print(rent)
    return render_template("returnbook.html", trans=transaction,rent=rent)


@app.route('/returnbookconfirm', methods=['POST'])
def return_book_confirm():
    if request.method == "POST":
        id = request.form["id"]
        trans, member = db.session.query(Transaction, Member).join(Member).filter(Transaction.id == id).first()
        stock = Stock.query.filter_by(book_id=trans.book_id).first()
        charge=Charges.query.first()
        rent=(datetime.date.today() - trans.issue_date.date() ).days * charge.rentfee
        if stock:
            stock.available_quantity += 1
            stock.borrowed_quantity -= 1

            trans.return_date = datetime.date.today()
            trans.rent_fee =rent
            db.session.commit()
            flash(f"{member.name} Returned book successfully", 'success')
        else:
            flash("Error updating stock information", 'error')

    return redirect('transactions')

def calculate_rent(transaction):
    charge=Charges.query.first()
    rent=(datetime.date.today() - transaction.Transaction.issue_date.date() ).days * charge.rentfee
    return rent

API_BASE_URL = "https://frappe.io/api/method/frappe-library"


@app.route('/import_book', methods=['GET', 'POST'])
def imp():
    if request.method == 'POST':
        title = request.form.get('title', default='', type=str)
        num_books = request.form.get('num_books', default=20, type=int)
        num_pages = (num_books + 19) // 20
        all_books = []
        for page in range(1, num_pages + 1):
            url = f"{API_BASE_URL}?page={page}&title={title}"
            response = requests.get(url)
            data = response.json()
            all_books.extend(data.get('message', []))  
        return render_template('imp.html', data=all_books[:num_books], title=title, num_books=num_books)


    return render_template('imp.html', data=[], title='', num_books=20)

@app.route('/save_all_books', methods=['POST'])
def save_all_books():
    data = request.json

    for book_data in data:
        book_id = book_data['id']
        existing_book = Book.query.get(book_id)

        if existing_book is None:
            book = Book(
                id=book_id,
                title=book_data['title'],
                author=book_data['authors'],
                isbn=book_data['isbn'],
                publisher=book_data['publisher'],
                page=book_data['numPages']
            )
            st = book_data['stock']

            try:
                db.session.add(book)
                stock = Stock(book_id=book_id, total_quantity=st, available_quantity=st)
                db.session.add(stock)
                db.session.commit()
            except IntegrityError as e:
                db.session.rollback()  
                print(f"Error adding book with ID {book_id}: {str(e)}")
        else:
            print(f"Book with ID {book_id} already exists, skipping.")

    flash("Books added successfully", "success")
    return redirect('/import_book')

@app.route('/stockupdate/<int:id>',methods=['GET','POST'])
def stock_update(id):
    stock,book=db.session.query(Stock,Book).join(Book).filter(Stock.book_id == id).first()
    if request.method=="POST":
        qty=int(request.form['qty'])
        if qty > stock.total_quantity:
            stock.available_quantity+=qty
            stock.total_quantity+=qty
        else:
            stock.available_quantity-=qty
            stock.total_quantity-=qty
        db.session.commit()
        flash("Stock Updated" , "success")
    return render_template('stockupdate.html',stock=stock,book=book)