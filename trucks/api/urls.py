from django.urls import path
from trucks.api import views

urlpatterns = [
    # Public APIs
    path('types/', views.TruckTypeListView.as_view(), name='truck-types'),
    path('search/', views.truck_search, name='truck-search'),
    path('', views.TruckListCreateView.as_view(), name='truck-list-create'),
    path('<int:pk>/', views.TruckDetailView.as_view(), name='truck-detail'),
    path('<int:truck_id>/images/', views.TruckImageListView.as_view(), name='truck-images'),
    
    # Vendor APIs
    path('vendor/my-trucks/', views.VendorTrucksView.as_view(), name='vendor-trucks'),
    path('vendor/drivers/', views.DriverListCreateView.as_view(), name='driver-list-create'),
    path('vendor/drivers/<int:pk>/', views.DriverDetailView.as_view(), name='driver-detail'),
    path('vendor/upload-image/', views.TruckImageUploadView.as_view(), name='upload-truck-image'),
    path('vendor/<int:truck_id>/location/', views.UpdateTruckLocationView.as_view(), name='update-truck-location'),
    path('vendor/<int:truck_id>/location-history/', views.TruckLocationHistoryView.as_view(), name='truck-location-history'),
]
