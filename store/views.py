# === Complete store/views.py with session-based login and fixed basket flow ===
from opcode import opname
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import connection
from django.db.models import Max
from .models import *
from datetime import datetime
from django.contrib import messages
from django.db import IntegrityError

# Simple Login

def login_view(request):
    if request.method == 'POST':
        cid = request.POST.get('cid')
        try:
            customer = Customer.objects.get(cid=cid)
            request.session['cid'] = customer.cid
            return redirect('home')
        except Customer.DoesNotExist:
            return render(request, 'store/login.html', {'error': 'Invalid CID'})
    return render(request, 'store/login.html')
def logout_view(request):
    request.session.flush()
    return redirect('login')

# Home
def home(request):
    if 'cid' not in request.session:
        return redirect('login')
    return render(request, 'store/home.html')

# Customer Registration
def register_customer(request):
    if request.method == 'POST':
        Customer.objects.create(
            cid=request.POST['cid'],
            fname=request.POST['fname'],
            lname=request.POST['lname'],
            email=request.POST['email'],
            address=request.POST['address'],
            phone=request.POST['phone']
        )
        return redirect('login')
    return render(request, 'store/register.html')

# Credit Card Management
def manage_credit_cards(request):
    if 'cid' not in request.session:
        return redirect('login')
    customer = Customer.objects.get(cid=request.session['cid'])
    if request.method == 'POST':
        CreditCard.objects.create(
            ccnumber=request.POST['ccnumber'],
            secnumber=request.POST['secnumber'],
            ownername=request.POST['ownername'],
            cctype=request.POST['cctype'],
            biladdress=request.POST['biladdress'],
            expdate=request.POST['expdate'],
            customer=customer
        )
        return redirect('credit_cards')
    cards = CreditCard.objects.filter(customer=customer)
    return render(request, 'store/credit_cards.html', {'cards': cards})

# Shipping Address Management
def manage_shipping_addresses(request):
    if 'cid' not in request.session:
        return redirect('login')
    customer = Customer.objects.get(cid=request.session['cid'])
    if request.method == 'POST':
        ShippingAddress.objects.create(
            saname=request.POST['saname'],
            street=request.POST['street'],
            snumber=request.POST['snumber'],
            city=request.POST['city'],
            zip=request.POST['zip'],
            state=request.POST['state'],
            country=request.POST['country'],
            customer=customer
        )
        return redirect('shipping_addresses')
    addresses = ShippingAddress.objects.filter(customer=customer)
    return render(request, 'store/shipping.html', {'addresses': addresses})

# Product Listing
def product_list(request):
    if 'cid' not in request.session:
        return redirect('login')
    products = Product.objects.all()
    return render(request, 'store/product_list.html', {'products': products})

from .models import Basket, Customer

def get_or_create_current_basket(request):
    customer = Customer.objects.get(cid=request.session['cid'])
    basket_id = request.session.get('basket_id')

    if basket_id:
        try:
            basket = Basket.objects.get(pk=basket_id, cid = customer)
            return basket
        except Basket.DoesNotExist:
            pass  # Continue to create a new basket

    # Create new basket
    newBasketId = Basket.objects.count() + 1
    basket = Basket.objects.create(bid=newBasketId, cid = customer)
    request.session['basket_id'] = basket.bid
    return basket


def add_to_basket(request, product_id):
    if 'cid' not in request.session:
        return redirect('login')

    product = get_object_or_404(Product, pk=product_id)
    basket = get_or_create_current_basket(request)

    with connection.cursor() as cursor:
        # Check if item already in basket
        cursor.execute("""
            SELECT quantity FROM appears_in
            WHERE bid = %s AND pid = %s
        """, [basket.pk, product.pk])
        row = cursor.fetchone()

        if row:
            # Update quantity if already exists
            cursor.execute("""
                UPDATE appears_in
                SET quantity = quantity + 1
                WHERE bid = %s AND pid = %s
            """, [basket.pk, product.pk])
            messages.success(request, f"🔁 Updated quantity for {product.pname}.")
        else:
            # Insert new item
            cursor.execute("""
                INSERT INTO appears_in (bid, pid, quantity, pricesold)
                VALUES (%s, %s, %s, %s)
            """, [basket.pk, product.pk, 1, product.pprice])
            messages.success(request, f"✅ Added {product.pname} to basket.")

    return redirect('product_list')

