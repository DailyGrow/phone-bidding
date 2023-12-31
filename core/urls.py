from django.urls import path
from .views import *
from .chatbot import *

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('product/<slug>/', ItemDetailView.as_view(), name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
    path('bid/<slug:slug>/', BidView.as_view(), name='place_bid'),
    path('my-inventory/', InventoryView.as_view(), name='my_inventory'),
    path('product/edit/<slug:slug>/', ProductEditView.as_view(), name='edit_product'),
    path('product/delete/<slug:slug>/', ProductDeleteView.as_view(), name='delete_product'),
    path('add-phone/', AddPhoneView.as_view(), name='add_phone'),
    path('make-a-deal/<slug>/', make_a_deal, name='make-a-deal'),
    path('deal/<int:bid_id>/', DealView.as_view(), name='deal'),
    path('send-notifications/<int:bid_id>', send_notifications, name='send-notifications'),
    path('notice-list/', NoticeListView.as_view(), name='notice-list'),
    path('notice-update/<notice_verb>/', NoticeUpdateView.as_view(), name='notice-update'),
    path('chat-rooms/', chat_rooms, name='chat_rooms'),
    path('send-message/<int:user_id>/<int:item_id>/', send_message, name='send_message'),
    path('view-messages/<int:user_id>/<int:item_id>/', view_messages, name='view_messages'),
    path('profile/update/<int:pk>/', UserProfileUpdateView.as_view(), name='profile_update'),
    path('rate-seller/<int:seller_id>/', rate_seller, name='rate_seller'),
    path('order_history/', order_history, name='order_history'),
    path('sales-report/', WeeklySalesReportView.as_view(), name='sales_report'),
    path('chatbot/', SQLQueryView.as_view(), name='chatbot'),
]
