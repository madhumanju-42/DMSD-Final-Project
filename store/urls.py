from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # 1. Registration & Management
    path('register/', views.register_customer, name='register'),
    path('credit-cards/', views.manage_credit_cards, name='credit_cards'),
    path('shipping/', views.manage_shipping_addresses, name='shipping_addresses'),

    # 2. Online Sale
    path('products/', views.product_list, name='product_list'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.transaction_history, name='transaction_history'),
    path('add/<int:product_id>/', views.add_to_basket, name='add_to_basket'),
    path('basket/', views.view_basket, name='view_basket'),

    # 3. Statistics
    path('stats/', views.sales_statistics, name='sales_statistics'),
]