def view_basket(request):
    if 'cid' not in request.session:
        return redirect('login')

    basket = get_or_create_current_basket(request)
    items = []

    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.pname, a.quantity, a.pricesold
            FROM appears_in a
            JOIN product p ON a.pid = p.pid
            WHERE a.bid = %s
        """, [basket.bid])
        rows = cursor.fetchall()
    items = [
        {
            'pname': row[0],
            'quantity': row[1],
            'pricesold': row[2],
            'total': row[1] * float(row[2]),
        }
        for row in rows
    ]
    print(items)
    total = sum(item['pricesold'] * item['quantity'] for item in items)

    return render(request, 'store/basket.html', {
        'basket': basket,
        'items': items,
        'total': total,
    })

def checkout(request):
    if 'cid' not in request.session:
        return redirect('login')

    customer = Customer.objects.get(cid=request.session['cid'])
    basket = get_or_create_current_basket(request)
    basket_id = request.session.get('basket_id')
    items = []

    if request.method == 'POST':
        saname = request.POST.get('saname')  # unique shipping address name
        cc_id = request.POST.get('cc_id')

        shipping = ShippingAddress.objects.get(customer=customer, saname=saname)
        card = CreditCard.objects.get(customer=customer, ccnumber=cc_id)

        Transaction.objects.create(
            bid=basket,
            customer=customer,
            saname=shipping.saname,
            ccnumber=card,
            tdate=timezone.now().date(),
            ttag='Pending'
        )

        del request.session['basket_id']

        messages.success(request, "Order placed successfully!")
        return redirect('transaction_history')

    shipping_addresses = ShippingAddress.objects.filter(customer=customer)
    credit_cards = CreditCard.objects.filter(customer=customer)
    if basket_id:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.pname, a.quantity, a.pricesold
                FROM appears_in a
                JOIN product p ON a.pid = p.pid
                WHERE a.bid = %s
            """, [basket_id])
            rows = cursor.fetchall()
        items = [
            {
                'pname': row[0],
                'quantity': row[1],
                'pricesold': row[2],
                'total': row[1] * float(row[2]),
            }
            for row in rows
        ]
        print(items)

    total = sum(item['pricesold'] * item['quantity'] for item in items)

    return render(request, 'store/checkout.html', {
        'items' : items,
        'shipping_addresses': shipping_addresses,
        'credit_cards': credit_cards,
        'total' :total
    })

# Transaction History
def transaction_history(request):
    if 'cid' not in request.session:
        return redirect('login')
    customer = Customer.objects.get(cid=request.session['cid'])
    transactions = Transaction.objects.filter(customer=customer)
    return render(request, 'store/history.html', {'transactions': transactions})

# Sales Statistics (Raw SQL)
def sales_statistics(request):
    stats = {}
    if request.method == 'POST':
        which = request.POST.get('which_query')
        start = request.POST.get('start')
        end = request.POST.get('end')
        with connection.cursor() as cursor:
            if which == 'query1':
                cursor.execute("""
                    SELECT c.ccnumber, SUM(ai.pricesold)
                    FROM transaction t
                    JOIN credit_card c ON t.ccnumber = c.ccnumber
                    JOIN basket b ON t.bid = b.bid
                    JOIN appears_in ai ON b.bid = ai.bid
                    GROUP BY c.ccnumber
                """)
                stats['query1'] = cursor.fetchall()

            elif which == 'query2':
                cursor.execute("""
                    SELECT c.cid, CONCAT(c.fname, ' ', c.lname), SUM(ai.pricesold)
                    FROM transaction t
                    JOIN customer c ON t.cid = c.cid
                    JOIN basket b ON t.bid = b.bid
                    JOIN appears_in ai ON b.bid = ai.bid
                    GROUP BY c.cid, c.fname, c.lname
                    ORDER BY SUM(ai.pricesold) DESC
                    LIMIT 10
                """)
                stats['query2'] = cursor.fetchall()

            elif which == 'query3':
                cursor.execute("""
                    SELECT ai.pid, p.pname, COUNT(*)
                    FROM transaction t
                    JOIN basket b ON t.bid = b.bid
                    JOIN appears_in ai ON b.bid = ai.bid
                    JOIN product p ON ai.pid = p.pid
                    WHERE t.tdate BETWEEN %s AND %s
                    GROUP BY ai.pid, p.pname
                """, [start, end])
                stats['query3'] = cursor.fetchall()

            elif which == 'query4':
                cursor.execute("""
                    SELECT p.pid, p.pname, COUNT(DISTINCT t.cid)
                    FROM transaction t
                    JOIN basket b ON t.bid = b.bid
                    JOIN appears_in ai ON b.bid = ai.bid
                    JOIN product p ON ai.pid = p.pid
                    WHERE t.tdate BETWEEN %s AND %s
                    GROUP BY p.pid, p.pname
                    ORDER BY COUNT(DISTINCT t.cid) DESC
                    LIMIT 1
                """, [start, end])
                stats['query4'] = cursor.fetchall()

            elif which == 'query5':
                cursor.execute("""
                    SELECT
                        ccnumber,
                        max(totalamount)
                    FROM
                        transaction
                    WHERE
                        tdate BETWEEN %s AND %s
                    GROUP BY
                        ccnumber;
                """, [start, end])
                
                stats['query5'] = cursor.fetchall()

            elif which == 'query6':
                cursor.execute("""
                    SELECT p.ptype, AVG(p.pprice * ai.quantity)
                    FROM product p
                    JOIN appears_in ai ON p.pid = ai.pid
                    JOIN basket b ON ai.bid = b.bid
                    JOIN transaction t ON b.bid = t.bid
                    WHERE t.tdate BETWEEN %s AND %s
                    GROUP BY p.ptype
                    ORDER BY AVG(p.pprice * ai.quantity) DESC
                """, [start, end])
                stats['query6'] = cursor.fetchall()

    return render(request, 'store/statistics.html', {'stats': stats})