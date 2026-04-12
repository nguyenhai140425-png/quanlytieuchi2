from django.urls import path
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView)

from master_admin import views

urlpatterns = [
    path('quanLySuKien/', views.quan_ly_view, name='quanLySuKien'),
    path('xoaSuKien/<int:event_id>/', views.xoa_su_kien_view, name='xoaSuKien'),
    path('quanLyDanhMuc/', views.quan_ly_danh_muc_view, name='quanLyDanhMuc'),
    path('xoaTieuChi/<int:id>/', views.xoa_tieu_chi, name='xoaTieuChi'),
    path('getCategories/', views.get_categories_by_year, name='get_categories_api'),
    path('login/', views.custom_login_view, name='login'),

    path('logout/', views.logout_view, name='logout'),
    # path('signup/', views.signup, name="signup")
]
