import random
import string

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, View, UpdateView, DeleteView, CreateView
from django.urls import reverse_lazy
from django.http import Http404
from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm, BidForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile, Bid
from notifications.signals import notify

from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile, Bid, Message
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid

class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():

                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the default shipping address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the default billing address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False,
                'STRIPE_PUBLIC_KEY' : settings.STRIPE_PUBLIC_KEY
            }
            userprofile = self.request.user.userprofile
            if userprofile.one_click_purchasing:
                # fetch the users card list
                cards = stripe.Customer.list_sources(
                    userprofile.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    # update the context with the default card
                    context.update({
                        'card': card_list[0]
                    })
            return render(self.request, "payment.html", context)
        else:
            messages.warning(
                self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)
        if form.is_valid():
            print("form is valid")
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save:
                if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id)
                    customer.sources.create(source=token)

                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                    )
                    customer.sources.create(source=token)
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

            amount = int(order.get_total() * 100)

            try:

                if use_default or save:
                    # charge the customer because we cannot charge the token more than once
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        customer=userprofile.stripe_customer_id
                    )
                else:
                    # charge once off on the token
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        source=token
                    )

                # create the payment
                payment = Payment()
                payment.stripe_charge_id = charge['id']
                payment.user = self.request.user
                payment.amount = order.get_total()
                payment.save()

                # assign the payment to the order

                order_items = order.items.all()
                order_items.update(ordered=True)
                for item in order_items:
                    item.save()

                order.ordered = True
                order.payment = payment
                order.ref_code = create_ref_code()
                order.save()

                messages.success(self.request, "Your order was successful!")
                return redirect("/")

            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("/")

            except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.warning(self.request, "Rate limit error")
                return redirect("/")

            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                print(e)
                messages.warning(self.request, "Invalid parameters")
                return redirect("/")

            except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.warning(self.request, "Not authenticated")
                return redirect("/")

            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                messages.warning(self.request, "Network error")
                return redirect("/")

            except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
                messages.warning(
                    self.request, "Something went wrong. You were not charged. Please try again.")
                return redirect("/")

            except Exception as e:
                # send an email to ourselves
                messages.warning(
                    self.request, "A serious error occurred. We have been notifed.")
                return redirect("/")

        messages.warning(self.request, "Invalid data received")
        return redirect("/payment/stripe/")


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"

    def get_queryset(self):
        queryset = Item.objects.all()
        search_query = self.request.GET.get('search', None)
        system_filter = self.request.GET.get('system', None)

        if search_query:
            queryset = queryset.filter(title__icontains=search_query)
        
        if system_filter:
            queryset = queryset.filter(system=system_filter)

        return queryset


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")

class DealView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        bid_id = kwargs.get('bid_id')
        try:
            bid = Bid.objects.get(id=bid_id)
            # order = Order.objects.get(user=self.request.user, ordered=False, items__in=[bid.item])
            context = {
                # 'object': order,
                'bid_id': bid_id,
                'bidder_username': bid.bidder.username,  # Pass the bidder's username to the context
                'item_title': bid.item.title,
                'item_price': bid.amount,
                'item_slug': bid.item.slug,
            }
            return render(self.request, 'deal.html', context)
        except Bid.DoesNotExist:
            messages.warning(self.request, "Bid not found")
            return redirect("/")
        except Order.DoesNotExist:
            messages.warning(self.request, "Order not found")
            return redirect("/")

class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"
    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['bids'] = Bid.objects.filter(item=self.get_object()).order_by('-time')
            return context

@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        # ordered_date = timezone.now()
        # order = Order.objects.create(
        #     user=request.user, ordered_date=ordered_date)
        # order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:order-summary")

@login_required
def make_a_deal(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("core:deal")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:deal")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:deal")

@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")


