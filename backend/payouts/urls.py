from django.urls import path
from . import views

urlpatterns = [
    path("me/", views.me, name="me"),
    path("ledger/", views.ledger_list, name="ledger-list"),
    path("payouts/", views.payout_list_create, name="payout-list-create"),
]
