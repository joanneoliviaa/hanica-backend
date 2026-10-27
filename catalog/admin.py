from django.contrib import admin

from .models import Customer, Product, Transaction, TransactionDetail, UploadHistory

admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Transaction)
admin.site.register(TransactionDetail)
admin.site.register(UploadHistory)