class BidView(LoginRequiredMixin, View):
    template_name = 'place_bid.html'

    def get(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        item = get_object_or_404(Item, slug=slug)
        form = BidForm(item=item)
        bids = Bid.objects.filter(item=item).order_by('-time')
        context = {'form': form, 'item': item, 'bids': bids}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        item = get_object_or_404(Item, slug=slug)
        form = BidForm(request.POST, item=item)
        bids = Bid.objects.filter(item=item).order_by('-time')
        context = {'form': form, 'item': item, 'bids': bids}
        if form.is_valid():
            Bid.objects.create(
                item=item, 
                bidder=request.user, 
                amount=form.cleaned_data['amount'],
                time=timezone.now()
            )
            messages.success(request, "Your bid was placed successfully!")
            return redirect(item.get_absolute_url())
        else:
            return render(request, self.template_name, context)


class InventoryView(LoginRequiredMixin, ListView):
    model = Item
    template_name = 'my_inventory.html'
    context_object_name = 'items'

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(seller=self.request.user)  # Filter to show only user's items

        system_filter = self.request.GET.get('system', 'ALL')
        search_query = self.request.GET.get('search', '')

        if system_filter != 'ALL':
            queryset = queryset.filter(system=system_filter)
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)

        return queryset
    

class ProductEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Item
    fields = ['title', 'description', 'starting_bid', 'condition', 'system', 'brand', 'image']
    template_name = 'edit_product.html'

    def get_success_url(self):
        return reverse_lazy('core:product', kwargs={'slug': self.object.slug})

    def test_func(self):
        return self.request.user == self.get_object().seller

class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Item
    template_name = 'delete_product.html'
    success_url = reverse_lazy('core:my_inventory')  # Redirect to home page after deletion

    def test_func(self):
        return self.request.user == self.get_object().seller
    
class AddPhoneView(LoginRequiredMixin, CreateView):
    model = Item
    fields = ['title', 'description', 'starting_bid', 'condition', 'system', 'brand', 'image']
    template_name = 'add_phone.html'

    def form_valid(self, form):
        form.instance.seller = self.request.user  # Set the seller to the current user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('core:my_inventory')  # Redirect to inventory page after adding

# def send_notifictaions(actor, verb, recipient, target, description, **kwargs):
#     notify.send(actor, recipient, verb, target, description, **kwargs)

@login_required
def send_notifications(request, bid_id):
    bid = Bid.objects.get(id=bid_id)
    send_bidder = bid.bidder
    message = {}
    message['recipient'] = send_bidder  # 消息接收人
    message['verb'] = bid_id  # 消息标题
    message['description'] = "bidding email"  # 详细内容
    message['target'] = send_bidder  # 目标对象
    notify.send(request.user, **message)
    messages.info(request, "Your deal was successful!")
    return redirect("/")


class NoticeListView(LoginRequiredMixin, ListView):
    """notice list"""

    context_object_name = 'notices'

    template_name = 'notice_list.html'


    # unread notice
    def get_queryset(self):
        return self.request.user.notifications.unread()


@login_required
def get_checkout(request, bid_id):
    try:

        print(bid_id)
        # bid = Bid.objects.get(id=verb)
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=self.request.user, ordered_date=ordered_date)
        # order.items.add(order_item)
        form = CheckoutForm()
        context = {
            'form': form,
            'couponform': CouponForm(),
            'order': order,
            'DISPLAY_COUPON_FORM': True
        }

        shipping_address_qs = Address.objects.filter(
            user=self.request.user,
            address_type='S',
            default=True
        )
        if shipping_address_qs.exists():
            context.update(
                {'default_shipping_address': shipping_address_qs[0]})

        billing_address_qs = Address.objects.filter(
            user=self.request.user,
            address_type='B',
            default=True
        )
        if billing_address_qs.exists():
            context.update(
                {'default_billing_address': billing_address_qs[0]})
        return render(self.request, "checkout.html", context)
    except ObjectDoesNotExist:
        messages.info(self.request, "You do not have an active order")
        # return redirect("core:notice-update")
        return redirect("/")

