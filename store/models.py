# === store/models.py matching Neon lowercase schema with related_name support ===
from django.db import models

class Customer(models.Model):
    cid = models.IntegerField(primary_key=True, db_column='cid')
    fname = models.CharField(max_length=50, db_column='fname')
    lname = models.CharField(max_length=50, db_column='lname')
    email = models.CharField(max_length=100, db_column='email')
    address = models.CharField(max_length=200, db_column='address')
    phone = models.CharField(max_length=20, db_column='phone')

    class Meta:
        db_table = 'customer'
        managed = False

class CreditCard(models.Model):
    ccnumber = models.CharField(primary_key=True, max_length=16, db_column='ccnumber')
    secnumber = models.CharField(max_length=4, db_column='secnumber')
    ownername = models.CharField(max_length=100, db_column='ownername')
    cctype = models.CharField(max_length=20, db_column='cctype')
    biladdress = models.CharField(max_length=200, db_column='biladdress')
    expdate = models.DateField(db_column='expdate')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, db_column='cid', related_name='credit_cards')

    class Meta:
        db_table = 'credit_card'
        managed = False

class ShippingAddress(models.Model):
    saname = models.CharField(max_length=100, db_column='saname', primary_key=True)
    street = models.CharField(max_length=100, db_column='street')
    snumber = models.CharField(max_length=10, db_column='snumber')
    city = models.CharField(max_length=50, db_column='city')
    zip = models.CharField(max_length=10, db_column='zip')
    state = models.CharField(max_length=50, db_column='state')
    country = models.CharField(max_length=50, db_column='country')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, db_column='cid')

    class Meta:
        db_table = 'shipping_address'
        unique_together = (('saname', 'customer'),)
        managed = False

class Basket(models.Model):
    bid = models.IntegerField(primary_key=True, db_column='bid')
    cid = models.ForeignKey(Customer, on_delete=models.CASCADE, db_column='cid')

    class Meta:
        db_table = 'basket'
        managed = False
    
class Transaction(models.Model):
    bid = models.ForeignKey(Basket, on_delete=models.CASCADE, primary_key=True, db_column='bid')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, db_column='cid')
    saname = models.CharField(max_length=100, db_column='saname')
    ccnumber = models.ForeignKey(CreditCard, on_delete=models.CASCADE, db_column='ccnumber')
    tdate = models.DateField(db_column='tdate')
    ttag = models.CharField(max_length=50, db_column='ttag')

    class Meta:
        db_table = 'transaction'
        managed = False
        unique_together = (('bid', 'customer'),)


class Product(models.Model):
    pid = models.IntegerField(primary_key=True, db_column='pid')
    ptype = models.CharField(max_length=50, db_column='ptype')
    pprice = models.DecimalField(max_digits=10, decimal_places=2, db_column='pprice')
    description = models.TextField(db_column='description')
    pname = models.CharField(max_length=100, db_column='pname')

    class Meta:
        db_table = 'product'
        managed = False

class Computer(models.Model):
    pid = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True, db_column='pid', related_name='computer')
    cputype = models.CharField(max_length=50, db_column='cputype')

    class Meta:
        db_table = 'computer'
        managed = False

class Printer(models.Model):
    pid = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True, db_column='pid', related_name='printer')
    printertype = models.CharField(max_length=50, db_column='printertype')
    resolution = models.CharField(max_length=50, db_column='resolution')

    class Meta:
        db_table = 'printer'
        managed = False

class Laptop(models.Model):
    pid = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True, db_column='pid', related_name='laptop')
    weight = models.DecimalField(max_digits=5, decimal_places=2, db_column='weight')
    btype = models.CharField(max_length=50, db_column='btype')

    class Meta:
        db_table = 'laptop'
        managed = False

class AppearsIn(models.Model):
    bid = models.ForeignKey(Basket, on_delete=models.CASCADE, db_column='bid')
    pid = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='pid')
    quantity = models.IntegerField(db_column='quantity')
    pricesold = models.DecimalField(max_digits=10, decimal_places=2, db_column='pricesold')

    class Meta:
        db_table = 'appears_in'
        managed = False
        unique_together = (('bid', 'pid'),)
        
    def save(self, *args, **kwargs):
        existing = AppearsIn.objects.filter(basket=self.basket, product=self.product).exclude(pk=self.pk).first()
        if existing:
            existing.quantity += self.quantity
            existing.save()
        else:
            super().save(*args, **kwargs)