class NoticeUpdateView(LoginRequiredMixin, View):
    """update notice"""
    def get(self, request, **kwargs):
        try:
            verb = kwargs.get('notice_verb')
            bid = Bid.objects.get(id=verb)
            order_item, created = OrderItem.objects.get_or_create(
                item=bid.item,
                user=request.user,
                ordered=False,
                price=bid.amount
            )
            ordered_date = timezone.now()
            order, created = Order.objects.get_or_create(
                user=self.request.user, ordered=False)
            order.ordered_date=ordered_date
            order.items.add(order_item)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            # return redirect("core:notice-update")
            return redirect("/")


    def post(self,request, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:

            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():

                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the default shipping address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        # return redirect('core:checkout')
                        return redirect("core:notice-update")
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the defualt billing address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        # return redirect('core:checkout')
                        return render("/")
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                elif payment_option == 'O':
                    order_items = order.items.all()
                    order_items.update(ordered=True)
                    for item in order_items:
                        item.save()

                    order.ordered = True
                    # order.payment = payment
                    order.ref_code = create_ref_code()
                    order.save()
                    messages.info(
                        self.request, "You can contact with seller to pay offline")
                    return redirect("core:notice-update")
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    # return redirect('core:checkout')
                    return redirect("core:notice-update")
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")


@login_required
def chat_rooms(request):
    # 获取当前登录的用户
    user = request.user

    # 查询与当前用户相关的所有消息
    messages = Message.objects.filter(Q(sender=user) | Q(receiver=user)).distinct()

    # 提取所有相关的聊天室（用户ID和商品ID的组合）
    chat_rooms = set()
    for message in messages:
        other_user = message.sender if message.sender != user else message.receiver
        chat_rooms.add((other_user.id, message.item.id))

    # 渲染模板，并传递聊天室数据
    return render(request, 'chat_rooms.html', {'chat_rooms': chat_rooms})


@login_required
def send_message(request, user_id, item_id):
    if request.method == "POST":
        if request.user.id == user_id:
          raise Http404("Cannot message yourself")

        content = request.POST.get('content')
        item = get_object_or_404(Item, id=item_id)
        receiver = get_object_or_404(User, id=user_id)

        Message.objects.create(
            sender=request.user,
            receiver=receiver,
            item=item,
            content=content,
            sent_time=timezone.now()
        )
        return redirect('core:view_messages', user_id=user_id, item_id=item_id)


@login_required
def view_messages(request, user_id, item_id):
    item = get_object_or_404(Item, id=item_id)
    
    if request.user.id == user_id:
        raise Http404("Cannot message yourself")

    receiver = get_object_or_404(User, id=user_id)
    messages = Message.objects.filter(
        item=item,
        sender__in=[request.user, receiver],
        receiver__in=[request.user, receiver]
    ).order_by('sent_time')

    context = {
        'receiver_id': user_id,
        'item_id': item_id,
        'item': item,
        'chat_messages': messages
    }

    return render(request, 'view_messages.html', context)

class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    fields = ['address', 'phone', 'stripe_customer_id', 'one_click_purchasing']  # specify the fields you want to be editable
    template_name = 'user_profile.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        if pk:
            return get_object_or_404(UserProfile, pk=pk)
        return UserProfile.objects.get(user=self.request.user)

    def get_success_url(self):
        pk = self.kwargs.get('pk')
        if pk:
            return reverse_lazy('core:profile_update', kwargs={'pk': pk})
        return reverse_lazy('core:profile_update', kwargs={'pk': self.request.user.pk})

    def form_valid(self, form):

        # Additional logic (if needed) when form is valid
        return super().form_valid(form)
    
@login_required
def rate_seller(request, seller_id):
    if request.method == 'POST':
        rating = request.POST.get('rating')
        item_id = request.POST.get('item_id')
        
        # Get seller's UserProfile
        seller = get_object_or_404(UserProfile, user__id=seller_id)
        
        # Update seller's rating
        if rating:
            seller.rating_num += 1
            seller.rating_all += int(rating)
            seller.save()
            messages.success(request, "Thank you for rating!")

        # Redirect to item page or another appropriate page
        return redirect('core:product', slug=Item.objects.get(id=item_id).slug)

    # Redirect if not a POST request
    return redirect('core:home')